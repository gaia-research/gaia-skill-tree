---
name: live-star-verification
description: Validates registry skill files against live GitHub metrics, resolving repository stargazer counts and generating partitioned raw source tier dumps.
---

# Live Star Verification

This skill handles Phase 2 of the evidence verification pipeline, programmatically updating stargazer metrics and partitioning raw evidence by tier.

## Context

Registry evidence must be validated against real-time signals from GitHub to confirm popularity and usage tiers:
- Stargazer metrics are cached or retrieved live via the GitHub CLI (`gh repo view`).
- Named skills under `registry/named/` are loaded alongside `registry/named-skills.json` and `registry/gaia.json`.
- The compilation step segments evidence into respective tier directories within `founder/sources/data_lake/`.

## Workflow

1. Check for authenticated GitHub CLI environment (`gh auth status`).
2. Run the star retrieval and generator script to update stargazer metrics and partition data dumps by tier:

```bash
.venv/bin/python founder/sources/scripts/generate_source_dump.py \
  --named-skills-json registry/named-skills.json \
  --gaia-json registry/gaia.json \
  --named-dir registry/named \
  --output-dir founder/sources/collectors/raw \
  --report-path founder/sources/source_report_2026_06_19.md
```

3. Ensure files `tier_1.md` through `tier_6.md` are correctly generated inside `founder/sources/data_lake/`.
