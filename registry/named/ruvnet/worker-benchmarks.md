---
id: ruvnet/worker-benchmarks
name: Worker Benchmarks
contributor: ruvnet
origin: false
genericSkillRef: skill-performance-benchmarking
status: named
title: The Performance Judge
catalogRef: ruvnet-worker-benchmarks
level: 2★
description: Benchmarks Ruflo background worker performance across latency, throughput,
  memory usage, and quality score dimensions.
links:
  github: https://github.com/ruvnet/ruflo
tags:
- benchmarking
- workers
- performance
- throughput
- quality-scoring
createdAt: '2026-05-19'
updatedAt: '2026-05-19'
suiteRef: ruvnet/ruflo
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
timeline:
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:21Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:39Z'
  details: TM 0.0 -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:45Z'
  details: TM 0.0 -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
trustMagnitudeInputHash: 993a4ba9e6056da8f292f060901ded87add3f1d23b1c84b090abc3ddbaddb7f3
---

## Overview

Worker Benchmarks provides a multi-dimensional performance evaluation framework for Ruflo background workers. It measures latency, throughput, memory usage, and quality scores simultaneously, checks results against defined compliance thresholds, tracks results over time to detect regressions, and produces comparative reports across worker configurations.

## Key Capabilities

- **Multi-dimensional benchmarking**: simultaneous measurement of latency, throughput, memory, and quality
- **Compliance threshold checking**: validates that workers meet defined performance SLAs
- **Historical regression tracking**: compares benchmark results across runs to surface regressions
- **Worker comparison reports**: side-by-side performance comparison across worker implementations

## Origin

Published by @ruvnet as a variant implementation for the `skill-performance-benchmarking` skill bucket.

Sourced from the Ruflo platform (ruvnet/ruflo, 34k+ stars).
