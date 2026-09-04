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
updatedAt: '2026-08-30'
timeline:
- timestamp: '2026-06-02T23:48:20Z'
  action: demote
  contributor: unknown
  details: Calibrated level from 3★ to 1★
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:20Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:38Z'
  details: TM 0.0 -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:43Z'
  details: TM 0.0 -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- timestamp: '2026-08-29T17:15:57Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM 0.0 -> 0.0, grade ungraded -> ungraded (gaia dev calibrate-trust-magnitude;
    Issue #1600)'
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
trustMagnitudeInputHash: 3f8ef3d445b37170db065d22f12388ed989450d89837e7ace73737f7cd26cbc1
suiteRef: "ruvnet/ruflo"
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
