---
id: ruvnet/pair-programming
name: Pair Programming
contributor: ruvnet
origin: false
genericSkillRef: subagent-driven-development
status: named
title: The Coding Companion
catalogRef: ruvnet-pair-programming
level: 2★
description: Structures collaborative coding sessions between a primary implementation
  agent and a review subagent with continuous feedback loops.
links:
  github: https://github.com/ruvnet/ruflo
tags:
- pair-programming
- subagent
- code-review
- collaborative
- feedback-loops
createdAt: '2026-05-19'
updatedAt: '2026-06-21'
suiteRef: ruvnet/ruflo
evidence:
- class: B
  source: https://github.com/ruvnet/ruflo
  evaluator: mbtiongson1
  date: '2026-06-10'
  notes: Part of the Ruflo orchestration platform (public repo); two-agent implement/review
    pattern documented in the suite. (backfilled — class-to-type migration)
  type: repo
  trustNumber: 70.0
  commits: 6899
  contributors: 32
  grade: B
timeline:
- timestamp: '2026-06-10T05:38:18Z'
  action: evidence_added
  contributor: unknown
  details: Added B evidence from https://github.com/ruvnet/ruflo
- timestamp: '2026-06-14T12:32:57Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/ruvnet/ruflo as B (trustNumber:
    70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:20Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T11:07:58Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:39Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:44Z'
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
  firstEvidenceAt: '2026-06-10T05:38:18Z'
trustMagnitudeInputHash: 808895e2a308ed10e020da3b0ff2c61842f641ecbc94cddcc4785f5b7b06247d
---

## Overview

Pair Programming establishes a structured two-agent coding pattern within Ruflo: a primary agent implements features while a review subagent simultaneously evaluates code quality, correctness, and style. Continuous feedback loops between agents replicate the benefits of human pair programming — catching bugs early, enforcing standards, and improving overall code quality before task completion.

## Key Capabilities

- **Primary + review agent pairing**: dedicated implementation and review roles operating in tandem
- **Continuous feedback loops**: real-time review cycles that catch issues during implementation
- **Shared context memory**: both agents read and write to the same Ruflo memory namespace
- **Real-time review cycles**: the review agent provides incremental feedback as code is written

## Origin

Published by @ruvnet as a variant implementation for the `subagent-driven-development` skill bucket.

Sourced from the Ruflo platform (ruvnet/ruflo, 34k+ stars).

## Installation

This skill is part of the Ruflo orchestration platform.

```bash
npx ruflo@latest init
```

See the [Ruflo (ruvnet/ruflo)](../ruvnet/ruflo.md) capstone for full multi-topology installation options.
