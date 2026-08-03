#!/usr/bin/env python3
"""Phase 2B benchmark-source verifier for the evidence pipeline.

This script is intentionally read-only. It validates the benchmark-source catalog,
scans named-skill registry frontmatter for ``benchmark-result`` evidence rows, and
classifies each row against the catalog policy introduced for #1419.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

try:
    import yaml  # type: ignore
except ImportError as exc:  # pragma: no cover - PyYAML is part of the repo test env
    raise SystemExit("PyYAML is required to parse registry frontmatter") from exc

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from gaia_cli.benchmarkCatalog import (  # noqa: E402
    SCORING_PROVENANCE,
    BenchmarkCatalogError,
    benchmarkEntriesById,
    benchmarkCatalogSchemaPath,
    isBenchmarkScoringEligible,
    validateBenchmarkCatalog,
)

CATALOG_STATUSES = {"candidate", "registered", "mirrored", "verified", "rejected", "retired"}
NON_SCORING_PROVENANCE = {"mirrored", "pending"}
DEFAULT_REQUIRED_FIELDS = [
    "benchmarkId",
    "score",
    "unit",
    "runAt",
    "provenance",
    "attestor",
    "datasetHash",
    "benchmarkInputHash",
    "percentile",
]


def load_catalog(catalog_path: Path) -> dict[str, Any]:
    """Load and validate a benchmark-source catalog from an explicit path."""
    try:
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BenchmarkCatalogError(f"failed to load benchmark catalog from {catalog_path}: {exc}") from exc
    if not isinstance(catalog, dict):
        raise BenchmarkCatalogError(f"benchmark catalog at {catalog_path} is not a JSON object")

    schema_path = benchmarkCatalogSchemaPath(catalog_path)
    validateBenchmarkCatalog(catalog, schema_path)
    return catalog


def parse_frontmatter(text: str) -> dict[str, Any]:
    if not text.startswith("---\n"):
        return {}
    try:
        raw = text.split("---", 2)[1]
    except IndexError:
        return {}
    parsed = yaml.safe_load(raw) or {}
    return parsed if isinstance(parsed, dict) else {}


def iter_benchmark_rows(registry_root: Path) -> Iterable[dict[str, Any]]:
    named_root = registry_root / "registry" / "named"
    if not named_root.exists():
        return
    for skill_path in sorted(named_root.glob("*/*.md")):
        fm = parse_frontmatter(skill_path.read_text(encoding="utf-8"))
        skill_id = fm.get("id") or f"{skill_path.parent.name}/{skill_path.stem}"
        evidence = fm.get("evidence") or []
        if not isinstance(evidence, list):
            continue
        for index, row in enumerate(evidence):
            if isinstance(row, dict) and row.get("type") == "benchmark-result":
                yield {
                    "skillId": str(skill_id),
                    "path": str(skill_path.relative_to(registry_root)),
                    "evidenceIndex": index,
                    "row": row,
                }


def _is_missing(value: Any) -> bool:
    return value is None or value == ""


def _missing_required_fields(row: dict[str, Any], entry: dict[str, Any] | None) -> list[str]:
    scoring = (entry or {}).get("scoring") or {}
    required = scoring.get("requiredFields") or DEFAULT_REQUIRED_FIELDS
    return [field for field in required if _is_missing(row.get(field))]


def _percentile_issues(row: dict[str, Any]) -> list[str]:
    if "percentile" not in row or row.get("percentile") in (None, ""):
        return ["missing percentile"]
    try:
        percentile = float(row.get("percentile"))
    except (TypeError, ValueError):
        return ["non-numeric percentile"]
    if percentile < 0 or percentile > 100:
        return ["percentile outside 0..100"]
    return []


def classify_registry_row(item: dict[str, Any], catalog: dict[str, Any]) -> dict[str, Any]:
    """Classify one registry benchmark-result row against the catalog.

    ``hardBlocker`` is deliberately narrower than ``issues``: Phase 2B should
    stop ingestion for rejected/retired sources and scoring claims that violate
    catalog policy, while legacy citation-only rows remain report findings.
    """
    row = item["row"]
    entries = benchmarkEntriesById(catalog)
    bench_id = row.get("benchmarkId")
    provenance = row.get("provenance")
    issues: list[str] = []
    hard = False

    result = {
        "kind": "registry-row",
        "skillId": item["skillId"],
        "path": item["path"],
        "evidenceIndex": item["evidenceIndex"],
        "benchmarkId": bench_id or "<missing>",
        "provenance": provenance or "<missing>",
        "status": "unknown-benchmark",
        "issues": issues,
        "hardBlocker": False,
    }

    if not isinstance(bench_id, str) or not bench_id:
        issues.append("missing benchmarkId; treat as legacy citation-only vendor claim until cataloged")
        if provenance in SCORING_PROVENANCE:
            hard = True
        result.update({"status": "citation-only", "hardBlocker": hard})
        return result

    entry = entries.get(bench_id)
    if entry is None:
        issues.append("benchmarkId is not registered in registry/benchmark-sources.json")
        if provenance in SCORING_PROVENANCE:
            issues.append("scoring provenance used on unknown benchmarkId")
            hard = True
        result.update({"status": "unknown-benchmark", "hardBlocker": hard})
        return result

    source_status = entry.get("status")
    scoring = entry.get("scoring") or {}
    allowed = set(scoring.get("allowedProvenance") or [])
    scores_tm = bool(scoring.get("scoresTrustMagnitude"))

    if source_status in {"rejected", "retired"}:
        issues.append(f"benchmark source is {source_status}; registry row must not use it")
        result.update({"status": str(source_status), "hardBlocker": True})
        return result

    if source_status == "candidate":
        issues.append("candidate benchmark source; citation only until human promotion to verified")
        if provenance in SCORING_PROVENANCE:
            issues.append("scoring provenance used on candidate source")
            hard = True
        result.update({"status": "candidate-only", "hardBlocker": hard})
        return result

    if source_status in {"registered", "mirrored"} or not scores_tm:
        if source_status == "registered":
            issues.append("registered benchmark source is not verified; citation only")
        if source_status == "mirrored":
            issues.append("mirrored benchmark source is citation only and excluded from TM")
        if provenance in SCORING_PROVENANCE:
            issues.append("scoring provenance used on non-verified/non-scoring source")
            hard = True
        result.update({"status": "citation-only", "hardBlocker": hard})
        return result

    # Verified + scoring-capable catalog entry.
    if provenance not in allowed:
        issues.append(f"provenance {provenance!r} is not allowed for scoring on {bench_id}")
        if provenance in SCORING_PROVENANCE:
            hard = True
        status = "pending" if provenance in NON_SCORING_PROVENANCE or not provenance else "citation-only"
        result.update({"status": status, "hardBlocker": hard})
        return result

    missing = _missing_required_fields(row, entry)
    if missing:
        issues.append("missing reproducibility/scoring fields: " + ", ".join(missing))
    issues.extend(_percentile_issues(row))

    if isBenchmarkScoringEligible(row, catalog=catalog):
        result.update({"status": "scoring-eligible", "hardBlocker": False})
    else:
        # A verified source with allowed provenance but incomplete payload must
        # stay out of TM until a human accepts a complete reproduced row.
        result.update({"status": "blocked", "hardBlocker": False})
    return result


def load_candidate_manifest(path: Path | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    entries: list[Any]
    if path.suffix.lower() == ".jsonl":
        entries = [json.loads(line) for line in text.splitlines() if line.strip()]
    else:
        loaded = json.loads(text)
        if isinstance(loaded, dict):
            for key in ("candidates", "entries", "rows"):
                if isinstance(loaded.get(key), list):
                    entries = loaded[key]
                    break
            else:
                entries = [loaded]
        elif isinstance(loaded, list):
            entries = loaded
        else:
            raise ValueError("candidate manifest must be a JSON object, array, or JSONL records")
    out: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("candidate manifest entries must be JSON objects")
        out.append(entry)
    return out


def classify_candidate(entry: dict[str, Any], catalog: dict[str, Any], index: int) -> dict[str, Any]:
    bench_id = entry.get("benchmarkId") or "<missing>"
    declared_status = entry.get("status") or "candidate"
    issues: list[str] = []
    entries = benchmarkEntriesById(catalog)
    catalog_entry = entries.get(bench_id) if isinstance(bench_id, str) else None

    if declared_status not in CATALOG_STATUSES:
        issues.append(f"status {declared_status!r} is not a benchmark-source catalog status")
    if bench_id == "<missing>":
        issues.append("candidate is missing benchmarkId")
    elif catalog_entry is None:
        issues.append("candidate benchmarkId is not in the catalog yet")
    else:
        issues.append(f"catalog currently marks source as {catalog_entry.get('status')}")
    missing = entry.get("missing") or []
    if isinstance(missing, str):
        missing = [missing]
    if missing:
        issues.append("candidate missing: " + ", ".join(str(v) for v in missing))

    status = "candidate-only"
    if declared_status in {"rejected", "retired"}:
        status = str(declared_status)
    elif declared_status == "verified" and catalog_entry and catalog_entry.get("status") == "verified":
        status = "pending"

    return {
        "kind": "candidate-manifest",
        "manifestIndex": index,
        "target": entry.get("target") or "<unspecified>",
        "source": entry.get("source") or entry.get("sourceUrl") or "<unspecified>",
        "benchmarkId": bench_id,
        "declaredStatus": declared_status,
        "status": status,
        "issues": issues,
        "notes": entry.get("notes") or "",
        "hardBlocker": False,
    }


def build_report(results: list[dict[str, Any]], catalog_path: Path) -> str:
    registry_results = [r for r in results if r["kind"] == "registry-row"]
    candidate_results = [r for r in results if r["kind"] == "candidate-manifest"]
    status_counts = Counter(str(r["status"]) for r in results)
    hard_count = sum(1 for r in registry_results if r.get("hardBlocker"))

    lines = [
        "# Phase 2B Benchmark-Source Verification Report",
        "",
        f"Catalog: `{catalog_path}`",
        f"Registry benchmark rows scanned: {len(registry_results)}",
        f"Candidate manifest entries scanned: {len(candidate_results)}",
        f"Hard blockers in existing registry rows: {hard_count}",
        "",
        "## Status summary",
        "",
        "| Status | Count |",
        "| --- | ---: |",
    ]
    for status, count in sorted(status_counts.items()):
        lines.append(f"| `{status}` | {count} |")

    lines.extend(["", "## Registry rows", "", "| Skill | Row | Benchmark | Provenance | Status | Issues |", "| --- | ---: | --- | --- | --- | --- |"])
    for r in registry_results:
        issues = "; ".join(r["issues"]) if r["issues"] else "—"
        blocker = " **HARD BLOCKER**" if r.get("hardBlocker") else ""
        lines.append(
            f"| `{r['skillId']}` | {r['evidenceIndex']} | `{r['benchmarkId']}` | `{r['provenance']}` | `{r['status']}`{blocker} | {issues} |"
        )

    if candidate_results:
        lines.extend(["", "## Candidate manifest entries", "", "Candidate-only entries are never hard blockers. They require human promotion before catalog registration, benchmark catalog promotion, or `/gaia-ingest-batch`.", "", "| # | Target | Source | Benchmark | Declared | Status | Issues |", "| ---: | --- | --- | --- | --- | --- | --- |"])
        for r in candidate_results:
            issues = "; ".join(r["issues"]) if r["issues"] else "—"
            lines.append(
                f"| {r['manifestIndex']} | `{r['target']}` | {r['source']} | `{r['benchmarkId']}` | `{r['declaredStatus']}` | `{r['status']}` | {issues} |"
            )

    lines.extend([
        "",
        "## Human gate",
        "",
        "Machines classify benchmark rows and candidate sources. Humans decide whether a source is promoted in `registry/benchmark-sources.json` and whether verified/scoring benchmark-result rows may enter `/gaia-ingest-batch`.",
        "Only rows backed by a `verified` catalog source, allowed scoring provenance, and complete reproducibility fields may count toward Trust Magnitude.",
        "",
    ])
    return "\n".join(lines)


def run(args: argparse.Namespace) -> tuple[int, str, list[dict[str, Any]]]:
    catalog_path = Path(args.catalog).resolve()
    registry_root = Path(args.registry_root).resolve()
    catalog = load_catalog(catalog_path)

    results: list[dict[str, Any]] = []
    for item in iter_benchmark_rows(registry_root):
        results.append(classify_registry_row(item, catalog))
    for index, entry in enumerate(load_candidate_manifest(Path(args.candidate_manifest).resolve() if args.candidate_manifest else None), start=1):
        results.append(classify_candidate(entry, catalog, index))

    report = build_report(results, catalog_path)
    if args.report:
        Path(args.report).write_text(report + "\n", encoding="utf-8")
    hard_count = sum(1 for r in results if r["kind"] == "registry-row" and r.get("hardBlocker"))
    return (1 if args.check and hard_count else 0), report, results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify benchmark-result rows against registry/benchmark-sources.json")
    parser.add_argument("--catalog", default="registry/benchmark-sources.json", help="Path to benchmark-source catalog JSON")
    parser.add_argument("--registry-root", default=".", help="Repository root containing registry/named")
    parser.add_argument("--candidate-manifest", help="Optional JSON/JSONL benchmark-source candidate manifest")
    parser.add_argument("--report", help="Optional markdown report path")
    parser.add_argument("--check", action="store_true", help="Exit nonzero when hard blockers exist in registry rows")
    args = parser.parse_args(argv)

    try:
        code, report, _results = run(args)
    except (BenchmarkCatalogError, ValueError, OSError) as exc:
        print(f"benchmark source verification failed: {exc}", file=sys.stderr)
        return 2
    if not args.report:
        print(report)
    return code


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
