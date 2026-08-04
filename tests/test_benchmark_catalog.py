"""Benchmark source catalog tests for issue #1419."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from gaia_cli.benchmarkCatalog import (
    BenchmarkCatalogError,
    isBenchmarkScoringEligible,
    loadBenchmarkCatalog,
    projectionMetadata,
    pushAliasMap,
    resolveBenchmarkAlias,
    validateBenchmarkCatalog,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
HEX_A = "a" * 64
HEX_B = "b" * 64


def _eligible_row(**overrides):
    row = {
        "type": "benchmark-result",
        "benchmarkId": "humaneval@v1.0",
        "score": 0.75,
        "unit": "pass@1",
        "runAt": "2026-07-06T10:44:08Z",
        "provenance": "ci-reproduced",
        "attestor": "https://github.com/gaia-research/gaia-skill-tree/actions/runs/1@abc1234",
        "datasetHash": HEX_A,
        "benchmarkInputHash": HEX_B,
        "percentile": 90,
    }
    row.update(overrides)
    return row


def test_catalog_loads_and_validates_from_source_checkout():
    catalog = loadBenchmarkCatalog(REPO_ROOT)
    ids = {entry["id"] for entry in catalog["benchmarks"]}
    assert ids == {"alphaxiv-arxivqa@v1.0", "humaneval@v1.0", "mmlu@2024-03"}


def test_catalog_shape_humaneval_verified_push_enabled_mmlu_reported_scoring():
    catalog = loadBenchmarkCatalog(REPO_ROOT)
    by_id = {entry["id"]: entry for entry in catalog["benchmarks"]}

    alphaxiv = by_id["alphaxiv-arxivqa@v1.0"]
    assert alphaxiv["status"] == "reported"
    assert alphaxiv["mode"] == "external"
    assert alphaxiv["unit"] == "pct"
    assert alphaxiv["defaultProvenance"] == "reported"
    assert alphaxiv["appliesToGenericSkillRefs"] == ["literature-search"]
    assert alphaxiv["push"]["enabled"] is False
    assert alphaxiv["scoring"]["scoresTrustMagnitude"] is True

    humaneval = by_id["humaneval@v1.0"]
    assert humaneval["status"] == "verified"
    assert humaneval["mode"] == "internal-ci"
    assert humaneval["unit"] == "pass@1"
    assert humaneval["defaultProvenance"] == "verified"
    assert humaneval["push"]["enabled"] is True
    assert "humaneval" in humaneval["push"]["aliases"]

    mmlu = by_id["mmlu@2024-03"]
    assert mmlu["status"] == "reported"
    assert mmlu["push"]["enabled"] is False
    assert mmlu["scoring"]["scoresTrustMagnitude"] is True


def test_push_alias_map_only_exposes_verified_internal_ci_aliases():
    catalog = loadBenchmarkCatalog(REPO_ROOT)
    aliases = pushAliasMap(catalog)
    assert aliases == {"humaneval": "humaneval@v1.0"}
    assert "mmlu" not in aliases
    assert resolveBenchmarkAlias("humaneval", root=REPO_ROOT) == "humaneval@v1.0"
    with pytest.raises(BenchmarkCatalogError):
        resolveBenchmarkAlias("mmlu", root=REPO_ROOT)


def test_projection_metadata_is_catalog_driven():
    catalog = loadBenchmarkCatalog(REPO_ROOT)
    by_id = {entry["id"]: entry for entry in catalog["benchmarks"]}
    meta = projectionMetadata(by_id["humaneval@v1.0"])
    assert meta["name"] == "HumanEval"
    assert meta["status"] == "verified"
    assert meta["scoresTrustMagnitude"] is True
    assert "allowedProvenance" not in meta


def test_projection_metadata_preserves_generic_applicability():
    catalog = loadBenchmarkCatalog(REPO_ROOT)
    by_id = {entry["id"]: entry for entry in catalog["benchmarks"]}
    entry = dict(by_id["humaneval@v1.0"])
    entry["appliesToGenericSkillRefs"] = ["code-generation", "test-driven-development"]
    meta = projectionMetadata(entry)
    assert meta["appliesToGenericSkillRefs"] == ["code-generation", "test-driven-development"]


def test_catalog_schema_accepts_unique_generic_applicability_refs():
    catalog = json.loads((REPO_ROOT / "registry" / "benchmark-sources.json").read_text(encoding="utf-8"))
    catalog["benchmarks"][0]["appliesToGenericSkillRefs"] = ["code-generation", "test-driven-development"]
    validateBenchmarkCatalog(catalog, REPO_ROOT / "registry" / "schema" / "benchmarkSourceCatalog.schema.json")


def test_catalog_schema_rejects_duplicate_or_invalid_generic_applicability_refs():
    catalog = json.loads((REPO_ROOT / "registry" / "benchmark-sources.json").read_text(encoding="utf-8"))
    catalog["benchmarks"][0]["appliesToGenericSkillRefs"] = ["CodeGeneration", "code-generation", "code-generation"]
    with pytest.raises(BenchmarkCatalogError):
        validateBenchmarkCatalog(catalog, REPO_ROOT / "registry" / "schema" / "benchmarkSourceCatalog.schema.json")


def test_scoring_eligibility_uses_lanes_and_required_fields():
    catalog = loadBenchmarkCatalog(REPO_ROOT)
    assert isBenchmarkScoringEligible(_eligible_row(), catalog=catalog) is True
    assert isBenchmarkScoringEligible(_eligible_row(provenance="verified"), catalog=catalog) is True
    assert isBenchmarkScoringEligible(_eligible_row(provenance="pending"), catalog=catalog) is False
    assert isBenchmarkScoringEligible(_eligible_row(benchmarkId="mmlu@2024-03", provenance="mirrored", unit="pct"), catalog=catalog) is True
    assert isBenchmarkScoringEligible(_eligible_row(benchmarkId="alphaxiv-arxivqa@v1.0", provenance="reported", score=53.3, unit="pct", runAt=None, datasetHash=None, benchmarkInputHash=None, percentile=None), catalog=catalog) is True
    assert isBenchmarkScoringEligible(_eligible_row(benchmarkId="unknown@v1.0"), catalog=catalog) is False
    assert isBenchmarkScoringEligible(_eligible_row(provenance="verified", datasetHash=None), catalog=catalog) is False


def test_accepted_source_is_not_locked_to_one_row_lane():
    # Row lane is the source of truth: an accepted benchmark source is not
    # exclusive to a single lane. HumanEval is a verified source, but a
    # reported row on it still scores at the reported 1.0x lane, and a verified
    # row scores at 2.0x. Catalog status governs acceptance, not row identity.
    catalog = loadBenchmarkCatalog(REPO_ROOT)
    reported_on_humaneval = _eligible_row(
        provenance="reported", datasetHash=None, benchmarkInputHash=None, runAt=None, percentile=None
    )
    assert isBenchmarkScoringEligible(reported_on_humaneval, catalog=catalog) is True
    assert isBenchmarkScoringEligible(_eligible_row(provenance="verified"), catalog=catalog) is True


def test_catalog_schema_rejects_rejected_scoring(tmp_path):
    catalog = json.loads((REPO_ROOT / "registry" / "benchmark-sources.json").read_text(encoding="utf-8"))
    entry = next(item for item in catalog["benchmarks"] if item["id"] == "alphaxiv-arxivqa@v1.0")
    entry["status"] = "rejected"
    entry["scoring"]["scoresTrustMagnitude"] = True
    with pytest.raises(BenchmarkCatalogError):
        validateBenchmarkCatalog(catalog, REPO_ROOT / "registry" / "schema" / "benchmarkSourceCatalog.schema.json")
