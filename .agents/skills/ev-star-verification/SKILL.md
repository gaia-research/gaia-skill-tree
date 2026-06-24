---
name: ev-star-verification
description: Validates registry skill files against live GitHub metrics, resolving repository stargazer counts and generating partitioned raw source tier dumps.
---

# Live Star Verification (ev-star-verification)

This skill handles Phase 2 of the evidence verification pipeline, updating stargazer metrics and partitioning raw evidence by star tier.

## Context

Registry evidence must be validated against real-time signals from GitHub:
- Stargazer metrics are fetched live via the GitHub CLI (`gh repo view`).
- Named skills under `registry/named/` are loaded alongside `registry/named-skills.json` and `registry/gaia.json`.
- Consolidates and segregates evidence records into individual tier dumps (`tier_1.md` through `tier_6.md`) inside `evidence/` and generates the daily consolidated report.

## Workflow

1. Ensure you have an authenticated GitHub CLI environment (`gh auth status`).
2. Run the generator script to programmatically query live star counts and partition evidence into tier files:

```bash
.venv/bin/python evidence/scripts/generate_source_dump.py \
  --named-skills-json registry/named-skills.json \
  --gaia-json registry/gaia.json \
  --named-dir registry/named \
  --output-dir evidence \
  --report-path evidence/source_report_2026_06_19.md
```

3. Confirm that the partitioned markdown files `tier_1.md` through `tier_6.md` are refreshed inside `evidence/`.
