---
id: mattpocock/scaffold-exercises
name: Scaffold Exercises
contributor: mattpocock
origin: false
genericSkillRef: skill-authoring
status: named
links:
  github: https://github.com/mattpocock/skills/blob/main/skills/misc/scaffold-exercises/SKILL.md
level: 2★
description: Create exercise directory structures with sections, problems, solutions,
  and explainers that pass linting.
createdAt: '2026-06-19'
updatedAt: '2026-09-05'
timeline:
- timestamp: '2026-06-19T13:01:41Z'
  action: add
  contributor: unknown
  details: Added named skill mattpocock/scaffold-exercises
- timestamp: '2026-06-19T13:06:26Z'
  action: evidence_added
  contributor: unknown
  details: Added evidence from https://github.com/mattpocock/skills/blob/main/skills/misc/scaffold-exercises/SKILL.md
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:38Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:41Z'
  details: TM 0.0 -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- timestamp: '2026-06-19T18:37:40Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/mattpocock/skills/blob/main/skills/misc/scaffold-exercises/SKILL.md
    (type: repo-own)'
- timestamp: '2026-06-19T18:37:41Z'
  action: evidence_graded
  contributor: mbtiongson1
  details: 'Graded evidence from https://github.com/mattpocock/skills/blob/main/skills/misc/scaffold-exercises/SKILL.md
    as B (trustNumber: 65.0)'
- timestamp: '2026-06-19T18:37:42Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/mattpocock/skills/blob/main/skills/misc/scaffold-exercises
    (type: self-attestation)'
- timestamp: '2026-06-19T18:37:42Z'
  action: evidence_graded
  contributor: mbtiongson1
  details: 'Graded evidence from https://github.com/mattpocock/skills/blob/main/skills/misc/scaffold-exercises
    as C (trustNumber: 45.0)'
- timestamp: '2026-06-19T18:41:31Z'
  action: rank_up
  contributor: mbtiongson1
  details: 'I13 classify: status promoted from awakened to named (evidence floor met:
    repo-own B + self-attestation C)'
- timestamp: '2026-06-20T06:31:32Z'
  action: demote
  contributor: mbtiongson1
  details: Level updated from 2★ to 1★ per G7 final rankings calibration.
- timestamp: '2026-08-20T05:14:34Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/mattpocock/skills (type: repo-own)'
- timestamp: '2026-08-20T05:15:20Z'
  action: rank_up
  contributor: mbtiongson1
  details: Calibrated level from 1★ to 2★
- timestamp: '2026-08-29T17:15:53Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM 0.0 -> 41.0, grade ungraded -> C (gaia dev calibrate-trust-magnitude;
    Issue #1600)'
- timestamp: '2026-09-04T10:58:45Z'
  action: recalibrate_trust_magnitude
  contributor: unknown
  details: 'TM 41.0 -> 41.0, grade C -> C (gaia dev calibrate-trust-magnitude; Issue
    #1600)'
- timestamp: '2026-09-04T18:43:51Z'
  action: recalibrate_trust_magnitude
  contributor: unknown
  details: 'TM 41.0 -> 41.0, grade C -> C (gaia dev calibrate-trust-magnitude; Issue
    #1600)'
evidence:
- source: https://github.com/mattpocock/skills/blob/main/skills/misc/scaffold-exercises/SKILL.md
  evaluator: unknown
  date: '2026-06-19'
  class: B
- source: https://github.com/mattpocock/skills/blob/main/skills/misc/scaffold-exercises/SKILL.md
  evaluator: mbtiongson1
  date: '2026-06-20'
  type: repo-own
  trustNumber: 65.0
  notes: 'I13 classify: repo-own evidence backfill (skill file)'
  skillCountInRepo: 34
  sourceStartedAt: '2026-06-19'
- source: https://github.com/mattpocock/skills/blob/main/skills/misc/scaffold-exercises
  evaluator: mbtiongson1
  date: '2026-06-20'
  type: self-attestation
  trustNumber: 45.0
  grade: C
  notes: 'I13 classify: contributor-owned skill directory evidence'
  sourceStartedAt: '2026-06-19'
- source: https://github.com/mattpocock/skills
  evaluator: mbtiongson1
  date: '2026-08-20'
  type: repo-own
  commits: 525
  contributors: 7
  grade: B
verification:
  firstEvidenceAt: '2026-06-19T13:06:25Z'
trustMagnitude: 41.0
overallTrustGrade: C
apexGateStatus:
  aGradedOriginsGte5: false
  sourceTenureDaysGte180AorS: false
  directNestedSuiteGte1: false
  depth2OnlyReachableGte1: false
  overallGradeS: false
  apexPromotionPrSigned: false
  crossOrgVerifier: null
  systemWideCap: null
trustMagnitudeInputHash: 763a947db45032c8a48515247203e3bc93cdded19abaefc5c44489e4eac948f3
title: Scaffold Exercises
suiteRef: mattpocock/misc
---

## Installation

This skill is included in the Matt Pocock skills suite. It is highly recommended to install the full suite to enable cross-skill context sharing.

```bash
npx skills@latest add mattpocock/skills
```

No additional setup required beyond the main suite installation.
