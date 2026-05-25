---
id: intelligentcode-ai/parallel-execution
name: Parallel Execution
contributor: intelligentcode-ai
origin: false
links:
  github: https://github.com/intelligentcode-ai/skills/blob/main/skills/parallel-execution/SKILL.md
genericSkillRef: parallel-execution
status: named
title: The Concurrency Master
catalogRef: intelligentcode-ai-parallel-execution
level: 2★
description: Manages concurrent work item execution with independence verification,
  queue-based state tracking, and configurable concurrency limits (default 5).
tags:
- parallelism
- concurrency
- task-execution
- queue
updatedAt: '2026-05-25'
---

## Overview

Before launching parallel tasks, verifies that each candidate is truly independent (no shared mutable state, no ordering constraints). Tracks running items in a queue and merges results once all branches complete.

## Key behaviours

- Independence check before fan-out: aborts if tasks share a dependency
- Configurable concurrency ceiling (default 5 simultaneous items)
- Queue-based tracking with per-item status (pending / running / done / failed)
- Fan-in: waits for all branches, merges outputs, surfaces failures individually

## Source

[intelligentcode-ai/skills — parallel-execution/SKILL.md](https://github.com/intelligentcode-ai/skills/blob/main/skills/parallel-execution/SKILL.md)
