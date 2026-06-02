---
id: ruvnet/stream-chain
name: Stream Chain
contributor: ruvnet
origin: true
genericSkillRef: sequential-agent-pipeline
status: named
title: The Flow Conductor
catalogRef: ruvnet-stream-chain
level: 2★
description: Chains agent outputs sequentially so each step receives prior output
  as context, enabling multi-stage data transformation pipelines.
links:
  github: https://github.com/ruvnet/ruflo
tags:
- streaming
- pipeline
- sequential
- context-chaining
- data-transformation
createdAt: '2026-05-19'
updatedAt: '2026-05-19'
suiteRef: ruvnet/ruflo
evidence:
- class: B
  source: https://github.com/ruvnet/ruflo
  evaluator: mbtiongson1
  date: '2026-05-19'
  notes: Ruflo orchestration platform — 34k+ GitHub stars.
---

## Overview

Stream Chain orchestrates agents in a sequential pipeline where each agent's output becomes the next agent's input context. This enables complex multi-stage data transformation workflows where information is progressively refined, enriched, or transformed through a series of specialist agents. Configurable timeouts and both custom and predefined pipeline templates give flexibility across use cases.

## Key Capabilities

- **Sequential context chaining**: each pipeline stage receives the full output of the preceding stage
- **Custom and predefined pipelines**: use built-in templates or define fully custom agent sequences
- **Configurable timeouts**: per-stage and global timeout controls for long-running transformations
- **Swarm and memory integration**: pipelines can fan out to swarms or persist state to Ruflo memory

## Origin

First published by @ruvnet as part of the Ruflo orchestration platform. This is the origin implementation for the `sequential-agent-pipeline` skill bucket.

Sourced from the Ruflo platform (ruvnet/ruflo, 34k+ stars).
