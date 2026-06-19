---
id: ruvnet/worker-integration
name: Worker Integration
contributor: ruvnet
origin: true
genericSkillRef: worker-agent-dispatch
status: named
title: The Task Dispatcher
catalogRef: ruvnet-worker-integration
level: 2★
description: Maps trigger events to optimal agent combinations for background task
  execution with performance tracking and adaptive feedback.
links:
  github: https://github.com/ruvnet/ruflo
tags:
- worker
- dispatch
- background-tasks
- event-driven
- performance-tracking
createdAt: '2026-05-19'
updatedAt: '2026-06-14'
suiteRef: ruvnet/ruflo
evidence:
- class: B
  source: https://github.com/ruvnet/ruflo
  evaluator: mbtiongson1
  date: '2026-05-19'
  notes: Ruflo orchestration platform — 34k+ GitHub stars. (backfilled — class-to-type
    migration)
  type: repo
  trustNumber: 70.0
  grade: B
  commits: 6899
  contributors: 32
timeline:
- timestamp: '2026-06-14T12:33:02Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/ruvnet/ruflo as B (trustNumber:
    70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:21Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T11:07:58Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:39Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
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

Worker Integration implements the core dispatch layer for Ruflo's background worker system. It maps incoming trigger events to curated agent combinations, routes tasks to the most suitable workers based on confidence scoring, and closes the feedback loop by recording performance data for continuous improvement. The system supports 8 distinct trigger types and adapts agent selection over time.

## Key Capabilities

- **8-trigger dispatch mapping**: routes code review, testing, documentation, security, performance, refactoring, deployment, and maintenance triggers to appropriate agent sets
- **Confidence-scored agent selection**: ranks available agents by historical performance and task affinity before dispatch
- **Performance feedback loop**: records task outcomes back into the dispatch model for adaptive routing improvement
- **Structured memory patterns**: stores task results and agent performance metrics in the Ruflo memory subsystem for cross-session learning

## Origin

First published by @ruvnet as part of the Ruflo orchestration platform. This is the origin implementation for the `worker-agent-dispatch` skill bucket.

Sourced from the Ruflo platform (ruvnet/ruflo, 34k+ stars).

## Installation

This skill is part of the Ruflo orchestration platform.

```bash
npx ruflo@latest init
```

See the [Ruflo (ruvnet/ruflo)](../ruvnet/ruflo.md) capstone for full multi-topology installation options.
