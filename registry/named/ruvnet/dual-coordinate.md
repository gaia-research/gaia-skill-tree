---
id: ruvnet/dual-coordinate
name: Dual Coordinate
contributor: ruvnet
origin: true
genericSkillRef: hybrid-workflow-coordination
status: named
title: "The Hybrid Orchestrator"
catalogRef: ruvnet-dual-coordinate
level: "2★"
description: Coordinates hybrid Claude+Codex workflows by routing tasks between interactive reasoning phases and parallel background execution.
links:
  github: https://github.com/ruvnet/ruflo
tags:
  - dual-mode
  - hybrid-workflow
  - orchestration
  - task-routing
  - parallel-execution
createdAt: "2026-05-19"
updatedAt: "2026-05-19"
suiteRef: "ruvnet/ruflo"
---

## Overview

Dual Coordinate is the orchestration layer of the Claude+Codex hybrid pattern. It analyzes incoming tasks, decides which components require Claude's interactive reasoning and which can be parallelized across Codex workers, and manages the handoff between the two execution planes. Three built-in workflow templates — hybrid_development, parallel_feature, and design_and_execute — cover the most common mixed-execution patterns.

## Key Capabilities

- **Platform task routing**: classifies tasks by complexity and parallelizability to assign them to Claude or Codex execution appropriately
- **3 workflow templates**: `hybrid_development`, `parallel_feature`, and `design_and_execute` patterns cover standard mixed-execution scenarios
- **Parallel worker management**: oversees the full lifecycle of Codex worker pools spawned during coordinated workflow execution
- **Hybrid handoff coordination**: synchronizes the transition between Claude interactive phases and Codex parallel phases to ensure coherent outputs

## Origin

First published by @ruvnet as part of the Ruflo orchestration platform. This is the origin implementation for the `hybrid-workflow-coordination` skill bucket.

Sourced from the Ruflo platform (ruvnet/ruflo, 34k+ stars).
