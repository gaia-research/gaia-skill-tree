---
name: ev-benchmark-verification
description: >
  Phase 2B of the Gaia evidence verification pipeline. Verifies benchmark-result rows and benchmark-source candidates against registry/benchmark-sources.json before adversarial audit, link validation, catalog promotion, or ingestion. Use when running /ev-pipeline, checking benchmark-result evidence, reviewing benchmark-source candidates, or preparing benchmark rows for /gaia-ingest-batch.
---

# Benchmark-Source Verification (ev-benchmark-verification)

Phase 2B runs after `/ev-star-verification` and before `/ev-adversarial-audit`. It is benchmark-only and read-only: it classifies existing `benchmark-result` registry rows and optional benchmark-source candidate manifests without mutating the registry, the catalog, or the evidence lake.

## Policy

`registry/benchmark-sources.json` is the benchmark allow/blacklist surface. Current lanes collapse to three values:

- `verified` — CI-reproduced or verifier-attested benchmark evidence; Trust Magnitude lane multiplier `2.0x`.
- `reported` — public claim or mirrored leaderboard evidence accepted by the human gate; Trust Magnitude lane multiplier `1.0x`.
- `rejected` — blacklisted, disputed, pending, retired, candidate, unknown, or otherwise not approved; Trust Magnitude multiplier `0x`.

Legacy aliases are accepted during migration: `ci-reproduced` and `verifier-attested` normalize to `verified`; `mirrored` normalizes to `reported`; `pending`, `unknown`, `retired`, and `candidate` normalize to `rejected`/no scoring. A catalog entry with `status: rejected` is the blacklist and always scores zero.

Reported rows do not need `runAt`, `datasetHash`, or `benchmarkInputHash`. Verified rows still need reproducibility fields. `appliesToGenericSkillRefs` records which generic skill IDs a benchmark applies to; it does not create a named-skill score by itself.

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
  "target": "firecrawl/firecrawl-research-index",
  "source": "https://www.firecrawl.dev/blog/research-index-launch",
  "benchmarkId": "alphaxiv-arxivqa@v1.0",
  "status": "candidate",
  "missing": [],
  "notes": "Candidate becomes reported only after the human gate approves it."
}
```

Firecrawl Research Index / alphaXiv ArXivQA is the model case: a public reported benchmark can count at 1.0x after the human gate, but a candidate report alone is not permission to ingest.

## Human gate

Machines classify. Humans approve or reject.

After Phase 2B benchmark-source verification, Phase 3 adversarial audit, and Phase 4 link validation, stop before benchmark catalog promotion or `/gaia-ingest-batch`. A human reviewer must approve reported benchmark evidence or mark it rejected/blacklisted. Do not treat a green Phase 2B report as permission to ingest.

## Output

The report summarizes:

- `scoring-eligible` rows that may count toward Trust Magnitude.
- `reported`, `rejected-row`, `candidate-only`, `blocked`, and `unknown-benchmark` rows that need human review or score zero.
- rejected/retired usage and scoring-lane misuse as hard blockers.
- missing verified-lane reproducibility fields and malformed percentiles as findings.

Candidate-only manifest entries are never hard blockers by themselves; they are backlog items for human review.
