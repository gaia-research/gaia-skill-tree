---
id: gsd-build/get-shit-done
name: Get Shit Done
contributor: gsd-build
origin: false
genericSkillRef: git-ship-done-pipeline
status: named
level: 3★
description: 'Git Ship Done pipeline for Claude Code: discuss, plan, execute, verify,
  and ship as a repeatable agentic software delivery loop.'
createdAt: '2026-07-03'
updatedAt: '2026-07-16'
tags:
- suite
- pipeline
- agentic-workflow
timeline:
- timestamp: '2026-07-02T18:04:57Z'
  action: add
  contributor: unknown
  details: Added named skill gsd-build/get-shit-done
- timestamp: '2026-07-02T18:05:09Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/gsd-build/get-shit-done/stargazers
    (type: github-stars-own)'
- timestamp: '2026-07-02T18:05:10Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/gsd-build/get-shit-done (type:
    repo-own)'
- timestamp: '2026-07-02T18:05:38Z'
  action: demote
  contributor: unknown
  details: Origin status set to false.
- timestamp: '2026-07-02T18:06:04Z'
  action: note
  contributor: unknown
  details: Updated GitHub link to https://github.com/gsd-build/get-shit-done/blob/main/README.md
- timestamp: '2026-07-02T18:09:49Z'
  action: note
  contributor: unknown
  details: 'Fused suite components: gsd-build/discuss-phase, gsd-build/plan-phase,
    gsd-build/execute-phase, gsd-build/verify-work, gsd-build/ship.'
- timestamp: '2026-07-02T20:53:12Z'
  action: name
  contributor: unknown
  details: Promoted from awakened to named.
- timestamp: '2026-07-02T20:53:12Z'
  action: rank_up
  contributor: unknown
  details: Calibrated level from 1★ to 2★
- timestamp: '2026-07-02T20:59:03Z'
  action: note
  contributor: unknown
  details: Set installable to false
- timestamp: '2026-07-02T21:04:08Z'
  action: note
  contributor: unknown
  details: Set installable to true
- action: migrate_trust_magnitude
  timestamp: '2026-07-02T21:30:15Z'
  details: TM None -> 202.16, grade ungraded -> A (direct edit -- CLI gap)
- timestamp: '2026-07-02T21:33:55Z'
  action: note
  contributor: unknown
  details: Updated GitHub link to https://github.com/gsd-build/get-shit-done/blob/main/README.md
- timestamp: '2026-07-02T21:34:10Z'
  action: rank_up
  contributor: unknown
  details: Calibrated level from 2★ to 4★
- timestamp: '2026-07-08T19:56:14Z'
  action: upstream_synced
  contributor: github-actions[bot]
  previousValue: null
  newValue: v1.42.3
  details: first-run baseline
- timestamp: '2026-07-16T08:36:43Z'
  action: type_change
  contributor: mbtiongson1
  details: 'Generic parent ''git-ship-done-pipeline'' type: extra/ultimate → fusion
    (Yggdrasil II taxonomy migration #997)'
  metaEpoch: yggdrasil-ii
  migrationBatch: yggdrasil-ii@2026-07-16
- timestamp: '2026-07-16T08:36:43Z'
  action: demote
  contributor: mbtiongson1
  previousValue: 4★
  newValue: 3★
  details: 'Yggdrasil II recalibration: 4★ suite-branch gate failed (suite-branch
    TM=52.2 (< 100.0)) — demoted to 3★ Evolved'
  metaEpoch: yggdrasil-ii
  migrationBatch: yggdrasil-ii@2026-07-16
evidence:
- source: https://github.com/gsd-build/get-shit-done/stargazers
  evaluator: unknown
  date: '2026-07-03'
  type: github-stars-own
  stars: 64635
  skillCountInRepo: 5
- source: https://github.com/gsd-build/get-shit-done
  evaluator: unknown
  date: '2026-07-03'
  type: repo-own
  commits: 2888
  contributors: 136
  grade: B
verification:
  firstEvidenceAt: '2026-07-02T18:05:09Z'
title: Get Shit Done
installable: true
suiteComponents:
- gsd-build/discuss-phase
- gsd-build/execute-phase
- gsd-build/plan-phase
- gsd-build/ship
- gsd-build/verify-work
trustMagnitude: 202.16
overallTrustGrade: A
apexGateStatus:
  aGradedOriginsGte5: false
  sourceTenureDaysGte180AorS: false
  directNestedSuiteGte1: false
  depth2OnlyReachableGte1: false
  overallGradeS: false
  apexPromotionPrSigned: false
  crossOrgVerifier: null
  systemWideCap: null
trustMagnitudeInputHash: e97616a7dfa339c7a99c95043b951f9b9a049190bc6ea5aacf7ab550d93cdf48
links:
  github: https://github.com/gsd-build/get-shit-done/blob/main/README.md
upstream:
  mode: components
  releasedAt: '2026-05-16T04:36:09Z'
  repo: gsd-build/get-shit-done
  sourceUrl: https://github.com/gsd-build/get-shit-done/releases/tag/v1.42.3
  syncedAt: '2026-07-08T19:56:14Z'
  version: v1.42.3
---

## Installation

Install the full GSD Core software development pipeline with:

```bash
npx @opengsd/gsd-core@latest
```

This is the recommended path from the upstream repo's Quickstart.
