"""Exercise canonical persistence consumers without changing real registry data."""
from pathlib import Path
from types import SimpleNamespace
import hashlib

import pytest
import yaml

from gaia_cli.commands.dev.sync_upstream import _validate_proposed_named_record

ROOT = Path(__file__).resolve().parents[1]


def test_watcher_scope_validates_without_normalization():
    from scripts.upstream_watcher.finder import iter_suite_skills
    paths = list(iter_suite_skills(ROOT / "registry/named"))
    assert len(paths) == 24  # 23 original campaign suites + t3dotgg/tstack from pinned main 80fb535bb.
    for path, _ in paths:
        before = path.read_bytes()
        _validate_proposed_named_record(str(ROOT), before.decode())
        assert path.read_bytes() == before


@pytest.fixture(params=[
    ("google-deepmind/workflow-skill-creator", "google-deepmind/science-skills"),
    ("ruvnet/v3-ddd-architecture", "ruvnet/ruflo"),
])
def legacySyncFixture(request, tmp_path):
    skillId, repo = request.param
    source = ROOT / "registry/named" / (skillId + ".md")
    path = tmp_path / "registry/named" / (skillId + ".md")
    path.parent.mkdir(parents=True)
    path.write_bytes(source.read_bytes())
    schema = tmp_path / "registry/schema/namedSkill.schema.json"
    schema.parent.mkdir(parents=True)
    schema.write_bytes((ROOT / "registry/schema/namedSkill.schema.json").read_bytes())
    tag = "v0.0.0-contract-probe"  # Synthetic format probe, not a release claim.
    args = SimpleNamespace(registry=str(tmp_path), skill_id=skillId, repo=repo, tag=tag,
                           source_url=f"https://github.com/{repo}/releases/tag/{tag}",
                           released_at="2026-11-01T00:00:00Z", user="mbtiongson1", dry_run=True)
    return path, args


def test_ordinary_sync_retains_legacy_bytes(legacySyncFixture, capsys):
    from gaia_cli.commands.dev.sync_upstream import sync_upstream_command
    path, args = legacySyncFixture
    before = path.read_bytes()
    sync_upstream_command(args)
    assert "DRY RUN" in capsys.readouterr().out
    assert path.read_bytes() == before


@pytest.mark.parametrize("corruption", [
    "unknown-root", "unknown-evidence", "negative-metric", "invalid-role",
    "legacy-author", "legacy-date", "invalid-actor", "invalid-ref", "invalid-release-date",
])
def test_legacy_compatibility_does_not_bypass_prospective_checks(legacySyncFixture, corruption):
    from gaia_cli.commands.dev.sync_upstream import sync_upstream_command
    path, args = legacySyncFixture
    meta = yaml.safe_load(path.read_text().split("---", 2)[1])
    if corruption == "unknown-root":
        meta["unknownRoot"] = True
    elif corruption == "unknown-evidence":
        meta["evidence"][0]["role"] = "variant"  # Root compatibility is not evidence widening.
    elif corruption == "negative-metric":
        meta["evidence"][0]["commits"] = -1
    elif corruption == "invalid-role":
        meta["role"] = "champion"
    elif corruption in ("legacy-author", "legacy-date"):
        event = dict(action="demote", timestamp="2026-09-05T00:00:00Z", author="example",
                     notes="Historical explanation.", previousValue="4★", newValue="1★")
        event["author" if corruption == "legacy-author" else "timestamp"] = "bad user"
        meta["timeline"].append(event)
    elif corruption == "invalid-actor":
        args.user = "arbitrary[bot]"
    elif corruption == "invalid-ref":
        args.tag = "v1..2"
        args.source_url = f"https://github.com/{args.repo}/releases/tag/{args.tag}"
    else:
        args.released_at = "yesterday"
    path.write_text("---\n" + yaml.safe_dump(meta, allow_unicode=True) + "---\nFixture body.\n")
    before = path.read_bytes()
    with pytest.raises(SystemExit):
        sync_upstream_command(args)
    assert path.read_bytes() == before


def test_update_named_emitted_note_validates(tmp_path, monkeypatch):
    from gaia_cli.commands.dev.named import meta_update_named_command
    from gaia_cli.timeline import append_skill_event
    import gaia_cli.commands.dev.named as named

    path = tmp_path / "registry/named/example/tool.md"
    path.parent.mkdir(parents=True)
    data = dict(id="example/tool", name="Tool", contributor="example", origin=False,
                genericSkillRef="tool", status="named", title="The Tool", level="2★",
                description="A concrete implementation.", createdAt="2026-01-01", updatedAt="2026-01-01")
    path.write_text("---\n" + yaml.safe_dump(data, allow_unicode=True) + "---\nBody.\n")
    schema = tmp_path / "registry/schema/namedSkill.schema.json"
    schema.parent.mkdir(parents=True)
    schema.write_bytes((ROOT / "registry/schema/namedSkill.schema.json").read_bytes())
    monkeypatch.setattr(named, "_get_contributor", lambda: "github-actions[bot]")
    # Named writer uses the real timeline persistence helper, not a mock log.
    monkeypatch.setattr(named, "append_skill_event", append_skill_event)
    args = SimpleNamespace(registry=str(tmp_path), skill_id="example/tool", status=None,
                           title=None, catalog_ref=None, generic_ref=None, suite_components=None,
                           suite_ref=None, installation_file=None, origin=None, installable=None,
                           github_link="https://github.com/example/tool/blob/main/SKILL.md",
                           no_build=True, notes="contract probe")
    meta_update_named_command(args)
    _validate_proposed_named_record(str(tmp_path), path.read_text())
    meta = yaml.safe_load(path.read_text().split("---", 2)[1])
    assert meta["timeline"][-1]["action"] == "note"
    assert meta["timeline"][-1]["contributor"] == "github-actions[bot]"


def test_real_frozen_suite_still_refused_without_writes(capsys):
    from gaia_cli.commands.dev.sync_upstream import sync_upstream_command
    path = ROOT / "registry/named/mattpocock/personal.md"
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    args = SimpleNamespace(registry=str(ROOT), skill_id="mattpocock/personal", repo=None,
                           tag="v9.0.0", source_url="https://github.com/mattpocock/skills/releases/tag/v9.0.0",
                           released_at="2026-01-01T00:00:00Z", user="mbtiongson1", dry_run=True)
    with pytest.raises(SystemExit):
        sync_upstream_command(args)
    output = capsys.readouterr()
    assert "frozen" in (output.out + output.err).lower()
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
