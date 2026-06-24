---
name: ev-star-verification
description: >
  Phase 2 of the evidence verification pipeline. Validates GitHub star counts in registry skill files
  against live GitHub API data, flags stale or inflated metrics, and partitions all evidence into
  six tier-ranked markdown dumps (tier_1.md through tier_6.md) inside evidence/. Use this after
  /ev-collection has compiled the unified data lake and before /ev-adversarial-audit begins.
  Trigger phrases: "verify stars", "check star counts", "refresh stargazer metrics",
  "partition evidence by tier", "run star verification", "ev-star-verification", "Phase 2",
  "live star check", "update tier dumps", "star tier partitioning".
---

# Live Star Verification (ev-star-verification)

Phase 2 of the evidence verification pipeline. Queries the GitHub API for live stargazer counts,
validates them against named skill files in the registry, and writes six partitioned tier dumps
that downstream phases (adversarial audit, link validation) use as their working input.

## Why This Phase Matters

Evidence scores in the Gaia Registry decay over time — a repo that had 500 stars when it was
catalogued may now have 5,000, or may have been deleted. Without live re-validation, Trust
Magnitude scores compound stale data and produce misleading skill grades. This phase is the
single point where raw GitHub reality is reconciled with what the registry believes.

The partitioned tier dumps also serve a practical purpose: they let the adversarial audit phase
(Phase 3) distribute work across parallel subagents by tier rather than scanning the entire lake
at once, which would exceed context budgets.

## Prerequisites

- Phase 1 (`/ev-collection`) has completed and `evidence/unified_evidence_lake.md` is current.
- GitHub CLI is authenticated: run `gh auth status` to confirm before proceeding.
- The virtual environment is active (`.venv/bin/python` resolves correctly).

## Workflow

### Step 1 — Confirm GitHub CLI authentication

```bash
gh auth status
```

If unauthenticated, the star queries will silently return zero counts and corrupt the tier
partitioning. Fix auth before continuing.

### Step 2 — Run the star verification and tier generation script

```bash
.venv/bin/python evidence/scripts/generate_source_dump.py \
  --named-skills-json registry/named-skills.json \
  --gaia-json registry/gaia.json \
  --named-dir registry/named \
  --output-dir evidence \
  --report-path evidence/source_report_$(date +%Y_%m_%d).md
```

This script:
1. Loads all named skills from `registry/named/` and cross-references `registry/named-skills.json`.
2. For each skill with a `links.github` URL, queries `gh repo view` for the live star count.
3. Compares the live count against stored values and flags discrepancies.
4. Partitions all evidence rows into six tier files (`tier_1.md` through `tier_6.md`) inside
   `evidence/`, based on star thresholds defined in the registry schema.
5. Appends a star-validation summary section to the daily source report.

### Step 3 — Confirm output

Verify that all six tier files are updated (check modification timestamps):

```bash
ls -lh evidence/tier_*.md
```

Also confirm the daily report was written or updated:

```bash
ls -lh evidence/source_report_*.md
```

### Step 4 — Hand off to Phase 3

Once tier files are confirmed, invoke the adversarial audit:

```bash
/ev-adversarial-audit
```

## Output Artifacts

| File | Contents |
|---|---|
| `evidence/tier_1.md` | Skills with 1★ star threshold evidence |
| `evidence/tier_2.md` | Skills with 2★ star threshold evidence (typically the largest file) |
| `evidence/tier_3.md` | Skills with 3★ star threshold evidence |
| `evidence/tier_4.md` | Skills with 4★ star threshold evidence |
| `evidence/tier_5.md` | Skills with 5★ star threshold evidence |
| `evidence/tier_6.md` | Skills with 6★ star threshold evidence |
| `evidence/source_report_YYYY_MM_DD.md` | Daily audit log including star delta summary |

## Common Issues

**Stars all show 0:** GitHub CLI is not authenticated or the corporate proxy is blocking `gh`
API calls. Run `gh auth status` and resolve before re-running.

**Script not found:** Run from the repo root, not a subdirectory. The path
`evidence/scripts/generate_source_dump.py` is relative to the project root.

**Tier file timestamps are stale:** The script completed without errors but wrote no changes —
usually means the evidence lake has not been updated since the last run. Confirm Phase 1 ran
first with a fresh `unified_evidence_lake.md`.
