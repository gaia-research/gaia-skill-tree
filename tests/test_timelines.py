"""Tests for the user-tree timeline integrity gate (scripts/validate_timelines.py).

The gate proves that every named skill a contributor owns is charted at its
*current* registry rank — i.e. a demotion/promotion applied on the registry node
must also appear on the user tree the profile renders. This is the regression
guard for the silent-demotion bug (e.g. semantic-cache, ruvnet, openai).
"""

from __future__ import annotations

import importlib.util
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
