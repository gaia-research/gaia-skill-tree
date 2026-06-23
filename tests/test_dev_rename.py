"""Unit tests for gaia dev rename (#791)."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gaia_cli.commands.dev.rename import meta_rename_command
pytestmark = [pytest.mark.integration]



# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_skill(nodes_dir: Path, skill_id: str) -> None:
    nodes_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "id": skill_id,
        "name": skill_id.replace("-", " ").title(),
        "type": "basic",
        "level": "1★",
        "description": f"Description of {skill_id}.",
        "status": "provisional",
        "prerequisites": [],
        "derivatives": [],
        "evidence": [],
        "timeline": [],
        "createdAt": "2026-06-01",
        "updatedAt": "2026-06-01",
        "version": "0.1.0",
    }
    (nodes_dir / f"{skill_id}.json").write_text(json.dumps(data, indent=2))


def _make_registry(tmp_path: Path) -> str:
    nodes = tmp_path / "registry" / "nodes" / "basic"
    _write_skill(nodes, "skill-old")
    _write_skill(nodes, "skill-existing")
    schema = tmp_path / "registry" / "schema"
    schema.mkdir(parents=True)
    (schema / "meta.json").write_text(json.dumps({}))
    return str(tmp_path)


def _args(root: str, old_id: str = "skill-old", new_id: str = "skill-new",
          **kw) -> SimpleNamespace:
    base = dict(registry=root, old_id=old_id, new_id=new_id, no_build=True)
    base.update(kw)
    return SimpleNamespace(**base)


@pytest.fixture(autouse=True)
def _patches(monkeypatch):
    monkeypatch.setattr("gaia_cli.commands.dev.rename._get_contributor", lambda: "tester")
    monkeypatch.setattr("gaia_cli.commands.dev.rename._run_docs_build", lambda *a, **kw: None)
    monkeypatch.setattr("gaia_cli.commands.dev.rename.append_skill_event", lambda *a, **kw: None)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_rename_creates_new_file(tmp_path):
    root = _make_registry(tmp_path)
    meta_rename_command(_args(root))
    new_file = Path(root) / "registry" / "nodes" / "basic" / "skill-new.json"
    assert new_file.exists()
    with open(new_file, encoding="utf-8") as f:
        data = json.load(f)
    assert data["id"] == "skill-new"


def test_rename_removes_old_file(tmp_path):
    root = _make_registry(tmp_path)
    meta_rename_command(_args(root))
    old_file = Path(root) / "registry" / "nodes" / "basic" / "skill-old.json"
    assert not old_file.exists()


# ---------------------------------------------------------------------------
# Rejection paths
# ---------------------------------------------------------------------------


def test_rename_missing_old_id_exits(tmp_path):
    root = _make_registry(tmp_path)
    with pytest.raises(SystemExit) as exc:
        meta_rename_command(_args(root, old_id="does-not-exist"))
    assert exc.value.code != 0


def test_rename_to_existing_id_exits(tmp_path):
    root = _make_registry(tmp_path)
    with pytest.raises(SystemExit) as exc:
        meta_rename_command(_args(root, new_id="skill-existing"))
    assert exc.value.code != 0
