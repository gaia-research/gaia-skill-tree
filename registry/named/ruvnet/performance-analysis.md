---
id: ruvnet/performance-analysis
name: Performance Analysis
contributor: ruvnet
origin: false
genericSkillRef: performance-tuning
status: named
title: The Bottleneck Hunter
catalogRef: ruvnet-performance-analysis
level: 2★
description: Profiles agent and system execution for CPU, memory, and I/O hotspots
  and produces actionable optimization recommendations.
links:
  github: https://github.com/ruvnet/ruflo/blob/main/.agents/skills/performance-analysis/SKILL.md
tags:
- performance
- profiling
- bottleneck
- optimization
- benchmarking
createdAt: '2026-05-19'
updatedAt: '2026-06-02'
suiteRef: ruvnet/ruflo
timeline:
- timestamp: '2026-06-02T01:43:00Z'
  action: demote
  contributor: unknown
  details: Origin status removed. Transferred to addy-osmani/performance-optimization.
---

## Overview

Performance Analysis provides systematic profiling of Ruflo agents and system components to identify bottlenecks and guide optimization efforts. It instruments CPU, memory, and I/O subsystems to produce ranked hotspot reports, pairs measurements with concrete optimization recommendations, and supports both micro-benchmark experiments and full end-to-end workflow profiling.

## Key Capabilities

- **CPU/memory/I/O profiling**: instrumented measurement across all major resource dimensions
- **Hotspot ranking**: identifies and ranks the top bottlenecks by impact on overall performance
- **Optimization recommendations**: actionable advice paired with each identified hotspot
- **Micro-benchmarking**: isolated timing experiments for evaluating optimization hypotheses
- **End-to-end workflow profiling**: full-stack performance measurement across complete agent runs

## Origin

First published by @ruvnet as part of the Ruflo orchestration platform. This is the origin implementation for the `performance-tuning` skill bucket.

Sourced from the Ruflo platform (ruvnet/ruflo, 34k+ stars).
