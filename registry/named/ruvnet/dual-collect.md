---
id: ruvnet/dual-collect
name: Dual Collect
contributor: ruvnet
origin: true
genericSkillRef: headless-worker-collect
status: named
title: The Result Harvester
catalogRef: ruvnet-dual-collect
level: 2★
description: Collects and aggregates results from headless Codex workers stored in
  shared memory with filtering and health status reporting.
links:
  github: https://github.com/ruvnet/ruflo
tags:
- dual-mode
- result-collection
- aggregation
- worker-health
- memory-retrieval
createdAt: '2026-05-19'
updatedAt: '2026-06-14'
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
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T11:07:58Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:38Z'
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

Dual Collect is the harvest phase of the Claude+Codex dual-mode orchestration pattern. After headless Codex workers complete their tasks, Dual Collect queries the shared memory namespace to retrieve, filter, and aggregate their outputs. It reports on worker completion status and health, and surfaces results in summary, detailed, or raw JSON format for downstream consumption by the Claude session.

## Key Capabilities

- **Namespace-based result querying**: retrieves all worker outputs from the designated shared memory namespace with optional key filtering
- **Multi-format output**: supports summary, detailed, and raw JSON output modes for different consumption contexts
- **Worker health reporting**: provides completion status, error counts, and overall health score for each spawned worker
- **Completion tracking**: distinguishes between completed, running, and failed workers to guide collection timing decisions

## Origin

First published by @ruvnet as part of the Ruflo orchestration platform. This is the origin implementation for the `headless-worker-collect` skill bucket.

Sourced from the Ruflo platform (ruvnet/ruflo, 34k+ stars).
