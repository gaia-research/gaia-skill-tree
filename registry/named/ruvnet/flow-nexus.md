---
id: ruvnet/flow-nexus
name: Flow Nexus
contributor: ruvnet
origin: true
genericSkillRef: multi-node-orchestration
status: named
title: The Grand Conductor's Trilogy
catalogRef: ruvnet-flow-nexus
level: 3★
description: 'Complete Flow Nexus platform: multi-topology swarm deployment, cloud
  platform management with Queen Seraphina AI assistant, and distributed neural training.'
links:
  github: https://github.com/ruvnet/ruflo
tags:
- flow-nexus
- orchestration
- swarm
- cloud-platform
- neural-training
- queen-seraphina
createdAt: '2026-05-19'
updatedAt: '2026-08-30'
suiteRef: ruvnet/ruflo
suiteComponents:
- ruvnet/flow-nexus-neural
- ruvnet/flow-nexus-platform
- ruvnet/flow-nexus-swarm
evidence:
- class: B
  source: https://github.com/ruvnet/ruflo
  evaluator: mbtiongson1
  date: '2026-05-19'
  notes: 'Ruflo orchestration platform — 34k+ GitHub stars. (backfilled — class-to-type"
    migration) (CLI gap: --commits/--contributors not supported by gaia dev evidence)'
  type: repo
  trustNumber: 70.0
  commits: 6899
  contributors: 32
  grade: B
timeline:
- timestamp: '2026-06-14T12:32:55Z'
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
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:44Z'
  details: TM 0.0 -> 96.0, grade ungraded -> B (direct edit -- CLI gap)
- timestamp: '2026-06-20T06:31:36Z'
  action: demote
  contributor: mbtiongson1
  details: Level updated from 4★ to 3★ per G7 final rankings calibration.
- timestamp: '2026-07-08T19:57:06Z'
  action: upstream_synced
  contributor: github-actions[bot]
  previousValue: null
  newValue: v3.25.5
  details: first-run baseline
- timestamp: '2026-08-29T17:15:58Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM 96.0 -> 36.0, grade B -> C (gaia dev calibrate-trust-magnitude; Issue
    #1600)'
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
trustMagnitudeInputHash: e3e469ea614c63c8ead7495b8e0f3be1393f770f60eed9f95cf4ae19c935f895
upstream:
  mode: components
  releasedAt: '2026-07-08T17:27:46Z'
  repo: ruvnet/ruflo
  sourceUrl: https://github.com/ruvnet/ruflo/releases/tag/v3.25.5
  syncedAt: '2026-07-08T19:57:06Z'
  version: v3.25.5
---

## Overview

Flow Nexus is a 4★ fusion of the three Flow Nexus discipline skills: `flow-nexus-swarm` (multi-topology agent swarm deployment), `flow-nexus-platform` (cloud orchestration platform with the Queen Seraphina AI assistant), and `flow-nexus-neural` (distributed neural training across multi-agent networks). Together they form a complete cloud-native AI orchestration solution capable of managing agents from individual workers up to planetary-scale distributed training runs.

## Key Capabilities

- **Multi-topology swarm deployment**: hierarchical, mesh, ring, and star agent networks with event-driven workflow orchestration
- **Cloud platform management**: full lifecycle management of cloud-hosted agent fleets, powered by the Queen Seraphina AI assistant in the platform tier
- **Distributed neural training**: federated training across multi-agent networks with gradient aggregation and fault tolerance
- **Unified orchestration surface**: single interface spanning swarm control, platform ops, and neural training coordination

## Origin

First published by @ruvnet as part of the Ruflo orchestration platform. This is the origin implementation for the `flow-nexus-orchestration` skill bucket.

This 4★ fusion unites flow-nexus-swarm + flow-nexus-platform + flow-nexus-neural. Queen Seraphina lives in the platform tier.

Sourced from the Ruflo platform (ruvnet/ruflo, 34k+ stars).

## Installation

This skill is part of the Ruflo orchestration platform.

```bash
npx ruflo@latest init
```

See the [Ruflo (ruvnet/ruflo)](../ruvnet/ruflo.md) capstone for full multi-topology installation options.
