"""Tests for the 4-tier verification workflow (verification.py).

Covers each predicate (community-verified, benchmark-verified,
security-reviewed, enterprise-ready) and the resolveTier roll-up.
"""

from __future__ import annotations

import datetime

import pytest

from gaia_cli.verification import (
    TIER_ORDER,
    filterScanEvents,
    isBenchmarkVerified,
    isCommunityVerified,
    isEnterpriseReady,
    isSecurityReviewed,
    maxGrade,
    resolveTier,
    stampFirstEvidenceAt,
)
pytestmark = [pytest.mark.integration]


UTC = datetime.timezone.utc


def now():
    """Fixed clock so tenure / scan-window math is deterministic."""
    return datetime.datetime(2026, 6, 16, 12, 0, 0, tzinfo=UTC)


def isoDaysAgo(n: int, ref=None) -> str:
    ref = ref or now()
    return (ref - datetime.timedelta(days=n)).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# isCommunityVerified
# ---------------------------------------------------------------------------


def testCommunityVerifiedNoEvidenceFails():
    skill = {"id": "x"}
    passed, reason = isCommunityVerified(skill, [])
    assert passed is False
    assert "no graded evidence" in reason


def testCommunityVerifiedWithGradedRowPasses():
    skill = {"id": "x"}
    evidence = [
        {"source": "https://example/a", "evaluator": "alice", "date": "2026-01-01", "grade": "C"},
    ]
    passed, reason = isCommunityVerified(skill, evidence)
    assert passed is True
    assert "graded evidence row" in reason


def testCommunityVerifiedFallsBackToLegacyClass():
    """Pre-grade evidence (only `class`) must still satisfy community-verified."""
    skill = {"id": "x"}
    evidence = [
        {"source": "https://example/b", "evaluator": "bob", "date": "2026-01-01", "class": "B"},
    ]
    passed, _ = isCommunityVerified(skill, evidence)
    assert passed is True


# ---------------------------------------------------------------------------
# isBenchmarkVerified
# ---------------------------------------------------------------------------


def testBenchmarkVerifiedNoBenchmarkRowFails():
    skill = {"id": "x"}
    evidence = [
        {"source": "https://x/repo", "evaluator": "a", "date": "2026-01-01", "type": "repo", "grade": "A"},
    ]
    passed, reason = isBenchmarkVerified(skill, evidence)
    assert passed is False
    assert "no benchmark-result" in reason


def testBenchmarkVerifiedWithBenchmarkResultRowPasses():
    skill = {"id": "x"}
    evidence = [
        {
            "source": "https://x/bench",
            "evaluator": "a",
            "date": "2026-01-01",
            "type": "benchmark-result",
            "grade": "A",
        },
    ]
    passed, reason = isBenchmarkVerified(skill, evidence)
    assert passed is True
    assert "benchmark-result" in reason


# ---------------------------------------------------------------------------
# isSecurityReviewed
# ---------------------------------------------------------------------------


def testSecurityReviewedNoEventsFails():
    skill = {"id": "x"}
    passed, reason = isSecurityReviewed(skill, [], now())
    assert passed is False
    assert "no clean scan" in reason


def testSecurityReviewed89DaysAgoPasses():
    skill = {"id": "x"}
    events = [
        {"action": "security_scan_passed", "at": isoDaysAgo(89)},
    ]
    passed, reason = isSecurityReviewed(skill, events, now())
    assert passed is True
    assert "scan passed" in reason


def testSecurityReviewed91DaysAgoFails():
    skill = {"id": "x"}
    events = [
        {"action": "security_scan_passed", "at": isoDaysAgo(91)},
    ]
    passed, reason = isSecurityReviewed(skill, events, now())
    assert passed is False
    assert "no clean scan" in reason


def testSecurityReviewedReadsTimestampFallback():
    """Events written with the canonical `timestamp` field also count."""
    skill = {"id": "x"}
    events = [
        {"action": "security_scan_passed", "timestamp": isoDaysAgo(10)},
    ]
    passed, _ = isSecurityReviewed(skill, events, now())
    assert passed is True


# ---------------------------------------------------------------------------
# isEnterpriseReady (boundary regressions)
# ---------------------------------------------------------------------------


def buildSkillWithBaseline(daysAgo: int) -> dict:
    return {
        "id": "x",
        "verification": {"firstEvidenceAt": isoDaysAgo(daysAgo)},
    }


def testEnterpriseReadyTenure30AndGradeAPasses():
    skill = buildSkillWithBaseline(30)
    evidence = [
        {"source": "https://x", "evaluator": "a", "date": "2026-01-01", "grade": "A"},
    ]
    passed, reason = isEnterpriseReady(skill, evidence, now())
    assert passed is True
    assert "Trust Grade A" in reason
    assert "tenure 30 days" in reason


def testEnterpriseReadyTenure29AndGradeAFails():
    """Boundary regression: 29 days < 30-day tenure floor."""
    skill = buildSkillWithBaseline(29)
    evidence = [
        {"source": "https://x", "evaluator": "a", "date": "2026-01-01", "grade": "A"},
    ]
    passed, reason = isEnterpriseReady(skill, evidence, now())
    assert passed is False
    assert "tenure 29 days" in reason


def testEnterpriseReadyTenure30AndGradeBFails():
    """Grade gate: B is below the >=A floor."""
    skill = buildSkillWithBaseline(30)
    evidence = [
        {"source": "https://x", "evaluator": "a", "date": "2026-01-01", "grade": "B"},
    ]
    passed, reason = isEnterpriseReady(skill, evidence, now())
    assert passed is False
    assert "Trust Grade B" in reason
    assert "need >=A" in reason


def testEnterpriseReadyTenure30AndGradeSPasses():
    """S satisfies the >=A floor."""
    skill = buildSkillWithBaseline(30)
    evidence = [
        {"source": "https://x", "evaluator": "a", "date": "2026-01-01", "grade": "S"},
    ]
    passed, _ = isEnterpriseReady(skill, evidence, now())
    assert passed is True


def testEnterpriseReadyMissingFirstEvidenceAtFails():
    """No firstEvidenceAt and no evidence_added timeline entry → fail."""
    skill = {"id": "x"}
    evidence = [
        {"source": "https://x", "evaluator": "a", "date": "2026-01-01", "grade": "A"},
    ]
    passed, reason = isEnterpriseReady(skill, evidence, now())
    assert passed is False
    assert "no firstEvidenceAt" in reason


def testEnterpriseReadyFallsBackToTimelineEvidenceAdded():
    """If firstEvidenceAt isn't set, the earliest evidence_added timeline event
    is used as the tenure baseline."""
    skill = {
        "id": "x",
        "timeline": [
            {"action": "evidence_added", "timestamp": isoDaysAgo(45)},
            {"action": "evidence_added", "timestamp": isoDaysAgo(10)},
        ],
    }
    evidence = [
        {"source": "https://x", "evaluator": "a", "date": "2026-01-01", "grade": "A"},
    ]
    passed, reason = isEnterpriseReady(skill, evidence, now())
    assert passed is True
    assert "tenure 45 days" in reason


# ---------------------------------------------------------------------------
# resolveTier
# ---------------------------------------------------------------------------


def testResolveTierReturnsHighestPassedAndFullMap():
    """A skill that passes all four tiers surfaces enterprise-ready and
    returns a status map with one entry per tier."""
    skill = buildSkillWithBaseline(60)
    evidence = [
        {
            "source": "https://x/bench",
            "evaluator": "a",
            "date": "2026-01-01",
            "type": "benchmark-result",
            "grade": "S",
        },
    ]
    scanEvents = [
        {"action": "security_scan_passed", "at": isoDaysAgo(5)},
    ]
    highest, statusMap = resolveTier(skill, evidence, scanEvents, now())
    assert highest == "enterprise-ready"
    assert set(statusMap.keys()) == set(TIER_ORDER)
    for tier in TIER_ORDER:
        assert statusMap[tier]["passed"] is True
        assert isinstance(statusMap[tier]["reason"], str)


def testResolveTierReturnsCommunityVerifiedWhenOnlyThatPasses():
    skill = {"id": "x"}  # no firstEvidenceAt → enterprise-ready blocked
    evidence = [
        # graded but not benchmark-result; grade C blocks enterprise even with tenure
        {
            "source": "https://x/repo",
            "evaluator": "a",
            "date": "2026-01-01",
            "type": "repo",
            "grade": "C",
        },
    ]
    highest, statusMap = resolveTier(skill, evidence, [], now())
    assert highest == "community-verified"
    assert statusMap["community-verified"]["passed"] is True
    assert statusMap["benchmark-verified"]["passed"] is False
    assert statusMap["security-reviewed"]["passed"] is False
    assert statusMap["enterprise-ready"]["passed"] is False


def testResolveTierReturnsNoneWhenNothingPasses():
    skill = {"id": "x"}
    highest, statusMap = resolveTier(skill, [], [], now())
    assert highest is None
    for tier in TIER_ORDER:
        assert statusMap[tier]["passed"] is False


# ---------------------------------------------------------------------------
# Helper coverage
# ---------------------------------------------------------------------------


def testMaxGradeReadsLegacyClass():
    evidence = [
        {"source": "x", "evaluator": "a", "date": "2026-01-01", "class": "A"},
        {"source": "y", "evaluator": "a", "date": "2026-01-01", "class": "C"},
    ]
    assert maxGrade(evidence) == "A"


def testFilterScanEventsExtractsOnlyMatchingAction():
    timeline = [
        {"action": "evidence_added", "timestamp": isoDaysAgo(10)},
        {"action": "security_scan_passed", "at": isoDaysAgo(5)},
        {"action": "rank_up", "timestamp": isoDaysAgo(3)},
    ]
    events = filterScanEvents(timeline)
    assert len(events) == 1
    assert events[0]["action"] == "security_scan_passed"


def testStampFirstEvidenceAtSetsAndIsIdempotent():
    record: dict = {}
    first = stampFirstEvidenceAt(record, "2026-01-01T00:00:00Z")
    assert first == "2026-01-01T00:00:00Z"
    assert record["verification"]["firstEvidenceAt"] == "2026-01-01T00:00:00Z"

    # Second call must not overwrite.
    second = stampFirstEvidenceAt(record, "2026-06-01T00:00:00Z")
    assert second is None
    assert record["verification"]["firstEvidenceAt"] == "2026-01-01T00:00:00Z"


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
