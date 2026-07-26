"""Tests for the user-tree timeline integrity gate (scripts/validate_timelines.py).

The gate proves that every named skill a contributor owns is charted at its
*current* registry rank — i.e. a demotion/promotion applied on the registry node
must also appear on the user tree the profile renders. This is the regression
guard for the silent-demotion bug (e.g. semantic-cache, ruvnet, openai).
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest
pytestmark = [pytest.mark.integration]


REPO = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "validate_timelines", REPO / "scripts" / "validate_timelines.py")
vt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vt)


@pytest.mark.parametrize("raw,expected", [
    ("3★", "3★"), ("3", "3★"), (3, "3★"), ("Level 4★", "4★"),
    (None, ""), ("", ""), ("★", ""),
])
def test_norm_level(raw, expected):
    assert vt._norm(raw) == expected


def test_latest_level_event_picks_most_recent():
    tl = [
        {"skillId": "a/b", "timestamp": "2026-05-15T00:00:00Z", "newValue": "3★"},
        {"skillId": "a/b", "timestamp": "2026-06-02T00:00:00Z", "newValue": "1★"},
        {"skillId": "a/b", "timestamp": "2026-05-20T00:00:00Z", "action": "note"},  # no newValue
        {"skillId": "x/y", "timestamp": "2026-07-01T00:00:00Z", "newValue": "5★"},
    ]
    assert vt._latest_level_event(tl, "a/b") == "1★"
    assert vt._latest_level_event(tl, "missing") is None


def test_registry_levels_loads():
    levels = vt._registry_levels()
    assert levels  # non-empty
    assert all(v.endswith("★") for v in levels.values() if v)


def test_repo_timelines_are_consistent():
    """Every owned named skill's timeline explains its current rank."""
    result = subprocess.run([sys.executable, str(REPO / "scripts" / "validate_timelines.py")],
                            cwd=str(REPO), capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


# ---------------------------------------------------------------------------
# Migration-provenance invariant (#1189) — inline RED/GREEN pure-helper tests
#
# check_migration_provenance() reads the registry named-skill index from
# vt.NAMED_JSON. We point it at a scratch index built inline so the invariant
# is exercised in isolation, independent of live registry data.
# ---------------------------------------------------------------------------

_BATCH = "yggdrasil-ii@2026-07-16"


def _run_provenance(monkeypatch, tmp_path, entries):
    """Point check_migration_provenance at a scratch named-skills.json of `entries`."""
    scratch = tmp_path / "named-skills.json"
    index = {
        "generatedAt": "2026-07-16T00:00:00Z",
        "buckets": {"named": entries},
        "awaitingClassification": [],
    }
    scratch.write_text(json.dumps(index), encoding="utf-8")
    monkeypatch.setattr(vt, "NAMED_JSON", scratch)
    return vt.check_migration_provenance()


def test_provenance_green_paired_demote_and_type_change(monkeypatch, tmp_path):
    """GREEN: a demote paired with a type_change sharing the same batch passes."""
    entries = [{
        "id": "alice/skill",
        "timeline": [
            {"timestamp": "2026-07-16T00:00:00Z", "action": "type_change",
             "migrationBatch": _BATCH},
            {"timestamp": "2026-07-16T00:01:00Z", "action": "demote",
             "migrationBatch": _BATCH, "previousValue": "4★", "newValue": "3★"},
        ],
    }]
    assert _run_provenance(monkeypatch, tmp_path, entries) == []


def test_provenance_red_batched_demote_without_type_change(monkeypatch, tmp_path):
    """RED: a batched demote with no matching type_change is flagged."""
    entries = [{
        "id": "bob/skill",
        "timeline": [
            {"timestamp": "2026-07-16T00:01:00Z", "action": "demote",
             "migrationBatch": _BATCH, "previousValue": "4★", "newValue": "3★"},
        ],
    }]
    violations = _run_provenance(monkeypatch, tmp_path, entries)
    assert len(violations) == 1
    assert "bob/skill" in violations[0]


def test_provenance_red_type_change_different_batch(monkeypatch, tmp_path):
    """RED: a batched demote whose type_change carries a DIFFERENT batch is flagged."""
    entries = [{
        "id": "carol/skill",
        "timeline": [
            {"timestamp": "2026-07-16T00:00:00Z", "action": "type_change",
             "migrationBatch": "yggdrasil-ii@2026-01-01"},
            {"timestamp": "2026-07-16T00:01:00Z", "action": "demote",
             "migrationBatch": _BATCH, "previousValue": "4★", "newValue": "3★"},
        ],
    }]
    violations = _run_provenance(monkeypatch, tmp_path, entries)
    assert len(violations) == 1
    assert "carol/skill" in violations[0]


def test_provenance_control_unbatched_demote_not_flagged(monkeypatch, tmp_path):
    """CONTROL: a demote with no migrationBatch (e.g. Yggdrasil I) is exempt by absence."""
    entries = [{
        "id": "dave/skill",
        "timeline": [
            {"timestamp": "2026-06-01T00:00:00Z", "action": "demote",
             "previousValue": "3★", "newValue": "2★",
             "details": "Level updated from 3★ to 2★ per G7 final rankings calibration."},
        ],
    }]
    assert _run_provenance(monkeypatch, tmp_path, entries) == []
