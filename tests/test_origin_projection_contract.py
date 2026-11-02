"""Automatic Origin publication and frozen-write boundaries, using disposable roots."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from gaia_cli.frozen import frozenIds, requireFrozenLocks
from gaia_cli.origin import publicOriginStandings
from scripts.generateNamedIndex import write_index


def entry(sid, ref, level="3★", tm=70.0, grade="B", **extra):
    return {"id": sid, "contributor": sid.split("/")[0], "genericSkillRef": ref,
            "name": sid, "status": "named", "level": level,
            "trustMagnitude": tm, "overallTrustGrade": grade, **extra}


def test_low_star_awakened_origin_is_public_as_redacted_standing_not_a_named_row(tmp_path):
    from scripts.buildApiProjection import build_skills_pages

    buckets = {"shared": [entry("a/tool", "shared"), entry("b/tool", "shared")]}
    awaiting = [entry("private/hermes", "social", "1★", 42.47, "C", status="awakened")]
    path = tmp_path / "registry/named-skills.json"
    write_index(buckets, awaiting, {}, str(path), "2026-10-31")
    index = json.loads(path.read_text())
    standings = index["originStandings"]
    assert {row["id"] for row in standings["shared"]} == {"a/tool", "b/tool"}
    assert standings["social"] == [{"origin": True, "level": "1★", "status": "awakened", "redacted": True}]
    assert "private/hermes" not in json.dumps(standings)
    assert index["awaitingClassification"][0]["status"] == "awakened"
    assert index["awaitingClassification"][0]["level"] == "1★"
    assert index["awaitingClassification"][0]["origin"] is True
    assert "social" not in index["buckets"]

    build_skills_pages(tmp_path / "api", buckets["shared"], standings)
    public = json.loads((tmp_path / "api/skills/index.json").read_text())
    assert public["originStandings"] == standings
    assert public["totalSkills"] == 2
    assert "private/hermes" not in json.dumps(public)


def test_ledger_and_leaderboard_preserve_same_origin_snapshot(tmp_path, monkeypatch):
    stdout = sys.stdout
    import scripts.generateLeaderboardData as ledger
    assert sys.stdout is stdout  # inspector import must not close pytest/the caller\'s stream
    from scripts.buildApiProjection import build_leaderboard

    named = {"buckets": {}, "awaitingClassification": [
        entry("private/hermes", "social", "1★", 42.47, "C", status="awakened", origin=True)
    ]}
    named_path = tmp_path / "registry/named-skills.json"
    named_path.parent.mkdir(parents=True)
    named_path.write_text(json.dumps(named))
    output = tmp_path / "ledger.json"
    monkeypatch.setattr(ledger, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(ledger, "NODES_DIR", tmp_path / "registry/nodes")
    monkeypatch.setattr(ledger, "NAMED_DIR", tmp_path / "registry/named")
    monkeypatch.setattr(ledger, "DEFAULT_OUT", tmp_path / "docs/graph/ledger/data.json")
    monkeypatch.setattr(ledger, "buildRows", lambda: [])
    monkeypatch.setattr(ledger, "readGaiaVersion", lambda: "8.29.1")
    monkeypatch.setattr(sys, "argv", ["generateLeaderboardData.py", "--out", str(output)])
    assert ledger.main() == 0
    expected = publicOriginStandings(named["buckets"], named["awaitingClassification"])
    data = json.loads(output.read_text())
    assert data["originStandings"] == expected
    assert data["rows"] == []  # no invented named row/rank to expose the holder
    build_leaderboard(tmp_path / "api", output)
    api = json.loads((tmp_path / "api/leaderboard.json").read_text())
    assert api["originStandings"] == expected
    assert api["rows"] == []
    assert "private/hermes" not in json.dumps(api)


def test_add_named_extra_fields_rejects_manual_origin_injection(tmp_path):
    from gaia_cli.commands.dev.helpers import _run_dev_preflights, preflightAddCommand

    (tmp_path / "registry/nodes/basic").mkdir(parents=True)
    (tmp_path / "registry/named").mkdir(parents=True)
    (tmp_path / "registry/nodes/basic/demo-skill.json").write_text(
        json.dumps({"id": "demo-skill", "name": "Demo Skill", "type": "basic", "status": "provisional", "description": "Valid generic skill description."}),
        encoding="utf-8",
    )
    args = SimpleNamespace(
        registry=str(tmp_path),
        name="Demo Tool",
        id="demo-tool",
        named=True,
        contributor="alice",
        description="Valid named skill description.",
        level="2★",
        status="named",
        title="The Demo Tool",
        generic_ref="demo-skill",
        extra_fields=json.dumps({"origin": True}),
    )
    with pytest.raises(SystemExit):
        _run_dev_preflights([lambda: preflightAddCommand(args)])


def test_sweep_checks_public_derived_holders_not_legacy_source_flags():
    from scripts.run_meta_sweep import originProjectionFindings

    projection = {"buckets": {"shared": [
        entry("a/tool", "shared", origin=True), entry("b/tool", "shared", origin=True),
    ]}, "awaitingClassification": [entry("private/hermes", "social", "1★", status="awakened", origin=True)]}
    holders = {"shared": {"a/tool", "b/tool"}, "social": {"private/hermes"}}
    assert originProjectionFindings(projection, holders) == []
    projection["buckets"]["shared"][1]["origin"] = False
    findings = originProjectionFindings(projection, holders)
    assert len(findings) == 1 and findings[0]["target"] == "shared"
    assert "preserve historical source attribution" in findings[0]["suggestedAction"]


def write_named(root, meta):
    path = root / "registry/named" / (meta["id"] + ".md")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("---\n" + yaml.safe_dump(meta, allow_unicode=True, sort_keys=False) + "---\nHistorical body.\n")
    return path


def test_uncached_nested_suite_member_freeze_fails_before_any_write(tmp_path, capsys):
    from gaia_cli.commands.dev.freeze import freeze_command

    suite = entry("a/suite", "suite", suiteComponents=["a/nested"])
    nested = entry("a/nested", "nested", suiteComponents=["a/member"])
    member = entry("a/member", "member")
    member.pop("trustMagnitude")
    paths = [write_named(tmp_path, meta) for meta in (suite, nested, member)]
    before = {path: path.read_bytes() for path in paths}
    with pytest.raises(SystemExit) as exc:
        freeze_command(SimpleNamespace(registry=str(tmp_path), skill_id="a/suite",
                                       reason="approved upstream freeze", dry_run=False, user="founder"))
    assert exc.value.code != 0
    assert "a/member" in capsys.readouterr().err
    assert {path: path.read_bytes() for path in paths} == before


def test_nested_suite_freeze_locks_all_contenders_without_mutating_components(tmp_path):
    from gaia_cli.commands.dev.freeze import freeze_command
    from gaia_cli.commands.dev.helpers import _parse_md, _run_dev_preflights, preflightNamedSkillMutable

    metas = [entry("a/suite", "suite", suiteComponents=["a/nested"]),
             entry("a/nested", "nested", suiteComponents=["a/member"]),
             entry("a/member", "member")]
    paths = [write_named(tmp_path, meta) for meta in metas]
    before = {path: path.read_bytes() for path in paths[1:]}
    freeze_command(SimpleNamespace(registry=str(tmp_path), skill_id="a/suite",
                                   reason="approved upstream freeze", dry_run=False, user="founder"))
    frozen = [_parse_md(path)[0] for path in paths]
    assert frozenIds(frozen) == {"a/suite", "a/nested", "a/member"}
    requireFrozenLocks(frozen)
    assert {path: path.read_bytes() for path in before} == before
    all_before = {path: path.read_bytes() for path in paths}
    with pytest.raises(SystemExit):
        _run_dev_preflights([lambda: preflightNamedSkillMutable(str(tmp_path), "a/member")])
    assert {path: path.read_bytes() for path in paths} == all_before
