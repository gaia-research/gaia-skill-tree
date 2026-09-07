"""Tests for src/gaia_cli/promotion.py — canon-side rank/grade helpers.

Under Yggdrasil II the self-promote machinery (candidate handshake, level
writes into user trees) has been retired. These tests cover the surviving
canon-curation helpers plus the pure level/evidence helpers.
"""

import pytest

import gaia_cli.promotion as promotion_mod
from gaia_cli.promotion import (
    LEVEL_ORDER,
    LEVEL_NAMES,
    next_level,
    _effective_grade,
    _holds_bucket_origin,
    _contributor_holds_origin_in,
    checkUniqueBranchGate,
)
from gaia_cli.trustMagnitude import (
    GRADE_A_FLOOR,
    GRADE_B_FLOOR,
    GRADE_C_FLOOR,
    GRADE_S_FLOOR,
    computeOverallTrustGrade,
    computeOverallTrustGradeFromSkill,
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
# Tests: _effective_grade (grade/class translation on a single row)
# ---------------------------------------------------------------------------


class TestGradeTranslation:
    """`_effective_grade` reads evidence[].grade first, evidence[].class second.

    Per G7 Trust Taxonomy RFC the new ``grade`` field (S/A/B/C) supersedes the
    legacy ``class`` (A/B/C). This helper survives Yggdrasil II because
    verification.py still reports a per-row letter; what it NO LONGER does is
    gate promotion (see TestEvidenceFloorRemoved).
    """

    def test_grade_field_wins(self):
        assert _effective_grade({"grade": "S", "class": "C"}) == "S"

    def test_class_is_the_legacy_fallback(self):
        assert _effective_grade({"class": "B"}) == "B"

    def test_unrecognised_row_is_ungraded(self):
        assert _effective_grade({"source": "http://x.com"}) is None
        assert _effective_grade({"grade": "Z"}) is None


# ---------------------------------------------------------------------------
# Tests: the Evidence Floor is GONE — Trust Magnitude is the sole gate
# ---------------------------------------------------------------------------


class TestEvidenceFloorRemoved:
    """Yggdrasil II (ratified 2026-07-07) removed the **Evidence Floor**.

    Pre-Ygg-II, promotion needed at least one evidence row whose letter grade
    met a per-level floor (``meta.json levels.evidenceFloors``), enforced by
    ``promotion._meets_evidence_floor``. Both the schema block and the helper
    are deleted; Trust Magnitude alone decides.

    These tests are the tripwire: they fail loudly if anyone reintroduces a
    per-level evidence-class gate, in the schema OR in code.
    """

    def test_promotion_module_exposes_no_evidence_floor(self):
        assert not hasattr(promotion_mod, "EVIDENCE_FLOOR"), (
            "EVIDENCE_FLOOR is back — Yggdrasil II made Trust Magnitude the "
            "sole promotion gate; raise the TM threshold instead of adding a "
            "per-level evidence-class floor."
        )
        assert not hasattr(promotion_mod, "_meets_evidence_floor"), (
            "_meets_evidence_floor is back — see promotion.py's Yggdrasil II note."
        )

    def test_schema_declares_no_evidence_floors(self):
        levels = promotion_mod._META["levels"]
        assert "evidenceFloors" not in levels, (
            "registry/schema/meta.json levels.evidenceFloors was dropped in "
            "Yggdrasil II; reintroducing it re-splits the promotion gate."
        )


# ---------------------------------------------------------------------------
# Tests: TM-only gating — magnitude decides, the row's letter does not
# ---------------------------------------------------------------------------


class TestTrustMagnitudeIsTheSoleGate:
    """The promotion verdict is a function of Trust Magnitude, not row letters.

    Each test below states the pre-Yggdrasil-II floor behaviour it inverts, so
    a reader can see exactly which invariant was retired.
    """

    def _stars_row(self, url, stars=120_000, **extra):
        """A github-stars-own row worth TM 250 (min(250, stars/250) x weight 1.0).

        github-stars-own does not decay (no freshness rate), so the magnitude
        is stable over calendar time — these tests will not rot.
        """
        row = {
            "type": "github-stars-own",
            "source": url,
            "stars": stars,
            "skillCountInRepo": 1,
            "date": "2026-06-01",
            "evaluator": "test",
            "notes": "",
        }
        row.update(extra)
        return row

    def test_grade_ladder_is_a_pure_function_of_magnitude(self):
        """computeOverallTrustGrade takes NO evidence-letter input at all."""
        assert computeOverallTrustGrade(GRADE_S_FLOOR, 3, True) == "S"
        assert computeOverallTrustGrade(GRADE_A_FLOOR, 1, False) == "A"
        assert computeOverallTrustGrade(GRADE_B_FLOOR, 1, False) == "B"
        assert computeOverallTrustGrade(GRADE_C_FLOOR, 0, False) == "C"
        assert computeOverallTrustGrade(GRADE_C_FLOOR - 1, 0, False) == "ungraded"

    def test_c_graded_row_still_reaches_A(self):
        """WAS: a lone grade="C" row failed the 3★ ["B","A"] floor outright.

        NOW: the letter is inert. A C-graded row carrying 120k stars is worth
        TM 120, which clears the A floor.
        """
        skill = _make_skill(
            "weak-letter-strong-magnitude",
            evidence=[self._stars_row("https://github.com/a/b", grade="C")],
        )
        assert computeOverallTrustGradeFromSkill(skill) == "A"

    def test_ungraded_row_scores_identically_to_a_graded_one(self):
        """WAS: a row with neither `class` nor `grade` was skipped by the floor.

        NOW: it contributes exactly the same magnitude as the graded twin — the
        letter is not an input to the score.
        """
        graded = _make_skill(
            "graded",
            evidence=[self._stars_row("https://github.com/a/b", grade="A")],
        )
        ungraded = _make_skill(
            "ungraded",
            evidence=[self._stars_row("https://github.com/a/b")],
        )
        assert computeOverallTrustGradeFromSkill(ungraded) == (
            computeOverallTrustGradeFromSkill(graded)
        )
        assert computeOverallTrustGradeFromSkill(ungraded) == "A"

    def test_s_graded_row_of_low_magnitude_does_not_confer_rank(self):
        """WAS: grade="S" satisfied EVERY floor, including the 6★ ["A"] gate.

        NOW: a self-attestation is worth 5 TM no matter what letter it carries,
        so it lands below even the C floor. This is the load-bearing direction —
        it is what stops a curator from minting rank with a letter.
        """
        skill = _make_skill(
            "strong-letter-weak-magnitude",
            evidence=[
                {
                    "type": "self-attestation",
                    "grade": "S",
                    "source": "https://example.com/claim",
                    "date": "2026-06-01",
                    "evaluator": "test",
                    "notes": "",
                }
            ],
        )
        assert computeOverallTrustGradeFromSkill(skill) == "ungraded"

    def test_no_evidence_is_ungraded_not_blocked(self):
        """An empty pool scores 0 and grades `ungraded` — a magnitude verdict,
        not a floor rejection. There is no separate "blocked by evidence" state
        left in the model."""
        assert computeOverallTrustGradeFromSkill(_make_skill("bare")) == "ungraded"


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

    def test_tm_floor_is_the_only_numeric_gate(self, monkeypatch):
        """Origin + Trust Magnitude are the whole 4-star Unique gate.

        The skill below carries ZERO evidence rows, so under the retired
        Evidence Floor it could never promote. Here the verdict flips purely on
        whether the live TM clears `_UNIQUE_GATE_BY_LEVEL["4★"]["tmFloor"]`
        (100.0) — nothing consults an evidence-class letter.
        """
        named = {
            "id": "someone/impl",
            "contributor": "someone",
            "genericSkillRef": "knowledge-graph-build",
            "origin": True,
            "evidence": [],
        }
        generic_map = {"knowledge-graph-build": {"prerequisites": ["a", "b"]}}
        named_map = {named["id"]: named}

        self._patch_tm_branch(monkeypatch, tm=99.9)
        below = checkUniqueBranchGate(named, "4★", generic_map, named_map)
        assert below["originPresent"] is True
        assert below["tmThresholdMet"] is False
        assert below["passed"] is False

        self._patch_tm_branch(monkeypatch, tm=100.0)
        at_floor = checkUniqueBranchGate(named, "4★", generic_map, named_map)
        assert at_floor["tmThresholdMet"] is True
        assert at_floor["passed"] is True, (
            "A 4-star Unique with Origin and TM >= 100 must pass with an empty "
            "evidence list — reintroducing an evidence floor would break this."
        )

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

    def test_suite_components_delegates_to_suite_branch(self, monkeypatch):
        """A skill with suiteComponents is on the Suite branch, not Unique.
        checkUniqueBranchGate returns passed=False with branch='suite' and an explanation."""
        self._patch_tm_branch(monkeypatch, tm=150.0, branch="suite")
        named = {
            "id": "leonxlnx/taste-skill",
            "contributor": "leonxlnx",
            "genericSkillRef": "design-generation",
            "origin": False,
            "suiteComponents": ["leonxlnx/brandkit", "leonxlnx/minimalist-skill"],
        }
        res = checkUniqueBranchGate(named, "4★")
        assert res["passed"] is False
        assert res["branch"] == "suite"
        assert res["reason"] is not None
        assert "Suite branch applies" in res["reason"]
        assert res["tmThresholdMet"] is True


