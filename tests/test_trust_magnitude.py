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
