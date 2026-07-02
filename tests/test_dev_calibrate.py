"""Unit tests for gaia dev calibrate (#791).

Covers meta_calibrate_command happy path, level-validation rejection,
generic-skill rejection, and the Star Bar pre-flight (#789).
"""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from gaia_cli.commands.dev.calibrate import meta_calibrate_command
pytestmark = [pytest.mark.integration]



# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _write_named_skill(named_dir: Path, slug: str = "alice/test-skill", level: str = "2★",
                       github_link: str = "") -> Path:
    contributor, name = slug.split("/", 1)
    skill_dir = named_dir / contributor
    skill_dir.mkdir(parents=True, exist_ok=True)
    path = skill_dir / f"{name}.md"
    links_block = f"\nlinks:\n  github: {github_link}\n" if github_link else ""
    path.write_text(
        f"---\nid: {slug}\nname: Test Skill\ncontributor: {contributor}\n"
        f"origin: true\ngenericSkillRef: test-skill\nstatus: named\nlevel: {level}\n"
        f"description: A test named skill for calibrate tests.{links_block}---\n",
        encoding="utf-8",
    )
    return path


def _make_registry(tmp_path: Path, *, level: str = "2★", github_link: str = "") -> str:
    named_dir = tmp_path / "registry" / "named"
    _write_named_skill(named_dir, level=level, github_link=github_link)
    schema = tmp_path / "registry" / "schema"
    schema.mkdir(parents=True)
    (schema / "meta.json").write_text(json.dumps({}))
    return str(tmp_path)


def _args(registry_root: str, skill_id: str = "alice/test-skill", level: str = "3★",
          **overrides) -> SimpleNamespace:
    base = dict(registry=registry_root, skill_id=skill_id, level=level, no_build=True)
    base.update(overrides)
    return SimpleNamespace(**base)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_calibrate_up(tmp_path, monkeypatch):
    """Calibrating from 2★ to 3★ writes level and appends rank_up event."""
    root = _make_registry(
        tmp_path,
        github_link="https://github.com/alice/repo/blob/main/skills/test-skill/SKILL.md",
    )
    monkeypatch.setattr("gaia_cli.commands.dev.calibrate._get_contributor", lambda: "alice")
    monkeypatch.setattr("gaia_cli.commands.dev.calibrate._run_docs_build", lambda *a, **kw: None)
    monkeypatch.setattr("gaia_cli.commands.dev.calibrate.append_skill_event", lambda *a, **kw: None)

    meta_calibrate_command(_args(root, level="3★"))

    md_path = tmp_path / "registry" / "named" / "alice" / "test-skill.md"
    text = md_path.read_text(encoding="utf-8")
    assert "level: 3★" in text


def test_calibrate_down(tmp_path, monkeypatch):
    """Calibrating from 3★ to 2★ writes level (no Star Bar check on demotion)."""
    root = _make_registry(tmp_path, level="3★")
    monkeypatch.setattr("gaia_cli.commands.dev.calibrate._get_contributor", lambda: "alice")
    monkeypatch.setattr("gaia_cli.commands.dev.calibrate._run_docs_build", lambda *a, **kw: None)
    monkeypatch.setattr("gaia_cli.commands.dev.calibrate.append_skill_event", lambda *a, **kw: None)

    meta_calibrate_command(_args(root, level="2★"))

    md_path = tmp_path / "registry" / "named" / "alice" / "test-skill.md"
    assert "level: 2★" in md_path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Rejection paths
# ---------------------------------------------------------------------------


def test_invalid_level_exits(tmp_path, monkeypatch):
    root = _make_registry(tmp_path)
    monkeypatch.setattr("gaia_cli.commands.dev.calibrate._run_docs_build", lambda *a, **kw: None)
    with pytest.raises(SystemExit) as exc:
        meta_calibrate_command(_args(root, level="7★"))
    assert exc.value.code != 0


def test_generic_skill_rejected(tmp_path, monkeypatch):
    """Calibrating a bare generic skill ID (no /) is rejected."""
    root = _make_registry(tmp_path)
    monkeypatch.setattr("gaia_cli.commands.dev.calibrate._run_docs_build", lambda *a, **kw: None)
    with pytest.raises(SystemExit) as exc:
        meta_calibrate_command(_args(root, skill_id="test-skill", level="2★"))
    assert exc.value.code != 0


def test_missing_named_skill_exits(tmp_path, monkeypatch):
    root = _make_registry(tmp_path)
    monkeypatch.setattr("gaia_cli.commands.dev.calibrate._run_docs_build", lambda *a, **kw: None)
    with pytest.raises(SystemExit) as exc:
        meta_calibrate_command(_args(root, skill_id="alice/nonexistent", level="2★"))
    assert exc.value.code != 0


# ---------------------------------------------------------------------------
# Star Bar pre-flight (#789)
# ---------------------------------------------------------------------------


def test_starbar_rejects_missing_github_link_before_write(tmp_path, monkeypatch, capsys):
    """Calibrating to 3★ without links.github raises SystemExit(1)."""
    root = _make_registry(tmp_path)  # no github_link
    md_path = tmp_path / "registry" / "named" / "alice" / "test-skill.md"
    before = md_path.read_text(encoding="utf-8")
    monkeypatch.setattr("gaia_cli.commands.dev.calibrate._run_docs_build", lambda *a, **kw: None)

    with pytest.raises(SystemExit) as exc:
        meta_calibrate_command(_args(root, level="3★"))

    assert exc.value.code != 0
    assert md_path.read_text(encoding="utf-8") == before
    err = capsys.readouterr().err
    assert "links.github" in err
    assert "gaia dev update-named alice/test-skill --github-link" in err


def test_starbar_rejects_tree_url(tmp_path, monkeypatch, capsys):
    """Calibrating to 3★ with a tree/ URL (not blob/) is rejected."""
    root = _make_registry(
        tmp_path,
        github_link="https://github.com/alice/repo/tree/main/skills/test-skill",
    )
    monkeypatch.setattr("gaia_cli.commands.dev.calibrate._run_docs_build", lambda *a, **kw: None)
    md_path = tmp_path / "registry" / "named" / "alice" / "test-skill.md"
    before = md_path.read_text(encoding="utf-8")

    with pytest.raises(SystemExit) as exc:
        meta_calibrate_command(_args(root, level="4★"))

    assert exc.value.code != 0
    assert md_path.read_text(encoding="utf-8") == before
    err = capsys.readouterr().err
    assert "blob/" in err


def test_starbar_passes_with_blob_url(tmp_path, monkeypatch):
    """Calibrating to 4★ with a valid blob/ URL succeeds."""
    root = _make_registry(
        tmp_path,
        github_link="https://github.com/alice/repo/blob/main/skills/SKILL.md",
    )
    monkeypatch.setattr("gaia_cli.commands.dev.calibrate._get_contributor", lambda: "alice")
    monkeypatch.setattr("gaia_cli.commands.dev.calibrate._run_docs_build", lambda *a, **kw: None)
    monkeypatch.setattr("gaia_cli.commands.dev.calibrate.append_skill_event", lambda *a, **kw: None)

    meta_calibrate_command(_args(root, level="4★"))

    md_path = tmp_path / "registry" / "named" / "alice" / "test-skill.md"
    assert "level: 4★" in md_path.read_text(encoding="utf-8")


def test_starbar_not_triggered_for_2star(tmp_path, monkeypatch):
    """Calibrating to 2★ does not require links.github."""
    root = _make_registry(tmp_path)  # no github_link
    monkeypatch.setattr("gaia_cli.commands.dev.calibrate._get_contributor", lambda: "alice")
    monkeypatch.setattr("gaia_cli.commands.dev.calibrate._run_docs_build", lambda *a, **kw: None)
    monkeypatch.setattr("gaia_cli.commands.dev.calibrate.append_skill_event", lambda *a, **kw: None)

    meta_calibrate_command(_args(root, level="2★"))

    md_path = tmp_path / "registry" / "named" / "alice" / "test-skill.md"
    assert "level: 2★" in md_path.read_text(encoding="utf-8")
