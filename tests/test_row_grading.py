"""Unit tests for derive_row_grade (Issue #761, #765)."""

import pytest

from gaia_cli.grading import derive_row_grade

THRESHOLDS = {
    "fusion-recipe":        {"S": 200, "A": 120, "B": 60,  "C": 30},
    "github-stars-own":     {"S": 88,  "A": 60,  "B": 35,  "C": 20},
    "proxy-containment":    {"S": 112, "A": 64,  "B": 32,  "C": 16},
    "verifier-attestation": {"S": 90,  "A": 54,  "B": 27,  "C": 14},
    "benchmark-result":     {"S": 90,  "A": 70,  "B": 40,  "C": 20},
    "arxiv":                {"S": 95,  "A": 70,  "B": 40,  "C": 15},
    "peer-review":          {"S": 88,  "A": 60,  "B": 35,  "C": 14},
    "repo-own":             {                    "B": 22,  "C": 9},
    "self-attestation":     {                              "C": 4},
    "social-signal":        {          "A": 60,  "B": 28,  "C": 12},
}


# --- arxiv: now S-capable (gradeCeiling lifted to S) ---

def test_arxiv_at_s_floor():
    assert derive_row_grade(95.0, "arxiv", THRESHOLDS, "S") == "S"

def test_arxiv_at_max_gets_s():
    assert derive_row_grade(100.0, "arxiv", THRESHOLDS, "S") == "S"

def test_arxiv_just_below_s_gets_a():
    assert derive_row_grade(94.9, "arxiv", THRESHOLDS, "S") == "A"

def test_arxiv_at_a_floor():
    assert derive_row_grade(70.0, "arxiv", THRESHOLDS, "S") == "A"

def test_arxiv_at_b_floor():
    assert derive_row_grade(40.0, "arxiv", THRESHOLDS, "S") == "B"

def test_arxiv_at_c_floor():
    assert derive_row_grade(15.0, "arxiv", THRESHOLDS, "S") == "C"

def test_arxiv_below_c_floor_returns_none():
    assert derive_row_grade(14.9, "arxiv", THRESHOLDS, "S") is None

def test_arxiv_old_ceiling_a_still_clamps():
    # backward-compat: if caller still passes "A" ceiling, S is clamped
    assert derive_row_grade(100.0, "arxiv", THRESHOLDS, "A") == "A"


# --- peer-review: now S-capable (gradeCeiling lifted to S) ---

def test_peer_review_at_s_floor():
    assert derive_row_grade(88.0, "peer-review", THRESHOLDS, "S") == "S"

def test_peer_review_above_s_floor():
    assert derive_row_grade(90.0, "peer-review", THRESHOLDS, "S") == "S"

def test_peer_review_just_below_s():
    assert derive_row_grade(87.9, "peer-review", THRESHOLDS, "S") == "A"

def test_peer_review_a_grade():
    assert derive_row_grade(60.0, "peer-review", THRESHOLDS, "S") == "A"

def test_peer_review_b_grade():
    assert derive_row_grade(35.0, "peer-review", THRESHOLDS, "S") == "B"

def test_peer_review_below_c():
    assert derive_row_grade(13.9, "peer-review", THRESHOLDS, "S") is None


# --- github-stars-own: S floor recalibrated from 140 to 88 ---

def test_github_stars_own_s_grade():
    assert derive_row_grade(200.0, "github-stars-own", THRESHOLDS, "S") == "S"

def test_github_stars_own_at_new_s_floor():
    assert derive_row_grade(88.0, "github-stars-own", THRESHOLDS, "S") == "S"

def test_github_stars_own_just_below_s():
    assert derive_row_grade(87.9, "github-stars-own", THRESHOLDS, "S") == "A"

def test_github_stars_own_at_a():
    assert derive_row_grade(60.0, "github-stars-own", THRESHOLDS, "S") == "A"

def test_github_stars_own_at_b():
    assert derive_row_grade(35.0, "github-stars-own", THRESHOLDS, "S") == "B"


# --- self-attestation: only C ceiling ---

def test_self_attestation_at_c_floor():
    assert derive_row_grade(4.0, "self-attestation", THRESHOLDS, "C") == "C"

def test_self_attestation_above_c_stays_c_due_to_ceiling():
    assert derive_row_grade(50.0, "self-attestation", THRESHOLDS, "C") == "C"

def test_self_attestation_below_c_floor():
    assert derive_row_grade(3.9, "self-attestation", THRESHOLDS, "C") is None


# --- repo-own: B ceiling (no A or S) ---

def test_repo_own_at_b_floor():
    assert derive_row_grade(22.0, "repo-own", THRESHOLDS, "B") == "B"

def test_repo_own_above_b_clamped_to_b():
    assert derive_row_grade(150.0, "repo-own", THRESHOLDS, "B") == "B"

def test_repo_own_at_c():
    assert derive_row_grade(9.0, "repo-own", THRESHOLDS, "B") == "C"

def test_repo_own_below_c():
    assert derive_row_grade(8.9, "repo-own", THRESHOLDS, "B") is None


# --- verifier-attestation: S floor recalibrated from 94 to 90 ---

def test_verifier_attestation_at_s_floor():
    assert derive_row_grade(90.0, "verifier-attestation", THRESHOLDS, "S") == "S"

def test_verifier_attestation_just_below_s():
    assert derive_row_grade(89.9, "verifier-attestation", THRESHOLDS, "S") == "A"


# --- benchmark-result: S floor recalibrated from 98 to 90 ---

def test_benchmark_result_at_s_floor():
    assert derive_row_grade(90.0, "benchmark-result", THRESHOLDS, "S") == "S"

def test_benchmark_result_at_a_floor():
    assert derive_row_grade(70.0, "benchmark-result", THRESHOLDS, "S") == "A"

def test_benchmark_result_just_below_s():
    assert derive_row_grade(89.9, "benchmark-result", THRESHOLDS, "S") == "A"


# --- edge cases ---

def test_none_thresholds_returns_none():
    assert derive_row_grade(100.0, "arxiv", None, "S") is None

def test_unknown_type_returns_none():
    assert derive_row_grade(100.0, "nonexistent-type", THRESHOLDS, "S") is None

def test_empty_thresholds_dict_returns_none():
    assert derive_row_grade(100.0, "arxiv", {}, "S") is None

def test_no_ceiling_does_not_clamp():
    assert derive_row_grade(200.0, "github-stars-own", THRESHOLDS, None) == "S"
