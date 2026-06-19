---
id: yonatangross/orchestkit-rag
name: OrchestrKit RAG
contributor: yonatangross
origin: true
genericSkillRef: rag-pipeline
status: named
title: The Knowledge Architect
catalogRef: yonatangross-orchestkit-rag
level: 1★
description: Production-grade RAG retrieval skill covering 30+ patterns including
  core pipeline composition, HyDE query expansion, pgvector hybrid search, cross-encoder
  reranking, multimodal chunking, and agentic self-RAG and corrective-RAG loops.
links:
  github: https://github.com/yonatangross/orchestkit
tags:
- rag
- retrieval
- hybrid-search
- hyde
- pgvector
- reranking
- agentic-rag
createdAt: '2026-04-30'
updatedAt: '2026-06-02'
timeline:
- timestamp: '2026-06-02T23:48:24Z'
  action: demote
  contributor: unknown
  details: Calibrated level from 3★ to 1★
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:21Z'
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

OrchestrKit RAG is a comprehensive RAG retrieval skill drawn from the OrchestrKit AI development toolkit. It ships with 30+ rule files spanning every stage of the retrieval pipeline: embedding model selection, chunking strategies, pgvector schema design, hybrid BM25+dense search, HyDE query expansion, cross-encoder and LLM-based reranking, multimodal embeddings, and agentic patterns like self-RAG, corrective-RAG, and adaptive retrieval.

## Key Patterns

- **Core**: basic RAG, context management, hybrid search, pipeline composition
- **HyDE**: per-concept generation, fallback chains, HyDE+query combo
- **pgvector**: schema, indexing, hybrid search, metadata filtering
- **Reranking**: cross-encoder, LLM judge, combined ensemble
- **Agentic**: self-RAG, corrective-RAG, adaptive retrieval, knowledge graph
- **Multimodal**: chunking, embeddings, multimodal pipeline

## Origin

First published by @yonatangross as part of the OrchestrKit Claude Code toolkit (103 skills). This is the origin implementation for the `rag-pipeline` skill bucket.

Sourced from the SkillsMP marketplace entry for `rag-retrieval` (orchestkit, 160 stars).
