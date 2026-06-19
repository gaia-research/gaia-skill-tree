---
id: intelligentcode-ai/parallel-execution
name: Parallel Execution
contributor: intelligentcode-ai
origin: false
links:
  github: https://github.com/intelligentcode-ai/skills/blob/main/skills/parallel-execution/SKILL.md
genericSkillRef: parallel-execution
status: named
title: The Concurrency Master
level: 2★
description: Manages concurrent work item execution with independence verification,
  queue-based state tracking, and configurable concurrency limits (default 5).
tags:
- parallelism
- concurrency
- task-execution
- queue
updatedAt: '2026-06-14'
evidence:
- class: C
  source: https://github.com/intelligentcode-ai/skills/blob/main/skills/parallel-execution/SKILL.md
  evaluator: mbtiongson1
  date: '2026-04-30'
  notes: intelligentcode-ai/skills parallel-execution — concurrent work item execution
    with independence verification and configurable concurrency (default 5). (backfilled
    — class-to-type migration)
  type: repo
  commits: 34
  contributors: 1
  trustNumber: 50.0
  grade: C
timeline:
- timestamp: '2026-06-14T12:32:41Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/intelligentcode-ai/skills/blob/main/skills/parallel-execution/SKILL.md
    as C (trustNumber: 50.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:17Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T11:10:48Z'
  details: TM 0.0 -> 1.3, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:38Z'
  details: TM 0.0 -> 1.3, grade ungraded -> ungraded (direct edit -- CLI gap)
trustMagnitude: 0.0
overallTrustGrade: ungraded
apexGateStatus:
  aGradedOriginsGte5: false
  sourceTenureDaysGte180AorS: false
  directNestedSuiteGte1: false
  depth2OnlyReachableGte1: false
  overallGradeS: false
  apexPromotionPrSigned: false
  crossOrgVerifier: null
  systemWideCap: null
---

## Overview

Before launching parallel tasks, verifies that each candidate is truly independent (no shared mutable state, no ordering constraints). Tracks running items in a queue and merges results once all branches complete.

## Key behaviours

- Independence check before fan-out: aborts if tasks share a dependency
- Configurable concurrency ceiling (default 5 simultaneous items)
- Queue-based tracking with per-item status (pending / running / done / failed)
- Fan-in: waits for all branches, merges outputs, surfaces failures individually

## Source

[intelligentcode-ai/skills — parallel-execution/SKILL.md](https://github.com/intelligentcode-ai/skills/blob/main/skills/parallel-execution/SKILL.md)
