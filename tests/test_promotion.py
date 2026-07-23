"""Tests for src/gaia_cli/promotion.py — canon-side rank/grade helpers.

Under Yggdrasil II the self-promote machinery (candidate handshake, level
writes into user trees) has been retired. These tests cover the surviving
canon-curation helpers plus the pure level/evidence helpers.
"""

import pytest

from gaia_cli.promotion import (
    LEVEL_ORDER,
    LEVEL_NAMES,
    next_level,
    _effective_grade,
    _meets_evidence_floor,
    _holds_bucket_origin,
    _contributor_holds_origin_in,
    checkUniqueBranchGate,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_skill(skill_id, name=None, level="0★", evidence=None, demerits=None):
    """Build a minimal skill node."""
    return {
        "id": skill_id,
        "name": name or skill_id.replace("-", " ").title(),
        "type": "basic",
        "level": level,
        "description": f"Test skill: {skill_id}",
        "prerequisites": [],
        "derivatives": [],
        "conditions": "",
        "evidence": evidence or [],
        "knownAgents": [],
        "status": "provisional",
        "createdAt": "2026-01-01",
        "updatedAt": "2026-01-01",
        "version": "0.1.0",
        "demerits": demerits or [],
    }


# ---------------------------------------------------------------------------
# Tests: next_level
# ---------------------------------------------------------------------------


class TestNextLevel:
    def test_basic_to_awakened(self):
        assert next_level("0★") == "1★"

    def test_awakened_to_named(self):
        assert next_level("1★") == "2★"

    def test_transcendent_to_transcendent_star(self):
        assert next_level("5★") == "6★"

    def test_max_level_returns_none(self):
        assert next_level("6★") is None

    def test_invalid_level_returns_none(self):
        assert next_level("X") is None

    def test_full_progression(self):
        level = "0★"
        visited = [level]
        while True:
            nxt = next_level(level)
            if nxt is None:
                break
            visited.append(nxt)
            level = nxt
        assert visited == LEVEL_ORDER


# ---------------------------------------------------------------------------
# Tests: Constants
# ---------------------------------------------------------------------------


class TestConstants:
    def test_level_order_length(self):
        assert len(LEVEL_ORDER) == 7

    def test_level_names_keys_match_order(self):
        assert list(LEVEL_NAMES.keys()) == LEVEL_ORDER

    def test_level_names_apex(self):
        assert LEVEL_NAMES["6★"] == "Apex"


# ---------------------------------------------------------------------------
# Tests: _effective_grade and _meets_evidence_floor (grade/class translation)
# ---------------------------------------------------------------------------


class TestGradeTranslation:
    """Tests for evidence grade/class fallback logic in _meets_evidence_floor.

    Per G7 Trust Taxonomy RFC: evidence[].grade (S/A/B/C) supersedes the
    legacy evidence[].class (A/B/C).  Floor lists encode "at least one row at
    grade >= the weakest letter in the list".  Grade ordering: S > A > B > C.
    """

    # 1. Legacy: class-only row passes a ["B","A"] floor.
    def test_legacy_class_only_passes_floor(self):
        """A row with only class="B" (no grade field) satisfies a ["B","A"] floor."""
        skill = _make_skill(
            "legacy-skill",
            evidence=[{"class": "B", "source": "http://x.com", "evaluator": "x",
                        "date": "2026-01-01", "notes": ""}],
        )
        assert _meets_evidence_floor(skill, "3★") is True

    # 2. New: grade-only row passes a ["B","A"] floor.
    def test_new_grade_only_passes_floor(self):
        """A row with only grade="B" (no class field) satisfies a ["B","A"] floor."""
        skill = _make_skill(
            "graded-skill",
            evidence=[{"grade": "B", "source": "http://x.com", "evaluator": "x",
                        "date": "2026-01-01", "notes": ""}],
        )
        assert _meets_evidence_floor(skill, "3★") is True

    # 3. Mixed list: one class-only + one grade-only together pass a ["B","A"] floor.
    def test_mixed_class_and_grade_rows_pass_floor(self):
        """A list with one class-only (C) and one grade-only (B) entry passes ["B","A"]."""
        skill = _make_skill(
            "mixed-skill",
            evidence=[
                {"class": "C", "source": "http://c.com", "evaluator": "x",
                 "date": "2026-01-01", "notes": "class-only"},
                {"grade": "B", "source": "http://b.com", "evaluator": "x",
                 "date": "2026-01-01", "notes": "grade-only"},
            ],
        )
        assert _meets_evidence_floor(skill, "3★") is True

    # 4. Boundary: grade="C" only FAILS a ["B","A"] floor.
    def test_grade_c_fails_b_floor(self):
        """A row with only grade="C" does NOT satisfy a ["B","A"] floor."""
        skill = _make_skill(
            "weak-skill",
            evidence=[{"grade": "C", "source": "http://x.com", "evaluator": "x",
                        "date": "2026-01-01", "notes": ""}],
        )
        assert _meets_evidence_floor(skill, "3★") is False

    # 5. Bonus: S satisfies an A floor (["A"]).
    def test_grade_s_satisfies_a_floor(self):
        """A row with grade="S" satisfies a ["A"] floor (6★ gate). S > A."""
        skill = _make_skill(
            "apex-skill",
            evidence=[{"grade": "S", "source": "http://x.com", "evaluator": "x",
                        "date": "2026-01-01", "notes": ""}],
        )
        assert _meets_evidence_floor(skill, "6★") is True

    # 6. Ungraded entry (no class, no grade) is ignored.
    def test_ungraded_entry_ignored(self):
        """An entry with neither class nor grade does not satisfy any floor."""
        skill = _make_skill(
            "ungraded-skill",
            evidence=[{"source": "http://x.com", "evaluator": "x",
                        "date": "2026-01-01", "notes": "no grade or class"}],
        )
        assert _meets_evidence_floor(skill, "2★") is False


# ---------------------------------------------------------------------------
# Unique-branch origin gate (Yggdrasil II Q3, amended 2026-07-19)
# 4★ Unique = BUCKET-LEVEL origin (§4.1); 5★+ = fusion-structure origin.
# Regression: graphify (sole 4★ named on a fusion generic with 0-named-impl
# prereqs) must PASS the 4★ gate — its Origin is on its own bucket, not on the
# prerequisite fusion structure.
# ---------------------------------------------------------------------------
class TestBucketOrigin:
    def test_holds_bucket_origin_true(self):
        assert _holds_bucket_origin(
            {"genericSkillRef": "knowledge-graph-build", "origin": True}
        ) is True

    def test_holds_bucket_origin_false_when_not_origin(self):
        assert _holds_bucket_origin(
            {"genericSkillRef": "knowledge-graph-build", "origin": False}
        ) is False

    def test_holds_bucket_origin_false_without_generic_ref(self):
        # No bucket to hold Origin on.
        assert _holds_bucket_origin({"origin": True}) is False


class TestUniqueBranchGateOriginFork:
    """The 4★ Unique gate reads bucket-level origin; 5★ reads fusion structure."""

    def _patch_tm_branch(self, monkeypatch, tm, branch="unique"):
        import gaia_cli.trustMagnitude as tmm
        import gaia_cli.taxonomy as tax
        monkeypatch.setattr(tmm, "computeTrustMagnitude", lambda *a, **k: tm)
        monkeypatch.setattr(tax, "branchFor", lambda *a, **k: branch)

    def test_4star_passes_on_bucket_origin_despite_empty_prereqs(self, monkeypatch):
        """Regression for graphify: fusion generic, prereqs have zero named
        implementations, but the skill holds Origin on its OWN bucket → PASS."""
        self._patch_tm_branch(monkeypatch, tm=122.85)
        named = {
            "id": "safishamsi/graphify",
            "contributor": "safishamsi",
            "genericSkillRef": "knowledge-graph-build",
            "origin": True,
        }
        generic_map = {
            "knowledge-graph-build": {
                "id": "knowledge-graph-build",
                "type": "fusion",
                # prereqs with NO named implementations (unsatisfiable at 5★)
                "prerequisites": ["extract-entities", "logical-inference"],
            }
        }
        named_map = {named["id"]: named}
        res = checkUniqueBranchGate(named, "4★", generic_map, named_map)
        assert res["originPresent"] is True
        assert res["tmThresholdMet"] is True
        assert res["passed"] is True

    def test_4star_fails_when_not_bucket_origin(self, monkeypatch):
        self._patch_tm_branch(monkeypatch, tm=200.0)
        named = {
            "id": "someone/impl",
            "contributor": "someone",
            "genericSkillRef": "knowledge-graph-build",
            "origin": False,
        }
        generic_map = {"knowledge-graph-build": {"prerequisites": ["a", "b"]}}
        res = checkUniqueBranchGate(named, "4★", generic_map, {named["id"]: named})
        assert res["originPresent"] is False
        assert res["passed"] is False

    def test_5star_still_reads_fusion_structure_origin(self, monkeypatch):
        """5★ gate is UNCHANGED: origin comes from holding Origin on a
        prerequisite node, NOT the skill's own bucket flag."""
        self._patch_tm_branch(monkeypatch, tm=300.0)
        # This skill holds bucket origin (origin: True) but does NOT hold origin
        # on any prerequisite node → 5★ fusion-structure origin must be False.
        named = {
            "id": "safishamsi/graphify",
            "contributor": "safishamsi",
            "genericSkillRef": "knowledge-graph-build",
            "origin": True,
        }
        generic_map = {
            "knowledge-graph-build": {
                "prerequisites": ["extract-entities", "logical-inference"],
            }
        }
        # No named skill by this contributor holds origin on a prereq node.
        named_map = {named["id"]: named}
        res = checkUniqueBranchGate(named, "5★", generic_map, named_map)
        assert res["originPresent"] is False
        assert res["passed"] is False

    def test_5star_passes_when_contributor_holds_prereq_origin(self, monkeypatch):
        self._patch_tm_branch(monkeypatch, tm=300.0)
        capstone = {
            "id": "c/capstone",
            "contributor": "c",
            "genericSkillRef": "knowledge-graph-build",
            "origin": True,
        }
        prereq_impl = {
            "id": "c/entities",
            "contributor": "c",
            "genericSkillRef": "extract-entities",
            "origin": True,
        }
        generic_map = {
            "knowledge-graph-build": {
                "prerequisites": ["extract-entities", "logical-inference"],
            }
        }
        named_map = {capstone["id"]: capstone, prereq_impl["id"]: prereq_impl}
        res = checkUniqueBranchGate(capstone, "5★", generic_map, named_map)
        assert res["originPresent"] is True
        assert res["passed"] is True

