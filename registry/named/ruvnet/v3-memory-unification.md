---
id: ruvnet/v3-memory-unification
name: V3 Memory Unification
contributor: ruvnet
origin: false
role: variant
genericSkillRef: memory-manage
status: named
title: The Memory Consolidator
catalogRef: ruvnet-v3-memory-unification
level: 1★
description: Unifies disparate Ruflo v3 memory subsystems (AgentDB, RVF, RAG memory)
  into a single coherent memory management layer.
links:
  github: https://github.com/ruvnet/ruflo
tags:
- memory-unification
- agentdb
- rvf
- rag-memory
- v3-sprint
createdAt: '2026-05-19'
updatedAt: '2026-09-05'
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
timeline:
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:21Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:39Z'
  details: TM 0.0 -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:44Z'
  details: TM 0.0 -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- timestamp: '2026-06-20T06:31:37Z'
  action: demote
  contributor: mbtiongson1
  details: Level updated from 2★ to 1★ per G7 final rankings calibration.
- timestamp: '2026-08-29T17:16:00Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM 0.0 -> 0.0, grade ungraded -> ungraded (gaia dev calibrate-trust-magnitude;
    Issue #1600)'
- timestamp: '2026-09-04T18:43:52Z'
  action: recalibrate_trust_magnitude
  contributor: unknown
  details: 'TM 0.0 -> 0.0, grade ungraded -> ungraded (gaia dev calibrate-trust-magnitude;
    Issue #1600)'
trustMagnitudeInputHash: 65ddbad347c545e83e8b9236e6f32bdea8ae3f5d1a12f5f5cc2921589adc3016
suiteRef: ruvnet/ruflo
---

## Overview

V3 Memory Unification consolidates all Ruflo v3 memory subsystems into a single coherent management layer. It bridges AgentDB (vector memory), RVF (cross-session persistence), and RAG memory (hybrid search) behind a unified interface, enabling agents to read and write across all storage backends transparently.

## Key Capabilities

- **Unified memory interface**: single API abstracting AgentDB, RVF, and RAG memory backends
- **AgentDB/RVF/RAG bridge**: transparent routing of reads and writes to the appropriate backend
- **Cross-session persistence**: durable storage enabling memory retrieval across agent sessions
- **Unified search**: single query surface spanning vector, relational, and hybrid search backends

## Origin

Published by @ruvnet as a variant implementation for the `memory-manage` skill bucket.

Sourced from the Ruflo platform (ruvnet/ruflo, 34k+ stars).

## Installation

This skill is part of the Ruflo orchestration platform.

```bash
npx ruflo@latest init
```

See the [Ruflo (ruvnet/ruflo)](../ruvnet/ruflo.md) capstone for full multi-topology installation options.
