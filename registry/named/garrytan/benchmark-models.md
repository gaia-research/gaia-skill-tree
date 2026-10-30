---
id: garrytan/benchmark-models
name: Benchmark Models
contributor: garrytan
origin: false
genericSkillRef: skill-performance-benchmarking
status: named
title: Gstack Benchmark Models — LLM Performance Profiling
catalogRef: garrytan-benchmark-models
level: 2★
description: Runs a standardised prompt suite across multiple model versions, records
  latency and quality scores, and produces a ranked comparison table to guide model
  selection.
links:
  github: https://github.com/garrytan/gstack/blob/main/benchmark-models/SKILL.md
tags:
- skill-performance-benchmarking
- llm
- evaluation
createdAt: '2026-05-18'
updatedAt: '2026-08-30'
suiteRef: garrytan/gstack
evidence:
- class: B
  source: https://github.com/garrytan/gstack/blob/main/benchmark-models/SKILL.md
  evaluator: mbtiongson1
  date: '2026-06-03'
  notes: 'Public SKILL.md in the garrytan/gstack suite repo (verified live). Runs
    a standardised prompt suite across multiple model versions, records latency and
    quality scores, and produces a ranked comparison table to… (backfilled — class-to-type
    migration) (CLI gap: commits+contributors not writable via gaia dev evidence)'
  type: repo
  commits: 323
  contributors: 9
  trustNumber: 70.0
  grade: B
timeline:
- timestamp: '2026-06-03T05:51:29Z'
  action: evidence_added
  contributor: unknown
  details: Added B evidence from https://github.com/garrytan/gstack/blob/main/benchmark-models/SKILL.md
- timestamp: '2026-06-14T12:32:18Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/garrytan/gstack/blob/main/benchmark-models/SKILL.md
    as B (trustNumber: 70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:14Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T10:36:26Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:37Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:36Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- timestamp: '2026-06-20T06:31:20Z'
  action: demote
  contributor: mbtiongson1
  details: Level updated from 3★ to 2★ per G7 final rankings calibration.
- timestamp: '2026-08-29T17:15:45Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM 36.0 -> 36.0, grade C -> C (gaia dev calibrate-trust-magnitude; Issue
    #1600)'
trustMagnitude: 36.0
overallTrustGrade: C
apexGateStatus:
  aGradedOriginsGte5: false
  sourceTenureDaysGte180AorS: false
  directNestedSuiteGte1: false
  depth2OnlyReachableGte1: false
  overallGradeS: false
  apexPromotionPrSigned: false
  crossOrgVerifier: null
  systemWideCap: null
verification:
  firstEvidenceAt: '2026-06-03T05:51:29Z'
trustMagnitudeInputHash: 3aebf88aca279b2a253216213cc74e9ebff390b568f5e724d2d877d353e164b4
---

## Overview

Runs a standardised prompt suite across multiple model versions, records latency and quality scores, and produces a ranked comparison table to guide model selection.
