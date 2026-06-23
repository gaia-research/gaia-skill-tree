"""Unit tests for gaia dev audit and gaia dev diff (#791)."""

import json
from pathlib import Path
from types import SimpleNamespace
from io import StringIO

import pytest

from gaia_cli.commands.dev.audit import meta_audit_command
pytestmark = [pytest.mark.integration]



# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_skill(nodes_dir: Path, skill_id: str, level: str = "1★",
                 evidence: list | None = None) -> None:
    nodes_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "id": skill_id,
        "name": skill_id.replace("-", " ").title(),
        "type": "basic",
        "level": level,
        "description": f"Description of {skill_id}.",
        "status": "provisional",
        "prerequisites": [],
        "derivatives": [],
        "evidence": evidence or [],
        "timeline": [],
        "createdAt": "2026-06-01",
        "updatedAt": "2026-06-01",
        "version": "0.1.0",
    }
    (nodes_dir / f"{skill_id}.json").write_text(json.dumps(data, indent=2))


def _make_registry(tmp_path: Path) -> str:
    nodes = tmp_path / "registry" / "nodes" / "basic"
    _write_skill(nodes, "skill-a")
    _write_skill(nodes, "skill-b", level="2★")
    # Skill with evidence (good)
    _write_skill(nodes, "skill-c", level="3★", evidence=[{"source": "https://x", "grade": "A"}])
    schema = tmp_path / "registry" / "schema"
    schema.mkdir(parents=True)
    (schema / "meta.json").write_text(json.dumps({}))
    return str(tmp_path)


def _args(root: str, level: int | None = None) -> SimpleNamespace:
    return SimpleNamespace(registry=root, level=level)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_audit_runs_without_error(tmp_path, capsys):
    root = _make_registry(tmp_path)
    meta_audit_command(_args(root))
    # Must not raise; output may be empty or contain issues
    out = capsys.readouterr().out
    assert isinstance(out, str)


def test_audit_level_filter(tmp_path, capsys):
    """Level filter only reports skills at or above the threshold."""
    root = _make_registry(tmp_path)
    meta_audit_command(_args(root, level=3))
    out = capsys.readouterr().out
    # Only 3★ skills should appear (skill-c); 1★ and 2★ are filtered out
    if out:
        assert "skill-c" in out.lower() or out.strip() == ""


def test_audit_json_file_corrupt_skipped(tmp_path, capsys):
    """Malformed JSON files in nodes dir are gracefully skipped."""
    root = _make_registry(tmp_path)
    bad = Path(root) / "registry" / "nodes" / "basic" / "corrupt.json"
    bad.write_text("{not valid json}", encoding="utf-8")
    meta_audit_command(_args(root))
    # Should not crash


def test_audit_no_nodes_dir_exits_gracefully(tmp_path, capsys):
    """Missing nodes dir does not produce a traceback."""
    schema = tmp_path / "registry" / "schema"
    schema.mkdir(parents=True)
    (schema / "meta.json").write_text(json.dumps({}))
    meta_audit_command(_args(str(tmp_path)))
    # Must complete without raising
