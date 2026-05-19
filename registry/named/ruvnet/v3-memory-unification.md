---
id: ruvnet/v3-memory-unification
name: V3 Memory Unification
contributor: ruvnet
origin: false
role: variant
genericSkillRef: memory-manage
status: named
title: "The Memory Consolidator"
catalogRef: ruvnet-v3-memory-unification
level: "2★"
description: Unifies disparate Ruflo v3 memory subsystems (AgentDB, RVF, RAG memory) into a single coherent memory management layer.
links:
  github: https://github.com/ruvnet/ruflo
tags:
  - memory-unification
  - agentdb
  - rvf
  - rag-memory
  - v3-sprint
createdAt: "2026-05-19"
updatedAt: "2026-05-19"
suiteRef: "ruvnet/ruflo"
---

## Overview

V3 Memory Unification consolidates all Ruflo v3 memory subsystems into a single coherent management layer. It bridges AgentDB (vector memory), RVF (cross-session persistence), and RAG memory (hybrid search) behind a unified interface, enabling agents to read and write across all storage backends transparently.

## Key Capabilities

- **Unified memory interface**: single API abstracting AgentDB, RVF, and RAG memory backends
- **AgentDB/RVF/RAG bridge**: transparent routing of reads and writes to the appropriate backend
- **Cross-session persistence**: durable storage enabling memory retrieval across agent sessions
- **Unified search**: single query surface spanning vector, relational, and hybrid search backends

## Origin

Published by @ruvnet as a variant implementation for the `memory-manage` skill bucket.

Sourced from the Ruflo platform (ruvnet/ruflo, 34k+ stars).
