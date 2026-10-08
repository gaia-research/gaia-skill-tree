---
id: hikari9/office-submit
name: Office Submit
contributor: hikari9
origin: false
genericSkillRef: verification-before-completion
status: named
level: 2★
description: 'Finish an Auto Office executor task: behavior-preserving simplify pass,
  adversarial self-review of the diff, fix and mutation-prove medium+ findings, run
  the brief''s checks, commit and push, `office preflight`, `office submit`, and end
  with one status line. Use when you are an Office executor (inside a task worktree
  with an Office brief) and your work is ready to submit, or when asked to submit,
  resubmit, or finish an Office task.'
createdAt: '2026-10-09'
updatedAt: '2026-10-09'
title: Office Submit
links:
  github: https://github.com/Hikari9/auto-office/blob/da6aa9a93dbab98c03d2fbb3593f994acf85d7a7/skills/office-submit/SKILL.md
attribution:
  upstream_author: Hikari9
  skill_file_url: https://github.com/Hikari9/auto-office/blob/da6aa9a93dbab98c03d2fbb3593f994acf85d7a7/skills/office-submit/SKILL.md
  type: self-made
suiteRef: hikari9/auto-office
timeline:
- timestamp: '2026-10-08T21:36:12Z'
  action: add
  contributor: unknown
  details: Added named skill hikari9/office-submit
- timestamp: '2026-10-08T21:36:17Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/Hikari9/auto-office/blob/da6aa9a93dbab98c03d2fbb3593f994acf85d7a7/skills/office-submit/SKILL.md
    (type: repo-own)'
- timestamp: '2026-10-08T21:36:19Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/Hikari9/auto-office (type: github-stars-own)'
- timestamp: '2026-10-08T21:36:55Z'
  action: rank_up
  contributor: unknown
  details: Calibrated level from 1★ to 2★
- timestamp: '2026-10-08T21:37:24Z'
  action: installation_updated
  contributor: unknown
  details: 'Replaced ## Installation section from generated-output/2054-installation.md'
- timestamp: '2026-10-08T21:47:58Z'
  action: installation_updated
  contributor: unknown
  details: 'Replaced ## Installation section from generated-output/2054-installation.md'
evidence:
- source: https://github.com/Hikari9/auto-office/blob/da6aa9a93dbab98c03d2fbb3593f994acf85d7a7/skills/office-submit/SKILL.md
  evaluator: unknown
  date: '2026-10-08'
  type: repo-own
  notes: 'Explicit shared whole-repository baseline, not exclusive component activity
    or independent implementation corroboration. suiteRef bounds combined repo-own
    plus github-stars-own baseline to 50 TM, NOT 50 commits or contributors. Supplemental
    path history: 11 commits / 1 contributor; SHA-256 261a30a5bc0b1b5c9211634bd96ab3e2b497255cb3336b924b55a91d0ecd7ea2.'
  commits: 826
  contributors: 4
  skillCountInRepo: 21
  sourceStartedAt: '2026-10-08'
  grade: C
- source: https://github.com/Hikari9/auto-office
  evaluator: unknown
  date: '2026-10-08'
  type: github-stars-own
  notes: Explicit shared suite repository adoption baseline (1 star, 21 skills). Not
    independent component adoption. Combined repo-own plus github-stars-own maximum
    is 50 TM, not a count limit.
  stars: 1
  skillCountInRepo: 21
  sourceStartedAt: '2026-10-08'
verification:
  firstEvidenceAt: '2026-10-08T21:36:17Z'
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
