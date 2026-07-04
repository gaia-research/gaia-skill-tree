---
id: huggingface/semantic-cache
name: Semantic Cache
contributor: huggingface
origin: false
genericSkillRef: semantic-cache
status: named
title: The Neural Memory
catalogRef: huggingface-semantic-cache
level: 2★
description: High-performance semantic caching for LLM responses using embedding similarity.
tags:
- semantic-cache
- embeddings
- vector-search
- cost-optimization
- unique
createdAt: '2026-05-15'
updatedAt: '2026-07-05'
evidence:
- class: B
  source: https://github.com/codefuse-ai/ModelCache
  evaluator: mbtiongson1
  date: '2026-04-30'
  notes: 'ModelCache -- LLM semantic caching system reducing response time via cached
    query-result pairs; reproducible, MIT license. (backfilled — class-to-type migration)
    (CLI gap: commits+contributors not writable via gaia dev evidence)'
  type: repo
  commits: 192
  contributors: 10
  trustNumber: 70.0
  grade: B
- source: https://huggingface.co/spaces/HuggingFaceH4/open_llm_leaderboard
  evaluator: unknown
  date: '2026-07-05'
  type: benchmark-result
  benchmarkId: mmlu@2024-03
  score: 63.9
  unit: pct
  runAt: '2024-03-01T00:00:00Z'
  provenance: mirrored
  attestor: https://huggingface.co/spaces/HuggingFaceH4/open_llm_leaderboard
  datasetHash: ab313191b8c989dea045d52eeb8896a4646eb66140b0f7723b8f0ebebea43eb5
  benchmarkInputHash: 641e81ab9f021cec48470ee367820d5d8da81b22c92bbe31b0cf1e6d214066ac
timeline:
- timestamp: '2026-06-02T23:48:18Z'
  action: demote
  contributor: unknown
  details: Calibrated level from 4★ to 1★
- timestamp: '2026-06-04T20:30:47Z'
  action: note
  contributor: unknown
  details: Updated GitHub link to https://github.com/codefuse-ai/ModelCache/blob/main/README.md
- timestamp: '2026-06-04T20:30:53Z'
  action: rank_up
  contributor: unknown
  details: Calibrated level from 1★ to 4★
- timestamp: '2026-06-04T20:34:01Z'
  action: note
  contributor: unknown
  details: Set installable to false
- timestamp: '2026-06-04T20:34:03Z'
  action: demote
  contributor: unknown
  details: Calibrated level from 4★ to 1★
- timestamp: '2026-06-14T12:32:40Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/codefuse-ai/ModelCache as B
    (trustNumber: 70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:17Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T10:36:26Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:38Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:40Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- timestamp: '2026-06-20T06:31:28Z'
  action: rank_up
  contributor: mbtiongson1
  details: Level updated from 1★ to 2★ per G7 final rankings calibration.
- timestamp: '2026-07-04T22:35:20Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://huggingface.co/spaces/HuggingFaceH4/open_llm_leaderboard
    (type: benchmark-result)'
installable: false
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
trustMagnitudeInputHash: 218c09e58c2261c5210efad6f857a14f94bb2f35051476ca0207c34654dd5904
verification:
  firstEvidenceAt: '2026-07-04T22:35:20Z'
---

## Overview

Semantic Cache stores and retrieves responses based on meaning rather than literal string matches, enabling high hit rates and low latency for agent workflows.
