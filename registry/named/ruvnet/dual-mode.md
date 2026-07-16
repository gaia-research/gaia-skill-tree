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
updatedAt: '2026-07-16'
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
  notes: 'Ruflo orchestration platform — 34k+ GitHub stars. (backfilled — class-to-type"
    migration) (CLI gap: --commits/--contributors not supported by gaia dev evidence)'
  type: repo
  trustNumber: 70.0
  commits: 6899
  contributors: 32
  grade: B
timeline:
- timestamp: '2026-06-14T12:32:53Z'
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
  timestamp: '2026-06-19T13:26:43Z'
  details: TM 0.0 -> 126.0, grade ungraded -> A (direct edit -- CLI gap)
- timestamp: '2026-06-20T06:31:36Z'
  action: rank_up
  contributor: mbtiongson1
  details: Level updated from 3★ to 4★ per G7 final rankings calibration.
- timestamp: '2026-07-08T19:56:47Z'
  action: upstream_synced
  contributor: github-actions[bot]
  previousValue: null
  newValue: v3.25.5
  details: first-run baseline
- timestamp: '2026-07-16T08:36:44Z'
  action: type_change
  contributor: mbtiongson1
  details: 'Generic parent ''dual-mode'' type: extra/ultimate → fusion (Yggdrasil
    II taxonomy migration #997)'
- timestamp: '2026-07-16T08:36:44Z'
  action: demote
  contributor: mbtiongson1
  previousValue: 4★
  newValue: 3★
  details: 'Yggdrasil II recalibration: 4★ suite-branch gate failed (suite-branch
    TM=36.0 (< 100.0)) — demoted to 3★ Evolved'
trustMagnitude: 126.0
overallTrustGrade: A
apexGateStatus:
  aGradedOriginsGte5: false
  sourceTenureDaysGte180AorS: false
  directNestedSuiteGte1: false
  depth2OnlyReachableGte1: false
  overallGradeS: false
  apexPromotionPrSigned: false
  crossOrgVerifier: null
  systemWideCap: null
trustMagnitudeInputHash: fcb3300e49c8ccf214a079a824cb1f57634afb2b7cb3fba6b7045bc19e6c880f
upstream:
  mode: components
  releasedAt: '2026-07-08T17:27:46Z'
  repo: ruvnet/ruflo
  sourceUrl: https://github.com/ruvnet/ruflo/releases/tag/v3.25.5
  syncedAt: '2026-07-08T19:56:47Z'
  version: v3.25.5
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
