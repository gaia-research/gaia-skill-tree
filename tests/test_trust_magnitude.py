"""Tests for G7 Trust Magnitude (Phase 1.5 I2).

Covers RFC §2-§4 + §10 with delta §A/§B amendments.
"""

from __future__ import annotations

import datetime
import math

import pytest

from gaia_cli.trustMagnitude import (
    GRADE_A_FLOOR,
    GRADE_B_FLOOR,
    GRADE_C_FLOOR,
    GRADE_S_FLOOR,
    checkAGradedOriginsGte5,
    checkApexPromotionPrSigned,
    checkCrossOrgVerifier,
    checkDepth2OnlyReachableGte1,
    checkDirectNestedSuiteGte1,
    checkOverallGradeS,
    checkSourceTenureDaysGte180AorS,
    checkSystemWideCap,
    computeArtifactScore,
    computeArtifactScoreOrNone,
    computeOverallTrustGrade,
    computeOverallTrustGradeFromSkill,
    computeTrustMagnitude,
    enforceAntiAutoMint,
    isApex,
    passesApexGate,
)
from gaia_cli.promotion import _passes_rank_floor


# ---------------------------------------------------------------------------
# Batch A: Per-type magnitude (10 tests, one per RFC §2 evidence type)
# ---------------------------------------------------------------------------


def test_fusion_recipe_magnitude_under_10_origins_linear():
    """RFC §2.2: m = 20 * origins for origins <= 10. weight=1.5."""
    row = {"type": "fusion-recipe", "origins": ["a", "b", "c"]}
    score = computeArtifactScore(row)
    # 20 * 3 = 60; weight 1.5 => 90.0
    assert score == pytest.approx(90.0)


def test_github_stars_own_magnitude_basic():
    """RFC §2.3: m = stars / 1000. weight=1.0."""
    row = {"type": "github-stars-own", "stars": 5000}
    score = computeArtifactScore(row)
    # 5000/1000 = 5.0; weight 1.0 => 5.0
    assert score == pytest.approx(5.0)


def test_proxy_containment_below_threshold_returns_zero():
    """RFC §2.4: external stars < 10000 contributes 0."""
    row = {"type": "proxy-containment", "externalStars": 5000}
    assert computeArtifactScore(row) == 0.0


def test_proxy_containment_above_threshold_scales():
    """RFC §2.4: m = (externalStars/1000)*0.8. weight=1.0."""
    row = {"type": "proxy-containment", "externalStars": 20000}
    # 20000/1000=20; *0.8 = 16; weight 1.0 = 16
    assert computeArtifactScore(row) == pytest.approx(16.0)


def test_verifier_attestation_magnitude_per_verifier():
    """RFC §2.5: m = 30 * verifiers. weight=1.5."""
    row = {"type": "verifier-attestation", "verifiers": 2}
    # 30*2=60; weight 1.5 => 90
    assert computeArtifactScore(row) == pytest.approx(90.0)


def test_benchmark_result_magnitude_is_percentile():
    """RFC §2.6: m = percentile. weight=1.4. Cap 100."""
    row = {"type": "benchmark-result", "percentile": 90}
    # 90 capped at 100, weight 1.4 => 126
    assert computeArtifactScore(row) == pytest.approx(126.0)


def test_arxiv_magnitude_from_citations():
    """RFC §2.7: m = citations / 5. weight=1.0. cap=100."""
    row = {"type": "arxiv", "citations": 200}
    # 200/5=40; weight 1.0 => 40
    assert computeArtifactScore(row) == pytest.approx(40.0)


def test_peer_review_magnitude_per_reviewer():
    """RFC §2.8: m = 25 * reviewers. weight=1.2."""
    row = {"type": "peer-review", "reviewers": 2}
    # 25*2=50; weight 1.2 => 60
    assert computeArtifactScore(row) == pytest.approx(60.0)


def test_repo_own_magnitude_combines_commits_and_contributors():
    """RFC §2.9: m = commits/200 + contributors^2 * 2. weight=0.6. cap 60."""
    row = {"type": "repo-own", "commits": 200, "contributors": 3}
    # 200/200=1; 3^2*2=18; sum=19; weight 0.6 => 11.4
    assert computeArtifactScore(row) == pytest.approx(11.4)


def test_self_attestation_magnitude_is_constant():
    """RFC §2.10: m = 10 (constant). weight=0.5. cap 10."""
    row = {"type": "self-attestation"}
    # 10 capped at 10, weight 0.5 => 5
    assert computeArtifactScore(row) == pytest.approx(5.0)


def test_social_signal_magnitude_log_views():
    """RFC §2.11: m = log10(views) * 8 if views >= 1000. weight=1.0."""
    row = {"type": "social-signal", "views": 10000}
    # log10(10000) = 4; 4*8=32; weight 1.0 => 32
    assert computeArtifactScore(row) == pytest.approx(32.0)


# ---------------------------------------------------------------------------
# Batch B: Mothership discount (3) + same-source dedup (2) + sqrt fusion (2)
# ---------------------------------------------------------------------------


def test_mothership_discount_single_skill_no_change():
    """RFC §3.1: skillCountInRepo <= 1 means full magnitude (no discount)."""
    row = {"type": "github-stars-own", "stars": 4000, "skillCountInRepo": 1}
    # 4 stars/k * weight 1.0 = 4.0 (full)
    assert computeArtifactScore(row) == pytest.approx(4.0)


def test_mothership_discount_two_skills_halved():
    """RFC §3.1: skillCountInRepo=2 means *1/2 multiplier."""
    row = {"type": "github-stars-own", "stars": 4000, "skillCountInRepo": 2}
    # 4.0 * 0.5 = 2.0
    assert computeArtifactScore(row) == pytest.approx(2.0)


def test_mothership_discount_capped_at_quarter():
    """RFC §3.1: skillCountInRepo capped at 4 -> minimum *1/4 multiplier."""
    row = {"type": "github-stars-own", "stars": 4000, "skillCountInRepo": 100}
    # min(100,4)=4 -> *1/4 = 1.0
    assert computeArtifactScore(row) == pytest.approx(1.0)


def test_same_source_dedup_collapses_duplicate_urls():
    """RFC §5.2: identical canonical URL on same type -> highest wins, only one counted."""
    skill = {
        "evidence": [
            {"type": "github-stars-own", "stars": 1000, "source": "https://github.com/o/r"},
            {"type": "github-stars-own", "stars": 5000, "source": "https://github.com/o/r/"},
        ]
    }
    tm = computeTrustMagnitude(skill)
    # Both same canonical url; higher (5000 -> 5.0) wins; 1000 dropped
    assert tm == pytest.approx(5.0)


def test_same_source_dedup_normalizes_tree_to_blob():
    """Canonical URL normalization: tree/ and blob/ collapse together."""
    skill = {
        "evidence": [
            {"type": "repo-own", "commits": 200, "contributors": 0,
             "source": "https://github.com/o/r/tree/main/x"},
            {"type": "repo-own", "commits": 400, "contributors": 0,
             "source": "https://github.com/o/r/blob/main/x"},
        ]
    }
    tm = computeTrustMagnitude(skill)
    # Higher of (200/200=1) vs (400/200=2); take 2; weight 0.6 => 1.2
    assert tm == pytest.approx(1.2)


def test_fusion_recipe_sqrt_softening_above_10_origins():
    """RFC §2.2: m = 200 + 20*sqrt(origins-10) for origins > 10. weight=1.5."""
    row = {"type": "fusion-recipe", "gradedOriginCount": 14}
    # 200 + 20*sqrt(4)=200+40=240; weight 1.5 => 360
    assert computeArtifactScore(row) == pytest.approx(360.0)


def test_fusion_recipe_at_exactly_10_origins_linear_endpoint():
    """RFC §2.2: at origins=10, linear path applies (m=200)."""
    row = {"type": "fusion-recipe", "gradedOriginCount": 10}
    # 20*10=200; weight 1.5 => 300
    assert computeArtifactScore(row) == pytest.approx(300.0)


# ---------------------------------------------------------------------------
# Batch C: Anti-auto-mint (3) + null-on-derank (2) + diversity (3) + rank-floor (2)
# ---------------------------------------------------------------------------


def test_anti_auto_mint_strips_phantom_rows():
    """RFC §10.14: rows marked _phantom or phantom are stripped."""
    skill = {
        "evidence": [
            {"type": "github-stars-own", "stars": 5000},
            {"type": "verifier-attestation", "verifiers": 1, "_phantom": True},
            {"type": "arxiv", "citations": 100, "phantom": True},
        ]
    }
    cleaned = enforceAntiAutoMint(skill)
    assert len(cleaned) == 1
    assert cleaned[0]["type"] == "github-stars-own"


def test_anti_auto_mint_strips_auto_minted_non_fusion_rows():
    """Only fusion-recipe rows can be auto-derived; auto-minted others get dropped."""
    skill = {
        "evidence": [
            {"type": "verifier-attestation", "verifiers": 1, "autoMinted": True},
            {"type": "fusion-recipe", "origins": ["a", "b"], "autoMinted": True},
        ]
    }
    cleaned = enforceAntiAutoMint(skill)
    assert len(cleaned) == 1
    assert cleaned[0]["type"] == "fusion-recipe"


def test_anti_auto_mint_preserves_real_evidence():
    """Real (non-phantom, non-auto-minted) evidence rows pass through unchanged."""
    rows = [
        {"type": "github-stars-own", "stars": 1000},
        {"type": "arxiv", "citations": 50},
        {"type": "self-attestation"},
    ]
    skill = {"evidence": list(rows)}
    cleaned = enforceAntiAutoMint(skill)
    assert len(cleaned) == 3
    assert cleaned == rows


def test_null_on_derank_excludes_verifier_with_inactive_rank():
    """RFC §10.4 / §5.6: verifierActiveRank=False -> row evaluates to None and is excluded."""
    row = {"type": "verifier-attestation", "verifiers": 2, "verifierActiveRank": False}
    assert computeArtifactScoreOrNone(row) is None
    # The non-or-none variant returns 0
    assert computeArtifactScore(row) == 0.0


def test_null_on_derank_legacy_derank_field_also_honored():
    """Legacy `derank: true` should also evaluate to None."""
    row = {"type": "verifier-attestation", "verifiers": 1, "derank": True}
    assert computeArtifactScoreOrNone(row) is None


def test_diversity_gate_blocks_S_when_only_self_producible():
    """RFC §4: S grade requires non-self-producible evidence type."""
    # Pure fusion-recipe, repo-own, self-attestation are all self-producible
    skill = {
        "evidence": [
            {"type": "fusion-recipe", "gradedOriginCount": 12},  # huge
            {"type": "repo-own", "commits": 1000, "contributors": 5},
            {"type": "self-attestation"},
        ]
    }
    grade = computeOverallTrustGradeFromSkill(skill)
    # TM clearly >= 250, but no non-self-producible -> max is A
    assert grade == "A"


def test_diversity_gate_S_requires_three_distinct_types():
    """RFC §4: even with non-self-producible, distinct types must be >= 3."""
    skill = {
        "evidence": [
            # one verifier (non-self-producible) + one fusion = only 2 types
            {"type": "verifier-attestation", "verifiers": 8},  # 30*8=240; *1.5=360
            {"type": "fusion-recipe", "gradedOriginCount": 5},  # 100*1.5=150
        ]
    }
    # TM = 510, has non-self-producible, but only 2 types -> A (not S)
    grade = computeOverallTrustGradeFromSkill(skill)
    assert grade == "A"


def test_diversity_gate_S_passes_with_three_types_and_non_self_producible():
    """RFC §4: passes S when TM >= 250, distinctTypes >= 3, non-self-producible present."""
    skill = {
        "evidence": [
            {"type": "verifier-attestation", "verifiers": 4},  # 30*4*1.5 = 180
            {"type": "github-stars-own", "stars": 50000},  # 50*1.0=50, capped 200
            {"type": "arxiv", "citations": 200},  # 40*1.0 = 40
        ]
    }
    # TM = 180+50+40 = 270, 3 distinct types (all non-self-producible) -> S
    grade = computeOverallTrustGradeFromSkill(skill)
    assert grade == "S"


def test_rank_floor_grade_thresholds_constants():
    """Rank-floor sanity (RFC §4.3): the four thresholds are exposed and ordered."""
    assert GRADE_S_FLOOR == 250.0
    assert GRADE_A_FLOOR == 100.0
    assert GRADE_B_FLOOR == 50.0
    assert GRADE_C_FLOOR == 20.0
    assert GRADE_S_FLOOR > GRADE_A_FLOOR > GRADE_B_FLOOR > GRADE_C_FLOOR


def test_rank_floor_grade_returns_ungraded_below_C():
    """TM under 20 -> ungraded."""
    assert computeOverallTrustGrade(15.0, 1, False) == "ungraded"
    assert computeOverallTrustGrade(20.0, 1, False) == "C"
    assert computeOverallTrustGrade(50.0, 1, False) == "B"
    assert computeOverallTrustGrade(100.0, 1, False) == "A"


# ---------------------------------------------------------------------------
# Batch D: Apex gate (5) + role=variant zeroing (2) + edge cases (3)
# ---------------------------------------------------------------------------


def _apexReadySkill():
    """Build a skill that should pass all 6 active apex predicates."""
    today = datetime.datetime.now(datetime.timezone.utc)
    longAgo = (today - datetime.timedelta(days=365)).date().isoformat()
    return {
        "id": "apex-skill",
        "suiteComponents": ["nestedSuiteId"],
        "evidence": [
            # Fusion-recipe with 5 non-variant origins (A-graded in the map).
            # origin1 is also depth1Skill to satisfy depth2OnlyReachableGte1.
            {
                "type": "fusion-recipe",
                "origins": ["origin1", "origin2", "origin3", "origin4", "origin5"],
            },
            # A/S-graded evidence rows for sourceTenureDaysGte180AorS predicate
            {"type": "verifier-attestation", "verifiers": 4, "grade": "A",
             "source": "https://verifier.example/1", "sourceStartedAt": longAgo},
            {"type": "arxiv", "citations": 200, "grade": "A",
             "source": "https://arxiv.org/abs/1234.5678", "sourceStartedAt": longAgo},
            {"type": "github-stars-own", "stars": 50000, "grade": "A",
             "source": "https://github.com/o/r", "sourceStartedAt": longAgo},
        ],
        "apexGateStatus": {"apexPromotionPrSigned": True},
    }


def _apexReadyGenericMap():
    """GenericSkillMap for use with _apexReadySkill.

    - nestedSuiteId: has suiteComponents -> directNestedSuiteGte1 passes.
    - origin1: has a fusion-recipe leading to depth2Skill -> depth2OnlyReachableGte1 passes.
    - origin1..origin5: all A-graded -> aGradedOriginsGte5 passes.
    """
    return {
        "nestedSuiteId": {"id": "nestedSuiteId", "suiteComponents": ["x", "y"]},
        "origin1": {
            "id": "origin1",
            "overallTrustGrade": "A",
            "evidence": [
                {"type": "fusion-recipe", "origins": ["depth2Skill"]},
            ],
        },
        "origin2": {"id": "origin2", "overallTrustGrade": "A"},
        "origin3": {"id": "origin3", "overallTrustGrade": "A"},
        "origin4": {"id": "origin4", "overallTrustGrade": "A"},
        "origin5": {"id": "origin5", "overallTrustGrade": "A"},
        "depth2Skill": {"id": "depth2Skill"},
    }


def test_apex_gate_passes_with_full_setup():
    """Six active predicates all True => isApex returns True."""
    skill = _apexReadySkill()
    genericSkillMap = _apexReadyGenericMap()
    state = {"genericSkillMap": genericSkillMap}
    result = passesApexGate(skill, state)
    # Inactive scaffolds -> None
    assert result["crossOrgVerifier"] is None
    assert result["systemWideCap"] is None
    # Six active predicates all pass
    assert result["aGradedOriginsGte5"] is True
    assert result["sourceTenureDaysGte180AorS"] is True
    assert result["directNestedSuiteGte1"] is True
    assert result["depth2OnlyReachableGte1"] is True
    assert result["overallGradeS"] is True
    assert result["apexPromotionPrSigned"] is True
    assert isApex(result) is True


def test_apex_gate_fails_when_only_4_a_graded_origins():
    """Predicate 1 fails when only 4 out of 5 fusion-graph origins are A-graded."""
    skill = _apexReadySkill()
    genericSkillMap = _apexReadyGenericMap()
    # Downgrade origin5 to B so only 4 origins are A-graded
    genericSkillMap["origin5"] = {"id": "origin5", "overallTrustGrade": "B"}
    result = passesApexGate(skill, {"genericSkillMap": genericSkillMap})
    assert result["aGradedOriginsGte5"] is False
    assert isApex(result) is False


def test_apex_gate_fails_when_tenure_under_180_days():
    """Predicate 2 fails when no A/S row has sourceStartedAt >= 180 days old."""
    skill = _apexReadySkill()
    recent = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=30)).date().isoformat()
    for row in skill["evidence"]:
        if "sourceStartedAt" in row:
            row["sourceStartedAt"] = recent
    genericSkillMap = _apexReadyGenericMap()
    result = passesApexGate(skill, {"genericSkillMap": genericSkillMap})
    assert result["sourceTenureDaysGte180AorS"] is False
    assert isApex(result) is False


def test_apex_gate_fails_without_signed_promotion_pr():
    """Predicate 6 fails when apexPromotionPrSigned not set."""
    skill = _apexReadySkill()
    skill["apexGateStatus"] = {}
    skill.pop("apexPromotionPr", None)
    assert checkApexPromotionPrSigned(skill) is False


def test_apex_gate_inactive_predicates_return_none():
    """crossOrgVerifier and systemWideCap are feature-flagged OFF."""
    assert checkCrossOrgVerifier({}) is None
    assert checkSystemWideCap({"systemWideApexCount": 100}) is None


def test_role_variant_origin_does_not_count_in_fusion_recipe():
    """Delta §C-2: role='variant' origins contribute 0 to graded-origin count."""
    row = {
        "type": "fusion-recipe",
        "origins": [
            {"id": "a", "grade": "A"},
            {"id": "b", "grade": "A"},
            {"id": "c", "role": "variant", "grade": "S"},  # excluded
        ],
    }
    score = computeArtifactScore(row)
    # Only 2 graded origins counted: 20*2 = 40; weight 1.5 = 60
    assert score == pytest.approx(60.0)


def test_role_variant_excluded_from_depth1_fusion_origins_for_apex():
    """Apex predicate 4 must skip variant edges in fusion graph traversal."""
    skill = {
        "id": "host",
        "evidence": [
            {"type": "fusion-recipe",
             "origins": [
                 {"id": "variantOrigin", "role": "variant"},
                 {"id": "realOrigin"},
             ]},
        ],
    }
    state = {"genericSkillMap": {
        "variantOrigin": {"id": "variantOrigin",
                          "evidence": [{"type": "fusion-recipe", "origins": ["x"]}]},
        "realOrigin": {"id": "realOrigin",
                       "evidence": [{"type": "fusion-recipe", "origins": ["y"]}]},
        "x": {}, "y": {},
    }}
    # depth1 must include realOrigin only; depth2 reaches y (not x)
    assert checkDepth2OnlyReachableGte1(skill, state) is True


def test_edge_case_empty_evidence_returns_zero_tm_and_ungraded():
    """Empty evidence -> TM=0 -> ungraded."""
    skill = {"evidence": []}
    assert computeTrustMagnitude(skill) == 0.0
    assert computeOverallTrustGradeFromSkill(skill) == "ungraded"


def test_edge_case_unknown_type_yields_zero_score():
    """Unknown evidence type returns 0 (defensive default)."""
    row = {"type": "completely-made-up-type", "value": 99999}
    assert computeArtifactScore(row) == 0.0


def test_edge_case_social_signal_below_1000_views_zero():
    """RFC §2.11: views < 1000 contributes 0."""
    row = {"type": "social-signal", "views": 500}
    assert computeArtifactScore(row) == 0.0


# ---------------------------------------------------------------------------
# Batch E: Rank-floor direct unit tests (CRITICAL #1)
# ---------------------------------------------------------------------------


def test_rank_floor_4star_at_C_grade_fails():
    """RFC §4.3: a skill at 4★ with grade=C fails the rank-floor sanity rule."""
    result = _passes_rank_floor({}, "4★", "C")
    assert result is False


def test_rank_floor_4star_at_B_grade_passes():
    """RFC §4.3: a skill at 4★ with grade=B passes the rank-floor sanity rule."""
    result = _passes_rank_floor({}, "4★", "B")
    assert result is True


# ---------------------------------------------------------------------------
# Batch F: Apex gate delta §B edge cases (MAJOR #2)
# ---------------------------------------------------------------------------


def test_apex_gate_source_tenure_absent_treats_as_age_zero():
    """Delta §B: A/S row with no sourceStartedAt -> age=0 -> tenure predicate False."""
    skill = {
        "id": "tenure-test",
        "evidence": [
            # A-graded row with no sourceStartedAt field
            {"type": "verifier-attestation", "verifiers": 2, "grade": "A",
             "source": "https://verifier.example/1"},
            {"type": "arxiv", "citations": 200, "grade": "A",
             "source": "https://arxiv.org/abs/9999.0000"},
        ],
    }
    # Conservative fallback treats absent sourceStartedAt as age=0 days.
    # max([0, 0]) = 0 < 180, so result is False.
    result = checkSourceTenureDaysGte180AorS(skill)
    assert result is False
    # Also confirm via passesApexGate
    gate = passesApexGate(skill, {})
    assert gate["sourceTenureDaysGte180AorS"] is False


def test_apex_gate_depth2_suite_inclusion():
    """Founder ruling #746: suiteComponents edges DO count in the fusion graph.

    Suite-based ultimates (e.g. garrytan/gstack) carry no fusion-recipe rows;
    their fusion graph IS the suiteComponents array. Per RFC §11.12.3 founder
    ruling, the apex depth walker must include both fusion-recipe origins AND
    suiteComponents at every depth.
    """
    skill = {
        "id": "suite-host",
        "suiteComponents": ["suiteChild"],
        # No fusion-recipe evidence row — depth-1 must come from suiteComponents.
        "evidence": [],
    }
    suiteChildNode = {
        "id": "suiteChild",
        "suiteComponents": ["grandchild"],
    }
    state = {
        "genericSkillMap": {
            "suiteChild": suiteChildNode,
            "grandchild": {"id": "grandchild"},
        },
        "namedSkillMap": {
            "suiteChild": suiteChildNode,
        },
    }
    # depth1 = {"suiteChild"}; depth2 reaches "grandchild" via suiteComponents.
    result = checkDepth2OnlyReachableGte1(skill, state)
    assert result is True
    gate = passesApexGate(skill, state)
    assert gate["depth2OnlyReachableGte1"] is True


# ---------------------------------------------------------------------------
# Batch G: Same-creator social-signal plateau (MAJOR #3)
# ---------------------------------------------------------------------------


def test_same_creator_social_signal_plateau():
    """Three social-signal rows from same creator plateau at 1.0x / 0.5x / 0.25x."""
    # All rows from creator="alice", views=10000 each.
    # Raw score per row: log10(10000)*8 * 1.0 (weight) = 32.0
    skill = {
        "evidence": [
            {"type": "social-signal", "views": 10000, "creator": "alice",
             "source": "https://social.example/1"},
            {"type": "social-signal", "views": 10000, "creator": "alice",
             "source": "https://social.example/2"},
            {"type": "social-signal", "views": 10000, "creator": "alice",
             "source": "https://social.example/3"},
        ]
    }
    # Rank 0 (highest) -> 32.0 * 1.0 = 32.0
    # Rank 1 -> 32.0 * 0.5 = 16.0
    # Rank 2 -> 32.0 * 0.25 = 8.0
    # Sum = 56.0; well under social 80-cap, so TM = 56.0
    tm = computeTrustMagnitude(skill)
    assert tm == pytest.approx(56.0)


# ---------------------------------------------------------------------------
# Batch H: engagementRatio computed from raw fields (MAJOR #5)
# ---------------------------------------------------------------------------


def test_social_signal_computes_engagement_ratio_from_raw_fields():
    """RFC §2.11: engagementRatio computed from views/likes/comments when not pre-stored."""
    # views=10000, likes=200, comments=50; no engagementRatio field
    # engagement_ratio = min(1.5, (200 + 50*5) / 10000 * 50) = min(1.5, 2.25) = 1.5
    # raw_magnitude = log10(10000)*8 = 32.0
    # score = 32.0 * 1.0 (weight) * 1.5 (engagement) = 48.0
    row = {"type": "social-signal", "views": 10000, "likes": 200, "comments": 50}
    score = computeArtifactScore(row)
    assert score == pytest.approx(48.0)


# ---------------------------------------------------------------------------
# Batch I: Single self-attestation edge case (MAJOR #6)
# ---------------------------------------------------------------------------


def test_edge_case_single_self_attestation_only_yields_ungraded():
    """I2 edge case: one self-attestation -> TM≈5; below 20 floor -> ungraded."""
    skill = {"evidence": [{"type": "self-attestation"}]}
    # self-attestation: m=10, cap=10, weight=0.5 -> 5.0
    tm = computeTrustMagnitude(skill)
    assert tm == pytest.approx(5.0)
    # Compute grade: TM=5 < 20 -> ungraded
    grade = computeOverallTrustGrade(tm, 1, False)
    assert grade == "ungraded"
    # Also via convenience wrapper
    assert computeOverallTrustGradeFromSkill(skill) == "ungraded"


# ---------------------------------------------------------------------------
# Batch J: aGradedOriginsGte5 strict-semantics tests (issue #729)
# ---------------------------------------------------------------------------


def test_aGradedOriginsGte5_counts_fusion_recipe_origins_with_A_grade():
    """Fusion-recipe origins all A-graded in namedSkillMap -> True."""
    skill = {
        "evidence": [
            {
                "type": "fusion-recipe",
                "origins": ["s1", "s2", "s3", "s4", "s5"],
            }
        ]
    }
    namedSkillMap = {
        "s1": {"overallTrustGrade": "A"},
        "s2": {"overallTrustGrade": "A"},
        "s3": {"overallTrustGrade": "A"},
        "s4": {"overallTrustGrade": "S"},
        "s5": {"overallTrustGrade": "A"},
    }
    assert checkAGradedOriginsGte5(skill, namedSkillMap=namedSkillMap) is True


def test_aGradedOriginsGte5_counts_suite_components_with_A_grade():
    """Suite components all A-graded in genericSkillMap -> True (strict+expansion)."""
    skill = {
        "suiteComponents": ["c1", "c2", "c3", "c4", "c5"],
        "evidence": [],
    }
    genericSkillMap = {
        "c1": {"overallTrustGrade": "A"},
        "c2": {"overallTrustGrade": "S"},
        "c3": {"overallTrustGrade": "A"},
        "c4": {"overallTrustGrade": "A"},
        "c5": {"overallTrustGrade": "A"},
    }
    assert checkAGradedOriginsGte5(skill, genericSkillMap=genericSkillMap) is True


def test_aGradedOriginsGte5_dedupes_suite_and_fusion_overlap():
    """Overlap between suiteComponents and fusion-recipe origins is deduplicated.

    3 IDs in both sources + 2 unique fusion + 2 unique suite = 7 distinct origins.
    5 are A-graded. Returns True. Dedup verified (overlap counted once).
    """
    # shared: x1, x2, x3 appear in BOTH fusion-recipe origins and suiteComponents
    # uniqueFusion: f1, f2  unique to fusion-recipe
    # uniqueSuite: u1, u2   unique to suiteComponents
    skill = {
        "suiteComponents": ["x1", "x2", "x3", "u1", "u2"],
        "evidence": [
            {
                "type": "fusion-recipe",
                "origins": ["x1", "x2", "x3", "f1", "f2"],
            }
        ],
    }
    genericSkillMap = {
        "x1": {"overallTrustGrade": "A"},
        "x2": {"overallTrustGrade": "A"},
        "x3": {"overallTrustGrade": "A"},
        "f1": {"overallTrustGrade": "A"},
        "f2": {"overallTrustGrade": "A"},
        "u1": {"overallTrustGrade": "B"},  # not A/S
        "u2": {"overallTrustGrade": "C"},  # not A/S
    }
    # 7 distinct origins; 5 are A-graded (x1..x3, f1, f2) -> True
    result = checkAGradedOriginsGte5(skill, genericSkillMap=genericSkillMap)
    assert result is True


def test_aGradedOriginsGte5_evidence_rows_alone_do_not_count():
    """Bare verifier-attestation rows graded A with no fusion/suite -> False.

    This is the loose-semantic refutation per #729 strict ruling.
    """
    skill = {
        "evidence": [
            {"type": "verifier-attestation", "verifiers": 1, "grade": "A",
             "source": "https://v.example/1"},
            {"type": "verifier-attestation", "verifiers": 1, "grade": "A",
             "source": "https://v.example/2"},
            {"type": "verifier-attestation", "verifiers": 1, "grade": "A",
             "source": "https://v.example/3"},
            {"type": "verifier-attestation", "verifiers": 1, "grade": "A",
             "source": "https://v.example/4"},
            {"type": "verifier-attestation", "verifiers": 1, "grade": "A",
             "source": "https://v.example/5"},
        ]
    }
    genericSkillMap: dict = {}
    # Zero fusion-recipe rows and no suiteComponents -> no origins -> False
    assert checkAGradedOriginsGte5(skill, genericSkillMap=genericSkillMap) is False


def test_aGradedOriginsGte5_role_variant_origin_excluded():
    """Fusion-recipe with role='variant' origin excluded; only 4 non-variant A-graded -> False."""
    skill = {
        "evidence": [
            {
                "type": "fusion-recipe",
                "origins": [
                    {"id": "a", "grade": "A"},
                    {"id": "b", "grade": "A"},
                    {"id": "c", "grade": "A"},
                    {"id": "d", "grade": "A"},
                    {"id": "variant-x", "role": "variant", "grade": "S"},  # excluded
                ],
            }
        ]
    }
    genericSkillMap = {
        "a": {"overallTrustGrade": "A"},
        "b": {"overallTrustGrade": "A"},
        "c": {"overallTrustGrade": "A"},
        "d": {"overallTrustGrade": "A"},
        "variant-x": {"overallTrustGrade": "S"},
    }
    # variant-x excluded from origin set; only 4 A-graded non-variant origins -> False
    assert checkAGradedOriginsGte5(skill, genericSkillMap=genericSkillMap) is False


def test_aGradedOriginsGte5_unresolvable_origin_skipped():
    """Origins that resolve in neither map are skipped; 4 A-graded + 1 B -> False."""
    skill = {
        "evidence": [
            {
                "type": "fusion-recipe",
                "origins": ["r1", "r2", "r3", "r4", "unknown-skill"],
            }
        ]
    }
    genericSkillMap = {
        "r1": {"overallTrustGrade": "A"},
        "r2": {"overallTrustGrade": "A"},
        "r3": {"overallTrustGrade": "A"},
        "r4": {"overallTrustGrade": "A"},
        # "unknown-skill" is NOT in either map -> skipped
    }
    # 5 origins in origin set; 4 resolve to A, 1 unresolvable -> count=4 < 5 -> False
    assert checkAGradedOriginsGte5(skill, genericSkillMap=genericSkillMap) is False


# ---------------------------------------------------------------------------
# Batch K: v2 inheritance contract — 5 tests (Section H.3)
# ---------------------------------------------------------------------------


def test_inheritance_arxiv_inherits_with_multiplier_0_70():
    """H.3 test 1: named child inherits arxiv row from generic with 0.70 multiplier.

    Generic skill has one arxiv row (citations=500 -> raw=100, capped at 100).
    Named child has no own evidence, only genericSkillRef.
    The inherited row should contribute 100 * weight(1.0) * 0.70 = 70.0
    (freshness=1.0 since no lastVerified).
    """
    genericId = "generic-ml"
    generic = {
        "id": genericId,
        "evidence": [
            {
                "type": "arxiv",
                "citations": 500,  # 500/5=100, capped at 100
                "source": "https://arxiv.org/abs/2024.00001",
                "layer": "generic",
            }
        ],
    }
    named = {
        "id": "marco-ml",
        "genericSkillRef": genericId,
        "evidence": [],
    }
    genericSkillMap = {genericId: generic}
    tm = computeTrustMagnitude(named, genericSkillMap=genericSkillMap)
    # Expected: base 100 x weight 1.0 x freshness 1.0 x inheritMultiplier 0.70 = 70.0
    assert 65 < tm < 75, f"Expected ~70 but got {tm}"


def test_inheritance_named_layer_arxiv_no_discount():
    """H.3 test 2: arxiv row on the named skill itself (layer='named') — no 0.70 discount.

    When the arxiv row is attached directly to the named skill (same layer),
    _inheritMultiplierFor returns 1.0 and the full magnitude applies.
    """
    named = {
        "id": "marco-ml",
        "genericSkillRef": "some-generic",
        "evidence": [
            {
                "type": "arxiv",
                "citations": 500,  # 100 raw, capped; full weight
                "source": "https://arxiv.org/abs/2024.99999",
                "layer": "named",  # own layer — no inherit discount
            }
        ],
    }
    tm = computeTrustMagnitude(named, genericSkillMap={})
    # Expected: base 100 x weight 1.0 x inheritMultiplier 1.0 = 100.0
    assert 95 < tm <= 100.0, f"Expected ~100 (no discount) but got {tm}"


def test_inheritance_pinned_named_only_zero_or_passes_through():
    """H.3 test 3: pinned-named type (verifier-attestation) slipping through on a generic.

    Schema validator (PR #726) is the layer that rejects this at intake time.
    If a row slips through anyway, _inheritMultiplierFor returns 1.0 (defensive:
    does NOT silently zero it) — the compute layer is not the enforcement gate.
    """
    # Schema validator (PR #726) is the gate that rejects verifier-attestation
    # on generic nodes. compute is defensive and does not silently zero.
    genericId = "generic-with-verifier"
    generic = {
        "id": genericId,
        "evidence": [
            {
                "type": "verifier-attestation",
                "verifiers": 1,
                "source": "https://verifier.example/1",
                "layer": "generic",  # invalid per schema, but we test compute defensiveness
            }
        ],
    }
    named = {
        "id": "named-child",
        "genericSkillRef": genericId,
        "evidence": [],
    }
    genericSkillMap = {genericId: generic}
    # Should not crash; should contribute at face value (1.0 multiplier)
    tm = computeTrustMagnitude(named, genericSkillMap=genericSkillMap)
    # verifier-attestation: 30*1=30; weight 1.5 => 45.0 at face value (no discount)
    assert tm > 0, f"Expected non-zero contribution (1.0 multiplier), got {tm}"
    # The exact value should be 45.0 (30 * 1.5 * 1.0 inherit)
    assert abs(tm - 45.0) < 1.0, f"Expected ~45.0 (face-value, no discount), got {tm}"


def test_inheritance_multi_child_amplification_bounded():
    """H.3 test 4: N named children each inherit the same arxiv row from generic.

    Each child's TM includes the full inherited contribution (arxiv * 0.70).
    This documents the N-child amplification math from RFC Section 2.14.4:
    total contribution across 8 children = 8 * ~70 = ~560.
    """
    genericId = "shared-generic"
    generic = {
        "id": genericId,
        "evidence": [
            {
                "type": "arxiv",
                "citations": 500,  # 100 raw, capped
                "source": "https://arxiv.org/abs/2024.multi",
                "layer": "generic",
            }
        ],
    }
    genericSkillMap = {genericId: generic}

    children = []
    for i in range(8):
        children.append({
            "id": f"named-child-{i}",
            "genericSkillRef": genericId,
            "evidence": [],
        })

    total = sum(
        computeTrustMagnitude(child, genericSkillMap=genericSkillMap)
        for child in children
    )
    # Each child gets ~70.0; 8 * 70 = 560 (tolerance for freshness drift)
    assert 520 < total < 600, f"Expected ~560 across 8 children, got {total}"


def test_inheritance_multiplier_chain_visible_in_explain():
    """H.3 test 5: explainTrustMagnitude output annotates inherited rows.

    For a named skill with one inherited arxiv row (0.70 multiplier), the
    explain output must contain '0.70' AND ('inherited' OR '^').
    """
    from gaia_cli.trustMagnitude import explainTrustMagnitude

    genericId = "explain-generic"
    generic = {
        "id": genericId,
        "evidence": [
            {
                "type": "arxiv",
                "citations": 500,
                "source": "https://arxiv.org/abs/2024.explain",
                "layer": "generic",
            }
        ],
    }
    named = {
        "id": "named-for-explain",
        "genericSkillRef": genericId,
        "evidence": [],
    }
    genericSkillMap = {genericId: generic}

    output = explainTrustMagnitude(named, genericSkillMap=genericSkillMap)
    assert "0.70" in output, "Expected '0.70' in output, got: " + repr(output[:200])
    assert ("inherited" in output or "^" in output), "Expected inheritance annotation in output, got: " + repr(output[:200])


# ---------------------------------------------------------------------------
# Batch J: Apex lock-in tests (Issue #746)
# ---------------------------------------------------------------------------


def test_suiteBasedDepth2TraversalWorksForSuiteOnlyUltimates():
    """Verify suite-based depth-2 traversal works for suite-only ultimates (Issue #746 target 1).

    An ultimate skill has no fusion-recipe evidence, only suiteComponents.
    Its depth-1 suite component itself has suiteComponents.
    """
    ultimate = {
        "id": "ultimate-suite",
        "suiteComponents": ["d1-component"],
        "evidence": []
    }
    d1Node = {
        "id": "d1-component",
        "suiteComponents": ["d2-component"],
        "evidence": []
    }
    state = {
        "genericSkillMap": {
            "d1-component": d1Node,
            "d2-component": {"id": "d2-component"}
        },
        "namedSkillMap": {
            "d1-component": d1Node
        }
    }
    # Should resolve depth1 = {"d1-component"}, depth2 = {"d2-component"}.
    # Since len(depth2) >= 1, the predicate passes.
    assert checkDepth2OnlyReachableGte1(ultimate, state) is True

    # Test failure: if depth-1 node has no suiteComponents or fusion origins.
    ultimateNoD2 = {
        "id": "ultimate-suite",
        "suiteComponents": ["d1-component-leaf"],
        "evidence": []
    }
    stateNoD2 = {
        "genericSkillMap": {
            "d1-component-leaf": {"id": "d1-component-leaf"}
        },
        "namedSkillMap": {}
    }
    assert checkDepth2OnlyReachableGte1(ultimateNoD2, stateNoD2) is False


def test_missingSourceStartedAtOnAOrSEvidenceFailsTenure():
    """Verify missing sourceStartedAt on A/S evidence fails tenure predicate (Issue #746 target 2)."""
    # Case A: A/S row has no sourceStartedAt field
    skillNoField = {
        "id": "tenure-fail-no-field",
        "evidence": [
            {"type": "arxiv", "citations": 200, "grade": "A"}  # No sourceStartedAt
        ]
    }
    assert checkSourceTenureDaysGte180AorS(skillNoField) is False

    # Case B: A/S row has None for sourceStartedAt
    skillNone = {
        "id": "tenure-fail-none",
        "evidence": [
            {"type": "arxiv", "citations": 200, "grade": "A", "sourceStartedAt": None}
        ]
    }
    assert checkSourceTenureDaysGte180AorS(skillNone) is False

    # Case C: A/S row has empty string for sourceStartedAt
    skillEmpty = {
        "id": "tenure-fail-empty",
        "evidence": [
            {"type": "arxiv", "citations": 200, "grade": "A", "sourceStartedAt": ""}
        ]
    }
    assert checkSourceTenureDaysGte180AorS(skillEmpty) is False

    # Case D: A/S row has malformed sourceStartedAt
    skillMalformed = {
        "id": "tenure-fail-malformed",
        "evidence": [
            {"type": "arxiv", "citations": 200, "grade": "A", "sourceStartedAt": "invalid-date-format"}
        ]
    }
    assert checkSourceTenureDaysGte180AorS(skillMalformed) is False


def test_validSourceStartedAtOlderThan180DaysPassesTenure():
    """Verify valid sourceStartedAt older than 180 days passes tenure predicate (Issue #746 target 3)."""
    nowRef = datetime.datetime(2026, 7, 2, 12, 0, 0, tzinfo=datetime.timezone.utc)

    # Case A: Exactly 180 days ago: 2026-07-02 - 180 days = 2026-01-03
    started180Days = "2026-01-03T12:00:00Z"
    skill180 = {
        "id": "tenure-pass-180",
        "evidence": [
            {"type": "arxiv", "citations": 200, "grade": "A", "sourceStartedAt": started180Days}
        ]
    }
    assert checkSourceTenureDaysGte180AorS(skill180, now=nowRef) is True

    # Case B: Older than 180 days (e.g. 181 days ago): 2026-01-02
    started181Days = "2026-01-02T12:00:00Z"
    skill181 = {
        "id": "tenure-pass-181",
        "evidence": [
            {"type": "arxiv", "citations": 200, "grade": "A", "sourceStartedAt": started181Days}
        ]
    }
    assert checkSourceTenureDaysGte180AorS(skill181, now=nowRef) is True

    # Case C: Less than 180 days ago (e.g. 179 days ago): 2026-01-04
    started179Days = "2026-01-04T12:00:00Z"
    skill179 = {
        "id": "tenure-fail-179",
        "evidence": [
            {"type": "arxiv", "citations": 200, "grade": "A", "sourceStartedAt": started179Days}
        ]
    }
    assert checkSourceTenureDaysGte180AorS(skill179, now=nowRef) is False

    # Case D: Multi-row where one row passes and one fails (due to missing or young)
    skillMulti = {
        "id": "tenure-pass-multi",
        "evidence": [
            {"type": "arxiv", "citations": 200, "grade": "A", "sourceStartedAt": started179Days},
            {"type": "github-stars-own", "stars": 500, "grade": "A", "sourceStartedAt": started181Days}
        ]
    }
    assert checkSourceTenureDaysGte180AorS(skillMulti, now=nowRef) is True


def test_asOriginCountingUsesIntendedClosureAndDoesNotOvercount():
    """Verify A/S-origin counting uses intended suite/fusion origin closure and does not overcount (Issue #746 target 4).

    Deduplicates elements listed in both suiteComponents and fusion-recipe origins.
    """
    # We set up an origin list of 5 distinct A-graded skills.
    # If B is in both suiteComponents and fusion-recipe, it must only be counted once.
    # genericSkillMap will contain the definitions and grades.
    genericSkillMap = {
        "origin-a": {"id": "origin-a", "overallTrustGrade": "A"},
        "origin-b": {"id": "origin-b", "overallTrustGrade": "A"},
        "origin-c": {"id": "origin-c", "overallTrustGrade": "A"},
        "origin-d": {"id": "origin-d", "overallTrustGrade": "A"},
        "origin-e": {"id": "origin-e", "overallTrustGrade": "A"},
    }

    # Case 1: Deduplication between suiteComponents and fusion-recipe origins.
    # If "origin-b" is in both, total unique A/S graded origins = 5.
    # Should PASS checkAGradedOriginsGte5.
    skillDup = {
        "id": "host-skill",
        "suiteComponents": ["origin-a", "origin-b"],
        "evidence": [
            {
                "type": "fusion-recipe",
                "origins": ["origin-b", "origin-c", "origin-d", "origin-e"]
            }
        ]
    }
    assert checkAGradedOriginsGte5(skillDup, genericSkillMap=genericSkillMap) is True

    # Case 2: Overcounting prevention.
    # If we had 4 unique origins, but one was listed multiple times (which would count as 5 if not deduped),
    # it should FAIL checkAGradedOriginsGte5.
    skillOvercount = {
        "id": "host-skill",
        "suiteComponents": ["origin-a", "origin-b"],
        "evidence": [
            {
                "type": "fusion-recipe",
                "origins": ["origin-b", "origin-c", "origin-d"]
            }
        ]
    }
    # Unique origins are A, B, C, D (4 unique). Should fail because min required is 5.
    assert checkAGradedOriginsGte5(skillOvercount, genericSkillMap=genericSkillMap) is False

    # Case 3: Exclusion of variant roles.
    # "origin-e" is listed as variant, so only A, B, C, D count. Total 4. Should fail.
    genericSkillMapVariant = dict(genericSkillMap)
    genericSkillMapVariant["origin-e"] = {"id": "origin-e", "overallTrustGrade": "A", "role": "variant"}
    skillVariant = {
        "id": "host-skill",
        "suiteComponents": ["origin-a", "origin-b"],
        "evidence": [
            {
                "type": "fusion-recipe",
                "origins": ["origin-b", "origin-c", "origin-d", "origin-e"]
            }
        ]
    }
    assert checkAGradedOriginsGte5(skillVariant, genericSkillMap=genericSkillMapVariant) is False

