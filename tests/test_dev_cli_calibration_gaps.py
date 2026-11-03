"""Regression tests for the Yggdrasil IV batch-calibration CLI gaps.

Covers: star-gate pre-flight on `gaia dev calibrate` (Unique vs Suite),
minimal-diff `skill-tree.json` rewrites, and `update-named --origin --notes`
with the operator identity fallback.
"""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gaia_cli.commands.dev.calibrate import meta_calibrate_command

pytestmark = [pytest.mark.integration]

BLOB = "https://github.com/alice/repo/blob/main/skills/s/SKILL.md"


def _registry(tmp_path: Path, slug: str, frontmatter: str) -> str:
    contributor, name = slug.split("/")
    d = tmp_path / "registry" / "named" / contributor
    d.mkdir(parents=True)
    (d / f"{name}.md").write_text(
        f"---\nid: {slug}\ncontributor: {contributor}\nstatus: named\n{frontmatter}---\n## Installation\n",
        encoding="utf-8",
    )
    schema = tmp_path / "registry" / "schema"
    schema.mkdir(parents=True)
    (schema / "meta.json").write_text("{}")
    return str(tmp_path)


def _calibrate(root, slug, level):
    meta_calibrate_command(SimpleNamespace(registry=root, skill_id=slug, level=level, no_build=True))


@pytest.fixture(autouse=True)
def _quiet(monkeypatch):
    monkeypatch.setattr("gaia_cli.commands.dev.calibrate._run_docs_build", lambda *a, **kw: None)
    monkeypatch.setattr("gaia_cli.commands.dev.calibrate.append_skill_event", lambda *a, **kw: None)
    monkeypatch.setattr("gaia_cli.commands.dev.calibrate._get_contributor", lambda: "op")


def test_same_level_recalibration_warns_but_proceeds(tmp_path, capsys):
    root = _registry(tmp_path, "alice/s", f"level: 5★\ngenericSkillRef: g\norigin: true\nlinks:\n  github: {BLOB}\n")
    _calibrate(root, "alice/s", "5★")
    err = capsys.readouterr().err
    assert "Warning" in err and "Re-calibrating at the same level" in err
    assert "level: 5★" in (tmp_path / "registry/named/alice/s.md").read_text(encoding="utf-8")


def test_strict_raise_5star_refused(tmp_path, capsys):
    root = _registry(tmp_path, "alice/s", f"level: 4★\ngenericSkillRef: g\norigin: true\nlinks:\n  github: {BLOB}\n")
    with pytest.raises(SystemExit):
        _calibrate(root, "alice/s", "5★")
    assert "Grade S" in capsys.readouterr().err


def test_unique_raise_to_4star_refused_without_trust(tmp_path):
    root = _registry(tmp_path, "alice/s", f"level: 3★\ngenericSkillRef: g\norigin: true\nlinks:\n  github: {BLOB}\n")
    with pytest.raises(SystemExit):
        _calibrate(root, "alice/s", "4★")
    assert "level: 3★" in (tmp_path / "registry/named/alice/s.md").read_text(encoding="utf-8")


def test_lowering_overranked_skill_is_always_allowed(tmp_path):
    root = _registry(tmp_path, "alice/s", f"level: 5★\ngenericSkillRef: g\norigin: true\nlinks:\n  github: {BLOB}\n")
    _calibrate(root, "alice/s", "3★")
    assert "level: 3★" in (tmp_path / "registry/named/alice/s.md").read_text(encoding="utf-8")


def test_suite_4star_is_judged_by_suite_rules_not_unique_origin(tmp_path, capsys, monkeypatch):
    # Suite branch, no bucket origin: the message must not demand bucket Origin at 4★.
    root = _registry(tmp_path, "alice/suite", "level: 3★\nsuiteComponents:\n  - alice/a\n")
    with pytest.raises(SystemExit):
        _calibrate(root, "alice/suite", "4★")
    err = capsys.readouterr().err
    assert "Suite" in err and "bucket-level Origin" not in err


def test_suite_4star_passes_when_grade_a(tmp_path, monkeypatch):
    root = _registry(tmp_path, "alice/suite", "level: 3★\nsuiteComponents:\n  - alice/a\n")
    monkeypatch.setattr("gaia_cli.trustMagnitude.computeTrustMagnitude", lambda *a, **kw: 150.0)
    monkeypatch.setattr("gaia_cli.trustMagnitude.computeOverallTrustGradeFromSkill", lambda *a, **kw: "A")
    _calibrate(root, "alice/suite", "4★")
    assert "level: 4★" in (tmp_path / "registry/named/alice/suite.md").read_text(encoding="utf-8")


def test_suite_5star_needs_component_origin(tmp_path, monkeypatch, capsys):
    root = _registry(tmp_path, "alice/suite", "level: 4★\nsuiteComponents:\n  - alice/a\n")
    monkeypatch.setattr("gaia_cli.trustMagnitude.computeTrustMagnitude", lambda *a, **kw: 300.0)
    monkeypatch.setattr("gaia_cli.trustMagnitude.computeOverallTrustGradeFromSkill", lambda *a, **kw: "S")
    with pytest.raises(SystemExit):
        _calibrate(root, "alice/suite", "5★")
    assert "Origin on at least one suiteComponent" in capsys.readouterr().err


def test_suite_5star_refused_when_origin_held_by_other_contributor(tmp_path, monkeypatch, capsys):
    root = _registry(tmp_path, "alice/suite", "level: 4★\nsuiteComponents:\n  - bob/a\n")
    other = tmp_path / "registry/named/bob"
    other.mkdir(parents=True)
    (other / "a.md").write_text("---\nid: bob/a\ncontributor: bob\nstatus: named\norigin: true\ngenericSkillRef: ga\nlevel: 2★\n---\n")
    monkeypatch.setattr("gaia_cli.trustMagnitude.computeTrustMagnitude", lambda *a, **kw: 300.0)
    monkeypatch.setattr("gaia_cli.trustMagnitude.computeOverallTrustGradeFromSkill", lambda *a, **kw: "S")
    with pytest.raises(SystemExit):
        _calibrate(root, "alice/suite", "5★")
    assert "proposing contributor" in capsys.readouterr().err


def test_suite_5star_passes_when_proposer_holds_component_origin(tmp_path, monkeypatch):
    root = _registry(tmp_path, "alice/suite", "level: 4★\nsuiteComponents:\n  - alice/a\n")
    own = tmp_path / "registry/named/alice"
    (own / "a.md").write_text("---\nid: alice/a\ncontributor: alice\nstatus: named\norigin: true\ngenericSkillRef: ga\nlevel: 2★\n---\n")
    monkeypatch.setattr("gaia_cli.trustMagnitude.computeTrustMagnitude", lambda *a, **kw: 300.0)
    monkeypatch.setattr("gaia_cli.trustMagnitude.computeOverallTrustGradeFromSkill", lambda *a, **kw: "S")
    _calibrate(root, "alice/suite", "5★")
    assert "level: 5★" in (tmp_path / "registry/named/alice/suite.md").read_text(encoding="utf-8")


def test_6star_raise_only_enforces_grade_s(tmp_path, monkeypatch, capsys):
    root = _registry(tmp_path, "alice/suite", "level: 5★\nsuiteComponents:\n  - alice/a\n")
    monkeypatch.setattr("gaia_cli.trustMagnitude.computeTrustMagnitude", lambda *a, **kw: 100.0)
    monkeypatch.setattr("gaia_cli.trustMagnitude.computeOverallTrustGradeFromSkill", lambda *a, **kw: "A")
    with pytest.raises(SystemExit):
        _calibrate(root, "alice/suite", "6★")
    assert "Grade S" in capsys.readouterr().err


# --- timeline --user minimal diff ------------------------------------------


def test_save_tree_preserves_unicode_indent_and_newline(tmp_path):
    from gaia_cli.timeline import append_skill_tree_event

    tree_dir = tmp_path / "skill-trees" / "alice"
    tree_dir.mkdir(parents=True)
    path = tree_dir / "skill-tree.json"
    original = {"userId": "alice", "unlockedSkills": [], "note": "café ★", "timeline": []}
    path.write_text(json.dumps(original, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    append_skill_tree_event("alice", "x", "note", "hello", registry_path=str(tmp_path))

    text = path.read_text(encoding="utf-8")
    assert "café ★" in text and "\\u" not in text
    assert text.endswith("}\n")
    assert text.splitlines()[1].startswith('  "')
    assert json.loads(text)["timeline"][0]["skillId"] == "x"


def test_save_tree_keeps_escapes_when_file_already_uses_them(tmp_path):
    from gaia_cli.treeManager import save_tree

    tree_dir = tmp_path / "skill-trees" / "carol"
    tree_dir.mkdir(parents=True)
    path = tree_dir / "skill-tree.json"
    path.write_text(json.dumps({"n": "caf\u00e9"}, indent=2) + "\n", encoding="utf-8")
    save_tree("carol", {"n": "caf\u00e9", "m": 1}, str(tmp_path))
    assert "\\u00e9" in path.read_text(encoding="utf-8")
    save_tree("newuser", {"n": "caf\u00e9"}, str(tmp_path))
    assert "caf\u00e9" in (tmp_path / "skill-trees/newuser/skill-tree.json").read_text(encoding="utf-8")


def test_save_tree_keeps_missing_trailing_newline_and_4_indent(tmp_path):
    from gaia_cli.treeManager import save_tree

    tree_dir = tmp_path / "skill-trees" / "bob"
    tree_dir.mkdir(parents=True)
    path = tree_dir / "skill-tree.json"
    path.write_text(json.dumps({"a": {"b": 1}}, indent=4), encoding="utf-8")
    save_tree("bob", {"a": {"b": 2}}, str(tmp_path))
    text = path.read_text(encoding="utf-8")
    assert not text.endswith("\n")
    assert '\n    "a"' in text


# --- update-named --origin (retired) / --notes -----------------------------


def _update_args(root, **kw):
    base = dict(
        registry=root, skill_id="alice/s", origin="true", notes=None, no_build=True, status=None,
        name=None, title=None, catalog_ref=None, generic_ref=None, suite_components=None,
        suite_ref=None, installation_file=None, github_link=None, installable=None,
    )
    base.update(kw)
    return SimpleNamespace(**base)


def test_update_named_origin_is_refused_origin_is_automatic(tmp_path, monkeypatch, capsys):
    """Founder ruling 2026-10-30: Origin is automatic; --origin refuses and writes nothing."""
    import pytest
    from gaia_cli.commands.dev import named

    root = _registry(tmp_path, "alice/s", "level: 2★\ngenericSkillRef: g\ntitle: T\norigin: false\n")
    skill_file = next((tmp_path / "registry" / "named").rglob("*.md"))
    before = skill_file.read_text(encoding="utf-8")
    events = []
    monkeypatch.setattr(named, "append_skill_event", lambda *a, **kw: events.append(a))
    monkeypatch.setattr(named, "_run_docs_build", lambda *a, **kw: None)

    with pytest.raises(SystemExit):
        named.meta_update_named_command(_update_args(root, notes="Most renowned in bucket"))

    assert skill_file.read_text(encoding="utf-8") == before
    assert events == []
    assert "Origin is automatic" in capsys.readouterr().err


def test_update_named_notes_reach_other_timeline_events(tmp_path, monkeypatch):
    from gaia_cli.commands.dev import named

    root = _registry(tmp_path, "alice/s", "level: 2★\ngenericSkillRef: g\ntitle: T\norigin: false\n")
    events = []
    monkeypatch.setattr(named, "append_skill_event", lambda *a, **kw: events.append(a))
    monkeypatch.setattr(named, "_run_docs_build", lambda *a, **kw: None)
    monkeypatch.setattr("gaia_cli.commands.dev.helpers.load_config", lambda: {})
    monkeypatch.setenv("GITHUB_ACTOR", "detected-op")

    named.meta_update_named_command(_update_args(root, origin=None, suite_ref="alice/suite", notes="why"))

    assert events[0][2] == "detected-op"
    assert events[0][3] == "Set suiteRef to alice/suite why"


def _fake_git(email=None, remote="https://github.com/gaia-research/gaia-skill-tree.git"):
    import subprocess

    def run(cmd, **kw):
        out = {"user.email": email, "get-url": remote}.get(cmd[-1] if cmd[-1] != "origin" else "get-url")
        return subprocess.CompletedProcess(cmd, 0 if out else 1, stdout=(out or "") + "\n", stderr="")
    return run


def test_get_contributor_order_config_actor_noreply_unknown(monkeypatch):
    from gaia_cli.commands.dev import helpers

    monkeypatch.setattr(helpers, "load_config", lambda: {"gaiaUser": "cfg"})
    monkeypatch.setenv("GITHUB_ACTOR", "ci-actor")
    assert helpers._get_contributor() == "cfg"

    monkeypatch.setattr(helpers, "load_config", lambda: {})
    assert helpers._get_contributor() == "ci-actor"
    monkeypatch.setenv("GITHUB_ACTOR", "dependabot[bot]")
    assert helpers._get_contributor() == "dependabot[bot]"

    monkeypatch.delenv("GITHUB_ACTOR")
    monkeypatch.setattr(helpers.subprocess, "run", _fake_git(email="123+realdev@users.noreply.github.com"))
    assert helpers._get_contributor() == "realdev"


def test_get_contributor_never_uses_remote_owner(monkeypatch):
    from gaia_cli.commands.dev import helpers

    monkeypatch.setattr(helpers, "load_config", lambda: {})
    monkeypatch.delenv("GITHUB_ACTOR", raising=False)
    monkeypatch.setattr(helpers.subprocess, "run", _fake_git(email="dev@example.com"))
    assert helpers._get_contributor() == "unknown"
