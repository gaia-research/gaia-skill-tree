---
id: ruvnet/v3-memory-unification
name: V3 Memory Unification
contributor: ruvnet
origin: false
role: variant
genericSkillRef: memory-manage
status: named
title: The Memory Consolidator
catalogRef: ruvnet-v3-memory-unification
level: 2★
description: Unifies disparate Ruflo v3 memory subsystems (AgentDB, RVF, RAG memory)
  into a single coherent memory management layer.
links:
  github: https://github.com/ruvnet/ruflo
tags:
- memory-unification
- agentdb
- rvf
- rag-memory
- v3-sprint
createdAt: '2026-05-19'
updatedAt: '2026-05-19'
suiteRef: ruvnet/ruflo-v3
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
trustMagnitudeInputHash: 150734ff43ea2c6ee818aa81987c34fbd2cc5dee97092a166c72a73fecd11ec7
timeline:
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:21Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
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
