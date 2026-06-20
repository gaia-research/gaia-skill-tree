---
id: ruvnet/swarm-advanced
name: Swarm Advanced
contributor: ruvnet
origin: true
genericSkillRef: advanced-swarm-coordination
status: named
title: The Grand Swarm Master
catalogRef: ruvnet-swarm-advanced
level: 2★
description: Domain-specific swarm orchestration patterns for research, development,
  testing, and analysis workflows with neural learning and cross-session state persistence.
links:
  github: https://github.com/ruvnet/ruflo
tags:
- advanced-swarm
- neural-learning
- research-swarm
- dev-swarm
- state-persistence
createdAt: '2026-05-19'
updatedAt: '2026-06-14'
suiteRef: ruvnet/ruflo-v3
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
- timestamp: '2026-06-02T23:48:23Z'
  action: demote
  contributor: unknown
  details: Calibrated level from 3★ to 1★
- timestamp: '2026-06-14T12:32:59Z'
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
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:44Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- timestamp: '2026-06-20T06:31:37Z'
  action: rank_up
  contributor: mbtiongson1
  details: Level updated from 1★ to 2★ per G7 final rankings calibration.
trustMagnitude: 36.0
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
trustMagnitudeInputHash: b9ab812efe1e61a83768c7bd69d0fee8161d5de9b21ddde786e0d249ff535791
---

## Overview

Swarm Advanced provides four specialized swarm patterns for complex domain workflows: Research Swarm for parallel information gathering and synthesis, Development Swarm for full-stack application building, Testing Swarm for distributed quality assurance, and Analysis Swarm for deep system inspection. Each pattern uses specialized agent role differentiation. Neural pattern learning improves swarm performance over time, and state snapshots enable cross-session persistence.

## Key Capabilities

- **4 domain swarm patterns**: Research, Development, Testing, and Analysis swarms with role-differentiated agents
- **Neural pattern learning**: adaptive performance improvement from accumulated swarm execution history
- **State snapshots**: cross-session persistence enabling long-running swarm workflows to resume
- **2–3x performance improvement**: measured gains from domain-specific topology optimization

## Origin

First published by @ruvnet as part of the Ruflo orchestration platform. This is the origin implementation for the `advanced-swarm-coordination` skill bucket.

Sourced from the Ruflo platform (ruvnet/ruflo, 34k+ stars).

## Installation

This skill is part of the Ruflo orchestration platform.

```bash
npx ruflo@latest init
```

See the [Ruflo (ruvnet/ruflo)](../ruvnet/ruflo.md) capstone for full multi-topology installation options.
