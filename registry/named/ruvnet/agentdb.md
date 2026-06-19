---
id: ruvnet/agentdb
name: AgentDB
contributor: ruvnet
origin: true
genericSkillRef: agent-memory-platform
status: named
title: The Memory Sovereign
catalogRef: ruvnet-agentdb
level: 5★
description: Complete AgentDB vector memory platform fused from 5 discipline skills
  — QUIC-synchronized distributed storage, pattern learning, memory design, optimization,
  and vector search.
links:
  github: https://github.com/ruvnet/ruflo
tags:
- agentdb
- vector-memory
- distributed
- ultimate
- memory-platform
createdAt: '2026-05-19'
updatedAt: '2026-06-19'
suiteRef: ruvnet/ruflo
suiteComponents:
- ruvnet/agentdb-advanced
- ruvnet/agentdb-learning
- ruvnet/agentdb-memory-patterns
- ruvnet/agentdb-optimization
- ruvnet/agentdb-vector-search
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
- source: https://github.com/ruvnet/ruflo/issues/1207
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: peer-review
  class: A
  notes: Major AgentDB upgrade introducing RVF backend, self-learning capabilities,
    and witness chain for memory persistence.
- source: https://github.com/ruvnet/ruflo/issues/829
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: peer-review
  class: A
  notes: High-engagement feature request demonstrating AgentDB performance benefits
    (150x-12,500x improvements) with backward compatibility.
timeline:
- timestamp: '2026-06-14T12:32:52Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/ruvnet/ruflo as B (trustNumber:
    70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:20Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T11:07:58Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- timestamp: '2026-06-19T12:51:31Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/ruvnet/ruflo/issues/1207 (type:
    peer-review)'
- timestamp: '2026-06-19T12:51:49Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/ruvnet/ruflo/issues/829 (type:
    peer-review)'
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
trustMagnitudeInputHash: 1d9fd98e4b2fb18e7e2b0bda1a01273d694aba5f7fe66cda5c5dea4078308c6a
verification:
  firstEvidenceAt: '2026-06-19T12:51:31Z'
---

## Overview

AgentDB is the 5★ Ultimate fusion of the complete AgentDB skill suite: `agentdb-vector-search`, `agentdb-memory-patterns`, `agentdb-optimization`, `agentdb-learning`, and `agentdb-advanced`. It represents mastery of the entire AgentDB vector memory platform — from QUIC-synchronized distributed storage and pattern learning, to memory schema design, query optimization, and advanced vector search. At this level, an agent can architect, operate, and extend the full AgentDB stack.

## Key Capabilities

- **QUIC-synchronized distributed storage**: multi-node AgentDB clusters with low-latency QUIC transport and strong consistency guarantees
- **Pattern learning and memory design**: adaptive pattern recognition that shapes memory schemas for evolving agent knowledge domains
- **Query optimization and vector search**: 150x–12,500x faster than brute-force HNSW search through learned index structures and pruning
- **Cross-session persistence**: durable memory that survives agent restarts, migrations, and platform upgrades
- **Full platform mastery**: end-to-end ownership of the AgentDB stack from wire protocol to application-layer memory API

## Origin

First published by @ruvnet as part of the Ruflo orchestration platform. This is the origin implementation for the `agent-memory-platform` skill bucket.

This 5★ Ultimate fuses agentdb-vector-search + agentdb-memory-patterns + agentdb-optimization + agentdb-learning + agentdb-advanced. Evidence: 34k+ stars, 150x–12,500x faster than brute-force HNSW search, exceeding the 10k-star Grandmaster threshold.

Sourced from the Ruflo platform (ruvnet/ruflo, 34k+ stars).

## Installation

This skill is part of the Ruflo orchestration platform.

```bash
npx ruflo@latest init
```

See the [Ruflo (ruvnet/ruflo)](../ruvnet/ruflo.md) capstone for full multi-topology installation options.
