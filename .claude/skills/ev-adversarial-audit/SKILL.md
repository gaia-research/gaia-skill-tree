---
name: ev-adversarial-audit
description: Audits the unified evidence data lake using parallel adversarial reviewer subagents and a synthesis subagent to catch dead links, formatting issues, proxy mismatches, and evaluative noise.
---

# Adversarial Evidence Audit (ev-adversarial-audit)

This skill handles Phase 3 of the evidence verification pipeline, deploying parallel subagents to audit local tier dumps from a critical "Devil's Advocate" perspective.

## Core Directives

- **Parallel Audit Distribution:** Divide the data lake review work among 4 parallel adversarial subagents to ensure maximum speed and context efficiency.
- **Devil's Advocate Perspective:** Subagents must act as adversarial judges, aggressively questioning the validity of star thresholds, proxy mappings, and correctness of classifications.
- **Noise Filtering:** Identify and flag subjective wording ("elite", "high-quality"), procedural rank annotations, or stale database migration notes.
- **Format Errors:** Scan for bare repository URLs used for suite components instead of `blob/branch/subpath` subpaths, `tree/` folder references instead of `blob/`, case-sensitivity discrepancies, and missing trailing `/SKILL.md` suffixes.

## Workflow

1. Divide data lake files among 4 parallel adversarial reviewer agents:
   - Agent 1: Tiers 1★, 5★, and 6★ (`tier_1.md`, `tier_5.md`, `tier_6.md`).
   - Agent 2: Tier 2★ Part A (`tier_2.md` lines 1 to 1382).
   - Agent 3: Tier 2★ Part B (`tier_2.md` lines 1383 to 2767).
   - Agent 4: Tiers 3★ and 4★ (`tier_3.md`, `tier_4.md`).

2. Invoke the adversarial check command:

```bash
/ev-adversarial-audit
```

3. Collect the reports and merge findings using a 5th synthesis subagent (type `self`).
4. Append findings to the master report under `## 6. Adversarial Data Lake Audit Findings (YYYY-MM-DD)` in the active source report file (e.g., `evidence/source_report_2026_06_19.md`).
