---
id: ruvnet/reasoningbank
name: ReasoningBank
contributor: ruvnet
origin: true
genericSkillRef: reasoning-pattern-bank
status: named
title: The Pattern Sage
catalogRef: ruvnet-reasoningbank
level: 3★
description: Fuses adaptive pattern learning with persistent vector memory to build
  a self-improving agent knowledge base across sessions.
links:
  github: https://github.com/ruvnet/ruflo
tags:
- reasoningbank
- pattern-learning
- memory-integration
- self-improvement
createdAt: '2026-05-19'
updatedAt: '2026-07-16'
suiteRef: ruvnet/ruflo
suiteComponents:
- ruvnet/reasoningbank-agentdb
- ruvnet/reasoningbank-intelligence
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
- source: https://github.com/ruvnet/ruflo/issues/2410
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: peer-review
  class: A
  notes: Dream cycle research issue documenting ReasoningBank performance gaps vs
    OPD-Evolver (11.5% improvement) and proposing bi-temporal indexing improvements
    via ADR-161.
  grade: C
- source: https://github.com/ruvnet/ruflo/issues/928
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: peer-review
  class: A
  notes: Direct user feedback on reasoningbank-intelligence skill implementation and
    usage.
  grade: C
- source: https://github.com/ruvnet/ruflo/issues/914
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: peer-review
  class: A
  notes: Production issue with ReasoningBank backend initialization and database migrations.
- source: https://github.com/ruvnet/ruflo/issues/812
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: peer-review
  class: A
  notes: Bug showing MCP memory tools bypass ReasoningBank semantic search capabilities
    despite initialization.
- source: https://github.com/ruvnet/ruflo/issues/801
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: peer-review
  class: A
  notes: User praise for ReasoningBank semantic search performance in v2.7.0-alpha.10
    release.
timeline:
- timestamp: '2026-06-14T12:32:58Z'
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
- timestamp: '2026-06-19T12:49:58Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/ruvnet/ruflo/issues/2410 (type:
    peer-review)'
- timestamp: '2026-06-19T12:50:15Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/ruvnet/ruflo/issues/928 (type:
    peer-review)'
- timestamp: '2026-06-19T12:50:32Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/ruvnet/ruflo/issues/914 (type:
    peer-review)'
- timestamp: '2026-06-19T12:50:49Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/ruvnet/ruflo/issues/812 (type:
    peer-review)'
- timestamp: '2026-06-19T12:51:07Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/ruvnet/ruflo/issues/801 (type:
    peer-review)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T12:53:51Z'
  details: TM 36.0 -> 88.5, grade C -> B (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:39Z'
  details: TM 0.0 -> 88.5, grade ungraded -> B (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:44Z'
  details: TM 0.0 -> 118.5, grade ungraded -> A (direct edit -- CLI gap)
- timestamp: '2026-06-20T06:31:36Z'
  action: rank_up
  contributor: mbtiongson1
  details: Level updated from 3★ to 4★ per G7 final rankings calibration.
- timestamp: '2026-07-08T19:57:22Z'
  action: upstream_synced
  contributor: github-actions[bot]
  previousValue: null
  newValue: v3.25.5
  details: first-run baseline
- timestamp: '2026-07-16T08:36:44Z'
  action: type_change
  contributor: mbtiongson1
  details: 'Generic parent ''reasoning-pattern-bank'' type: extra/ultimate → fusion
    (Yggdrasil II taxonomy migration #997)'
  metaEpoch: yggdrasil-ii
  migrationBatch: yggdrasil-ii@2026-07-16
- timestamp: '2026-07-16T08:36:44Z'
  action: demote
  contributor: mbtiongson1
  previousValue: 4★
  newValue: 3★
  details: 'Yggdrasil II recalibration: 4★ suite-branch gate failed (suite-branch
    TM=88.5 (< 100.0)) — demoted to 3★ Evolved'
  metaEpoch: yggdrasil-ii
  migrationBatch: yggdrasil-ii@2026-07-16
trustMagnitude: 118.5
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
verification:
  firstEvidenceAt: '2026-06-19T12:49:58Z'
trustMagnitudeInputHash: 14db5a1d7daf78680d3d2f58499fde5caa3ce712339f9dd377d1e383263f6f27
upstream:
  mode: components
  releasedAt: '2026-07-08T17:27:46Z'
  repo: ruvnet/ruflo
  sourceUrl: https://github.com/ruvnet/ruflo/releases/tag/v3.25.5
  syncedAt: '2026-07-08T19:57:22Z'
  version: v3.25.5
---

## Overview

ReasoningBank is a 3★ fusion of the two ReasoningBank discipline skills: `reasoningbank-intelligence` (adaptive pattern recognition and reasoning strategy selection) and `reasoningbank-agentdb` (AgentDB-backed persistent vector memory for cross-session knowledge retention). Together they form a self-improving agent knowledge base that learns from every interaction, stores reasoning patterns in durable vector storage, and retrieves relevant patterns to accelerate future problem solving.

## Key Capabilities

- **Adaptive pattern learning**: recognizes and abstracts successful reasoning strategies from completed tasks for future reuse
- **Persistent vector memory**: stores learned patterns in AgentDB with semantic indexing for high-recall retrieval
- **Self-improving knowledge base**: continuously refines pattern quality scores based on downstream task outcomes
- **Cross-session reasoning continuity**: resumes prior reasoning context across session boundaries via durable memory

## Origin

First published by @ruvnet as part of the Ruflo orchestration platform. This is the origin implementation for the `reasoning-pattern-bank` skill bucket.

This 3★ fusion unites reasoningbank-intelligence + reasoningbank-agentdb.

Sourced from the Ruflo platform (ruvnet/ruflo, 34k+ stars).

## Installation

This skill is part of the Ruflo orchestration platform.

```bash
npx ruflo@latest init
```

See the [Ruflo (ruvnet/ruflo)](../ruvnet/ruflo.md) capstone for full multi-topology installation options.
