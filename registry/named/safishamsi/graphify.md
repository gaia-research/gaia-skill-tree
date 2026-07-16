---
id: safishamsi/graphify
name: Graphify
contributor: safishamsi
origin: true
genericSkillRef: knowledge-graph-build
status: named
title: The Structural Muse
level: 3★
description: Maps codebases and documentation into a queryable knowledge graph using
  AST analysis and semantic extraction.
links:
  github: https://github.com/safishamsi/graphify
tags:
- knowledge-graph
- rag
- ast
createdAt: '2026-05-14'
updatedAt: '2026-07-16'
timeline:
- timestamp: '2026-06-02T23:48:24Z'
  action: demote
  contributor: unknown
  details: Calibrated level from 3★ to 1★
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:21Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- timestamp: '2026-06-19T09:19:58Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/safishamsi/graphify (type: github-stars-own)'
- timestamp: '2026-06-19T09:22:28Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://arxiv.org/abs/2408.03910 (type: arxiv)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T09:29:08Z'
  details: TM 0.0 -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T09:34:47Z'
  details: TM 0.0 -> 86.57, grade ungraded -> B (direct edit -- CLI gap)
- timestamp: '2026-06-19T10:41:29Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://www.youtube.com/watch?v=q6t8xTjV5rM (type:
    social-signal)'
- timestamp: '2026-06-19T10:47:07Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/safishamsi/graphify (type: peer-review)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T10:52:25Z'
  details: TM 86.57 -> 116.57, grade B -> A (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:39Z'
  details: TM 0.0 -> 116.57, grade ungraded -> A (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:45Z'
  details: TM 0.0 -> 116.57, grade ungraded -> A (direct edit -- CLI gap)
- timestamp: '2026-06-20T06:31:38Z'
  action: rank_up
  contributor: mbtiongson1
  details: Level updated from 1★ to 4★ per G7 final rankings calibration.
- timestamp: '2026-07-16T08:36:44Z'
  action: type_change
  contributor: mbtiongson1
  details: 'Generic parent ''knowledge-graph-build'' type: extra/ultimate → fusion
    (Yggdrasil II taxonomy migration #997)'
  metaEpoch: yggdrasil-ii
  migrationBatch: yggdrasil-ii@2026-07-16
- timestamp: '2026-07-16T08:36:44Z'
  action: demote
  contributor: mbtiongson1
  previousValue: 4★
  newValue: 3★
  details: 'Yggdrasil II recalibration: 4★ unique-branch gate failed (unique-branch
    origin=False TM=122.9 (≥ 100.0)) — demoted to 3★ Evolved'
  metaEpoch: yggdrasil-ii
  migrationBatch: yggdrasil-ii@2026-07-16
trustMagnitude: 116.57
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
evidence:
- source: https://github.com/safishamsi/graphify/stargazers
  evaluator: mbtiongson1
  updatedAt: '2026-07-01'
  date: '2026-06-19'
  type: github-stars-own
  class: A
  notes: 68,766 GitHub stars as of 2026-06-19 (verified via firecrawl validation report;
    standalone skill)
  stars: 75052
  grade: A
- source: https://arxiv.org/abs/2408.03910
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: arxiv
  class: A
  notes: GraphRAG / knowledge graph paper — ~89 citations as of 2026-06-19 (arXiv:2408.03910)
  citations: 89
  grade: C
- source: https://www.youtube.com/watch?v=q6t8xTjV5rM
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: social-signal
  class: A
  notes: 'Charlie Automates YouTube: creator interview with Safi Shamsi explaining
    Graphify architecture and 70x token savings claim. Validated third-party creator.'
- source: https://github.com/safishamsi/graphify
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: peer-review
  class: A
  notes: 'Consolidated GitHub community reviews (Issues + r/LocalLLaMA): token efficiency
    praised, Leiden clustering limits on non-modular codebases documented. Mid-2026.'
  grade: C
verification:
  firstEvidenceAt: '2026-06-19T09:19:58Z'
trustMagnitudeInputHash: ae90ab68d4801463666f7bd7e7c88a76e5d8f530513b89a05c4073ebbafdd701
---

## Overview

Graphify is a memory layer for AI agents that transforms unstructured project data into a structured knowledge graph. By combining tree-sitter for code structural analysis with LLMs for semantic extraction, it enables assistants to perform deep architectural queries and maintain long-term context across large repositories.
