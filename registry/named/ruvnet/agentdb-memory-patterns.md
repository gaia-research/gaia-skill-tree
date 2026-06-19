---
id: ruvnet/agentdb-memory-patterns
name: AgentDB Memory Patterns
contributor: ruvnet
origin: true
genericSkillRef: memory-pattern-design
status: named
title: The Memory Weaver
catalogRef: ruvnet-agentdb-memory-patterns
level: 2★
description: Designs recurring memory storage patterns for AI agents with LRU caching,
  SQLite persistence, and associative retrieval across multiple memory types.
links:
  github: https://github.com/ruvnet/ruflo
tags:
- memory-patterns
- lru-cache
- sqlite
- associative-retrieval
createdAt: '2026-05-19'
updatedAt: '2026-06-14'
suiteRef: ruvnet/agentdb
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
- timestamp: '2026-06-14T12:32:50Z'
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
  timestamp: '2026-06-19T13:19:38Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
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
trustMagnitudeInputHash: 87d720e33a8666e1f7ae8a292b5802a84e0124c4a7c8bef2791a05157d8aa38d
---

## Overview

AgentDB Memory Patterns provides structured approaches to agent memory organization. It covers eight memory types: knowledge, context, task data, results, errors, metrics, consensus records, and system configuration. LRU caching ensures fast access to frequently used patterns. SQLite persistence enables cross-session continuity with WAL mode for concurrent access.

## Key Capabilities

- **8 memory type taxonomy**: knowledge, context, task data, results, errors, metrics, consensus records, and system config
- **LRU caching**: fast retrieval for frequently accessed memory patterns
- **SQLite WAL persistence**: cross-session continuity with concurrent-access write-ahead logging
- **Associative memory building**: structured links between related memory entries for contextual retrieval

## Origin

First published by @ruvnet as part of the Ruflo orchestration platform. This is the origin implementation for the `memory-pattern-design` skill bucket.

Sourced from the Ruflo platform (ruvnet/ruflo, 34k+ stars).
