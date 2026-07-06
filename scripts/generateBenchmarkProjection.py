#!/usr/bin/env python3
"""Generate per-benchmark JSON projections for ``docs/api/v1/benchmarks/``.

For each ``benchmarkId`` found across all ``registry/named/**/*.md`` evidence
rows of type ``benchmark-result``, writes one file:

    docs/api/v1/benchmarks/<benchmark-slug>.json

and updates ``docs/api/v1/benchmarks/index.json`` with the set of live
benchmarks (idempotent — ``generatedAt: null`` per Sprint D convention).

Row shape (written to each file):
    {
      "skillId":            "contributor/slug",
      "score":              <number>,
      "unit":               "<unit>",
      "provenance":         "ci-reproduced" | "mirrored" | "verifier-attested" | "pending" | ...,
      "attestor":           "<url or null>",
      "datasetHash":        "<hex or null>",
      "benchmarkInputHash": "<hex or null>",
      "runAt":              "<ISO 8601 or null>",
      "harnessUrl":         "<url or null>",
      "percentile":         <number or null>,
      "modelRef":           "<model id or null>",
      "notes":              "<string or null>"
    }

Rows are sorted by score DESC (highest first).

Usage:
    python scripts/generateBenchmarkProjection.py
    python scripts/generateBenchmarkProjection.py --out-dir docs/api/v1/benchmarks
    python scripts/generateBenchmarkProjection.py --check
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None  # type: ignore

REPO_ROOT = Path(__file__).resolve().parent.parent
NAMED_DIR = REPO_ROOT / "registry" / "named"
DEFAULT_OUT = REPO_ROOT / "docs" / "api" / "v1" / "benchmarks"

SCHEMA_VERSION = "1.0.0"

# Known benchmark metadata: id -> {name, unit, provenance, sourceUrl, methodologyUrl, notes}
BENCHMARK_META: dict[str, dict[str, Any]] = {
    "humaneval@v1.0": {
        "name": "HumanEval",
        "unit": "pass@1",
        "provenance": "ci-reproduced",
        "sourceUrl": "https://github.com/openai/human-eval",
        "methodologyUrl": "/benchmarks/humaneval-v1/",
        "notes": (
            "Python function-completion benchmark (164 problems). Gaia reproduces "
            "via CI harness; each row carries a datasetHash + benchmarkInputHash. "
            "ci-reproduced rows count toward Trust Magnitude. pending rows are "
            "awaiting first CI reproduction run."
        ),
    },
    "mmlu@2024-03": {
        "name": "MMLU (Massive Multitask Language Understanding)",
        "unit": "pct",
        "provenance": "mirrored",
        "sourceUrl": "https://huggingface.co/spaces/HuggingFaceH4/open_llm_leaderboard",
        "sourceSnapshotDate": "2024-03-01",
        "methodologyUrl": "/benchmarks/mmlu-v1/",
        "notes": (
            "5-shot MMLU average scores sourced from the HuggingFace Open LLM "
            "Leaderboard snapshot dated 2024-03-01. Provenance is 'mirrored': "
            "these rows are citation-only and are permanently excluded from Trust "
            "Magnitude. See methodologyUrl for the full provenance rationale."
        ),
    },
}


# ---------------------------------------------------------------------------
# Frontmatter parsing
# ---------------------------------------------------------------------------

def parseFrontmatter(text: str) -> dict[str, Any]:
    """Extract YAML frontmatter from a Markdown file. Returns {} on failure."""
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", text, re.DOTALL)
    if not m:
        return {}
    raw = m.group(1)
    if yaml is not None:
        try:
            result = yaml.safe_load(raw)
            return result if isinstance(result, dict) else {}
        except Exception:
            return {}
    # Minimal YAML fallback (key: value, indented lists) — used only when
    # PyYAML is unavailable. The full pipeline always has PyYAML.
    out: dict[str, Any] = {}
    for line in raw.splitlines():
        stripped = line.lstrip()
        if ": " in stripped and not stripped.startswith("-"):
            k, _, v = stripped.partition(": ")
            out[k.strip()] = v.strip().strip("'\"")
    return out


# ---------------------------------------------------------------------------
# Registry walk
# ---------------------------------------------------------------------------

def collectBenchmarkRows() -> dict[str, list[dict[str, Any]]]:
    """Walk registry/named/**/*.md and collect benchmark-result evidence rows.

    Returns {benchmarkId: [row, ...]} sorted by score DESC per benchmark.
    """
    buckets: dict[str, list[dict[str, Any]]] = {}

    if not NAMED_DIR.exists():
        return buckets

    for mdFile in sorted(NAMED_DIR.glob("**/*.md")):
        parts = mdFile.relative_to(NAMED_DIR).parts
        if len(parts) != 2:
            continue
        contributor, slug = parts[0], parts[1].removesuffix(".md")
        skillId = f"{contributor}/{slug}"

        text = mdFile.read_text(encoding="utf-8", errors="replace")
        fm = parseFrontmatter(text)
        evidenceList = fm.get("evidence") or []
        if not isinstance(evidenceList, list):
            continue

        for ev in evidenceList:
            if not isinstance(ev, dict):
                continue
            if ev.get("type") != "benchmark-result":
                continue
            benchId = ev.get("benchmarkId")
            if not benchId:
                continue

            row: dict[str, Any] = {
                "skillId": skillId,
                "score": ev.get("score"),
                "unit": ev.get("unit") or None,
                "provenance": ev.get("provenance") or "pending",
                "attestor": ev.get("attestor") or None,
                "datasetHash": ev.get("datasetHash") or None,
                "benchmarkInputHash": ev.get("benchmarkInputHash") or None,
                "runAt": ev.get("runAt") or None,
                "harnessUrl": ev.get("harnessUrl") or None,
                "percentile": ev.get("percentile") if ev.get("percentile") is not None else None,
                "modelRef": ev.get("modelRef") or None,
                "notes": ev.get("notes") or None,
            }

            buckets.setdefault(benchId, []).append(row)

    # Sort each bucket by score DESC (nulls last).
    for benchId in buckets:
        buckets[benchId].sort(
            key=lambda r: (r["score"] is not None, r["score"] or 0),
            reverse=True,
        )

    return buckets


# ---------------------------------------------------------------------------
# File builders
# ---------------------------------------------------------------------------

def buildBenchmarkFile(benchId: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Build the full JSON dict for a benchmark file."""
    slug = benchId.split("@")[0] if "@" in benchId else benchId
    meta = BENCHMARK_META.get(benchId, {})

    doc: dict[str, Any] = {
        "schemaVersion": SCHEMA_VERSION,
        "benchmarkId": benchId,
        "name": meta.get("name", benchId),
        "unit": meta.get("unit", ""),
        "provenance": meta.get("provenance", ""),
        "methodologyUrl": meta.get("methodologyUrl", f"/benchmarks/{slug}-v1/"),
    }
    if "sourceUrl" in meta:
        doc["sourceUrl"] = meta["sourceUrl"]
    if "sourceSnapshotDate" in meta:
        doc["sourceSnapshotDate"] = meta["sourceSnapshotDate"]
    doc["notes"] = meta.get("notes", "")
    doc["rows"] = rows
    return doc


def benchmarkSlug(benchId: str) -> str:
    """humaneval@v1.0 -> humaneval"""
    return benchId.split("@")[0] if "@" in benchId else benchId


def buildIndexDoc(liveIds: list[str]) -> dict[str, Any]:
    """Build the index.json document listing all live benchmarks."""
    entries = []
    for benchId in sorted(liveIds):
        slug = benchmarkSlug(benchId)
        meta = BENCHMARK_META.get(benchId, {})
        entries.append({
            "id": benchId,
            "name": meta.get("name", benchId),
            "provenance": meta.get("provenance", ""),
            "leaderboardUrl": f"/api/v1/benchmarks/{slug}.json",
            "methodologyUrl": meta.get("methodologyUrl", f"/benchmarks/{slug}-v1/"),
        })
    return {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": None,
        "benchmarks": entries,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def generate(outDir: Path) -> dict[str, bytes]:
    """Collect evidence and return {relative_filename: json_bytes} to write."""
    buckets = collectBenchmarkRows()
    outFiles: dict[str, bytes] = {}

    # Write per-benchmark files.
    for benchId, rows in buckets.items():
        slug = benchmarkSlug(benchId)
        doc = buildBenchmarkFile(benchId, rows)
        outFiles[f"{slug}.json"] = (json.dumps(doc, indent=2, ensure_ascii=False) + "\n").encode()

    # Update index.json: merge existing non-registry benchmarks with collected ones.
    indexPath = outDir / "index.json"
    existingIndex: dict[str, Any] = {}
    if indexPath.exists():
        try:
            existingIndex = json.loads(indexPath.read_text(encoding="utf-8"))
        except Exception:
            existingIndex = {}

    existingIds = {e["id"] for e in existingIndex.get("benchmarks", [])}
    liveIds = set(buckets.keys()) | existingIds
    indexDoc = buildIndexDoc(sorted(liveIds))
    outFiles["index.json"] = (json.dumps(indexDoc, indent=2, ensure_ascii=False) + "\n").encode()

    return outFiles


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--out-dir",
        default=str(DEFAULT_OUT),
        help="Output directory (default: docs/api/v1/benchmarks)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Return exit code 1 if regen would differ from committed files (dry-run)",
    )
    args = parser.parse_args(argv)

    outDir = Path(args.out_dir)
    outDir.mkdir(parents=True, exist_ok=True)

    outFiles = generate(outDir)

    if args.check:
        stale = False
        for filename, content in outFiles.items():
            path = outDir / filename
            if not path.exists():
                try:
                    label = path.relative_to(REPO_ROOT)
                except ValueError:
                    label = path
                print(f"MISSING {label}")
                stale = True
            elif path.read_bytes() != content:
                try:
                    label = path.relative_to(REPO_ROOT)
                except ValueError:
                    label = path
                print(f"STALE   {label}")
                stale = True
        if stale:
            return 1
        print("benchmark projection: up-to-date")
        return 0

    written = []
    for filename, content in outFiles.items():
        path = outDir / filename
        if not path.exists() or path.read_bytes() != content:
            path.write_bytes(content)
            written.append(str(path.relative_to(REPO_ROOT)))

    if written:
        print(f"benchmark projection: wrote {len(written)} file(s)")
        for f in written:
            print(f"  {f}")
    else:
        print("benchmark projection: nothing changed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
