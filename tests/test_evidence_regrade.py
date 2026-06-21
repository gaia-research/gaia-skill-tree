"""Tests for ``gaia dev evidence --index`` in-place re-grade mode.

PR-2 shipped ``gaia dev evidence`` as append-only, which made the class→grade
backfill (PR-3) impossible: re-running it over existing entries duplicated them
and could not preserve the deprecated ``class``. ``--index`` re-grades the entry
at a given position in place. These tests lock in that behaviour and the
``evidence_graded`` audit event (which also had to be added to the schema enum).
"""

import json
import os
from types import SimpleNamespace

import pytest

from gaia_cli.commands.dev import meta_evidence_command


def _build_registry(tmp_path, evidence):
    """Create a minimal registry with one node and a meta.json, return its root."""
    nodes = tmp_path / "registry" / "nodes" / "extra"
    nodes.mkdir(parents=True)
    schema = tmp_path / "registry" / "schema"
    schema.mkdir(parents=True)
    (schema / "meta.json").write_text(
        json.dumps(
            {
                "evidence": {
                    "gradeThresholds": {"S": 250, "A": 100, "B": 50, "C": 20},
                    "types": ["arxiv", "repo", "github-stars"],
                }
            }
        )
    )
    node = {
        "id": "demo-skill",
        "name": "Demo Skill",
        "type": "extra",
        "description": "A demo skill for evidence re-grade tests.",
        "evidence": evidence,
        "timeline": [],
    }
    (nodes / "demo-skill.json").write_text(json.dumps(node, indent=2))
    return str(tmp_path)


def _load_node(registry_root):
    path = os.path.join(
        registry_root, "registry", "nodes", "extra", "demo-skill.json"
    )
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _args(registry_root, **overrides):
    base = dict(
        registry=registry_root,
        skill_id="demo-skill",
        source="https://example.com/evidence",
        index=None,
        evidence_type=None,
        trust=None,
        evidence_class=None,
        evaluator=None,
        date=None,
        notes=None,
        no_build=True,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.fixture(autouse=True)
def _fixed_contributor(monkeypatch):
    monkeypatch.setattr(
        "gaia_cli.commands.dev._get_contributor", lambda: "tester"
    )


def test_append_mode_unchanged(tmp_path):
    """Without --index a new entry is appended (legacy behaviour)."""
    root = _build_registry(tmp_path, [{"source": "https://a", "class": "A"}])
    meta_evidence_command(
        _args(root, source="https://b", evidence_type="repo", trust=110)
    )
    ev = _load_node(root)["evidence"]
    assert len(ev) == 2
    assert ev[1]["type"] == "repo" and ev[1]["grade"] == "A"
    assert ev[1]["trustNumber"] == 110


def test_index_regrades_in_place_and_keeps_class(tmp_path):
    """--index updates the existing entry; count is stable and class survives."""
    root = _build_registry(
        tmp_path,
        [{"source": "https://a", "class": "A", "evaluator": "orig", "date": "2025-01-01"}],
    )
    meta_evidence_command(
        _args(root, index=0, evidence_type="arxiv", trust=110)
    )
    node = _load_node(root)
    ev = node["evidence"]
    assert len(ev) == 1  # no duplicate
    entry = ev[0]
    assert entry["type"] == "arxiv"
    assert entry["grade"] == "A"
    assert entry["trustNumber"] == 110
    assert entry["class"] == "A"  # deprecated field preserved
    assert entry["evaluator"] == "orig"  # untouched fields preserved
    assert entry["date"] == "2025-01-01"
    # audit trail
    assert node["timeline"][-1]["action"] == "evidence_graded"


def test_index_ungraded_drops_grade(tmp_path):
    """A trust number below the floor yields no grade but keeps trustNumber."""
    root = _build_registry(
        tmp_path, [{"source": "https://a", "class": "C", "grade": "B"}]
    )
    meta_evidence_command(_args(root, index=0, evidence_type="repo", trust=10))
    entry = _load_node(root)["evidence"][0]
    assert entry["trustNumber"] == 10
    assert "grade" not in entry  # stale grade cleared
    assert entry["class"] == "C"


def test_index_out_of_range_exits(tmp_path):
    root = _build_registry(tmp_path, [{"source": "https://a", "class": "A"}])
    with pytest.raises(SystemExit):
        meta_evidence_command(_args(root, index=5, trust=80))


def test_index_requires_update_field(tmp_path):
    """--index with nothing to set is rejected rather than a silent no-op."""
    root = _build_registry(tmp_path, [{"source": "https://a", "class": "A"}])
    with pytest.raises(SystemExit):
        meta_evidence_command(_args(root, index=0))


def test_source_started_at_appended(tmp_path):
    """`gaia dev evidence ... --source-started-at YYYY-MM-DD` writes sourceStartedAt."""
    root = _build_registry(tmp_path, [])
    meta_evidence_command(
        _args(
            root,
            source="https://example.com/evidence",
            evidence_type="repo",
            trust=80,
            source_started_at="2024-01-15",
        )
    )
    ev = _load_node(root)["evidence"]
    assert len(ev) == 1
    assert ev[0]["sourceStartedAt"] == "2024-01-15"


def test_source_started_at_in_place_update(tmp_path):
    """--index can also patch sourceStartedAt on an existing entry."""
    root = _build_registry(
        tmp_path,
        [{"source": "https://a", "type": "repo", "trustNumber": 80, "grade": "A"}],
    )
    meta_evidence_command(
        _args(root, index=0, source_started_at="2023-06-01")
    )
    entry = _load_node(root)["evidence"][0]
    assert entry["sourceStartedAt"] == "2023-06-01"
    # untouched fields preserved
    assert entry["trustNumber"] == 80


def test_source_started_at_invalid_iso_exits(tmp_path):
    """Bad ISO date is rejected loudly (not silently coerced)."""
    root = _build_registry(tmp_path, [])
    with pytest.raises(SystemExit):
        meta_evidence_command(
            _args(
                root,
                source="https://example.com/evidence",
                evidence_type="repo",
                trust=80,
                source_started_at="not-a-date",
            )
        )
