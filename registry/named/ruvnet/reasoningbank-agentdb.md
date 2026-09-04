---
id: ruvnet/reasoningbank-agentdb
name: ReasoningBank AgentDB
contributor: ruvnet
origin: false
genericSkillRef: agent-memory-learning
status: named
title: The Knowledge Crystallizer
catalogRef: ruvnet-reasoningbank-agentdb
level: 1★
description: Persists agent reasoning patterns in AgentDB vector memory and retrieves
  them semantically for continuous self-improvement across sessions.
links:
  github: https://github.com/ruvnet/ruflo
tags:
- reasoning-persistence
- vector-memory
- agentdb
- self-improvement
createdAt: '2026-05-19'
updatedAt: '2026-05-19'
suiteRef: ruvnet/reasoningbank
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
  timestamp: '2026-06-18T11:27:20Z'
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
trustMagnitudeInputHash: 12a3dc0d1d60b194d1984c85fa896d21ac13170ce51dd2441646f681e85e7d42
---

## Overview

ReasoningBank AgentDB bridges the reasoning pattern bank with AgentDB vector storage. It serializes agent decision trajectories into vector-searchable formats, enabling future sessions to retrieve relevant past reasoning patterns via semantic similarity. This creates a persistent institutional memory that improves decision quality over time.

## Key Capabilities

- **Reasoning pattern serialization**: conversion of decision trajectories into vector-searchable representations
- **Vector storage persistence**: AgentDB-backed durable storage for cross-session memory
- **Semantic pattern retrieval**: similarity-based lookup of relevant past reasoning chains
- **Trajectory analysis**: decomposition and indexing of multi-step agent decision paths

## Origin

First published by @ruvnet as part of the Ruflo orchestration platform. This is the origin implementation for the `learned-memory-integration` skill bucket.

Sourced from the Ruflo platform (ruvnet/ruflo, 34k+ stars).
