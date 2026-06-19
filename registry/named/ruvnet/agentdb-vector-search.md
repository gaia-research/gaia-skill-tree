---
id: ruvnet/agentdb-vector-search
name: AgentDB Vector Search
contributor: ruvnet
origin: true
genericSkillRef: vector-search
status: named
title: The Similarity Engine
catalogRef: ruvnet-agentdb-vector-search
level: 2★
description: Performs semantic similarity search over high-dimensional embeddings
  using cosine, Euclidean, dot-product, or custom distance metrics with HNSW indexing.
links:
  github: https://github.com/ruvnet/ruflo
tags:
- vector-search
- cosine-similarity
- hnsw
- semantic-search
- embeddings
createdAt: '2026-05-19'
updatedAt: '2026-06-14'
suiteRef: ruvnet/agentdb
evidence:
- class: B
  source: https://github.com/ruvnet/ruflo
  evaluator: mbtiongson1
  date: '2026-05-19'
  notes: Ruflo orchestration platform — 34k+ GitHub stars. (backfilled — class-to-type migration)
  type: repo
  trustNumber: 70.0
  grade: B
  commits: 6899
  contributors: 32
timeline:
- timestamp: '2026-06-14T12:32:51Z'
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
trustMagnitudeInputHash: 7828f934567afe6ee667b3966e3ca0c37e2ff77d4079a377a4d03c8863c1865c
---

## Overview

AgentDB Vector Search provides the core similarity search capability for agent memory retrieval. It supports multiple distance metrics: cosine similarity for semantic tasks, Euclidean/L2 for spatial data, dot product for normalized vectors, and fully customizable metric implementations. HNSW indexing enables sub-linear search complexity across millions of vectors.

## Key Capabilities

- **Multi-metric search**: cosine, Euclidean, dot-product, and custom distance metrics
- **HNSW indexing**: hierarchical navigable small-world graph for sub-linear search complexity
- **Sub-linear search complexity**: efficient querying across millions of high-dimensional vectors
- **Semantic query matching**: natural language to embedding-space similarity retrieval

## Origin

First published by @ruvnet as part of the Ruflo orchestration platform. This is the origin implementation for the `vector-search` skill bucket.

Sourced from the Ruflo platform (ruvnet/ruflo, 34k+ stars).
