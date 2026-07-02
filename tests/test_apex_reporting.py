"""Focused tests for apex gate operator-facing reporting."""

from __future__ import annotations

import datetime
import importlib.util
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent


def importScript(name: str):
    path = _REPO_ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_source_tenure_detail_distinguishes_missing_source_started_at():
    audit = importScript("auditApexAtG7")
    skill = {
        "evidence": [
            {"type": "verifier-attestation", "grade": "A", "source": "https://example.test/a"},
            {"type": "arxiv", "grade": "S", "source": "https://example.test/s"},
        ]
    }

    detail = audit.formatPredicateDetail("sourceTenureDaysGte180AorS", False, skill, {})

    assert "missing sourceStartedAt" in detail
    assert "2/2 A/S row" in detail
    assert "max age = 0d" in detail


def test_source_tenure_detail_distinguishes_insufficient_tenure():
    audit = importScript("auditApexAtG7")
    recent = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=30)).date().isoformat()
    skill = {
        "evidence": [
            {
                "type": "verifier-attestation",
                "grade": "A",
                "source": "https://example.test/recent",
                "sourceStartedAt": recent,
            }
        ]
    }

    detail = audit.formatPredicateDetail("sourceTenureDaysGte180AorS", False, skill, {})

    assert "insufficient tenure" in detail
    assert "< 180d" in detail
    assert "missing sourceStartedAt" not in detail


def test_a_graded_origins_detail_reports_deficit():
    audit = importScript("auditApexAtG7")
    skill = {"suiteComponents": ["origin-a", "origin-b"]}
    registryState = {
        "genericSkillMap": {
            "origin-a": {"overallTrustGrade": "A"},
            "origin-b": {"overallTrustGrade": "B"},
        },
        "namedSkillMap": {},
    }

    detail = audit.formatPredicateDetail("aGradedOriginsGte5", False, skill, registryState)

    assert "insufficient A/S origins" in detail
    assert "1/5" in detail
    assert "needs +4" in detail


def test_depth2_detail_reports_depth2_failure():
    audit = importScript("auditApexAtG7")
    skill = {"id": "ultimate", "suiteComponents": ["child"]}
    registryState = {
        "genericSkillMap": {"child": {"id": "child", "suiteComponents": []}},
        "namedSkillMap": {},
    }

    detail = audit.formatPredicateDetail("depth2OnlyReachableGte1", False, skill, registryState)

    assert "depth2 failure" in detail
    assert "1 depth-1 origin" in detail
    assert "0 depth-2 node" in detail


def test_pr_signed_detail_reports_gate_failure():
    audit = importScript("auditApexAtG7")
    skill = {"apexGateStatus": {"apexPromotionPrSigned": False}}

    detail = audit.formatPredicateDetail("apexPromotionPrSigned", False, skill, {})

    assert "PR-signed gate failure" in detail
    assert "no signed apex-promotion PR" in detail
