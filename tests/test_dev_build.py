"""Unit tests for gaia dev build, gaia dev add, gaia dev rm (#791)."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gaia_cli.commands.dev.build import (
    meta_build_command,
    meta_add_command,
    meta_remove_command,
)
pytestmark = [pytest.mark.integration]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_registry(tmp_path: Path) -> str:
    nodes = tmp_path / "registry" / "nodes" / "basic"
    nodes.mkdir(parents=True)
    schema = tmp_path / "registry" / "schema"
    schema.mkdir(parents=True)
    (schema / "meta.json").write_text(json.dumps({}))
    node = {
        "id": "existing-skill",
        "name": "Existing Skill",
        "type": "basic",
        "level": "1★",
        "description": "An existing skill for build tests.",
        "status": "provisional",
        "prerequisites": [],
        "derivatives": [],
        "evidence": [],
        "timeline": [],
        "createdAt": "2026-06-01",
        "updatedAt": "2026-06-01",
        "version": "0.1.0",
    }
    (nodes / "existing-skill.json").write_text(json.dumps(node, indent=2))
    return str(tmp_path)


def _add_args(root: str, name: str = "New Skill",
              description: str = "A brand new skill description here.",
              **kw) -> SimpleNamespace:
    base = dict(
        registry=root,
        name=name,
        id=None,
        type="basic",
        description=description,
        named=False,
        contributor="gaiabot",
        generic_ref=None,
        status=None,
        title=None,
        level=None,
        extra_fields=None,
        no_build=True,
    )
    base.update(kw)
    return SimpleNamespace(**base)


def _rm_args(root: str, skill_id: str = "existing-skill", **kw) -> SimpleNamespace:
    base = dict(registry=root, skill_id=skill_id, yes=True, no_build=True)
    base.update(kw)
    return SimpleNamespace(**base)


@pytest.fixture(autouse=True)
def _patches(monkeypatch):
    monkeypatch.setattr("gaia_cli.commands.dev.build._get_contributor", lambda: "tester")
    monkeypatch.setattr("gaia_cli.commands.dev.build._run_docs_build", lambda *a, **kw: None)
    monkeypatch.setattr("gaia_cli.commands.dev.build.append_skill_event", lambda *a, **kw: None)


# ---------------------------------------------------------------------------
# meta_build_command
# ---------------------------------------------------------------------------


def test_build_calls_docs_rebuild(tmp_path, monkeypatch, capsys):
    root = _make_registry(tmp_path)
    called = []
    monkeypatch.setattr("gaia_cli.commands.dev.build._run_docs_build", lambda *a, **kw: called.append(a))
    meta_build_command(SimpleNamespace(registry=root))
    assert len(called) == 1


# ---------------------------------------------------------------------------
# meta_add_command
# ---------------------------------------------------------------------------


def test_add_creates_skill_file(tmp_path):
    root = _make_registry(tmp_path)
    meta_add_command(_add_args(root))
    new_file = Path(root) / "registry" / "nodes" / "basic" / "new-skill.json"
    assert new_file.exists()
    data = json.loads(new_file.read_text(encoding="utf-8"))
    assert data["name"] == "New Skill"


def test_add_short_description_exits(tmp_path):
    root = _make_registry(tmp_path)
    with pytest.raises(SystemExit) as exc:
        meta_add_command(_add_args(root, description="too short"))
    assert exc.value.code != 0


def test_add_writes_timeline_add_event(tmp_path, monkeypatch):
    """add command calls append_skill_event with 'add' action."""
    root = _make_registry(tmp_path)
    events = []
    monkeypatch.setattr(
        "gaia_cli.commands.dev.build.append_skill_event",
        lambda *a, **kw: events.append(a),
    )
    meta_add_command(_add_args(root))
    assert any("add" in str(ev) for ev in events)


def test_add_explicit_id(tmp_path):
    root = _make_registry(tmp_path)
    meta_add_command(_add_args(root, id="custom-id"))
    assert (Path(root) / "registry" / "nodes" / "basic" / "custom-id.json").exists()


# ---------------------------------------------------------------------------
# meta_remove_command
# ---------------------------------------------------------------------------


def test_remove_deletes_skill_file(tmp_path):
    root = _make_registry(tmp_path)
    meta_remove_command(_rm_args(root))
    assert not (Path(root) / "registry" / "nodes" / "basic" / "existing-skill.json").exists()


def test_remove_missing_skill_exits(tmp_path):
    root = _make_registry(tmp_path)
    with pytest.raises(SystemExit) as exc:
        meta_remove_command(_rm_args(root, skill_id="nonexistent"))
    assert exc.value.code != 0
