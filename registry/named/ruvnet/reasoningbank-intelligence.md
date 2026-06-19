---
id: ruvnet/reasoningbank-intelligence
name: ReasoningBank Intelligence
contributor: ruvnet
origin: true
genericSkillRef: adaptive-pattern-learning
status: named
title: The Strategy Optimizer
catalogRef: ruvnet-reasoningbank-intelligence
level: 1★
description: Implements adaptive learning through pattern recognition, strategy optimization,
  and meta-learning that improves agent decision quality from cumulative experience.
links:
  github: https://github.com/ruvnet/ruflo
tags:
- adaptive-learning
- pattern-recognition
- meta-learning
- strategy-optimization
createdAt: '2026-05-19'
updatedAt: '2026-06-14'
suiteRef: ruvnet/reasoningbank
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
  commits: 6899
  contributors: 32
timeline:
- timestamp: '2026-06-02T23:48:22Z'
  action: demote
  contributor: unknown
  details: Calibrated level from 3★ to 1★
- timestamp: '2026-06-14T12:32:57Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/ruvnet/ruflo as B (trustNumber:
    70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:20Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T11:07:58Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
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

ReasoningBank Intelligence enables AI agents to develop genuine self-improvement through a feedback learning loop. Each task outcome is recorded with metrics and success indicators. The system identifies optimal strategies per scenario type, ranks approaches by historical performance, and builds meta-learning insights about effective learning approaches themselves. Knowledge transfers across related domains via vector similarity.

## Key Capabilities

- **Experience recording**: task outcomes logged with metrics and success indicators for analysis
- **Pattern matching**: scenario identification and optimal strategy association
- **Strategy ranking**: historical performance-based prioritization across approach types
- **Meta-learning**: learning about learning — insights about which learning strategies work best
- **Cross-domain knowledge transfer**: domain generalization via vector similarity matching

## Origin

First published by @ruvnet as part of the Ruflo orchestration platform. This is the origin implementation for the `adaptive-pattern-learning` skill bucket.

Sourced from the Ruflo platform (ruvnet/ruflo, 34k+ stars).
