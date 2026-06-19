---
id: ruvnet/agentic-jujutsu
name: Agentic Jujutsu
contributor: ruvnet
origin: true
genericSkillRef: git-diff-risk-analysis
status: named
title: The Risk Whisperer
catalogRef: ruvnet-agentic-jujutsu
level: 2★
description: Analyzes git diffs for complexity, churn, and risk scores to prioritize
  review attention and flag dangerous changes.
links:
  github: https://github.com/ruvnet/ruflo
tags:
- git
- diff-analysis
- risk-scoring
- code-review
- churn
createdAt: '2026-05-19'
updatedAt: '2026-06-14'
suiteRef: ruvnet/ruflo
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
  commits: 6899
  contributors: 32
timeline:
- timestamp: '2026-06-14T12:32:52Z'
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
---

## Overview

Agentic Jujutsu applies judo-style leverage to code review: instead of reviewing everything equally, it identifies the highest-risk changes and focuses attention there. By scoring diffs for complexity, historical churn, and structural risk, it helps reviewers spend effort where it matters most and surfaces dangerous changes that might otherwise slip through.

## Key Capabilities

- **Diff complexity scoring**: quantifies cyclomatic and structural complexity introduced by each change
- **Churn analysis**: tracks file-level change frequency to identify historically volatile areas
- **Historical risk correlation**: matches current changes against past bug-introducing patterns
- **Per-file risk breakdown**: produces file-by-file risk reports with prioritized review queues
- **Review prioritization**: ranks changes so reviewers tackle the riskiest items first

## Origin

First published by @ruvnet as part of the Ruflo orchestration platform. This is the origin implementation for the `git-diff-risk-analysis` skill bucket.

Sourced from the Ruflo platform (ruvnet/ruflo, 34k+ stars).

## Installation

This skill is part of the Ruflo orchestration platform.

```bash
npx ruflo@latest init
```

See the [Ruflo (ruvnet/ruflo)](../ruvnet/ruflo.md) capstone for full multi-topology installation options.
