---
id: gsd-build/gsd-plan-phase
name: GSD Plan Phase
contributor: gsd-build
origin: false
genericSkillRef: writing-plans
status: named
level: 3★
description: Researches, decomposes, and verifies an implementation plan against a
  fresh context window before execution.
createdAt: '2026-07-03'
updatedAt: '2026-10-09'
timeline:
- timestamp: '2026-07-02T18:04:48Z'
  action: add
  contributor: unknown
  details: Added named skill gsd-build/plan-phase
- timestamp: '2026-07-02T18:05:02Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/gsd-build/get-shit-done/blob/main/commands/gsd/plan-phase.md
    (type: github-stars-own)'
- timestamp: '2026-07-02T18:05:57Z'
  action: note
  contributor: unknown
  details: Updated GitHub link to https://github.com/gsd-build/get-shit-done/blob/main/commands/gsd/plan-phase.md
- timestamp: '2026-07-02T18:09:47Z'
  action: suite_ref_set
  contributor: unknown
  details: Set suiteRef to gsd-build/get-shit-done
- timestamp: '2026-07-02T20:53:07Z'
  action: name
  contributor: unknown
  details: Promoted from awakened to named.
- timestamp: '2026-07-02T20:53:07Z'
  action: rank_up
  contributor: unknown
  details: Calibrated level from 1★ to 2★
- timestamp: '2026-07-02T20:59:00Z'
  action: note
  contributor: unknown
  details: Set installable to false
- timestamp: '2026-07-02T21:04:06Z'
  action: note
  contributor: unknown
  details: Set installable to true
- timestamp: '2026-07-02T21:07:13Z'
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
  details: Updated GitHub link to https://github.com/gsd-build/get-shit-done/blob/main/commands/gsd/plan-phase.md
- timestamp: '2026-07-02T21:34:08Z'
  action: rank_up
  contributor: unknown
  details: Calibrated level from 2★ to 3★
- timestamp: '2026-08-06T04:54:31Z'
  action: note
  contributor: unknown
  details: Updated GitHub link to https://github.com/open-gsd/gsd-core/blob/next/commands/gsd/plan-phase.md
- timestamp: '2026-08-29T17:15:49Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM 52.16 -> 50.0, grade B -> B (gaia dev calibrate-trust-magnitude; Issue
    #1600)'
- timestamp: '2026-09-04T10:58:44Z'
  action: recalibrate_trust_magnitude
  contributor: unknown
  details: 'TM 50.0 -> 50.0, grade B -> B (gaia dev calibrate-trust-magnitude; Issue
    #1600)'
- timestamp: '2026-10-08T20:43:29Z'
  action: rename
  contributor: unknown
  details: Renamed named skill from gsd-build/plan-phase to gsd-build/gsd-plan-phase
- timestamp: '2026-10-08T20:43:34Z'
  action: installation_updated
  contributor: unknown
  details: 'Replaced ## Installation section from /tmp/gsd-install-plan-phase.md'
- timestamp: '2026-10-08T20:43:34Z'
  action: note
  contributor: unknown
  details: Updated GitHub link to https://github.com/open-gsd/gsd-core/blob/next/skills/gsd-plan-phase/SKILL.md
evidence:
- source: https://github.com/gsd-build/get-shit-done/blob/main/commands/gsd/plan-phase.md
  updatedAt: '2026-10-01'
  evaluator: unknown
  date: '2026-07-03'
  type: github-stars-own
  stars: 64413
  skillCountInRepo: 5
- source: https://github.com/gsd-build/get-shit-done
  evaluator: unknown
  date: '2026-07-03'
  type: repo-own
  commits: 2888
  contributors: 136
  grade: B
verification:
  firstEvidenceAt: '2026-07-02T18:05:02Z'
title: GSD Plan Phase
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
trustMagnitudeInputHash: b1e59f2b4c61dd89363da02bbd4343ea98e98798eb3b5bfa9cc87ed440cf579d
links:
  github: https://github.com/open-gsd/gsd-core/blob/next/skills/gsd-plan-phase/SKILL.md
---

## Installation

Install the agent skill into your agent harness with Gaia:

```bash
gaia install gsd-build/gsd-plan-phase
```

### Runtime Prerequisite

This skill executes workflow definitions that require the externally installed `@opengsd/gsd-core` runtime in `~/.claude/gsd-core`. Gaia installs the agent skill definition, but does not install the GSD runtime.

Install the GSD runtime separately before invoking the skill:

```bash
npx -y @opengsd/gsd-core@latest --claude --local
```
