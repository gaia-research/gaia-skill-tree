---
name: ev-adversarial-audit
description: >
  Run this skill for Phase 3 of the evidence verification pipeline — the adversarial audit step.
  Use when you need to check the evidence data lake for bad data before ingestion: dead links, wrong
  URL formats (tree/ vs blob/), subjective wording ("elite", "high-quality"), stale migration notes,
  or skills whose star tier doesn't match their classified evidence level. Triggers on phrases like:
  "audit the data lake", "adversarial check", "ev-adversarial-audit", "check for noise in evidence",
  "flag bad evidence", "run the audit phase", "quality check the tier files", or any reference to
  Phase 3 of the pipeline. Deploys 4 parallel adversarial reviewer subagents across the tier files,
  then a 5th synthesis subagent to merge findings, and appends results to the daily source report.
---

# Adversarial Evidence Audit (ev-adversarial-audit)

Phase 3 of the evidence verification pipeline. After `ev-star-verification` has partitioned the data lake into tier files, this skill deploys 4 parallel adversarial reviewer subagents to scan those files from a "Devil's Advocate" perspective, then a 5th synthesis subagent merges their findings into the master source report.

The adversarial approach matters because a single sequential pass over a large tier file tends to miss subtle issues — evaluative adjectives slipping through, a `tree/` URL that looks plausible at a glance, or a star threshold mismatch that only becomes visible when cross-referencing the tier. Parallelising reviewers and prompting them to actively look for problems (rather than rubber-stamp entries) catches the class of errors that confident single-pass scanning misses.

## What Each Reviewer Looks For

Reviewers check for four failure modes:

**Evaluative noise** — subjective wording like "elite", "high-quality", "best-in-class", or procedural rank annotations and stale database migration comments that crept into evidence descriptions. These are not evidence; they inflate perceived credibility.

**URL format errors** — bare repository URLs (`https://github.com/owner/repo`) used where a `blob/branch/subpath` pointing to the actual skill directory is required; `tree/` folder references that must be `blob/`; case-sensitivity mismatches; missing `/SKILL.md` suffix on installable skills.

**Proxy mismatches** — evidence typed as `github-stars-own` pointing to a URL that is already covered by a `repo-own` entry at the same path (same-source dedup means only the higher-scoring entry counts — the duplicate is silent waste).

**Tier/classification drift** — skills whose evidence star tier doesn't align with their classified rank in `registry/named-skills.json`, indicating a stale tier file or a promotion that wasn't reflected downstream.

## Workflow

Split the tier files across 4 parallel adversarial reviewer subagents to stay within context limits for large tiers (tier_2.md is the biggest and must be split):

- **Agent 1:** `tier_1.md`, `tier_5.md`, `tier_6.md`
- **Agent 2:** `tier_2.md` lines 1–1382
- **Agent 3:** `tier_2.md` lines 1383–2767
- **Agent 4:** `tier_3.md`, `tier_4.md`

Each agent receives the same adversarial reviewer prompt: act as a Devil's Advocate, assume every entry has at least one issue, and produce a structured findings list (entry name, tier file, line range, issue category, recommended fix).

After all 4 complete, run a 5th synthesis subagent (type `self`) to:
1. Deduplicate overlapping findings across agents.
2. Group by issue category.
3. Produce a final ranked summary ordered by severity.

Append the merged findings to the active source report under a new section:

```
## 6. Adversarial Data Lake Audit Findings (YYYY-MM-DD)
```

The source report lives at `evidence/source_report_YYYY_MM_DD.md` (use today's date).

## Invocation

```bash
/ev-adversarial-audit
```

This skill is normally invoked as part of the full pipeline via `/ev-pipeline`. Run it standalone when you want to re-audit the tier files after making corrections — for example, after fixing URL errors flagged in a previous run, re-run this skill to confirm the fixes are clean before proceeding to `/ev-link-validation`.
