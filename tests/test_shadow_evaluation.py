import copy
import datetime as dt
from dataclasses import replace

from gaia_cli import shadowEvaluation as shadow
from gaia_cli import trustMagnitude as tm

UTC = dt.timezone.utc
NOW = dt.datetime(2026, 10, 25, tzinfo=UTC)
CATALOG = {"benchmarks": [{
    "id": "bench-v1", "status": "reported",
    "scoring": {"scoresTrustMagnitude": True, "requiredFields": [
        "benchmarkId", "score", "unit", "provenance", "attestor",
    ]},
}]}


def context(generic=None, named=None, verifiers=None):
    return shadow.ShadowEvaluationContext(
        evaluationAtUTC=NOW,
        policyVersion="g7-v1", policyDigest="policy-digest",
        benchmarkCatalog=CATALOG, benchmarkCatalogDigest="catalog-digest",
        registryRevision="abc123", canonicalInputDigest="input-digest",
        genericSkillMap=generic or {}, namedSkillMap=named or {},
        verifierStanding=verifiers or {},
        perRowGradeThresholds={"github-stars-own": {"A": 100, "B": 50}, "peer-review": {"A": 60, "B": 30}},
        gradeCeiling={}, gradeThresholds={"S": 250, "A": 100, "B": 50, "C": 20},
    )


def row(kind, url, **values):
    return {"type": kind, "source": url, **values}


def test_no_change_and_contextual_clock_replay_are_stable():
    skill = {"id": "owner/tool", "genericSkillRef": "generic/tool", "evidence": [row("peer-review", "https://e/review", reviewers=3, lastVerified="2025-01-01T00:00:00Z")]}
    ctx = context({"generic/tool": {"id": "generic/tool", "evidence": []}})
    result = shadow.evaluateShadow(skill, ctx)
    assert result["status"] == "evaluated"
    assert result["tmRaw"] == tm.computeTrustMagnitude(skill, ctx.genericSkillMap, evaluationAtUTC=NOW, benchmarkCatalog=CATALOG, shadowCorrections=True)
    assert result["fingerprint"] == shadow.evaluateShadow(copy.deepcopy(skill), ctx)["fingerprint"]
    assert result["canonicalStars"] is None
    assert result["gradeCeilingProposal"] == 3


def test_missing_generic_or_catalog_context_is_not_evaluated_not_zero():
    skill = {"id": "x", "genericSkillRef": "missing", "evidence": []}
    result = shadow.evaluateShadow(skill, context())
    assert result["status"] == "not-evaluated"
    assert "generic context not resolved" in result["reason"]
    missingCatalog = replace(context(), benchmarkCatalog={})
    result = shadow.evaluateShadow({"id": "x", "evidence": []}, missingCatalog)
    assert result["status"] == "not-evaluated"
    assert "benchmark catalog context" in result["reason"]


def test_source_merge_is_cross_type_order_independent_and_tracks_row_layer():
    url = "https://github.com/o/repo"
    generic = {"g": {"id": "g", "evidence": [row("arxiv", url, citations=100)]}}
    ownRows = [row("github-stars-own", url, stars=1000), row("repo-own", url, commits=816, contributors=2)]
    a = {"id": "o/a", "genericSkillRef": "g", "evidence": ownRows}
    b = {**a, "evidence": list(reversed(ownRows))}
    ctx = context(generic)
    assert shadow.evaluateShadow(a, ctx)["tmRaw"] == shadow.evaluateShadow(b, ctx)["tmRaw"]
    assert shadow.evaluateShadow(a, ctx)["tmRaw"] == 91.248
    # Legacy call path remains unchanged until the canonical rollout gate.
    assert tm.computeTrustMagnitude(a, generic) != tm.computeTrustMagnitude(b, generic)
    # A same-URL own row must not erase the generic row when evidence types differ.
    onlyStars = {**a, "evidence": [row("github-stars-own", url, stars=1000)]}
    assert shadow.evaluateShadow(onlyStars, ctx)["tmRaw"] == 84.0
    # Source-less own rows retain named-layer provenance (no inheritance discount).
    noSource = {"id": "o/no-source", "genericSkillRef": "g", "evidence": [row("peer-review", "", reviewers=3)]}
    assert shadow.evaluateShadow(noSource, ctx)["tmRaw"] == 104.0


def test_ineligible_benchmark_winner_is_filtered_before_dedup():
    url = "https://example.test/result"
    invalid = row("benchmark-result", url, benchmarkId="bench-v1", percentile=99, score=0, unit="pct", provenance="rejected", attestor="x")
    valid = row("benchmark-result", url, benchmarkId="bench-v1", percentile=20, score=20, unit="pct", provenance="reported", attestor="x")
    skill = {"id": "x", "evidence": [invalid, valid]}
    result = shadow.evaluateShadow(skill, context())
    assert result["tmRaw"] > 0
    assert result["tmRaw"] == 20 * 1.4
    assert shadow.evaluateShadow({**skill, "evidence": [valid, invalid]}, context())["tmRaw"] == result["tmRaw"]


def test_revoked_verifier_does_not_hide_active_duplicate():
    url = "https://example.test/attestation"
    revoked = row("verifier-attestation", url, verifiers=20, verifierId="v1", verifierActiveRank=False)
    active = row("verifier-attestation", url, verifiers=1, verifierId="v2", verifierActiveRank=True)
    result = shadow.evaluateShadow({"id": "x", "evidence": [revoked, active]}, context(verifiers={"v1": False, "v2": True}))
    assert result["tmRaw"] == 45
    missing = shadow.evaluateShadow({"id": "x", "evidence": [active]}, context())
    assert missing["status"] == "not-evaluated"
    assert "verifier standing not resolved" in missing["reason"]


def test_component_grades_are_computed_before_suite_apex_predicate():
    components = []
    stale = {}
    for index in range(5):
        sid = f"owner/c{index}"
        components.append({"id": sid, "evidence": [row("github-stars-own", f"https://github.com/o/{index}", stars=10000)]})
        stale[sid] = {"id": sid, "overallTrustGrade": "B"}
    suite = {
        "id": "owner/suite", "suiteComponents": [item["id"] for item in components],
        "evidence": [
            row("github-stars-own", "https://github.com/o/suite", stars=1_000_000),
            row("arxiv", "https://papers.test/a", citations=500),
            row("peer-review", "https://review.test/a", reviewers=3, sourceStartedAt="2020-01-01"),
        ],
    }
    result = shadow.evaluateShadowRegistry([suite, *components], context(named=stale))
    assert result["status"] == "evaluated"
    suiteResult = next(item for item in result["assessments"] if item["skillId"] == suite["id"])
    assert suiteResult["grade"] == "S"
    assert suiteResult["gatePredicates"]["aGradedOriginsGte5"] is True


def test_trust_number_grade_leak_is_flagged_and_does_not_become_contextual_gate_grade():
    skill = {"id": "owner/x", "evidence": [{"type": "fusion-recipe", "origins": [], "trustNumber": 250, "grade": "S", "class": "S", "sourceStartedAt": "2020-01-01"}]}
    result = shadow.evaluateShadow(skill, context())
    report = result["rows"][0]
    assert report["trustNumberFallback"]
    assert report["trustNumberFallbackGrade"] == "S"
    assert report["contextualGrade"] is None
    assert report["gateGradeRisk"]


def test_future_date_is_not_evaluated_malformed_legacy_date_is_flagged():
    future = {"id": "x", "evidence": [row("peer-review", "https://e/f", reviewers=1, lastVerified="2027-01-01") ]}
    assert shadow.evaluateShadow(future, context())["status"] == "not-evaluated"
    malformed = {"id": "x", "evidence": [row("peer-review", "https://e/m", reviewers=1, lastVerified="not-a-date") ]}
    result = shadow.evaluateShadow(malformed, context())
    assert result["status"] == "evaluated"
    assert "malformed legacy date" in result["temporalWarnings"][0]


def test_threshold_crossing_and_fingerprint_inputs_are_bound():
    skill = {"id": "x", "evidence": [row("github-stars-own", "https://github.com/o/x", stars=10000)]}
    base = shadow.evaluateShadow(skill, context())
    lower = shadow.evaluateShadow({**skill, "evidence": [{**skill["evidence"][0], "stars": 1000}]}, context())
    assert (base["tmRaw"], base["grade"], base["gradeCeilingProposal"]) == (105, "A", 4)
    assert (lower["tmRaw"], lower["grade"], lower["gradeCeilingProposal"]) == (70, "B", 3)
    otherTime = shadow.evaluateShadow(skill, context().__class__(**{**context().__dict__, "evaluationAtUTC": NOW + dt.timedelta(days=1)}))
    assert base["fingerprint"] != otherTime["fingerprint"]


def test_explicit_evaluation_does_not_mutate_skill_or_maps():
    skill = {"id": "owner/x", "genericSkillRef": "g", "evidence": [row("peer-review", "https://e/x", reviewers=2)]}
    generic = {"g": {"id": "g", "evidence": [row("arxiv", "https://e/p", citations=100)]}}
    original = copy.deepcopy((skill, generic))
    shadow.evaluateShadow(skill, context(generic))
    assert (skill, generic) == original
