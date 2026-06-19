---
name: ev-link-validation
description: Automatically validates link status codes and scrapes evidence links using the Firecrawl API and CLI tools.
---

# Firecrawl Link Validation (ev-link-validation)

This skill handles Phase 4 of the evidence verification pipeline, dynamically scraping URLs inside the data lake to find dead (404) links or network errors.

## Context

All external links compiled into the evidence data lake (Tiers 1★ to 6★) must be continuously audited for uptime and validity:
- Firecrawl CLI (`firecrawl scrape`) is used to fetch and inspect link availability in parallel.
- Unique URLs are parsed from `founder/sources/data_lake/*.md` files.
- Run results are saved to a markdown report and logged within the chronological verification repository.

## Workflow

1. Ensure the Firecrawl CLI is installed and authenticated (`npx firecrawl-cli init` or globally).
2. Run the validation script:

```bash
.venv/bin/python founder/sources/scripts/validate_sources.py
```

*Note: For debugging/testing a subset of URLs, you can pass a limit parameter (e.g. `.venv/bin/python founder/sources/scripts/validate_sources.py 10`)*

3. Copy the output report `founder/sources/data_lake_validation_report.md` to a timestamped file under the verification folder:

```bash
cp founder/sources/data_lake_validation_report.md \
   founder/sources/collectors/verification/firecrawl_validation_report_2026_06_19.md
```

4. Document the validation findings and pointer reference in the daily source report `founder/sources/source_report_2026_06_19.md`.
5. Update the verification stats inside `founder/sources/verification_process.html` to reflect the latest audit counts.
