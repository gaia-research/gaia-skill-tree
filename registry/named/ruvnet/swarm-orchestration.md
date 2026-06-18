---
id: ruvnet/swarm-orchestration
name: Swarm Orchestration
contributor: ruvnet
origin: true
genericSkillRef: swarm-topology-management
status: named
title: The Topology Architect
catalogRef: ruvnet-swarm-orchestration
level: 1★
description: Initializes and manages multi-agent swarm network topologies (hierarchical,
  mesh, ring, star) with automatic load balancing, fault tolerance, and shared memory
  coordination.
links:
  github: https://github.com/ruvnet/ruflo
tags:
- swarm
- topology
- multi-agent
- load-balancing
- fault-tolerance
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
timeline:
- timestamp: '2026-06-02T23:48:23Z'
  action: demote
  contributor: unknown
  details: Calibrated level from 3★ to 1★
- timestamp: '2026-06-14T12:33:00Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/ruvnet/ruflo as B (trustNumber:
    70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:21Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
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
trustMagnitudeInputHash: f0b8a688bedd3bd788dec68460d174156b62c27fc648ec10f8eb98a702bdec74
---

## Overview

Swarm Orchestration provides foundational swarm network topology management for multi-agent systems. It supports four topology patterns: hierarchical for centralized coordination, mesh for peer-to-peer equality, ring for sequential processing, and star for delegation. The system handles load balancing through performance-based agent selection and provides built-in fault tolerance with retry logic and task reassignment.

## Key Capabilities

- **4 topology patterns**: hierarchical, mesh, ring, and star agent network configurations
- **Load balancing**: performance-based agent selection and dynamic work distribution
- **Fault tolerance**: retry logic and automatic task reassignment on agent failure
- **Shared memory coordination**: cross-agent context sharing for coherent swarm behavior
- **Real-time performance monitoring**: live agent health and throughput metrics

## Origin

First published by @ruvnet as part of the Ruflo orchestration platform. This is the origin implementation for the `swarm-topology-management` skill bucket.

Sourced from the Ruflo platform (ruvnet/ruflo, 34k+ stars).

## Installation

This skill is part of the Ruflo orchestration platform.

```bash
npx ruflo@latest init
```

See the [Ruflo (ruvnet/ruflo)](../ruvnet/ruflo.md) capstone for full multi-topology installation options.
