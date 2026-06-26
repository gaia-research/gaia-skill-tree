"""Hermetic tests for scripts/buildApiProjection.py.

All fixture data is built inline — no dependency on registry/named-skills.json
or any other live file outside tmp_path.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Import the module under test
# ---------------------------------------------------------------------------
SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import buildApiProjection as bap  # noqa: E402

# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _make_skill(
    skill_id: str,
    name: str,
    level: str = "2★",
    tm: float = 50.0,
    grade: str = "B",
    description: str = "",
    tags: list | None = None,
) -> dict:
    contributor, slug = skill_id.split("/", 1) if "/" in skill_id else (skill_id, skill_id)
    return {
        "id": skill_id,
        "name": name,
        "contributor": contributor,
        "level": level,
        "type": "basic",
        "status": "named",
        "trustMagnitude": tm,
        "overallTrustGrade": grade,
        "description": description,
        "tags": tags or [],
    }


def _make_named_skills_json(skills: list[dict], generated_at: str = "2026-06-01T00:00:00Z") -> dict:
    """Build a minimal named-skills.json structure with a single 'named' bucket."""
    return {
        "generatedAt": generated_at,
        "buckets": {
            "named": skills,
        },
    }


def _write_named_skills(tmp_path: Path, skills: list[dict]) -> Path:
    registry_dir = tmp_path / "registry"
    registry_dir.mkdir(parents=True, exist_ok=True)
    ns_path = registry_dir / "named-skills.json"
    ns_path.write_text(
        json.dumps(_make_named_skills_json(skills), ensure_ascii=False),
        encoding="utf-8",
    )
    return ns_path


def _run_projection(tmp_path: Path, skills: list[dict]) -> Path:
    """Write named-skills.json fixture and run the projection. Returns out_dir."""
    ns_path = _write_named_skills(tmp_path, skills)
    out_dir = tmp_path / "api" / "v1"

    # Write a minimal pyproject.toml so _read_version() doesn't blow up
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "gaia-cli"\nversion = "0.0.0-test"\n',
        encoding="utf-8",
    )

    # Monkey-patch ROOT so the script reads our fixture, not the real repo
    original_root = bap.ROOT
    bap.ROOT = tmp_path
    try:
        rc = bap.run(out_dir)
    finally:
        bap.ROOT = original_root

    assert rc == 0, f"bap.run() returned {rc}"
    return out_dir


def _simple_skills(n: int, start_tm: float = 100.0) -> list[dict]:
    return [
        _make_skill(
            f"alice/skill-{i:03d}",
            f"Skill {i:03d}",
            level="2★",
            tm=start_tm - i,
        )
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

# 1. Health structure
def test_health_structure(tmp_path):
    skills = [_make_skill("alice/foo", "Foo")]
    out_dir = _run_projection(tmp_path, skills)
    health = json.loads((out_dir / "health.json").read_text())
    for key in ("ok", "version", "registryGeneratedAt", "namedSkillsCount"):
        assert key in health, f"Missing key: {key}"


# 2. Health ok is True
def test_health_ok_is_true(tmp_path):
    skills = [_make_skill("alice/foo", "Foo")]
    out_dir = _run_projection(tmp_path, skills)
    health = json.loads((out_dir / "health.json").read_text())
    assert health["ok"] is True


# 3. Pagination math: 120 skills → 3 pages (50+50+20)
def test_skills_pagination_math(tmp_path):
    skills = _simple_skills(120)
    out_dir = _run_projection(tmp_path, skills)

    index = json.loads((out_dir / "skills" / "index.json").read_text())
    assert index["totalSkills"] == 120
    assert index["totalPages"] == 3
    assert len(index["skills"]) == 50

    page2 = json.loads((out_dir / "skills" / "page-2.json").read_text())
    assert page2["totalSkills"] == 120
    assert len(page2["skills"]) == 50

    page3 = json.loads((out_dir / "skills" / "page-3.json").read_text())
    assert page3["totalSkills"] == 120
    assert len(page3["skills"]) == 20


# 4. Page 1 has no prev link
def test_pagination_page1_no_prev(tmp_path):
    skills = _simple_skills(60)
    out_dir = _run_projection(tmp_path, skills)
    index = json.loads((out_dir / "skills" / "index.json").read_text())
    assert "prev" not in index["_links"]


# 5. Last page has no next link
def test_pagination_last_page_no_next(tmp_path):
    skills = _simple_skills(60)
    out_dir = _run_projection(tmp_path, skills)
    page2 = json.loads((out_dir / "skills" / "page-2.json").read_text())
    assert page2["page"] == 2
    assert "next" not in page2["_links"]


# 6. Middle page has both prev and next
def test_pagination_middle_page_has_both(tmp_path):
    skills = _simple_skills(120)
    out_dir = _run_projection(tmp_path, skills)
    page2 = json.loads((out_dir / "skills" / "page-2.json").read_text())
    assert "prev" in page2["_links"]
    assert "next" in page2["_links"]


# 7. Redaction excludes 1★ skill; 2★ IS present
def test_redaction_excludes_1star(tmp_path):
    skills = [
        _make_skill("alice/visible", "Visible Skill", level="2★", tm=80.0),
        _make_skill("bob/hidden", "Hidden Skill", level="1★", tm=90.0),
    ]
    out_dir = _run_projection(tmp_path, skills)
    index = json.loads((out_dir / "skills" / "index.json").read_text())
    ids = [s["id"] for s in index["skills"]]
    assert "alice/visible" in ids
    assert "bob/hidden" not in ids


# 8. Contributor with only 1★ skills is absent from contributors index
def test_redaction_excludes_contributor_with_only_1star(tmp_path):
    skills = [
        _make_skill("alice/good", "Good Skill", level="2★", tm=80.0),
        _make_skill("bob/shadow", "Shadow Skill", level="1★", tm=90.0),
    ]
    out_dir = _run_projection(tmp_path, skills)
    contrib_index = json.loads((out_dir / "contributors" / "index.json").read_text())
    handles = [c["handle"] for c in contrib_index["contributors"]]
    assert "alice" in handles
    assert "bob" not in handles


# 9. Skills sorted by TM descending on page 1
def test_skills_sorted_by_tm_desc(tmp_path):
    # Deliberately insert in non-TM order
    skills = [
        _make_skill("alice/low", "Low TM", tm=10.0),
        _make_skill("alice/high", "High TM", tm=99.0),
        _make_skill("alice/mid", "Mid TM", tm=55.0),
    ]
    out_dir = _run_projection(tmp_path, skills)
    index = json.loads((out_dir / "skills" / "index.json").read_text())
    tms = [s["trustMagnitude"] for s in index["skills"]]
    assert tms == sorted(tms, reverse=True)
    assert tms[0] == 99.0


# 10. Skill detail has required fields
def test_skill_detail_has_required_fields(tmp_path):
    skills = [_make_skill("alice/foo", "Foo Skill", tm=77.0)]
    out_dir = _run_projection(tmp_path, skills)
    detail = json.loads((out_dir / "skills" / "alice" / "foo.json").read_text())
    required = {"id", "name", "contributor", "level", "type", "trustMagnitude",
                "overallTrustGrade", "_links"}
    for field in required:
        assert field in detail, f"Missing field: {field}"


# 11. Skill detail _links.self format
def test_skill_detail_links_format(tmp_path):
    skills = [_make_skill("garrytan/gstack", "gstack")]
    out_dir = _run_projection(tmp_path, skills)
    detail = json.loads((out_dir / "skills" / "garrytan" / "gstack.json").read_text())
    assert detail["_links"]["self"] == "/api/v1/skills/garrytan/gstack.json"


# 12. Contributor prestige = sum of TMs
def test_contributors_prestige_is_sum_of_tms(tmp_path):
    skills = [
        _make_skill("alice/skill-a", "Skill A", tm=40.0),
        _make_skill("alice/skill-b", "Skill B", tm=60.0),
    ]
    out_dir = _run_projection(tmp_path, skills)
    contrib = json.loads((out_dir / "contributors" / "alice.json").read_text())
    assert contrib["prestigeScore"] == pytest.approx(100.0)


# 13. Leaderboard renames tm → trustMagnitude
def test_leaderboard_tm_field_renamed(tmp_path):
    skills = [_make_skill("alice/foo", "Foo")]
    out_dir = _run_projection(tmp_path, skills)

    # Inject a fake ledger
    ledger_dir = tmp_path / "docs" / "graph" / "ledger"
    ledger_dir.mkdir(parents=True, exist_ok=True)
    ledger = {
        "summary": {"A": 1},
        "rows": [
            {"skillId": "alice/foo", "tm": 75.0, "currentStars": "2★", "contributor": "alice"}
        ],
    }
    (ledger_dir / "data.json").write_text(json.dumps(ledger), encoding="utf-8")

    # Re-run just the leaderboard builder
    bap.build_leaderboard(out_dir, ledger_dir / "data.json")

    lb = json.loads((out_dir / "leaderboard.json").read_text())
    assert lb["rows"], "Expected at least one row"
    row = lb["rows"][0]
    assert "trustMagnitude" in row
    assert "tm" not in row


# 14. Leaderboard strips internal fields
def test_leaderboard_strips_internal_fields(tmp_path):
    skills = [_make_skill("alice/foo", "Foo")]
    out_dir = _run_projection(tmp_path, skills)

    ledger_dir = tmp_path / "docs" / "graph" / "ledger"
    ledger_dir.mkdir(parents=True, exist_ok=True)
    ledger = {
        "summary": {},
        "rows": [
            {
                "skillId": "alice/foo",
                "tm": 50.0,
                "currentStars": "2★",
                "contributor": "alice",
                "mayStars": 1,
                "juneStars": 2,
                "g7Stars": 3,
                "flag": "⚑",
                "apexResults": {"q1": True},
            }
        ],
    }
    (ledger_dir / "data.json").write_text(json.dumps(ledger), encoding="utf-8")

    bap.build_leaderboard(out_dir, ledger_dir / "data.json")
    lb = json.loads((out_dir / "leaderboard.json").read_text())
    row = lb["rows"][0]
    for banned in ("mayStars", "juneStars", "g7Stars", "flag", "apexResults"):
        assert banned not in row, f"Internal field should be stripped: {banned}"


# 15. Evidence types output has 'types' array
def test_evidence_types_has_types_array(tmp_path):
    skills = [_make_skill("alice/foo", "Foo")]
    out_dir = _run_projection(tmp_path, skills)
    # Run with no schema — should still write a valid stub
    bap.build_evidence_types(out_dir, tmp_path / "nonexistent-schema.json")
    ev = json.loads((out_dir / "evidence-types.json").read_text())
    assert "types" in ev
    assert isinstance(ev["types"], list)


# 16. Search tokens are lowercase
def test_search_tokens_are_lowercase(tmp_path):
    skills = [_make_skill("alice/FooBar", "FooBar Skill", description="UPPER lower Mixed")]
    out_dir = _run_projection(tmp_path, skills)
    search = json.loads((out_dir / "search-index.json").read_text())
    for entry in search:
        for token in entry["tokens"]:
            assert token == token.lower(), f"Token not lowercase: {token!r}"


# 17. Skill name words appear in tokens
def test_search_name_words_in_tokens(tmp_path):
    skills = [_make_skill("alice/deep-learning", "Deep Learning Networks")]
    out_dir = _run_projection(tmp_path, skills)
    search = json.loads((out_dir / "search-index.json").read_text())
    entry = next(e for e in search if e["id"] == "alice/deep-learning")
    tokens = entry["tokens"]
    # "deep", "learning", "networks" should all be present
    assert "deep" in tokens
    assert "learning" in tokens
    assert "networks" in tokens


# 18. Empty buckets: no crash, all output files written
def test_empty_buckets_no_crash(tmp_path):
    out_dir = _run_projection(tmp_path, [])
    # All top-level files must exist
    for filename in ("health.json", "leaderboard.json", "evidence-types.json",
                     "search-index.json"):
        assert (out_dir / filename).exists(), f"Missing: {filename}"
    # skills/index.json must exist and have totalSkills=0
    index = json.loads((out_dir / "skills" / "index.json").read_text())
    assert index["totalSkills"] == 0
    # contributors/index.json must exist
    assert (out_dir / "contributors" / "index.json").exists()


# 19. Missing named-skills.json → SystemExit raised
def test_missing_named_skills_exits_nonzero(tmp_path):
    out_dir = tmp_path / "api" / "v1"
    # Point ROOT at an empty directory — no registry/named-skills.json
    original_root = bap.ROOT
    bap.ROOT = tmp_path / "empty_root"
    try:
        rc = bap.run(out_dir)
    finally:
        bap.ROOT = original_root
    assert rc != 0, "Expected non-zero return code when named-skills.json is missing"


# 20. No top-level 'version' key in skills/index.json
def test_no_version_key_in_skills_output(tmp_path):
    skills = [_make_skill("alice/foo", "Foo")]
    out_dir = _run_projection(tmp_path, skills)
    index = json.loads((out_dir / "skills" / "index.json").read_text())
    assert "version" not in index, (
        "skills/index.json must not carry a top-level 'version' key "
        "(CLAUDE.md: decorative assets must not carry version metadata)"
    )
