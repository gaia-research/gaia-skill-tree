---
id: ruvnet/stream-chain
name: Stream Chain
contributor: ruvnet
origin: true
genericSkillRef: sequential-agent-pipeline
status: named
title: The Flow Conductor
catalogRef: ruvnet-stream-chain
level: 2★
description: Chains agent outputs sequentially so each step receives prior output
  as context, enabling multi-stage data transformation pipelines.
links:
  github: https://github.com/ruvnet/ruflo
tags:
- streaming
- pipeline
- sequential
- context-chaining
- data-transformation
createdAt: '2026-05-19'
updatedAt: '2026-08-30'
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
  commits: 6899
  contributors: 32
  grade: B
timeline:
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
- timestamp: '2026-08-29T17:15:59Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM 36.0 -> 36.0, grade C -> C (gaia dev calibrate-trust-magnitude; Issue
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
trustMagnitudeInputHash: 053cf1e6f25c49b8ccd55c6e5d957040be2ab5d82de8cd11a19dc456b4620a22
---

## Overview

Stream Chain orchestrates agents in a sequential pipeline where each agent's output becomes the next agent's input context. This enables complex multi-stage data transformation workflows where information is progressively refined, enriched, or transformed through a series of specialist agents. Configurable timeouts and both custom and predefined pipeline templates give flexibility across use cases.

## Key Capabilities

- **Sequential context chaining**: each pipeline stage receives the full output of the preceding stage
- **Custom and predefined pipelines**: use built-in templates or define fully custom agent sequences
- **Configurable timeouts**: per-stage and global timeout controls for long-running transformations
- **Swarm and memory integration**: pipelines can fan out to swarms or persist state to Ruflo memory

## Origin

First published by @ruvnet as part of the Ruflo orchestration platform. This is the origin implementation for the `sequential-agent-pipeline` skill bucket.

Sourced from the Ruflo platform (ruvnet/ruflo, 34k+ stars).

## Installation

This skill is part of the Ruflo orchestration platform.

```bash
npx ruflo@latest init
```

See the [Ruflo (ruvnet/ruflo)](../ruvnet/ruflo.md) capstone for full multi-topology installation options.
