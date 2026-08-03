---
name: ev-benchmark-verification
description: >
  Phase 2B of the Gaia evidence verification pipeline. Verifies benchmark-result rows and benchmark-source candidates against registry/benchmark-sources.json before adversarial audit, link validation, catalog promotion, or ingestion. Use when running /ev-pipeline, checking benchmark-result evidence, reviewing benchmark-source candidates, or preparing benchmark rows for /gaia-ingest-batch.
---

# Benchmark-Source Verification (ev-benchmark-verification)

Phase 2B runs after `/ev-star-verification` and before `/ev-adversarial-audit`. It is benchmark-only and read-only: it classifies existing `benchmark-result` registry rows and optional benchmark-source candidate manifests without mutating the registry, the catalog, or the evidence lake.

## Policy

`registry/benchmark-sources.json` is the allow-list for benchmark-source status. Valid statuses are:

- `candidate` — motivating source only; no Trust Magnitude scoring.
- `registered` — known source, not yet verified; citation only.
- `mirrored` — external leaderboard snapshot; citation only.
- `verified` — eligible to score only when provenance and reproducibility fields satisfy the catalog entry.
- `rejected` — must not be used.
- `retired` — must not be used for new scoring.

Only rows backed by a `verified` catalog source, allowed scoring provenance, and complete reproducibility fields may count toward Trust Magnitude. Candidate, registered, mirrored, rejected, retired, unknown, or incomplete rows are not scoring rows.

## Command

```bash
PYTHONPATH=src python evidence/scripts/verify_benchmark_sources.py \
  --catalog registry/benchmark-sources.json \
  --registry-root . \
  --check \
  --report /tmp/ev-phase2b-benchmark-report.md
```

With candidate sources discovered during Phase 0 or issue review:

```bash
PYTHONPATH=src python evidence/scripts/verify_benchmark_sources.py \
  --catalog registry/benchmark-sources.json \
  --registry-root . \
  --candidate-manifest /tmp/benchmark-candidates.jsonl \
  --check \
  --report /tmp/ev-phase2b-benchmark-report.md
```

Candidate manifest entries may be JSON or JSONL objects with fields such as:

```json
{
  "target": "firecrawl/firecrawl-skills",
  "source": "https://github.com/firecrawl/firecrawl/issues/741",
  "benchmarkId": "firecrawl-scrape@2026-05",
  "status": "candidate",
  "missing": ["datasetHash", "benchmarkInputHash", "percentile"],
  "notes": "Motivating candidate only; no scoring row yet."
}
```

Firecrawl #741 is the model case: candidate-only unless a catalog entry, reproducibility fingerprints, allowed provenance, and human approval exist. Do not add Firecrawl catalog entries or scoring evidence rows from the candidate report alone.

## Human gate

Machines classify. Humans promote.

After Phase 2B benchmark-source verification, Phase 3 adversarial audit, and Phase 4 link validation, stop before benchmark catalog promotion or `/gaia-ingest-batch`. A human reviewer must approve any move from candidate/registered/mirrored to verified and must approve any benchmark-result ingestion manifest. Do not treat a green Phase 2B report as permission to ingest.

## Output

The report summarizes:

- `scoring-eligible` rows that may count toward Trust Magnitude.
- `citation-only`, `pending`, `candidate-only`, `blocked`, and `unknown-benchmark` rows that must not score.
- rejected/retired usage and scoring-provenance misuse as hard blockers.
- missing reproducibility fields and missing/dubious percentiles as findings.

Candidate-only manifest entries are never hard blockers by themselves; they are backlog items for human review.
