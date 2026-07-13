---
name: ev-link-validation
description: |
  Phase 4 of the Gaia evidence verification pipeline. Checks every URL in the
  evidence data lake for HTTP liveness — catches dead links (404, 403, timeout,
  connection errors) before evidence is ingested into the registry. Use this
  skill when: running the full /ev-pipeline, asked to "validate links", "check
  evidence URLs", "run link validation", "find dead links in the data lake",
  "check HTTP status of evidence sources", or "verify evidence links still
  work". Also useful standalone when you suspect evidence sources have gone
  stale after a long gap between pipeline runs. Wraps validate_sources.py, which
  uses Firecrawl CLI to scrape each unique URL and records pass/fail status in a
  markdown report. Requires Firecrawl CLI to be installed and authenticated.
---

# Link Validation (ev-link-validation)

Phase 4 of the evidence verification pipeline. Its job is simple but critical: evidence that points to a dead URL is worthless, and importing it into the registry creates noise that degrades Trust Magnitude scores. This phase catches those bad links before ingestion.

## Prerequisites

Firecrawl CLI must be installed and authenticated. If it hasn't been set up yet:

```bash
npx firecrawl-cli init
```

This only needs to be done once per machine.

## Workflow

### 1. Run the validation script

```bash
.venv/bin/python evidence/scripts/validate_sources.py
```

The script parses every unique URL from `evidence/*.md` tier files, scrapes each one via Firecrawl, and records the HTTP status. Expect it to take several minutes on a full data lake — it's doing real HTTP calls.

To test on a small sample first (useful when debugging or checking a specific tier):

```bash
.venv/bin/python evidence/scripts/validate_sources.py 10
```

The optional integer argument caps the number of URLs processed.

### 2. Archive the report with today's date

The script writes its output to `evidence/data_lake_validation_report.md`. Archive a timestamped copy so the verification history is auditable:

```bash
cp evidence/data_lake_validation_report.md \
   evidence/collectors/verification/firecrawl_validation_report_$(date +%Y_%m_%d).md
```

Archiving matters because the next pipeline run will overwrite the live report. The timestamped copy is the permanent record.

### 3. Record findings in the daily source report

Open today's `evidence/source_report_YYYY_MM_DD.md` and add a section summarising:
- Total URLs checked
- Pass count (200 OK)
- Fail count (4xx, 5xx, timeouts, DNS errors)
- A brief note on any patterns (e.g. "all failures are from one domain that's rate-limiting")

Dead links should not be imported into the registry. Flag them in the source report so the evidence curator knows to skip or replace them.

### 4. Update the visual pipeline tracker

Open `evidence/verification_process.html` and update the link-validation stats block to reflect the latest pass/fail counts. This keeps the visual dashboard current for anyone reviewing pipeline health at a glance.

### 5. Handoff verified intake evidence

For an L4-approved intake, link validation is the final evidence-pipeline gate.
Do not hand-edit registry evidence. Hand each live, correctly scoped collector row
to `/gaia-ingest` (or `/gaia-ingest-batch` for a reviewed manifest), which
performs the CLI-only `gaia dev evidence` mutation, TM appraisal, and any
separately approved calibration.
