---
id: ruvnet/dual-mode
name: Dual Mode
contributor: ruvnet
origin: true
genericSkillRef: dual-mode
status: named
title: "The Hybrid Conductor"
catalogRef: ruvnet-dual-mode
level: "3★"
description: Fuses headless worker spawning, result collection, and hybrid workflow coordination into a complete Claude+Codex parallel orchestration pattern.
links:
  github: https://github.com/ruvnet/ruflo
tags:
  - dual-mode
  - claude-codex
  - hybrid
  - parallel-execution
  - orchestration
createdAt: "2026-05-19"
updatedAt: "2026-05-19"
---

## Overview

Dual Mode is a 3★ fusion of the three dual-mode sub-skills: `dual-spawn` (headless Codex worker launch), `dual-coordinate` (hybrid task routing and workflow management), and `dual-collect` (result harvesting and aggregation). Together they form the complete spawn→coordinate→collect pipeline for running Claude+Codex hybrid workflows. Claude handles interactive reasoning and architecture decisions while Codex workers execute parallelizable implementation tasks in the background.

## Key Capabilities

- **Headless worker spawning**: launches configurable Codex worker pools with shared memory namespaces for background task execution
- **Hybrid workflow coordination**: routes tasks between Claude's interactive reasoning and Codex's parallel execution using three built-in workflow templates
- **Result harvesting**: collects, filters, and aggregates Codex worker outputs with health reporting and multi-format output
- **Spawn→coordinate→collect pipeline**: end-to-end orchestration pattern enabling 3-10x throughput gains on parallelizable workloads

## Origin

First published by @ruvnet as part of the Ruflo orchestration platform. This is the origin implementation for the `dual-mode` skill bucket.

This 3★ fusion unites dual-spawn + dual-coordinate + dual-collect, forming the complete spawn→coordinate→collect hybrid orchestration pipeline.

Sourced from the Ruflo platform (ruvnet/ruflo, 34k+ stars).
