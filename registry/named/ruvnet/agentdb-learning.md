---
id: ruvnet/agentdb-learning
name: AgentDB Learning
contributor: ruvnet
origin: true
genericSkillRef: agent-memory-learning
status: named
title: The Pattern Seeker
catalogRef: ruvnet-agentdb-learning
level: 1★
description: Builds self-improving agent memory by analyzing task success patterns
  and adapting retrieval strategies with AgentDB-backed vector persistence.
links:
  github: https://github.com/ruvnet/ruflo
tags:
- self-learning
- vector-memory
- pattern-recognition
- adaptation
createdAt: '2026-05-19'
updatedAt: '2026-06-02'
suiteRef: ruvnet/agentdb
timeline:
- timestamp: '2026-06-02T23:48:20Z'
  action: demote
  contributor: unknown
  details: Calibrated level from 3★ to 1★
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
---

## Overview

AgentDB Learning enables AI agents to develop self-improving memory through experience recording, pattern recognition, and strategy adaptation. Each task outcome is logged with metrics and contextual details. The system identifies recurring scenarios and ranks optimal responses. Knowledge from one domain can be transferred to related domains through vector similarity.

## Key Capabilities

- **Experience recording**: task outcomes logged with metrics and full contextual detail
- **Pattern matching**: identification of recurring scenarios and optimal response strategies
- **Strategy ranking**: historical performance-based prioritization of response approaches
- **Knowledge transfer**: cross-domain learning via vector similarity to related contexts

## Origin

First published by @ruvnet as part of the Ruflo orchestration platform. This is the origin implementation for the `agent-memory-learning` skill bucket.

Sourced from the Ruflo platform (ruvnet/ruflo, 34k+ stars).
