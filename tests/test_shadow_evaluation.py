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
    causes = {item["cause"]: item["status"] for item in shadow.evaluateShadow(a, ctx)["correctionCauses"]}
    # Resolved by #2257 (history kept in the catalog, no longer "triggered").
    assert causes["source-only-inheritance-merge"] == "resolved"
    # #2257: merge_evidence dedups per type, so the legacy call path is now
    # order independent and agrees with the shadow path.
    legacyA = tm.computeTrustMagnitude(a, generic)
    assert legacyA == tm.computeTrustMagnitude(b, generic) == 91.248
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
    causes = {item["cause"]: item["status"] for item in result["correctionCauses"]}
    assert causes["eligibility-before-dedup"] == "triggered"
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
    causes = {item["cause"]: item["status"] for item in suiteResult["correctionCauses"]}
    assert causes["component-before-suite-grade"] == "triggered"


def test_trust_number_grade_leak_is_flagged_and_does_not_become_contextual_gate_grade():
    skill = {"id": "owner/x", "evidence": [{"type": "fusion-recipe", "origins": [], "trustNumber": 250, "grade": "S", "class": "S", "sourceStartedAt": "2020-01-01"}]}
    result = shadow.evaluateShadow(skill, context())
    report = result["rows"][0]
    assert report["trustNumberFallback"]
    assert report["trustNumberFallbackGrade"] == "S"
    assert report["contextualGrade"] is None
    assert report["gateGradeRisk"]
    causes = {item["cause"]: item["status"] for item in result["correctionCauses"]}
    assert causes["named-row-grade-context"] == "triggered"


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


def test_contextual_peer_grade_precedes_shadow_s_witness_and_tenure_gates():
    ctx = context()
    ctx = replace(ctx, perRowGradeThresholds={"peer-review": {"A": 60, "B": 20}})
    skill = {"id": "x", "evidence": [
        row("github-stars-own", "https://github.com/o/x", stars=10000),
        row("arxiv", "https://papers.test/x", citations=1000),
        row("peer-review", "https://reviews.test/x", reviewers=1, grade="A", sourceStartedAt="2020-01-01"),
        row("peer-review", "https://reviews.test/y", reviewers=1, grade="A", sourceStartedAt="2020-01-01"),
    ]}
    result = shadow.evaluateShadow(skill, ctx)
    peer = next(item for item in result["rows"] if item["type"] == "peer-review")
    assert result["tmRaw"] >= 250
    assert peer["contextualGrade"] == "B"
    assert result["grade"] != "S"


def test_named_row_cannot_claim_generic_layer_and_inherit_discount():
    url = "https://reviews.test/shared"
    generic = {"g": {"id": "g", "evidence": [row("peer-review", url, reviewers=1)]}}
    named = {"id": "o/tool", "genericSkillRef": "g", "evidence": [
        row("peer-review", url, reviewers=1, layer="generic"),
    ]}
    result = shadow.evaluateShadow(named, context(generic))
    assert result["tmRaw"] == 30
    assert result["rows"][0]["boundedArtifactScore"] == 30


def test_inherited_verifier_standing_overrides_stale_generic_active_flag():
    generic = {"g": {"id": "g", "evidence": [row(
        "verifier-attestation", "https://verify.test/v", verifiers=1,
        verifierId="v1", verifierActiveRank=False,
    )]}}
    skill = {"id": "o/tool", "genericSkillRef": "g", "evidence": []}
    result = shadow.evaluateShadow(skill, context(generic, verifiers={"v1": True}))
    assert result["tmRaw"] == 0
    assert result["rows"] == []
    own = shadow.evaluateShadow({"id": "o/own", "genericSkillRef": "g", "evidence": [row(
        "verifier-attestation", "https://verify.test/own", verifiers=1, verifierId="v1",
    )]}, context(generic, verifiers={"v1": True}))
    assert own["tmRaw"] == 45
    inactive = shadow.evaluateShadow(skill, context(generic, verifiers={"v1": False}))
    assert inactive["tmRaw"] == 0
    assert result["grade"] == "ungraded"


def test_shadow_dedup_uses_scoring_magnitude_not_proxy_comparator():
    url = "https://github.com/o/repo"
    skill = {"id": "x", "evidence": [
        row("repo-own", url, commits=0, contributors=2),
        row("repo-own", url, commits=150, contributors=1),
    ]}
    result = shadow.evaluateShadow(skill, context())
    assert result["tmRaw"] == 4.8
    assert sorted(item["boundedArtifactScore"] for item in result["rows"]) == [0.0, 4.8]
    assert sum(item["boundedArtifactScore"] for item in result["rows"]) == result["tmRaw"]
    # Production's default comparator and dedup path remain untouched.
    assert tm.computeTrustMagnitude(skill) == 1.65


def test_bounded_row_report_matches_plateau_aggregate_across_multiple_rows():
    skill = {"id": "owner/reviews", "evidence": [
        row("peer-review", f"https://reviews.test/{count}", reviewers=count)
        for count in (3, 2, 1, 4)
    ]}
    result = shadow.evaluateShadow(skill, context())
    bounded = [item["boundedArtifactScore"] for item in result["rows"]]
    assert sum(bounded) == result["tmRaw"]
    assert sum(value > 0 for value in bounded) == 3
    assert sorted(bounded)[0] == 0.0


def test_row_report_distinguishes_raw_artifact_score_from_suite_bounded_contribution():
    skill = {"id": "owner/component", "suiteRef": "owner/suite", "evidence": [
        row("github-stars-own", "https://github.com/owner/suite", stars=10000),
    ]}
    result = shadow.evaluateShadow(skill, context())
    report = result["rows"][0]
    assert report["rawArtifactScore"] == report["artifactScore"]
    assert report["rawArtifactScore"] > 50
    assert report["boundedArtifactScore"] == 50
    assert "pre-plateau/pre-suite-cap" in report["artifactScoreMeaning"]


def test_registry_reports_partial_coverage_and_dependency_unknowns():
    bad = {"id": "bad", "evidence": [row("arxiv", "https://p.test/x", citations=float("nan"))]}
    healthy = {"id": "healthy", "evidence": [row("arxiv", "https://p.test/y", citations=100)]}
    suite = {"id": "suite", "suiteComponents": ["missing-component"], "evidence": [
        row("github-stars-own", "https://github.com/o/s", stars=10000),
        row("arxiv", "https://p.test/s", citations=1000),
        row("peer-review", "https://reviews.test/s", reviewers=3),
    ]}
    result = shadow.evaluateShadowRegistry([bad, healthy, suite], context())
    assert result["status"] == "partial"
    assert result["coverage"] == {"total": 3, "evaluated": 1, "notEvaluated": 2}
    by_id = {item["skillId"]: item for item in result["assessments"]}
    assert by_id["bad"]["status"] == "not-evaluated"
    assert "non-finite" in by_id["bad"]["reason"]
    assert by_id["suite"]["status"] == "not-evaluated"
    assert by_id["suite"]["unknownDependencyIds"] == ["missing-component"]


def test_transitive_missing_component_is_not_reported_as_full_suite_coverage():
    suite = {"id": "suite", "suiteComponents": ["middle"], "evidence": []}
    middle = {"id": "middle", "suiteComponents": ["absent-leaf"], "evidence": []}
    result = shadow.evaluateShadowRegistry([suite, middle], context())
    by_id = {item["skillId"]: item for item in result["assessments"]}
    assert by_id["suite"]["status"] == "not-evaluated"
    assert by_id["suite"]["unknownDependencyIds"] == ["absent-leaf"]
    assert by_id["middle"]["unknownDependencyIds"] == ["absent-leaf"]


def test_direct_suite_api_requires_direct_and_transitive_canonical_components():
    suite = {"id": "suite", "type": "fusion", "suiteComponents": ["absent"], "evidence": []}
    missingDirect = shadow.evaluateShadow(suite, context())
    assert missingDirect["status"] == "not-evaluated"
    assert missingDirect["unknownDependencyIds"] == ["absent"]

    middle = {"id": "middle", "suiteComponents": ["absent-leaf"], "evidence": []}
    transitiveContext = context(named={"middle": middle})
    transitive = shadow.evaluateShadow({**suite, "suiteComponents": ["middle"]}, transitiveContext)
    assert transitive["status"] == "not-evaluated"
    assert transitive["unknownDependencyIds"] == ["absent-leaf"]

    malformed = shadow.evaluateShadow(
        {**suite, "suiteComponents": ["middle"]},
        context(named={"middle": {"id": "wrong-id", "suiteComponents": []}}),
    )
    assert malformed["status"] == "not-evaluated"
    assert malformed["unknownDependencyIds"] == ["middle"]


def test_direct_suite_api_recomputes_stale_component_grades_like_registry_api():
    components = [
        {"id": f"owner/c{index}", "evidence": [
            row("github-stars-own", f"https://github.com/o/{index}", stars=10000),
        ]}
        for index in range(5)
    ]
    stale = {item["id"]: {**item, "overallTrustGrade": "B"} for item in components}
    suite = {
        "id": "owner/suite", "type": "fusion",
        "suiteComponents": [item["id"] for item in components], "evidence": [],
    }
    ctx = context(named=stale)
    direct = shadow.evaluateShadow(suite, ctx)
    registry = shadow.evaluateShadowRegistry([suite, *components], ctx)
    registrySuite = next(item for item in registry["assessments"] if item["skillId"] == suite["id"])
    assert direct["status"] == registrySuite["status"] == "evaluated"
    assert direct["namedMapDependencyGrades"] == registrySuite["namedMapDependencyGrades"]
    assert direct["gatePredicates"] == registrySuite["gatePredicates"]
    assert direct["fingerprint"] == registrySuite["fingerprint"]
    assert direct["namedMapDependencyGrades"]["owner/c0"] != "B"


def test_dependency_cycle_is_explicit_and_nan_infinity_are_rejected():
    cycle = [
        {"id": "a", "suiteComponents": ["b"], "evidence": []},
        {"id": "b", "suiteComponents": ["a"], "evidence": []},
    ]
    result = shadow.evaluateShadowRegistry(cycle, context())
    assert result["status"] == "partial"
    assert all(item["reason"] == "component dependency cycle" for item in result["assessments"])
    for invalid in (float("nan"), float("inf"), float("-inf")):
        assessed = shadow.evaluateShadow({"id": "x", "evidence": [row("arxiv", "https://p.test/x", citations=invalid)]}, context())
        assert assessed["status"] == "not-evaluated"
        assert "non-finite" in assessed["reason"]


def test_fingerprint_canonicalizes_evidence_order_but_binds_actual_context():
    rows = [row("arxiv", "https://p.test/a", citations=100), row("peer-review", "https://r.test/a", reviewers=2)]
    a = {"id": "x", "evidence": rows}
    b = {"id": "x", "evidence": list(reversed(rows))}
    assert shadow.evaluateShadow(a, context())["fingerprint"] == shadow.evaluateShadow(b, context())["fingerprint"]
    baseline = shadow.evaluateShadow(a, context())
    changedCatalog = replace(context(), benchmarkCatalog={"benchmarks": [{"id": "different"}]})
    assert baseline["fingerprint"] != shadow.evaluateShadow(a, changedCatalog)["fingerprint"]
    assert set(baseline["contextBinding"]["sourceManifest"]) == {
        "shadowEvaluation", "trustMagnitude", "benchmarkCatalog", "evidence",
        "grading", "structuralGraph",
    }
    originalFile = shadow.tm.__file__
    try:
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            changedSource = Path(directory) / "trustMagnitude.py"
            changedSource.write_bytes(Path(originalFile).read_bytes() + b"\\n# scorer identity change\\n")
            shadow.tm.__file__ = str(changedSource)
            assert baseline["fingerprint"] != shadow.evaluateShadow(a, context())["fingerprint"]
    finally:
        shadow.tm.__file__ = originalFile
    changedLabel = replace(context(), policyVersion="g7-v2", policyDigest="new-declared-digest")
    metadataOnly = shadow.evaluateShadow(a, changedLabel)
    assert metadataOnly["tmRaw"] == baseline["tmRaw"]
    assert metadataOnly["fingerprint"] != baseline["fingerprint"]
    assert metadataOnly["contextBinding"]["actualPolicyDigest"] == baseline["contextBinding"]["actualPolicyDigest"]


def test_explicit_evaluation_does_not_mutate_skill_or_maps():
    skill = {"id": "owner/x", "genericSkillRef": "g", "evidence": [row("peer-review", "https://e/x", reviewers=2)]}
    generic = {"g": {"id": "g", "evidence": [row("arxiv", "https://e/p", citations=100)]}}
    original = copy.deepcopy((skill, generic))
    shadow.evaluateShadow(skill, context(generic))
    assert (skill, generic) == original
