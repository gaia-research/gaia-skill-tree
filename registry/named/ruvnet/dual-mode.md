---
id: ruvnet/dual-mode
name: Dual Mode
contributor: ruvnet
origin: true
genericSkillRef: dual-mode
status: named
title: The Hybrid Conductor
catalogRef: ruvnet-dual-mode
level: 3★
description: Fuses headless worker spawning, result collection, and hybrid workflow
  coordination into a complete Claude+Codex parallel orchestration pattern.
links:
  github: https://github.com/ruvnet/ruflo
tags:
- dual-mode
- claude-codex
- hybrid
- parallel-execution
- orchestration
createdAt: '2026-05-19'
updatedAt: '2026-06-14'
suiteRef: ruvnet/ruflo
suiteComponents:
- ruvnet/dual-collect
- ruvnet/dual-coordinate
- ruvnet/dual-spawn
evidence:
- class: B
  source: https://github.com/ruvnet/ruflo
  evaluator: mbtiongson1
  date: '2026-05-19'
  notes: "Ruflo orchestration platform — 34k+ GitHub stars. (backfilled — class-to-type\" migration) (CLI gap: --commits/--contributors not supported by gaia dev evidence)"
  type: repo
  trustNumber: 70.0
  grade: B
  commits: 6899
  contributors: 32
timeline:
- timestamp: '2026-06-14T12:32:53Z'
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
trustMagnitudeInputHash: 3e2a68364b3bf4d478d1dc2b9d87ab56c1dac1cb4e0e77d8cb56c0dfe03bd422
---

## Overview

Dual Mode is a 3★ fusion of the three dual-mode sub-skills: `dual-spawn` (headless Codex worker launch), `dual-coordinate` (hybrid task routing and workflow management), and `dual-collect` (result harvesting and aggregation). Together they form the complete spawn→coordinate→collect pipeline for running Claude+Codex hybrid workflows. Claude handles interactive reasoning and architecture decisions while Codex workers execute parallelizable implementation tasks in the background.

## Key Capabilities

- **Headless worker spawning**: launches configurable Codex worker pools with shared memory namespaces for background task execution
- **Hybrid workflow coordination**: routes tasks between Claude's interactive reasoning and Codex's parallel execution using three built-in workflow templates
- **Result harvesting**: collects, filters, and aggregates Codex worker outputs with health reporting and multi-format output
- **Spawn→coordinate→collect pipeline**: end-to-end orchestration pattern enabling 3-10x throughput gains on parallelizable workloads

## Origin

First published by @ruvnet as part of the Ruflo orchestration platform. This is the origin implementation for the `dual-mode` skill bucket.

This 3★ fusion unites dual-spawn + dual-coordinate + dual-collect, forming the complete spawn→coordinate→collect hybrid orchestration pipeline.

Sourced from the Ruflo platform (ruvnet/ruflo, 34k+ stars).

## Installation

This skill is part of the Ruflo orchestration platform.

```bash
npx ruflo@latest init
```

See the [Ruflo (ruvnet/ruflo)](../ruvnet/ruflo.md) capstone for full multi-topology installation options.
