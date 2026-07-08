---
id: gaia-research/skill-ci-churn
name: CI Churn
contributor: gaia-research
origin: false
genericSkillRef: ci-churn-analysis
status: awakened
level: 2★
description: Measures avoidable CI iteration cost for a pull request by classifying
  commits as feature work versus fix-the-CI rework, summing CI compute time burned
  on avoidable push rounds, and surfacing pre-push checks that would have prevented
  them.
createdAt: '2026-07-08'
updatedAt: '2026-07-08'
timeline:
- timestamp: '2026-07-08T10:19:05Z'
  action: add
  contributor: unknown
  details: Added named skill gaia-research/skill-ci-churn
- timestamp: '2026-07-08T10:21:40Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/gaia-research/gaia-skill-tree (type:
    repo-own)'
- timestamp: '2026-07-08T10:21:46Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/gaia-research/gaia-skill-tree/blob/main/.agents/skills/ci-churn/SKILL.md
    (type: self-attestation)'
- timestamp: '2026-07-08T10:22:19Z'
  action: demote
  contributor: unknown
  details: Calibrated level from 2★ to 2★
- timestamp: '2026-07-08T10:22:39Z'
  action: note
  contributor: unknown
  details: Updated GitHub link to https://github.com/gaia-research/gaia-skill-tree/blob/main/.agents/skills/ci-churn/SKILL.md
evidence:
- source: https://github.com/gaia-research/gaia-skill-tree
  evaluator: unknown
  date: '2026-07-08'
  type: repo-own
  notes: gaia-skill-tree repo — 2884 commits, 24 contributors; ci-churn SKILL.md lives
    at .agents/skills/ci-churn/
  commits: 2884
  contributors: 24
  grade: B
- source: https://github.com/gaia-research/gaia-skill-tree/blob/main/.agents/skills/ci-churn/SKILL.md
  evaluator: unknown
  date: '2026-07-08'
  type: self-attestation
  notes: Implemented and in active production use — called automatically by /fp-drift
    at every pipeline close
  grade: C
verification:
  firstEvidenceAt: '2026-07-08T10:21:40Z'
links:
  github: https://github.com/gaia-research/gaia-skill-tree/blob/main/.agents/skills/ci-churn/SKILL.md
---

## Installation
Add installation instructions here.
