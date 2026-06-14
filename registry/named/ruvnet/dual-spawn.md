---
id: ruvnet/dual-spawn
name: Dual Spawn
contributor: ruvnet
origin: true
genericSkillRef: headless-worker-spawn
status: named
title: The Headless Launcher
catalogRef: ruvnet-dual-spawn
level: 2★
description: Spawns headless Codex workers from Claude Code for parallel background
  execution with configurable worker types and shared memory.
links:
  github: https://github.com/ruvnet/ruflo
tags:
- dual-mode
- headless
- codex
- parallel-execution
- background-workers
createdAt: '2026-05-19'
updatedAt: '2026-06-14'
suiteRef: ruvnet/dual-mode
evidence:
- class: B
  source: https://github.com/ruvnet/ruflo
  evaluator: mbtiongson1
  date: '2026-05-19'
  notes: Ruflo orchestration platform — 34k+ GitHub stars. (backfilled — class-to-type
    migration)
  type: repo
  trustNumber: 70.0
  grade: B
timeline:
- timestamp: '2026-06-14T12:32:54Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/ruvnet/ruflo as B (trustNumber:
    70.0)'
---

## Overview

Dual Spawn is the launch phase of the Claude+Codex dual-mode orchestration pattern. It enables Claude Code to spin up headless Codex workers in the background without blocking interactive reasoning. Workers are configured with type, count, and shared memory namespace before being dispatched, allowing a Claude session to delegate parallelizable subtasks to multiple Codex instances simultaneously.

## Key Capabilities

- **Headless Codex worker launch**: spawns one or more Codex worker processes detached from the interactive Claude session
- **Configurable types/counts**: supports multiple worker types (research, implementation, review, test) with variable concurrency
- **Shared memory coordination**: establishes a named memory namespace accessible to both Claude and all spawned Codex workers
- **Parallel background execution**: enables simultaneous multi-task processing without blocking Claude's interactive reasoning loop

## Origin

First published by @ruvnet as part of the Ruflo orchestration platform. This is the origin implementation for the `headless-worker-spawn` skill bucket.

Sourced from the Ruflo platform (ruvnet/ruflo, 34k+ stars).
