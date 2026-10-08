---
id: hikari9/auto-office
name: Auto Office
contributor: hikari9
origin: false
genericSkillRef: autonomous-engineering-platform
status: named
level: 3★
description: Adaptive office engineering runtime for the complete lifecycle from intent
  through planning, routed execution, independent review, verification, and closeout,
  driven through one `office` CLI. Use when explicitly invoked as /auto-office or
  when the user directly asks to run an Auto Office lifecycle. Routes each role by
  harness, model, and effort under pinned policy, trust and capability floors, and
  live quota; the runtime owns state, receipts, evidence, and review mechanics. Preserves
  human merge-to-main unless the user chose merge or end-to-end at intake, no-self-approval,
  private evidence, and version-pinned runs.
createdAt: '2026-10-09'
updatedAt: '2026-10-09'
title: Auto Office
links:
  github: https://github.com/Hikari9/auto-office/blob/da6aa9a93dbab98c03d2fbb3593f994acf85d7a7/SKILL.md
attribution:
  upstream_author: Hikari9
  skill_file_url: https://github.com/Hikari9/auto-office/blob/da6aa9a93dbab98c03d2fbb3593f994acf85d7a7/SKILL.md
  type: self-made
timeline:
- timestamp: '2026-10-08T21:36:11Z'
  action: add
  contributor: unknown
  details: Added named skill hikari9/auto-office
- timestamp: '2026-10-08T21:36:14Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/Hikari9/auto-office/blob/da6aa9a93dbab98c03d2fbb3593f994acf85d7a7/SKILL.md
    (type: repo-own)'
- timestamp: '2026-10-08T21:36:16Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/Hikari9/auto-office (type: github-stars-own)'
- timestamp: '2026-10-08T21:36:34Z'
  action: suite_ref_set
  contributor: unknown
  details: 'Updated via `gaia dev fuse`: suiteRef=hikari9/auto-office, suiteComponents+=[''hikari9/office-submit''].'
- timestamp: '2026-10-08T21:36:52Z'
  action: rank_up
  contributor: unknown
  details: Calibrated level from 1★ to 3★
- timestamp: '2026-10-08T21:37:21Z'
  action: installation_updated
  contributor: unknown
  details: 'Replaced ## Installation section from generated-output/2054-installation.md'
- timestamp: '2026-10-08T21:47:57Z'
  action: installation_updated
  contributor: unknown
  details: 'Replaced ## Installation section from generated-output/2054-installation.md'
evidence:
- source: https://github.com/Hikari9/auto-office/blob/da6aa9a93dbab98c03d2fbb3593f994acf85d7a7/SKILL.md
  evaluator: unknown
  date: '2026-10-08'
  type: repo-own
  notes: Whole runtime repository baseline at pinned HEAD da6aa9a93dbab98c03d2fbb3593f994acf85d7a7;
    metrics enumerate whole repository, not this SKILL.md alone. See receipts/head.json,
    commit-shas.txt, contributors.json.
  commits: 826
  contributors: 4
  skillCountInRepo: 21
  sourceStartedAt: '2026-10-08'
  grade: C
- source: https://github.com/Hikari9/auto-office
  evaluator: unknown
  date: '2026-10-08'
  type: github-stars-own
  notes: Observed GitHub API stargazers_count. Shared repository baseline across 21
    skills; not independent per-component adoption.
  stars: 1
  skillCountInRepo: 21
  sourceStartedAt: '2026-10-08'
verification:
  firstEvidenceAt: '2026-10-08T21:36:14Z'
suiteComponents:
- hikari9/office-submit
---

## Installation
Auto Office uses its own runtime installer rather than a standalone SKILL.md copy. Install from upstream using either uv or pipx:

```bash
uv tool install git+https://github.com/Hikari9/auto-office.git
# Alternatively:
pipx install git+https://github.com/Hikari9/auto-office.git

office install
office doctor
```

`office install` registers the runtime and bundled skills, including Office Submit, with supported harnesses. Review the upstream installation instructions before allowing harness configuration changes. Packaging was verified at commit `da6aa9a93dbab98c03d2fbb3593f994acf85d7a7`; the commands above install the current upstream revision.
