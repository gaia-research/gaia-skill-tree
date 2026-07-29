---
name: gaia-ingest-batch
description: >-
  Batch wrapper for /gaia-ingest. Ingests a bounded set of already-verified
  evidence rows through CLI-only writes, uses --no-build on every row, appraises
  Trust Magnitude for every affected named skill, then runs exactly one build and
  validation pass. Use for an L4-approved intake after /ev-pipeline.
version: 1.0.0
argument-hint: "<verified-evidence-manifest>"
---

# Gaia Ingest Batch

This is a coordinator, not a second evidence-ingestion implementation. Every
row follows the contract in `/gaia-ingest`; this skill only sequences verified
rows efficiently and finalizes the resulting registry artifacts.

## Input manifest

Prepare a reviewed manifest with one row per source:

```yaml
rows:
  - skill: firecrawl/web-scrape-integration
    source: https://www.youtube.com/watch?v=...
    evidenceType: social-signal
    payload:
      views: 8510
    sourceStartedAt: 2025-07-20
    notes: "Third-party tutorial explicitly demonstrates page scraping."
```

The manifest must state a source URL, Evidence Type, source-start date,
verifiable numeric payload, factual notes, and attribution scope for every row.
Exclude any deferred candidate. Never infer an Evidence Type or a metric from a
summary.

## Procedure

1. Verify `/ev-pipeline` completed for the manifest’s sources and link health
   is recorded. Reject dead, unverified, duplicate, or scope-mismatched rows.
2. For each row, invoke the `/gaia-ingest` contract and execute its exact
   `gaia dev evidence ... --no-build` command. Process one row at a time and
   stop on the first CLI preflight or source-verification failure.
3. Appraise each affected skill after its final row:

   ```bash
   PYTHONPATH=src python3 scripts/trust_appraise.py --skill <contributor/skill-id>
   ```

4. Present proposed calibrations. Do not calibrate without explicit operator
   approval. If approval is already recorded, run each approved calibration
   with `--no-build`.
5. **Hand off the branch-close to `/gaia-review-meta-close`.** Do not run the
   build/validate/stage/PR steps here — that skill owns the single build, the
   calibration+Origin gate, suite wiring via `gaia dev fuse` (so `suiteComponents`
   survives the build), upstream-naming correction, the LF-renormalized artifact
   allowlist (dropping CRLF churn and blocking leaks), the UTF-8-safe validate,
   and the PR. Pass it the branch, the affected `contributor` handles (for badge/og
   staging), the per-skill appraised TM/grade from step 3, and the intake issues
   to `Resolves`. This skill stops at "evidence ingested + appraised."

## Output

Report, for every row: CLI command, source verdict, Evidence Type, row grade,
TM contribution, and duplicate/scope decision. Report, for every skill: final
TM, Overall Trust Grade, current level, and any calibration proposal. Then hand
these facts to `/gaia-review-meta-close` for the gated close-out.

Route suite creation only after components are ingested and appraised — the
capstone/`suiteComponents` wiring happens inside `/gaia-review-meta-close`
(`gaia dev fuse`), or via `/gaia-fuse-full-suite` for a standalone suite build.
