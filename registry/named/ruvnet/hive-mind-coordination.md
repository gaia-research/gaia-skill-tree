---
id: ruvnet/hive-mind-coordination
name: Hive Mind Coordination
contributor: ruvnet
origin: true
genericSkillRef: distributed-consensus-coordination
status: named
title: Queen Seraphina's Hive
level: 4★
description: Queen-led collective intelligence with Byzantine, majority, and weighted
  consensus mechanisms, eight worker specializations, and persistent collective SQLite
  memory with LRU caching.
links:
  github: https://github.com/ruvnet/ruflo/blob/main/.agents/skills/hive-mind/SKILL.md
tags:
- multi-agent
- consensus
- swarm
- collective-intelligence
- memory
createdAt: '2026-05-19'
updatedAt: '2026-06-14'
evidence:
- class: B
  source: https://github.com/ruvnet/ruflo
  evaluator: mbtiongson1
  date: '2026-05-19'
  notes: 'Ruflo orchestration platform — 34k+ GitHub stars. (backfilled — class-to-type"
    migration) (CLI gap: --commits/--contributors not supported by gaia dev evidence)'
  type: repo
  trustNumber: 70.0
  grade: B
  commits: 6899
  contributors: 32
timeline:
- timestamp: '2026-06-02T23:48:22Z'
  action: demote
  contributor: unknown
  details: Calibrated level from 4★ to 1★
- timestamp: '2026-06-04T20:30:49Z'
  action: note
  contributor: unknown
  details: Updated GitHub link to https://github.com/ruvnet/ruflo/blob/main/.agents/skills/hive-mind/SKILL.md
- timestamp: '2026-06-04T20:30:55Z'
  action: rank_up
  contributor: unknown
  details: Calibrated level from 1★ to 4★
- timestamp: '2026-06-14T12:32:56Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/ruvnet/ruflo as B (trustNumber:
    70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:20Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T11:52:12Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:39Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
suiteRef: ruvnet/ruflo
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

Hive Mind Coordination is a queen-led collective intelligence system from the Ruflo platform. The queen agent (Seraphina) coordinates specialized worker agents using Byzantine fault-tolerant, majority, and weighted consensus mechanisms. The system supports eight distinct worker specializations and persists collective memory in SQLite with LRU caching for fast associative retrieval.

## Key Capabilities

- **Queen-led consensus**: Byzantine, majority, and weighted voting mechanisms
- **Worker specializations**: eight distinct agent roles for diverse task coverage
- **Persistent memory**: SQLite-backed collective memory with LRU caching
- **Fault tolerance**: Byzantine consensus for resilience against worker failures

## Origin

First published by @ruvnet as part of the Ruflo orchestration platform. This is the origin implementation for the `hive-mind-coordination` unique skill bucket.

Sourced from the Ruflo platform (ruvnet/ruflo, 34k+ stars).

## Installation

This skill is part of the Ruflo orchestration platform.

```bash
npx ruflo@latest init
```

See the [Ruflo (ruvnet/ruflo)](../ruvnet/ruflo.md) capstone for full multi-topology installation options.
