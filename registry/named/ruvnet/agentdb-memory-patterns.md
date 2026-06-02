---
id: ruvnet/agentdb-memory-patterns
name: AgentDB Memory Patterns
contributor: ruvnet
origin: true
genericSkillRef: memory-pattern-design
status: named
title: The Memory Weaver
catalogRef: ruvnet-agentdb-memory-patterns
level: 2★
description: Designs recurring memory storage patterns for AI agents with LRU caching,
  SQLite persistence, and associative retrieval across multiple memory types.
links:
  github: https://github.com/ruvnet/ruflo
tags:
- memory-patterns
- lru-cache
- sqlite
- associative-retrieval
createdAt: '2026-05-19'
updatedAt: '2026-05-19'
suiteRef: ruvnet/agentdb
evidence:
- class: B
  source: https://github.com/ruvnet/ruflo
  evaluator: mbtiongson1
  date: '2026-05-19'
  notes: Ruflo orchestration platform — 34k+ GitHub stars.
---

## Overview

AgentDB Memory Patterns provides structured approaches to agent memory organization. It covers eight memory types: knowledge, context, task data, results, errors, metrics, consensus records, and system configuration. LRU caching ensures fast access to frequently used patterns. SQLite persistence enables cross-session continuity with WAL mode for concurrent access.

## Key Capabilities

- **8 memory type taxonomy**: knowledge, context, task data, results, errors, metrics, consensus records, and system config
- **LRU caching**: fast retrieval for frequently accessed memory patterns
- **SQLite WAL persistence**: cross-session continuity with concurrent-access write-ahead logging
- **Associative memory building**: structured links between related memory entries for contextual retrieval

## Origin

First published by @ruvnet as part of the Ruflo orchestration platform. This is the origin implementation for the `memory-pattern-design` skill bucket.

Sourced from the Ruflo platform (ruvnet/ruflo, 34k+ stars).
