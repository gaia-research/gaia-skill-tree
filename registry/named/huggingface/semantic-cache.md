---
id: huggingface/semantic-cache
name: Semantic Cache
contributor: huggingface
origin: false
genericSkillRef: semantic-cache
status: named
title: The Neural Memory
catalogRef: huggingface-semantic-cache
level: 1★
description: High-performance semantic caching for LLM responses using embedding similarity.
tags:
- semantic-cache
- embeddings
- vector-search
- cost-optimization
- unique
createdAt: '2026-05-15'
updatedAt: '2026-06-14'
evidence:
- class: B
  source: https://github.com/codefuse-ai/ModelCache
  evaluator: mbtiongson1
  date: '2026-04-30'
  notes: ModelCache -- LLM semantic caching system reducing response time via cached
    query-result pairs; reproducible, MIT license. (backfilled — class-to-type migration)
  type: repo
  trustNumber: 70.0
  grade: B
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
installable: false
---

## Overview

Semantic Cache stores and retrieves responses based on meaning rather than literal string matches, enabling high hit rates and low latency for agent workflows.
