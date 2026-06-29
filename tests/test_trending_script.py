"""Hermetic tests for scripts/buildTrendingProjection.py.

No network, no git, no real registry.  All fixtures are created in tmp_path.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Load the script under test without invoking main()
# ---------------------------------------------------------------------------

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "buildTrendingProjection.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("buildTrendingProjection", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


btp = _load_module()

# ---------------------------------------------------------------------------
# Helpers for fixture construction
# ---------------------------------------------------------------------------


def _skill(
    skill_id: str,
    name: str = "Test Skill",
    level: str = "2★",
    tm: float = 10.0,
    grade: str = "C",
    generic_ref: str | None = None,
    timeline: list[dict] | None = None,
) -> dict:
    contributor, slug = skill_id.split("/", 1)
    return {
        "id": skill_id,
        "name": name,
        "level": level,
        "trustMagnitude": tm,
        "overallTrustGrade": grade,
        "contributor": contributor,
        "type": "basic",
        "genericSkillRef": generic_ref,
        "timeline": timeline or [],
        "_links": {"self": f"/api/v1/skills/{contributor}/{slug}.json"},
    }


def _write_api(tmp_path: Path, skills: list[dict]) -> Path:
    """Write a minimal docs/api/v1/ layout in tmp_path."""
    api_dir = tmp_path / "api" / "v1"
    skills_dir = api_dir / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)

    # Write index.json
    slim = []
    for s in skills:
        contributor, slug = s["id"].split("/", 1)
        slim.append({
            "id": s["id"],
            "name": s["name"],
            "level": s["level"],
            "trustMagnitude": s["trustMagnitude"],
            "overallTrustGrade": s["overallTrustGrade"],
            "contributor": s["contributor"],
            "type": s["type"],
            "_links": {"self": f"/api/v1/skills/{contributor}/{slug}.json"},
        })

    (skills_dir / "index.json").write_text(
        json.dumps({"skills": slim, "page": 1, "totalPages": 1, "totalSkills": len(slim)}),
        encoding="utf-8",
    )

    # Write per-skill detail files
    for s in skills:
        contributor, slug = s["id"].split("/", 1)
        detail_dir = skills_dir / contributor
        detail_dir.mkdir(exist_ok=True)
        (detail_dir / f"{slug}.json").write_text(
            json.dumps(s), encoding="utf-8"
        )

    return api_dir


# ---------------------------------------------------------------------------
# Test: cold start produces valid JSON with firstRun: true
# ---------------------------------------------------------------------------


def test_cold_start_first_run(tmp_path):
    skills = [
        _skill("alice/foo", tm=50.0, grade="B"),
        _skill("bob/bar", tm=30.0, grade="C"),
    ]
    api_dir = _write_api(tmp_path, skills)
    trending_dir = tmp_path / "trending"
    trending_dir.mkdir()

    visible = [s for s in skills if not btp.is_redacted(s.get("level", ""))]
    current_state = {
        s["id"]: {"tm": s["trustMagnitude"], "grade": s["overallTrustGrade"],
                  "level": s["level"], "updatedAt": "2026-06-28T12:00:00Z"}
        for s in visible
    }

    btp.build_trending_window(
        trending_dir, "7d", 7, visible, api_dir,
        current_state,  # cold start: prior = current (all deltas = 0)
        first_run=True,
        generated_at="2026-06-28T12:00:00Z",
    )

    result = json.loads((trending_dir / "7d.json").read_text())

    assert result["firstRun"] is True
    assert result["window"] == "7d"
    assert isinstance(result["skills"], list)
    assert len(result["skills"]) == 2
    # Cold start: sorted by TM descending
    assert result["skills"][0]["id"] == "alice/foo"
    assert result["skills"][1]["id"] == "bob/bar"
    # All tmDelta should be 0 on cold start
    for s in result["skills"]:
        assert s["tmDelta"] == 0.0


# ---------------------------------------------------------------------------
# Test: skill with positive TM delta appears in trending list
# ---------------------------------------------------------------------------


def test_positive_delta_appears_in_trending(tmp_path):
    skills = [
        _skill("alice/foo", tm=60.0, grade="B"),
    ]
    api_dir = _write_api(tmp_path, skills)
    out_dir = tmp_path / "out"
    trending_dir = out_dir / "trending"
    trending_dir.mkdir(parents=True)

    prior_snapshot = {
        "alice/foo": {"tm": 50.0, "grade": "C", "level": "2★", "updatedAt": "2026-06-21T00:00:00Z"}
    }

    visible = [s for s in skills if not btp.is_redacted(s.get("level", ""))]

    btp.build_trending_window(
        trending_dir, "7d", 7, visible, api_dir,
        prior_snapshot,
        first_run=False,
        generated_at="2026-06-28T12:00:00Z",
    )

    result = json.loads((trending_dir / "7d.json").read_text())
    assert result["firstRun"] is False
    assert len(result["skills"]) == 1
    skill = result["skills"][0]
    assert skill["id"] == "alice/foo"
    assert skill["trendingScore"] > 0
    assert skill["tmDelta"] == pytest.approx(10.0, abs=0.01)


# ---------------------------------------------------------------------------
# Test: skill with negative score is excluded
# ---------------------------------------------------------------------------


def test_negative_score_excluded(tmp_path):
    skills = [
        _skill("alice/foo", tm=40.0, grade="C"),  # TM dropped from 50 -> 40
    ]
    api_dir = _write_api(tmp_path, skills)
    trending_dir = tmp_path / "trending"
    trending_dir.mkdir(parents=True)

    prior_snapshot = {
        "alice/foo": {"tm": 50.0, "grade": "B", "level": "2★", "updatedAt": "2026-06-21T00:00:00Z"}
    }

    visible = [s for s in skills if not btp.is_redacted(s.get("level", ""))]

    btp.build_trending_window(
        trending_dir, "7d", 7, visible, api_dir,
        prior_snapshot,
        first_run=False,
        generated_at="2026-06-28T12:00:00Z",
    )

    result = json.loads((trending_dir / "7d.json").read_text())
    # Negative delta (-10), no rank events, no evidence → score < 0 → excluded
    assert result["totalTrending"] == 0
    assert result["skills"] == []


# ---------------------------------------------------------------------------
# Test: skill absent from prior snapshot gets new: true
# ---------------------------------------------------------------------------


def test_new_skill_flagged(tmp_path):
    skills = [
        _skill("alice/foo", tm=50.0, grade="B"),  # existing
        _skill("bob/new", tm=20.0, grade="C"),    # new (not in prior)
    ]
    api_dir = _write_api(tmp_path, skills)
    trending_dir = tmp_path / "trending"
    trending_dir.mkdir(parents=True)

    # Only alice/foo in prior; bob/new is new
    prior_snapshot = {
        "alice/foo": {"tm": 50.0, "grade": "B", "level": "2★", "updatedAt": "2026-06-21T00:00:00Z"}
    }

    visible = [s for s in skills if not btp.is_redacted(s.get("level", ""))]

    btp.build_trending_window(
        trending_dir, "7d", 7, visible, api_dir,
        prior_snapshot,
        first_run=False,
        generated_at="2026-06-28T12:00:00Z",
    )

    result = json.loads((trending_dir / "7d.json").read_text())
    ids = {s["id"]: s for s in result["skills"]}

    assert "bob/new" in ids
    assert ids["bob/new"]["new"] is True
    assert ids["bob/new"]["trendingScore"] == pytest.approx(20.0 * 0.5, abs=0.01)

    # alice has no delta → not in trending (score=0, excluded)
    assert "alice/foo" not in ids


# ---------------------------------------------------------------------------
# Test: ascended — skill with rank_up event within window appears
# ---------------------------------------------------------------------------


def test_ascended_rank_up_within_window(tmp_path):
    recent_ts = (datetime.utcnow() - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
    old_ts = (datetime.utcnow() - timedelta(days=60)).strftime("%Y-%m-%dT%H:%M:%SZ")

    skills = [
        _skill(
            "alice/hero",
            tm=80.0,
            grade="A",
            timeline=[
                {"action": "rank_up", "timestamp": recent_ts, "details": "Promoted"},
            ],
        ),
        _skill(
            "bob/stale",
            tm=40.0,
            grade="C",
            timeline=[
                {"action": "rank_up", "timestamp": old_ts, "details": "Old promotion"},
            ],
        ),
    ]
    api_dir = _write_api(tmp_path, skills)
    trending_dir = tmp_path / "trending"
    trending_dir.mkdir(parents=True)

    visible = [s for s in skills if not btp.is_redacted(s.get("level", ""))]

    btp.build_ascended(
        trending_dir, visible, api_dir,
        generated_at="2026-06-28T12:00:00Z",
        window_days=30,
    )

    result = json.loads((trending_dir / "ascended.json").read_text())
    ids = [s["id"] for s in result["skills"]]

    assert "alice/hero" in ids
    assert "bob/stale" not in ids

    hero = next(s for s in result["skills"] if s["id"] == "alice/hero")
    assert hero["ascendedAt"] == recent_ts


# ---------------------------------------------------------------------------
# Test: contested — bucket with 2 skills on same genericSkillRef appears
# ---------------------------------------------------------------------------


def test_contested_bucket(tmp_path):
    skills = [
        _skill("alice/foo", tm=80.0, grade="A", generic_ref="browser-control"),
        _skill("bob/bar", tm=50.0, grade="B", generic_ref="browser-control"),
        _skill("carol/baz", tm=30.0, grade="C", generic_ref="unique-skill"),  # solo → excluded
    ]
    api_dir = _write_api(tmp_path, skills)
    trending_dir = tmp_path / "trending"
    trending_dir.mkdir(parents=True)

    visible = [s for s in skills if not btp.is_redacted(s.get("level", ""))]

    btp.build_contested(
        trending_dir, visible, api_dir,
        generated_at="2026-06-28T12:00:00Z",
    )

    result = json.loads((trending_dir / "contested.json").read_text())
    refs = [b["genericSkillRef"] for b in result["buckets"]]

    assert "browser-control" in refs
    assert "unique-skill" not in refs  # only 1 implementation → excluded

    bucket = next(b for b in result["buckets"] if b["genericSkillRef"] == "browser-control")
    assert bucket["implementations"] == 2
    assert bucket["topTM"] == pytest.approx(80.0)
    # Sorted by TM desc within bucket
    assert bucket["skills"][0]["id"] == "alice/foo"
    assert bucket["skills"][1]["id"] == "bob/bar"


# ---------------------------------------------------------------------------
# Test: snapshot round-trip
# ---------------------------------------------------------------------------


def test_snapshot_round_trip(tmp_path):
    snapshot_path = tmp_path / "snapshot.json"
    state = {
        "alice/foo": {"tm": 42.0, "grade": "B", "level": "3★", "updatedAt": "2026-06-28T00:00:00Z"},
    }
    btp._save_snapshot(snapshot_path, state, "2026-06-28T00:00:00Z")
    loaded = btp._load_snapshot(snapshot_path)
    assert loaded["skills"] == state


# ---------------------------------------------------------------------------
# Test: history pruning keeps only 30 days
# ---------------------------------------------------------------------------


def test_history_prune(tmp_path):
    history_dir = tmp_path / "history"
    history_dir.mkdir()

    # Write 35 day-old files + 1 recent
    now = datetime.utcnow()
    for i in range(35):
        date_str = (now - timedelta(days=35 - i)).strftime("%Y-%m-%d")
        (history_dir / f"{date_str}.json").write_text("{}", encoding="utf-8")

    btp._archive_history(history_dir, {}, "2026-06-28T12:00:00Z")

    remaining = sorted(f.name for f in history_dir.glob("*.json"))
    # Should have 30 days worth + today
    assert len(remaining) <= 31  # at most 30 history + today


# ---------------------------------------------------------------------------
# Test: redacted (1-star) skills are excluded everywhere
# ---------------------------------------------------------------------------


def test_redacted_excluded(tmp_path):
    skills = [
        _skill("alice/visible", tm=30.0, grade="C", level="2★"),
        _skill("bob/hidden", tm=99.0, grade="A", level="1★"),  # redacted
    ]
    api_dir = _write_api(tmp_path, skills)
    trending_dir = tmp_path / "trending"
    trending_dir.mkdir(parents=True)

    visible = [s for s in skills if not btp.is_redacted(s.get("level", ""))]

    # cold start
    current_state = {
        s["id"]: {"tm": s["trustMagnitude"], "grade": s["overallTrustGrade"],
                  "level": s["level"], "updatedAt": "2026-06-28T12:00:00Z"}
        for s in visible
    }

    btp.build_trending_window(
        trending_dir, "7d", 7, visible, api_dir,
        current_state,
        first_run=True,
        generated_at="2026-06-28T12:00:00Z",
    )

    result = json.loads((trending_dir / "7d.json").read_text())
    ids = [s["id"] for s in result["skills"]]
    assert "alice/visible" in ids
    assert "bob/hidden" not in ids
