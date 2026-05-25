"""Tests for #473 — unlockedAt is an ISO date-time, not a date.

The schema change widens `format` from `date` to `oneOf: [date, date-time]`,
keeping legacy `YYYY-MM-DD` valid (back-compat) while accepting full ISO
timestamps. The CLI runtime change (`main.py:926`) stops calling
`date.today().isoformat()` and starts calling
`datetime.now(timezone.utc).isoformat()`.

Coverage:
  - Schema accepts a freshly produced ISO date-time.
  - Schema still accepts legacy `YYYY-MM-DD` (back-compat).
  - Same-day unlocks issued ~1ms apart are chronologically distinguishable
    (the original motivation for #473).
  - End-to-end: `fuse_command` writes an unlockedSkill whose unlockedAt is
    a date-time string with a `T` separator.
"""

import json
import re
import time
import types
from datetime import datetime, timezone
from pathlib import Path

import jsonschema
import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "registry" / "schema" / "skillTree.schema.json"


@pytest.fixture(scope="module")
def skill_tree_schema():
    with SCHEMA_PATH.open(encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def validator(skill_tree_schema):
    return jsonschema.Draft7Validator(
        skill_tree_schema, format_checker=jsonschema.FormatChecker()
    )


def _tree_with(unlocked_at: str) -> dict:
    return {
        "userId": "alice",
        "updatedAt": "2026-05-25",
        "unlockedSkills": [
            {
                "skillId": "web-search",
                "level": "2★",
                "unlockedAt": unlocked_at,
                "unlockedIn": "owner/repo",
            }
        ],
        "pendingCombinations": [],
        "stats": {
            "totalUnlocked": 1,
            "highestRarity": "common",
            "deepestLineage": 0,
        },
    }


def test_schema_accepts_iso_date_time(validator):
    """Forward path: the new shape produced by main.py validates."""
    tree = _tree_with(datetime.now(timezone.utc).isoformat())
    validator.validate(tree)


def test_schema_accepts_legacy_date_only(validator):
    """Back-compat: legacy YYYY-MM-DD trees written before #473 still validate.

    Smoke check, not a regression guard — the prior `format: date` also
    accepted YYYY-MM-DD, so this asserts the post-#473 schema didn't lose
    that property.
    """
    tree = _tree_with("2026-05-01")
    validator.validate(tree)


def test_same_day_unlocks_have_strictly_increasing_unlocked_at(validator):
    """The motivating use case for #473: two unlocks on the same day must be
    chronologically distinguishable in unlockedAt alone."""
    first = datetime.now(timezone.utc).isoformat()
    time.sleep(0.001)
    second = datetime.now(timezone.utc).isoformat()
    assert first < second, f"{first!r} should sort before {second!r}"
    validator.validate(_tree_with(first))
    validator.validate(_tree_with(second))


def test_fuse_command_writes_iso_date_time_unlocked_at(validator, monkeypatch):
    """End-to-end: fuse_command produces an unlocked skill with date-time unlockedAt.

    Mocks the I/O boundary (load_config, load_tree, save_tree, open_pr) and
    the `gaia_cli.timeline` module that the function imports lazily (#482
    tracks that the real module is missing).
    """
    from gaia_cli import main as gaia_main

    saved = {}

    def fake_load_config():
        return {"gaiaUser": "alice"}

    def fake_load_tree(username, registry_path=None):
        return {
            "userId": username,
            "updatedAt": "2026-05-25",
            "unlockedSkills": [],
            "pendingCombinations": [
                {
                    "detectedSkills": ["web-search", "parse-html"],
                    "candidateResult": "web-scrape",
                    "levelFloor": "2★",
                    "promptedAt": "2026-05-01",
                }
            ],
            "stats": {"totalUnlocked": 0, "highestRarity": "common", "deepestLineage": 0},
        }

    def fake_save_tree(username, tree, registry_path=None):
        saved["tree"] = tree

    def fake_open_pr(*args, **kwargs):
        saved["pr_called"] = True

    fake_timeline = types.ModuleType("gaia_cli.timeline")
    fake_timeline.append_skill_tree_event = lambda *a, **kw: None

    monkeypatch.setattr(gaia_main, "load_config", fake_load_config)
    monkeypatch.setattr(gaia_main, "load_tree", fake_load_tree)
    monkeypatch.setattr(gaia_main, "save_tree", fake_save_tree)
    monkeypatch.setattr(gaia_main, "open_pr", fake_open_pr)
    monkeypatch.setitem(__import__("sys").modules, "gaia_cli.timeline", fake_timeline)

    args = types.SimpleNamespace(skillId="web-scrape", name=None, registry=None)
    gaia_main.fuse_command(args)

    assert "tree" in saved, "fuse_command should have called save_tree"
    unlocked = saved["tree"]["unlockedSkills"]
    assert len(unlocked) == 1
    entry = unlocked[0]
    assert entry["skillId"] == "web-scrape"

    unlocked_at = entry["unlockedAt"]
    assert "T" in unlocked_at, (
        f"expected ISO date-time with 'T' separator, got {unlocked_at!r} "
        "— this is the regression guard for #473"
    )
    assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", unlocked_at)

    validator.validate(saved["tree"])
