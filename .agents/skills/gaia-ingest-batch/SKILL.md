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
5. Regenerate once and validate once:

   ```bash
   GAIA_OPERATOR_OVERRIDE=1 gaia dev build
   GAIA_OPERATOR_OVERRIDE=1 gaia dev validate
   GAIA_OPERATOR_OVERRIDE=1 gaia validate --intake
   git diff --check
   ```

## Output

Report, for every row: CLI command, source verdict, Evidence Type, row grade,
TM contribution, and duplicate/scope decision. Report, for every skill: final
TM, Overall Trust Grade, current level, and any calibration proposal.

Route suite creation only after components are ingested and appraised. Use
`/gaia-fuse-full-suite` for that separate mutation sequence.
