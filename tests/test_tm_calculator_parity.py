"""tests/test_tm_calculator_parity.py

Verify exact scoring and gate parity between docs/js/tm-calculator.js
and src/gaia_cli/trustMagnitude.py for Issue #1722.
"""

import math
import pytest
from gaia_cli.trustMagnitude import (
    computeTrustMagnitude,
    computeOverallTrustGradeFromSkill,
    computeArtifactScore,
    TYPE_CAPS,
)


def test_logarithmic_star_curve_landmarks():
    """Verify landmarks on the logarithmic adoption curve match the canonical formula."""
    landmarks = [
        (1000, 70.0),
        (10000, 105.0),
        (50000, 35.0 * math.log10(50000 / 10.0)),   # ~129.46
        (100000, 140.0),
        (250000, 35.0 * math.log10(250000 / 10.0)), # ~153.93
        (1000000, 175.0),                            # capped at 175.0
    ]

    for stars, expected in landmarks:
        row = {"type": "github-stars-own", "stars": stars}
        score = computeArtifactScore(row)
        assert score == pytest.approx(expected, abs=0.01), f"Mismatch at {stars} stars"


def test_preset_popular_weak_parity():
    """Preset 1: 250k stars with no independent evidence resolves to Grade A (not S)."""
    skill = {
        "id": "fixture/popular-weak",
        "evidence": [
            {"type": "github-stars-own", "stars": 250000}
        ]
    }
    tm = computeTrustMagnitude(skill)
    grade = computeOverallTrustGradeFromSkill(skill)

    assert tm == pytest.approx(153.93, abs=0.01)
    assert grade == "A", "250k stars alone must resolve to Grade A (S floor is 250)"


def test_preset_popular_corroborated_parity():
    """Preset 2: 100k stars + verified benchmark + 2 verifiers clears Grade S."""
    skill = {
        "id": "fixture/popular-corroborated",
        "evidence": [
            {"type": "github-stars-own", "stars": 100000},
            {
                "type": "benchmark-result",
                "score": 85,
                "percentile": 85,
                "provenance": "verified",
                "unit": "accuracy",
                "benchmarkId": "humaneval@v1.0",
                "attestor": "eval-bot",
                "runAt": "2026-09-01T00:00:00Z",
                "datasetHash": "hash",
                "benchmarkInputHash": "hash",
            },
            {"type": "verifier-attestation", "verifiers": 2},
        ]
    }
    tm = computeTrustMagnitude(skill)
    grade = computeOverallTrustGradeFromSkill(skill)

    # 140 (stars) + 140 (benchmark 100 max * 1.4) + 90 (verifier 60 * 1.5) = 370.0
    assert tm == pytest.approx(370.0, abs=0.01)
    assert grade == "S", "Satisfies TM >= 250, 3 types, and strong witness"


def test_preset_low_stars_high_evidence_parity():
    """Preset 3: 800 stars with strong multi-channel independent evidence clears Grade S."""
    skill = {
        "id": "fixture/low-stars-high-evidence",
        "evidence": [
            {"type": "github-stars-own", "stars": 800},
            {
                "type": "benchmark-result",
                "score": 85,
                "percentile": 85,
                "provenance": "verified",
                "unit": "accuracy",
                "benchmarkId": "humaneval@v1.0",
                "attestor": "eval-bot",
                "runAt": "2026-09-01T00:00:00Z",
                "datasetHash": "hash",
                "benchmarkInputHash": "hash",
            },
            {"type": "verifier-attestation", "verifiers": 1},
            {"type": "peer-review", "reviewers": 1},
        ]
    }
    tm = computeTrustMagnitude(skill)
    grade = computeOverallTrustGradeFromSkill(skill)

    # Stars: 35 * log10(80) = ~66.61
    # Benchmark: 100 * 1.4 = 140.0
    # Verifier: 30 * 1.5 = 45.0
    # Peer review: 25 * 1.2 = 30.0
    # Sum: 281.61
    assert tm == pytest.approx(281.61, abs=0.01)
    assert grade == "S", "Satisfies TM >= 250, 4 types, and independent witness"


def test_preset_high_tm_no_witness_parity():
    """Preset 4: TM >= 250 and >= 3 types, but NO independent witness must resolve to Grade A."""
    skill = {
        "id": "fixture/high-tm-no-witness",
        "evidence": [
            {"type": "github-stars-own", "stars": 100000},
            {"type": "proxy-containment", "externalStars": 150000},
            {"type": "social-signal", "views": 100000},
        ]
    }
    tm = computeTrustMagnitude(skill)
    grade = computeOverallTrustGradeFromSkill(skill)

    # 140 (stars) + 120 (proxy) + 40 (social) = 300.0 TM
    assert tm == pytest.approx(300.0, abs=0.01)
    assert grade == "A", "Must be held at Grade A because independent witness is absent"


def test_preset_seed_baseline_parity():
    """Preset 5: 50 stars + self-attestation resolves to Grade C."""
    skill = {
        "id": "fixture/seed-baseline",
        "evidence": [
            {"type": "github-stars-own", "stars": 50},
            {"type": "self-attestation"},
        ]
    }
    tm = computeTrustMagnitude(skill)
    grade = computeOverallTrustGradeFromSkill(skill)

    # Stars: 35 * log10(5) = ~24.46
    # Self-attestation: 10 * 0.5 = 5.0
    # Sum: 29.46 TM
    assert tm == pytest.approx(29.46, abs=0.01)
    assert grade == "C", "TM >= 20 resolves to Grade C"
