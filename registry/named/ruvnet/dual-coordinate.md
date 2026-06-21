---
id: ruvnet/dual-coordinate
name: Dual Coordinate
contributor: ruvnet
origin: true
genericSkillRef: hybrid-workflow-coordination
status: named
title: The Hybrid Orchestrator
catalogRef: ruvnet-dual-coordinate
level: 2★
description: Coordinates hybrid Claude+Codex workflows by routing tasks between interactive
  reasoning phases and parallel background execution.
links:
  github: https://github.com/ruvnet/ruflo
tags:
- dual-mode
- hybrid-workflow
- orchestration
- task-routing
- parallel-execution
createdAt: '2026-05-19'
updatedAt: '2026-06-21'
suiteRef: ruvnet/dual-mode
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
- timestamp: '2026-06-14T12:32:53Z'
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
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:38Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:43Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
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
trustMagnitudeInputHash: e9047334727842d45ba6c3d14056f70bb85ff8ff715bb49d053188b1f75025d1
---

## Overview

Dual Coordinate is the orchestration layer of the Claude+Codex hybrid pattern. It analyzes incoming tasks, decides which components require Claude's interactive reasoning and which can be parallelized across Codex workers, and manages the handoff between the two execution planes. Three built-in workflow templates — hybrid_development, parallel_feature, and design_and_execute — cover the most common mixed-execution patterns.

## Key Capabilities

- **Platform task routing**: classifies tasks by complexity and parallelizability to assign them to Claude or Codex execution appropriately
- **3 workflow templates**: `hybrid_development`, `parallel_feature`, and `design_and_execute` patterns cover standard mixed-execution scenarios
- **Parallel worker management**: oversees the full lifecycle of Codex worker pools spawned during coordinated workflow execution
- **Hybrid handoff coordination**: synchronizes the transition between Claude interactive phases and Codex parallel phases to ensure coherent outputs

## Origin

First published by @ruvnet as part of the Ruflo orchestration platform. This is the origin implementation for the `hybrid-workflow-coordination` skill bucket.

Sourced from the Ruflo platform (ruvnet/ruflo, 34k+ stars).
