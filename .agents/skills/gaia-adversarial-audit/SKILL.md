---
name: gaia-adversarial-audit
description: Audits the unified evidence data lake using parallel adversarial reviewer subagents and a synthesis subagent to catch dead links, formatting issues, proxy mismatches, and evaluative noise.
version: 1.0.0
---

# gaia-adversarial-audit

Use this skill to perform a thorough, multi-agent adversarial audit of all raw evidence files in the Gaia data lake (`founder/sources/data_lake/`). It detects link failures, formatting violations, proxy mismatches, and evaluative noise, then compiles and logs the findings into the master source report.

## Core Directives

- **Parallel Audit Distribution:** Divide the data lake review work among 4 parallel adversarial subagents to ensure maximum speed and context efficiency.
- **Devil's Advocate Perspective:** Subagents must act as adversarial judges, aggressively questioning the validity of star thresholds, proxy mappings, and correctness of classifications.
- **Synthesized Logging:** Consolidate all findings via a 5th synthesis subagent that updates the master source report file.
- **Non-destructive Curation:** Identify candidates for removal or correction, but do not delete evidence from the data lake files directly without explicit user approval.

## Audit Checkpoints

Reviewers must scan for the following four error categories:
1. **Dead/Broken Links (404):** Verified broken links, non-existent private repositories, or defunct marketplace paths.
2. **Format Errors:** Violations of Gaia curation rules (e.g., bare repository URLs used for suite components instead of `blob/branch/subpath` subpaths, `tree/` folder references instead of `blob/`, case-sensitivity discrepancies, missing trailing `/SKILL.md` suffixes).
3. **Evaluative Noise:** Descriptions containing subjective praise ("elite", "high-quality"), rank/tier logic annotations, verifier attestations ("verified live"), or database migration notes.
4. **Proxy/Evidence Mismatches:** Unrelated/competitor repositories mapped as proxy-containment, general survey papers/runtimes mapped without direct linkage to the skill, or circular self-references.

## Workflow Instructions

1. **Work Distribution:**
   - **Subagent 1:** Audit Tiers 1★, 5★, and 6★ (`tier_1.md`, `tier_5.md`, `tier_6.md`).
   - **Subagent 2:** Audit Tier 2★ Part A (`tier_2.md` lines 1 to 1382).
   - **Subagent 3:** Audit Tier 2★ Part B (`tier_2.md` lines 1383 to 2767).
   - **Subagent 4:** Audit Tiers 3★ and 4★ (`tier_3.md`, `tier_4.md`).

2. **Parallel Invocation:**
   - Invoke 4 subagents of type `self` with prompts tailored to their assigned segments.
   - Subagents must check every link, query content when accessible, skip verifying star numbers, and output a detailed markdown report to a temporary artifact.

3. **Synthesis & Reporting:**
   - Once the 4 subagents complete, invoke a 5th synthesis subagent (type `self`).
   - The synthesis agent reads the 4 report artifacts, merges duplicate findings, and compiles them into a unified section.
   - Log the findings by appending a section `## 6. Adversarial Data Lake Audit Findings (YYYY-MM-DD)` to `founder/sources/source_report_YYYY_MM_DD.md`.

4. **Commit Changes:**
   - Stage and commit the updated source report to the active branch.
