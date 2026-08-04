"""Canonical benchmark-source catalog helpers.

The benchmark-result evidence schema intentionally remains broad and stable:
rows may name any semver-ish ``benchmarkId`` that satisfies the frozen schema.
This module is the narrower allow-list used by projections, ``gaia push
--benchmark`` aliases, and Trust Magnitude scoring eligibility.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CATALOG_RELATIVE_PATH = Path("registry") / "benchmark-sources.json"
SCHEMA_RELATIVE_PATH = Path("registry") / "schema" / "benchmarkSourceCatalog.schema.json"
BUNDLED_CATALOG_PATH = Path(__file__).resolve().parent / "data" / "registry" / "benchmark-sources.json"
BUNDLED_SCHEMA_PATH = Path(__file__).resolve().parent / "data" / "registry" / "schema" / "benchmarkSourceCatalog.schema.json"

SCORING_LANES = frozenset({"verified", "reported"})
VERIFIED_PROVENANCE_ALIASES = frozenset({"verified", "ci-reproduced", "verifier-attested"})
REPORTED_PROVENANCE_ALIASES = frozenset({"reported", "mirrored"})
REJECTED_PROVENANCE_ALIASES = frozenset({"rejected", "pending", "unknown", "retired", "candidate"})
SOURCE_STATUS_ALIASES = {
    "verified": "verified",
    "reported": "reported",
    "registered": "reported",
    "mirrored": "reported",
    "rejected": "rejected",
    "pending": "rejected",
    "unknown": "rejected",
    "retired": "rejected",
    "candidate": "rejected",
}


class BenchmarkCatalogError(RuntimeError):
    """Raised when the benchmark catalog cannot be loaded or is invalid."""


def _repoRootCandidates(start: Path | None = None) -> list[Path]:
    base = (start or Path.cwd()).resolve()
    if base.is_file():
        base = base.parent
    return [base, *base.parents]


def _sourceCatalogPath(root: str | Path | None = None) -> Path | None:
    if root is not None:
        candidate = Path(root) / CATALOG_RELATIVE_PATH
        return candidate if candidate.exists() else None
    for base in _repoRootCandidates():
        candidate = base / CATALOG_RELATIVE_PATH
        if candidate.exists():
            return candidate
    moduleRepoCandidate = Path(__file__).resolve().parents[2] / CATALOG_RELATIVE_PATH
    if moduleRepoCandidate.exists():
        return moduleRepoCandidate
    return None


def _sourceSchemaPath(catalogPath: Path) -> Path | None:
    repoRoot = catalogPath.parent.parent
    candidate = repoRoot / SCHEMA_RELATIVE_PATH
    return candidate if candidate.exists() else None


def benchmarkCatalogPath(root: str | Path | None = None) -> Path:
    """Return the source-checkout catalog path, falling back to bundled data."""
    sourcePath = _sourceCatalogPath(root)
    if sourcePath is not None:
        return sourcePath
    if BUNDLED_CATALOG_PATH.exists():
        return BUNDLED_CATALOG_PATH
    raise BenchmarkCatalogError("benchmark source catalog not found")


def benchmarkCatalogSchemaPath(catalogPath: Path | None = None) -> Path | None:
    """Return the matching catalog schema path when available."""
    if catalogPath is not None:
        sourceSchema = _sourceSchemaPath(catalogPath)
        if sourceSchema is not None:
            return sourceSchema
    if BUNDLED_SCHEMA_PATH.exists():
        return BUNDLED_SCHEMA_PATH
    return None


def _validateUniqueIdsAndAliases(catalog: dict[str, Any]) -> None:
    seenIds: set[str] = set()
    seenAliases: dict[str, str] = {}
    for entry in catalog.get("benchmarks", []):
        benchId = entry.get("id")
        if benchId in seenIds:
            raise BenchmarkCatalogError(f"duplicate benchmarkId in catalog: {benchId}")
        seenIds.add(benchId)
        for alias in entry.get("aliases", []):
            owner = seenAliases.get(alias)
            if owner and owner != benchId:
                raise BenchmarkCatalogError(f"duplicate benchmark alias {alias!r} for {owner} and {benchId}")
            seenAliases[alias] = benchId
        for alias in entry.get("push", {}).get("aliases", []):
            owner = seenAliases.get(alias)
            if owner and owner != benchId:
                raise BenchmarkCatalogError(f"duplicate benchmark alias {alias!r} for {owner} and {benchId}")
            seenAliases[alias] = benchId


def _validatePolicy(catalog: dict[str, Any]) -> None:
    for entry in catalog.get("benchmarks", []):
        benchId = entry.get("id", "<unknown>")
        status = entry.get("status")
        scoring = entry.get("scoring") or {}
        push = entry.get("push") or {}

        if scoring.get("scoresTrustMagnitude"):
            sourceLane = normalizeBenchmarkSourceStatus(status)
            if sourceLane not in SCORING_LANES:
                raise BenchmarkCatalogError(f"{benchId}: status {status!r} must not score Trust Magnitude")
        if normalizeBenchmarkSourceStatus(status) == "rejected" and scoring.get("scoresTrustMagnitude"):
            raise BenchmarkCatalogError(f"{benchId}: status {status!r} must not score Trust Magnitude")
        if push.get("enabled") and (normalizeBenchmarkSourceStatus(status) != "verified" or entry.get("mode") != "internal-ci"):
            raise BenchmarkCatalogError(f"{benchId}: push aliases require verified internal-ci status")


def validateBenchmarkCatalog(catalog: dict[str, Any], schemaPath: str | Path | None = None) -> None:
    """Validate catalog schema and cross-entry policy invariants."""
    schemaCandidate = Path(schemaPath) if schemaPath is not None else None
    if schemaCandidate is not None and schemaCandidate.exists():
        try:
            import jsonschema  # type: ignore
        except ImportError as exc:  # pragma: no cover - jsonschema is present in CI/dev envs
            raise BenchmarkCatalogError("jsonschema is required to validate benchmark catalog") from exc
        schema = json.loads(schemaCandidate.read_text(encoding="utf-8"))
        validator = jsonschema.Draft7Validator(schema)
        errors = sorted(validator.iter_errors(catalog), key=lambda e: list(e.path))
        if errors:
            first = errors[0]
            location = "/".join(str(p) for p in first.path) or "<root>"
            raise BenchmarkCatalogError(f"benchmark catalog schema violation at {location}: {first.message}")
    _validateUniqueIdsAndAliases(catalog)
    _validatePolicy(catalog)


def loadBenchmarkCatalog(root: str | Path | None = None, *, validate: bool = True) -> dict[str, Any]:
    """Load the benchmark catalog from source checkout, else bundled package data."""
    path = benchmarkCatalogPath(root)
    try:
        catalog = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BenchmarkCatalogError(f"failed to load benchmark catalog from {path}: {exc}") from exc
    if not isinstance(catalog, dict):
        raise BenchmarkCatalogError(f"benchmark catalog at {path} is not a JSON object")
    if validate:
        validateBenchmarkCatalog(catalog, benchmarkCatalogSchemaPath(path))
    return catalog


def benchmarkEntriesById(catalog: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return catalog entries keyed by benchmarkId."""
    entries: dict[str, dict[str, Any]] = {}
    for entry in catalog.get("benchmarks", []):
        if isinstance(entry, dict) and isinstance(entry.get("id"), str):
            entries[entry["id"]] = entry
    return entries


def getBenchmarkEntry(benchmarkId: str, root: str | Path | None = None, catalog: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Return a catalog entry for ``benchmarkId`` or ``None`` when unknown."""
    activeCatalog = catalog if catalog is not None else loadBenchmarkCatalog(root)
    return benchmarkEntriesById(activeCatalog).get(benchmarkId)


def pushAliasMap(catalog: dict[str, Any]) -> dict[str, str]:
    """Return push-enabled aliases only.

    Non-verified or non-internal benchmark entries are intentionally omitted, so
    reported sources such as MMLU cannot be filed through ``gaia push
    --benchmark`` unless a future catalog entry explicitly enables them under
    the verified/internal policy.
    """
    aliases: dict[str, str] = {}
    for entry in catalog.get("benchmarks", []):
        if entry.get("status") != "verified":
            continue
        if entry.get("mode") != "internal-ci":
            continue
        push = entry.get("push") or {}
        if not push.get("enabled"):
            continue
        for alias in push.get("aliases") or entry.get("aliases") or []:
            aliases[str(alias)] = str(entry["id"])
    return aliases


def resolveBenchmarkAlias(shortName: str, fromFileId: str | None = None, root: str | Path | None = None) -> str:
    """Resolve a push-enabled short alias to a canonical benchmarkId."""
    aliases = pushAliasMap(loadBenchmarkCatalog(root))
    canonical = aliases.get(shortName)
    if canonical is None:
        supported = ", ".join(sorted(aliases)) or "<none>"
        raise BenchmarkCatalogError(
            f"unknown --benchmark {shortName!r}; supported push-enabled aliases: {supported}"
        )
    if fromFileId is not None:
        if fromFileId != canonical:
            raise BenchmarkCatalogError(
                f"--benchmark {shortName!r} resolves to {canonical!r} but result file benchmarkId is {fromFileId!r}"
            )
    return canonical


def projectionMetadata(entry: dict[str, Any]) -> dict[str, Any]:
    """Return projection metadata fields for one catalog entry."""
    scoring = entry.get("scoring") or {}
    out: dict[str, Any] = {
        "name": entry.get("name", entry.get("id")),
        "unit": entry.get("unit", ""),
        "provenance": entry.get("defaultProvenance", ""),
        "methodologyUrl": entry.get("methodologyUrl", ""),
        "status": entry.get("status", ""),
        "mode": entry.get("mode", ""),
        "scoresTrustMagnitude": bool(scoring.get("scoresTrustMagnitude")),
    }
    for key in ("sourceUrl", "sourceSnapshotDate", "harnessUrl", "notes", "appliesToGenericSkillRefs"):
        if key in entry:
            out[key] = entry[key]
    return out


def normalizeBenchmarkLane(value: Any) -> str:
    """Collapse benchmark-result provenance aliases to verified/reported/rejected."""
    raw = str(value or "").strip().lower()
    if raw in VERIFIED_PROVENANCE_ALIASES:
        return "verified"
    if raw in REPORTED_PROVENANCE_ALIASES:
        return "reported"
    return "rejected"


def normalizeBenchmarkSourceStatus(value: Any) -> str:
    """Collapse catalog statuses to verified/reported/rejected."""
    raw = str(value or "").strip().lower()
    return SOURCE_STATUS_ALIASES.get(raw, "rejected")


def benchmarkLaneMultiplier(value: Any) -> float:
    lane = normalizeBenchmarkLane(value)
    if lane == "verified":
        return 2.0
    if lane == "reported":
        return 1.0
    return 0.0


def benchmarkScoreBase(row: dict[str, Any]) -> float:
    """Return the normalized benchmark score before lane multiplier and cap.

    Prefer percentile when present. Otherwise normalize score by unit: pct stays
    0..100; pass@*, accuracy, and f1 expressed as 0..1 become 0..100; raw and
    other units are used as-is. The Trust Magnitude cap is applied by the caller.
    """
    if row.get("percentile") is not None:
        return float(row.get("percentile") or 0)
    rawScore = float(row.get("score", 0) or 0)
    unit = str(row.get("unit") or "").lower()
    if unit == "pct":
        return rawScore
    if unit in {"pass@1", "pass@10", "accuracy", "f1"} and rawScore <= 1.0:
        return rawScore * 100.0
    return rawScore


def benchmarkFinalMagnitude(row: dict[str, Any]) -> float:
    """Compute benchmark raw magnitude before the existing type cap/weight."""
    return benchmarkScoreBase(row) * benchmarkLaneMultiplier(row.get("provenance"))


def isBenchmarkScoringEligible(
    row: dict[str, Any],
    catalog: dict[str, Any] | None = None,
    root: str | Path | None = None,
) -> bool:
    """Return True iff a benchmark-result row may contribute to Trust Magnitude.

    This helper fails closed: if the catalog cannot be loaded, the benchmarkId is
    unknown, the catalog status normalizes to ``rejected``, the catalog disables
    Trust Magnitude scoring, the row provenance normalizes to ``rejected``, a
    verified-lane row lacks reproducibility fields, or catalog-required fields
    are absent, the row is not eligible. Legacy provenance aliases are accepted:
    ci-reproduced/verifier-attested → verified, mirrored → reported, and
    pending/candidate/retired/rejected/unknown → rejected.
    """
    if row.get("type") != "benchmark-result":
        return False
    try:
        activeCatalog = catalog if catalog is not None else loadBenchmarkCatalog(root)
    except BenchmarkCatalogError:
        return False
    benchId = row.get("benchmarkId")
    if not isinstance(benchId, str) or not benchId:
        return False
    entry = benchmarkEntriesById(activeCatalog).get(benchId)
    if entry is None:
        return False
    sourceLane = normalizeBenchmarkSourceStatus(entry.get("status"))
    if sourceLane == "rejected":
        return False
    scoring = entry.get("scoring") or {}
    if not scoring.get("scoresTrustMagnitude"):
        return False
    rowLane = normalizeBenchmarkLane(row.get("provenance"))
    if rowLane == "rejected":
        return False
    requiredFields = list(scoring.get("requiredFields") or ["benchmarkId", "score", "unit", "provenance", "attestor"])
    if rowLane == "verified":
        for field in ("runAt", "attestor", "datasetHash", "benchmarkInputHash"):
            if field not in requiredFields:
                requiredFields.append(field)
    for field in requiredFields:
        value = row.get(field)
        if value is None or value == "":
            return False
    return True
