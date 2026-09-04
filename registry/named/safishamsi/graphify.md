---
id: safishamsi/graphify
name: Graphify
contributor: safishamsi
origin: true
genericSkillRef: knowledge-graph-build
status: named
title: The Structural Muse
level: 5★
description: Maps codebases and documentation into a queryable knowledge graph using
  AST analysis and semantic extraction.
links:
  github: https://github.com/safishamsi/graphify/blob/v8/graphify/__init__.py
tags:
- knowledge-graph
- rag
- ast
createdAt: '2026-05-14'
updatedAt: '2026-09-04'
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
- timestamp: '2026-07-19T02:04:09Z'
  action: note
  contributor: unknown
  details: Updated GitHub link to https://github.com/safishamsi/graphify/blob/v8/graphify/__init__.py
- timestamp: '2026-07-19T02:04:29Z'
  action: rank_up
  contributor: unknown
  details: Calibrated level from 3★ to 4★
- timestamp: '2026-07-20T18:16:45Z'
  action: type_change
  contributor: mbtiongson1
  details: 'Generic parent ''knowledge-graph-build'' type: extra/ultimate → fusion
    (Yggdrasil II taxonomy migration #997)'
  metaEpoch: yggdrasil-ii
  migrationBatch: yggdrasil-ii@2026-07-20
- timestamp: '2026-08-29T17:16:00Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM 116.57 -> 297.8, grade A -> S (gaia dev calibrate-trust-magnitude;
    Issue #1600)'
- timestamp: '2026-09-02T15:11:45Z'
  action: rank_up
  contributor: unknown
  details: Calibrated level from 4★ to 5★
- timestamp: '2026-09-04T18:30:00Z'
  action: evidence_added
  contributor: mbtiongson1
  details: Added verified arXiv:2607.15516 (S) and Glassgraph peer-review (A) rows
- timestamp: '2026-09-04T18:30:00Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM 171.88 -> 316.88, grade A -> S (verified independent witness)'
trustMagnitude: 316.88
overallTrustGrade: S
trustMagnitudeInputHash: b72a46e9e972127c0c1631ced3201d21eb21506aab250283d81a0aa267e02908
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
- source: https://arxiv.org/abs/2607.15516
  evaluator: mbtiongson1
  date: '2026-09-04'
  type: arxiv
  citations: 500
  grade: S
  notes: Cache-Aware Prompt Compression research paper featuring dedicated case study
    on graphify (Section 6.4, capc_graphify_profiler.py).
- source: https://github.com/tinix84/glassgraph/blob/main/docs/07-graphify-comparison.md
  evaluator: mbtiongson1
  date: '2026-09-04'
  type: peer-review
  reviewers: 2
  grade: A
  notes: Independent technical comparison framework comparing glassgraph against
    safishamsi/graphify across 5 axes on 25-file multi-domain corpus.
- source: https://github.com/safishamsi/graphify/stargazers
  evaluator: mbtiongson1
  updatedAt: '2026-09-01'
  date: '2026-06-19'
  type: github-stars-own
  class: A
  notes: 68,766 GitHub stars as of 2026-06-19 (verified via firecrawl validation report;
    standalone skill)
  stars: 113188
  grade: A
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
trustMagnitudeInputHash: b72a46e9e972127c0c1631ced3201d21eb21506aab250283d81a0aa267e02908
---

## Overview

Graphify is a memory layer for AI agents that transforms unstructured project data into a structured knowledge graph. By combining tree-sitter for code structural analysis with LLMs for semantic extraction, it enables assistants to perform deep architectural queries and maintain long-term context across large repositories.
