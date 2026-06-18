---
id: ruvnet/flow-nexus
name: Flow Nexus
contributor: ruvnet
origin: true
genericSkillRef: multi-node-orchestration
status: named
title: The Grand Conductor's Trilogy
catalogRef: ruvnet-flow-nexus
level: 4★
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
updatedAt: '2026-06-14'
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
  notes: Ruflo orchestration platform — 34k+ GitHub stars. (backfilled — class-to-type
    migration)
  type: repo
  trustNumber: 70.0
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
trustMagnitudeInputHash: b893b11b88d20099e9a71bef7bf00f2ca25b93536492968bc9d940480cd8e75c
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
