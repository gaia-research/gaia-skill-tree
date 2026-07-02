"""Unit tests for gaia dev merge and gaia dev split (#791)."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from gaia_cli.commands.dev.merge import meta_merge_command, meta_split_command
pytestmark = [pytest.mark.integration]



# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_skill(nodes_dir: Path, skill_id: str, **extra) -> None:
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
    data.update(extra)
    (nodes_dir / f"{skill_id}.json").write_text(json.dumps(data, indent=2))


def _make_registry(tmp_path: Path) -> str:
    nodes = tmp_path / "registry" / "nodes" / "basic"
    _write_skill(nodes, "skill-a")
    _write_skill(nodes, "skill-b")
    _write_skill(nodes, "skill-c")
    schema = tmp_path / "registry" / "schema"
    schema.mkdir(parents=True)
    (schema / "meta.json").write_text(json.dumps({}))
    return str(tmp_path)


def _load(root: str, skill_id: str) -> dict:
    p = Path(root) / "registry" / "nodes" / "basic" / f"{skill_id}.json"
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _merge_args(root: str, target: str, sources: list, **kw) -> SimpleNamespace:
    base = dict(registry=root, target=target, sources=sources, yes=True, named=False, no_build=True)
    base.update(kw)
    return SimpleNamespace(**base)


def _split_args(root: str, source: str, targets: list, **kw) -> SimpleNamespace:
    base = dict(registry=root, source=source, targets=targets, yes=True, no_build=True)
    base.update(kw)
    return SimpleNamespace(**base)


@pytest.fixture(autouse=True)
def _patches(monkeypatch):
    monkeypatch.setattr("gaia_cli.commands.dev.merge._get_contributor", lambda: "tester")
    monkeypatch.setattr("gaia_cli.commands.dev.merge._run_docs_build", lambda *a, **kw: None)
    monkeypatch.setattr("gaia_cli.commands.dev.merge.append_skill_event", lambda *a, **kw: None)


# ---------------------------------------------------------------------------
# Merge — happy path
# ---------------------------------------------------------------------------


def test_merge_deletes_source(tmp_path):
    root = _make_registry(tmp_path)
    meta_merge_command(_merge_args(root, "skill-a", ["skill-b"]))
    assert not (Path(root) / "registry" / "nodes" / "basic" / "skill-b.json").exists()
    assert (Path(root) / "registry" / "nodes" / "basic" / "skill-a.json").exists()


def test_merge_records_timeline_event(tmp_path):
    root = _make_registry(tmp_path)
    # After merge, the target file should still be valid JSON with the expected id.
    meta_merge_command(_merge_args(root, "skill-a", ["skill-b"]))
    data = _load(root, "skill-a")
    assert data["id"] == "skill-a"


# ---------------------------------------------------------------------------
# Merge — rejection paths
# ---------------------------------------------------------------------------


def test_merge_target_equals_source_exits(tmp_path):
    root = _make_registry(tmp_path)
    with pytest.raises(SystemExit) as exc:
        meta_merge_command(_merge_args(root, "skill-a", ["skill-a"]))
    assert exc.value.code != 0


def test_merge_missing_target_exits(tmp_path):
    root = _make_registry(tmp_path)
    with pytest.raises(SystemExit) as exc:
        meta_merge_command(_merge_args(root, "nonexistent", ["skill-a"]))
    assert exc.value.code != 0


def test_merge_missing_source_exits_before_write(tmp_path, capsys):
    root = _make_registry(tmp_path)
    target_file = Path(root) / "registry" / "nodes" / "basic" / "skill-a.json"
    before = target_file.read_text(encoding="utf-8")

    with pytest.raises(SystemExit) as exc:
        meta_merge_command(_merge_args(root, "skill-a", ["nonexistent"]))

    assert exc.value.code != 0
    assert target_file.read_text(encoding="utf-8") == before
    assert (Path(root) / "registry" / "nodes" / "basic" / "skill-b.json").exists()
    err = capsys.readouterr().err
    assert "Source skill 'nonexistent' does not exist" in err


def test_merge_duplicate_sources_exit_before_write(tmp_path, capsys):
    root = _make_registry(tmp_path)
    target_file = Path(root) / "registry" / "nodes" / "basic" / "skill-a.json"
    before = target_file.read_text(encoding="utf-8")

    with pytest.raises(SystemExit) as exc:
        meta_merge_command(_merge_args(root, "skill-a", ["skill-b", "skill-b"]))

    assert exc.value.code != 0
    assert target_file.read_text(encoding="utf-8") == before
    assert (Path(root) / "registry" / "nodes" / "basic" / "skill-b.json").exists()
    err = capsys.readouterr().err
    assert "Duplicate source IDs" in err


# ---------------------------------------------------------------------------
# Split — happy path
# ---------------------------------------------------------------------------


def test_split_creates_targets(tmp_path):
    root = _make_registry(tmp_path)
    meta_split_command(_split_args(root, "skill-a", ["skill-d", "skill-e"]))
    assert (Path(root) / "registry" / "nodes" / "basic" / "skill-d.json").exists()
    assert (Path(root) / "registry" / "nodes" / "basic" / "skill-e.json").exists()


def test_split_removes_source(tmp_path):
    root = _make_registry(tmp_path)
    meta_split_command(_split_args(root, "skill-a", ["skill-d", "skill-e"]))
    assert not (Path(root) / "registry" / "nodes" / "basic" / "skill-a.json").exists()


# ---------------------------------------------------------------------------
# Split — rejection paths
# ---------------------------------------------------------------------------


def test_split_missing_source_exits(tmp_path):
    root = _make_registry(tmp_path)
    with pytest.raises(SystemExit) as exc:
        meta_split_command(_split_args(root, "nonexistent", ["skill-d"]))
    assert exc.value.code != 0


def test_split_duplicate_targets_exit_before_write(tmp_path, capsys):
    root = _make_registry(tmp_path)
    source_file = Path(root) / "registry" / "nodes" / "basic" / "skill-a.json"
    before = source_file.read_text(encoding="utf-8")

    with pytest.raises(SystemExit) as exc:
        meta_split_command(_split_args(root, "skill-a", ["skill-d", "skill-d"]))

    assert exc.value.code != 0
    assert source_file.exists()
    assert source_file.read_text(encoding="utf-8") == before
    assert not (Path(root) / "registry" / "nodes" / "basic" / "skill-d.json").exists()
    err = capsys.readouterr().err
    assert "Duplicate split target IDs" in err


def test_split_source_as_target_exits_before_write(tmp_path, capsys):
    root = _make_registry(tmp_path)
    source_file = Path(root) / "registry" / "nodes" / "basic" / "skill-a.json"
    before = source_file.read_text(encoding="utf-8")

    with pytest.raises(SystemExit) as exc:
        meta_split_command(_split_args(root, "skill-a", ["skill-a", "skill-d"]))

    assert exc.value.code != 0
    assert source_file.read_text(encoding="utf-8") == before
    err = capsys.readouterr().err
    assert "cannot also be a target" in err


def test_split_existing_target_exits_before_write(tmp_path, capsys):
    root = _make_registry(tmp_path)
    source_file = Path(root) / "registry" / "nodes" / "basic" / "skill-a.json"
    before = source_file.read_text(encoding="utf-8")

    with pytest.raises(SystemExit) as exc:
        meta_split_command(_split_args(root, "skill-a", ["skill-b", "skill-d"]))

    assert exc.value.code != 0
    assert source_file.read_text(encoding="utf-8") == before
    assert not (Path(root) / "registry" / "nodes" / "basic" / "skill-d.json").exists()
    err = capsys.readouterr().err
    assert "already exists" in err
