---
id: ruvnet/agentdb-vector-search
name: AgentDB Vector Search
contributor: ruvnet
origin: true
genericSkillRef: vector-search
status: named
title: "The Similarity Engine"
catalogRef: ruvnet-agentdb-vector-search
level: "2★"
description: Performs semantic similarity search over high-dimensional embeddings using cosine, Euclidean, dot-product, or custom distance metrics with HNSW indexing.
links:
  github: https://github.com/ruvnet/ruflo
tags:
  - vector-search
  - cosine-similarity
  - hnsw
  - semantic-search
  - embeddings
createdAt: "2026-05-19"
updatedAt: "2026-05-19"
suiteRef: "ruvnet/agentdb"
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
