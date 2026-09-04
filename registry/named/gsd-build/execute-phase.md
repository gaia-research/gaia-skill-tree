---
id: gsd-build/execute-phase
name: GSD Execute Phase
contributor: gsd-build
origin: false
genericSkillRef: subagent-driven-development
status: named
level: 3★
description: Runs implementation plans in parallel executor waves where each executor
  starts from a clean context.
createdAt: '2026-07-03'
updatedAt: '2026-09-04'
timeline:
- timestamp: '2026-07-02T18:04:49Z'
  action: add
  contributor: unknown
  details: Added named skill gsd-build/execute-phase
- timestamp: '2026-07-02T18:05:04Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/gsd-build/get-shit-done/blob/main/commands/gsd/execute-phase.md
    (type: github-stars-own)'
- timestamp: '2026-07-02T18:05:57Z'
  action: note
  contributor: unknown
  details: Updated GitHub link to https://github.com/gsd-build/get-shit-done/blob/main/commands/gsd/execute-phase.md
- timestamp: '2026-07-02T18:09:47Z'
  action: suite_ref_set
  contributor: unknown
  details: Set suiteRef to gsd-build/get-shit-done
- timestamp: '2026-07-02T20:53:08Z'
  action: name
  contributor: unknown
  details: Promoted from awakened to named.
- timestamp: '2026-07-02T20:53:09Z'
  action: rank_up
  contributor: unknown
  details: Calibrated level from 1★ to 2★
- timestamp: '2026-07-02T20:59:01Z'
  action: note
  contributor: unknown
  details: Set installable to false
- timestamp: '2026-07-02T21:04:07Z'
  action: note
  contributor: unknown
  details: Set installable to true
- timestamp: '2026-07-02T21:07:14Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/gsd-build/get-shit-done (type:
    repo-own)'
- action: migrate_trust_magnitude
  timestamp: '2026-07-02T21:30:15Z'
  details: TM None -> 52.16, grade ungraded -> B (direct edit -- CLI gap)
- timestamp: '2026-07-02T21:33:53Z'
  action: note
  contributor: unknown
  details: Updated GitHub link to https://github.com/gsd-build/get-shit-done/blob/main/commands/gsd/execute-phase.md
- timestamp: '2026-07-02T21:34:09Z'
  action: rank_up
  contributor: unknown
  details: Calibrated level from 2★ to 3★
- timestamp: '2026-08-06T04:54:31Z'
  action: note
  contributor: unknown
  details: Updated GitHub link to https://github.com/open-gsd/gsd-core/blob/next/commands/gsd/execute-phase.md
- timestamp: '2026-08-29T17:15:48Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM 52.16 -> 50.0, grade B -> B (gaia dev calibrate-trust-magnitude; Issue
    #1600)'
- timestamp: '2026-09-04T10:58:44Z'
  action: recalibrate_trust_magnitude
  contributor: unknown
  details: 'TM 50.0 -> 50.0, grade B -> B (gaia dev calibrate-trust-magnitude; Issue
    #1600)'
evidence:
- source: https://github.com/gsd-build/get-shit-done/blob/main/commands/gsd/execute-phase.md
  updatedAt: '2026-09-01'
  evaluator: unknown
  date: '2026-07-03'
  type: github-stars-own
  stars: 64612
  skillCountInRepo: 5
- source: https://github.com/gsd-build/get-shit-done
  evaluator: unknown
  date: '2026-07-03'
  type: repo-own
  commits: 2888
  contributors: 136
  grade: B
verification:
  firstEvidenceAt: '2026-07-02T18:05:04Z'
title: GSD Execute Phase
installable: true
suiteRef: gsd-build/get-shit-done
trustMagnitude: 50.0
overallTrustGrade: B
apexGateStatus:
  aGradedOriginsGte5: false
  sourceTenureDaysGte180AorS: false
  directNestedSuiteGte1: false
  depth2OnlyReachableGte1: false
  overallGradeS: false
  apexPromotionPrSigned: false
  crossOrgVerifier: null
  systemWideCap: null
trustMagnitudeInputHash: 393cdbefeef7527270b8d7aa9be2bb60f5628f18eb141e6a8ca4af4df3d4b95e
links:
  github: https://github.com/open-gsd/gsd-core/blob/next/commands/gsd/execute-phase.md
---

## Installation

This skill is part of the GSD Core pipeline. Install the suite with:

```bash
npx @opengsd/gsd-core@latest
```

Then use the matching phase from the installed GSD workflow.
