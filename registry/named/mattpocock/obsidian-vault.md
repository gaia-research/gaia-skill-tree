---
id: mattpocock/obsidian-vault
name: Obsidian Vault Manager
contributor: mattpocock
origin: false
genericSkillRef: personal-knowledge-management
status: named
title: The Obsidian Vault Mapper
level: 3★
description: Manage notes and organization in a specific Obsidian vault using Title
  Case and wikilinks.
createdAt: '2026-05-21'
updatedAt: '2026-08-30'
suiteRef: mattpocock/personal
links:
  github: https://github.com/mattpocock/skills/blob/main/skills/personal/obsidian-vault
evidence:
- class: B
  source: https://github.com/mattpocock/skills/blob/main/skills/personal/obsidian-vault/SKILL.md
  evaluator: mbtiongson1
  date: '2026-05-22'
  notes: 'Obsidian vault management and PKM automation. (backfilled — class-to-type"
    migration) (CLI gap: --commits/--contributors not supported by gaia dev evidence)'
  type: repo
  trustNumber: 70.0
  commits: 137
  contributors: 3
  grade: C
- source: https://github.com/mattpocock/skills
  evaluator: unknown
  updatedAt: '2026-09-01'
  date: '2026-06-20'
  type: github-stars-own
  trustNumber: 88.0
  grade: C
  notes: mattpocock/skills suite — 137k GitHub stars; obsidian-vault is part of this
    repo
  stars: 243413
  skillCountInRepo: 21
  sourceStartedAt: '2025-01-01'
- source: https://www.youtube.com/watch?v=EJyuu6zlQCg
  evaluator: unknown
  date: '2026-06-20'
  type: social-signal
  trustNumber: 82.0
  grade: B
  notes: Matt Pocock — 5 Claude Code skills I use every single day; 412K views; covers
    mattpocock/skills repo (verified 2026-06-20)
  views: 412000
  sourceStartedAt: '2025-01-01'
timeline:
- timestamp: '2026-06-14T12:32:43Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/mattpocock/skills/blob/main/skills/personal/obsidian-vault/SKILL.md
    as B (trustNumber: 70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:18Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T11:52:12Z'
  details: TM 0.0 -> 11.21, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:38Z'
  details: TM 0.0 -> 11.21, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:41Z'
  details: TM 0.0 -> 11.21, grade ungraded -> ungraded (direct edit -- CLI gap)
- timestamp: '2026-06-19T17:07:33Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/mattpocock/skills (type: github-stars-own)'
- timestamp: '2026-06-19T17:07:33Z'
  action: evidence_graded
  contributor: unknown
  details: 'Graded evidence from https://github.com/mattpocock/skills as A (trustNumber:
    88.0)'
- timestamp: '2026-06-19T17:07:35Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://www.youtube.com/watch?v=EJyuu6zlQCg (type:
    social-signal)'
- timestamp: '2026-06-19T17:07:35Z'
  action: evidence_graded
  contributor: unknown
  details: 'Graded evidence from https://www.youtube.com/watch?v=EJyuu6zlQCg as A
    (trustNumber: 82.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T17:13:03Z'
  details: TM 11.21 -> 90.38, grade ungraded -> B (direct edit -- CLI gap)
- timestamp: '2026-08-19T11:49:10Z'
  action: upstream_deprecated
  contributor: unknown
  previousValue: null
  newValue: null
  details: 'deleted upstream for security: hardcoded personal vault path, was model-invocable'
- timestamp: '2026-08-29T17:15:53Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM 90.38 -> 306.13, grade B -> A (gaia dev calibrate-trust-magnitude;
    Issue #1600)'
trustMagnitude: 306.13
overallTrustGrade: A
apexGateStatus:
  aGradedOriginsGte5: false
  sourceTenureDaysGte180AorS: true
  directNestedSuiteGte1: false
  depth2OnlyReachableGte1: false
  overallGradeS: false
  apexPromotionPrSigned: false
  crossOrgVerifier: null
  systemWideCap: null
trustMagnitudeInputHash: edc269178e4d567153c29a4e69256decad48e91c9cd83d2ff11835556d81f4c2
verification:
  firstEvidenceAt: '2026-06-19T17:07:33Z'
installable: false
---

## Installation

This skill is included in the Matt Pocock skills suite. It is highly recommended to install the full suite to enable cross-skill context sharing.

```bash
npx skills@latest add mattpocock/skills
```

No additional setup required beyond the main suite installation.
