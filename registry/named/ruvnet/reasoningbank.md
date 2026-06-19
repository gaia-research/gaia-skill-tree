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
updatedAt: '2026-06-14'
suiteRef: ruvnet/ruflo
suiteComponents:
- ruvnet/reasoningbank-agentdb
- ruvnet/reasoningbank-intelligence
evidence:
- class: B
  source: https://github.com/ruvnet/ruflo
  evaluator: mbtiongson1
  date: '2026-05-19'
  notes: Ruflo orchestration platform — 34k+ GitHub stars. (backfilled — class-to-type
    migration) (CLI gap: --commits/--contributors not supported by gaia dev evidence)
  type: repo
  trustNumber: 70.0
  grade: B
  commits: 6899
  contributors: 32
timeline:
- timestamp: '2026-06-14T12:32:58Z'
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
trustMagnitudeInputHash: f2f5d7a532ae38efd6f520b2fb610e2ea77d34e28e1f8e3b17d3fafa2a8f30dd
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
