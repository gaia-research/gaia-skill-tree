---
name: adversarial-evidence-audit
description: Coordinates parallel adversarial review subagents to inspect the evidence data lake from a critical "Devil's Advocate" perspective.
---

# Adversarial Evidence Audit

This skill handles Phase 3 of the evidence verification pipeline, coordinating parallel review agents to scan for errors, noise, and proxy mismatches.

## Context

To protect the data lake from quality decay, evidence must be audited under adversarial rules:
- Format compliance (e.g., GitHub subdirectory URLs using `blob/` format instead of `tree/`).
- Evaluative noise filtration (stripping subjective prose like "elite", "top-tier").
- Proxy containment verification (ensuring external repositories consume/implement the capabilities directly).

## Workflow

1. Divide data lake files among parallel adversarial reviewer agents:
   - Agent 1: Tiers 1★, 5★, and 6★ (`tier_1.md`, `tier_5.md`, `tier_6.md`).
   - Agent 2: Tier 2★ Part A (`tier_2.md` lines 1 to 1382).
   - Agent 3: Tier 2★ Part B (`tier_2.md` lines 1383 to 2767).
   - Agent 4: Tiers 3★ and 4★ (`tier_3.md`, `tier_4.md`).

2. Execute the adversarial sweep:
   - Run the audit checkpoints to identify dead links, formatting deviations, subjective claims, and proxy mismatches.
   - Alternatively, execute the adversarial check command:

```bash
/gaia-adversarial-audit
```

3. Collect the reports and merge findings using a synthesis step.
4. Append findings to the master report under a dedicated section `## 6. Adversarial Data Lake Audit Findings (YYYY-MM-DD)` in the active source report file (e.g., `founder/sources/source_report_2026_06_19.md`).
