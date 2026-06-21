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
level: 1★
description: Manages concurrent work item execution with independence verification,
  queue-based state tracking, and configurable concurrency limits (default 5).
tags:
- parallelism
- concurrency
- task-execution
- queue
updatedAt: '2026-06-21'
evidence:
- class: C
  source: https://github.com/intelligentcode-ai/skills/blob/main/skills/parallel-execution/SKILL.md
  evaluator: mbtiongson1
  date: '2026-04-30'
  notes: intelligentcode-ai/skills — practical coding agent skills; parallel-execution
    provides production-ready implementation (trust updated from C=50 to B-equiv=65)
  type: repo
  commits: 34
  contributors: 1
  trustNumber: 65.0
- source: https://github.com/intelligentcode-ai/skills
  evaluator: unknown
  date: '2026-06-20'
  type: self-attestation
  trustNumber: 60.0
  grade: C
  notes: intelligentcode-ai/skills suite self-attested via README description; practical
    agent skill for parallel-execution domain
  sourceStartedAt: '2025-01-01'
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
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:40Z'
  details: TM 0.0 -> 1.3, grade ungraded -> ungraded (direct edit -- CLI gap)
- timestamp: '2026-06-19T17:10:12Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/intelligentcode-ai/skills/blob/main/skills/parallel-execution/SKILL.md
    as B (trustNumber: 65.0)'
- timestamp: '2026-06-19T17:10:46Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/intelligentcode-ai/skills (type:
    self-attestation)'
- timestamp: '2026-06-19T17:10:47Z'
  action: evidence_graded
  contributor: unknown
  details: 'Graded evidence from https://github.com/intelligentcode-ai/skills as B
    (trustNumber: 60.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T17:13:02Z'
  details: TM 1.3 -> 6.3, grade ungraded -> ungraded (direct edit -- CLI gap)
- timestamp: '2026-06-20T06:31:29Z'
  action: demote
  contributor: mbtiongson1
  details: Level updated from 2★ to 1★ per G7 final rankings calibration.
trustMagnitude: 6.3
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
trustMagnitudeInputHash: 9a005e6cb37f556d586495a51fd4d3b632cbc17ad1fc69658b0179321d7dba1d
verification:
  firstEvidenceAt: '2026-06-19T17:10:46Z'
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
