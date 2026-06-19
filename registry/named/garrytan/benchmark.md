---
id: garrytan/benchmark
name: Benchmark
contributor: garrytan
origin: false
genericSkillRef: evaluate-output
status: named
title: Gstack Benchmark
catalogRef: garrytan-benchmark
level: 4★
description: Web performance benchmarking that captures baseline metrics, compares
  current performance against those baselines, and identifies regressions in load
  times, Core Web Vitals, and bundle sizes across specified pages.
links:
  github: https://github.com/garrytan/gstack/blob/main/benchmark/SKILL.md
tags:
- performance
- benchmarking
- core-web-vitals
- regression
createdAt: '2026-05-18'
updatedAt: '2026-06-14'
suiteRef: garrytan/gstack
evidence:
- class: B
  source: https://github.com/garrytan/gstack/blob/main/benchmark/SKILL.md
  evaluator: mbtiongson1
  date: '2026-06-03'
  notes: 'Public SKILL.md in the garrytan/gstack suite repo (verified live). Web performance
    benchmarking that captures baseline metrics, compares current performance against
    those baselines, and identifies regressions in… (backfilled — class-to-type migration)
    (CLI gap: commits+contributors not writable via gaia dev evidence)'
  type: repo
  commits: 323
  contributors: 9
  trustNumber: 70.0
  grade: B
timeline:
- timestamp: '2026-06-03T05:51:29Z'
  action: evidence_added
  contributor: unknown
  details: Added B evidence from https://github.com/garrytan/gstack/blob/main/benchmark/SKILL.md
- timestamp: '2026-06-14T12:32:18Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/garrytan/gstack/blob/main/benchmark/SKILL.md
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
trustMagnitudeInputHash: cee3021b1e6fda990fe66417d776bd33fa1ca5f0307815884bdf18a280ea6fd7
---

## Overview

Gstack Benchmark measures web application performance end to end. It captures a baseline across target pages on first run, then compares every subsequent run against that baseline — surfacing regressions in Time to First Byte, Largest Contentful Paint, Total Blocking Time, and bundle size before they reach production.
