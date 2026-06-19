---
id: upsonic/unittest-generator
name: Unittest Generator
contributor: upsonic
origin: true
genericSkillRef: generate-test
status: named
title: The Test Weaver
catalogRef: upsonic-unittest-generator
level: 2★
description: Autonomous Claude agent that generates comprehensive unittest.TestCase
  suites from source code, organising tests into concept-based subfolders under a
  tests/ directory with proper imports, fixtures, and edge-case coverage.
links:
  github: https://github.com/Upsonic/Upsonic
tags:
- unit-testing
- unittest
- test-generation
- python
- autonomous-agent
createdAt: '2026-04-30'
updatedAt: '2026-06-19'
trustMagnitude: 33.0
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
timeline:
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:21Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- timestamp: '2026-06-19T09:23:55Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://arxiv.org/abs/2403.16218 (type: arxiv)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T09:29:08Z'
  details: TM 0.0 -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T09:34:47Z'
  details: TM 0.0 -> 3.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- timestamp: '2026-06-19T10:43:12Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://www.youtube.com/watch?v=fHNTpPpQQBo (type:
    social-signal)'
- timestamp: '2026-06-19T10:48:02Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/Upsonic/Upsonic (type: peer-review)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T10:52:25Z'
  details: TM 3.0 -> 33.0, grade ungraded -> C (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:39Z'
  details: TM 0.0 -> 33.0, grade ungraded -> C (direct edit -- CLI gap)
evidence:
- source: https://arxiv.org/abs/2403.16218
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: arxiv
  class: A
  notes: Automated unit test generation paper — ~15 citations as of 2026-06-19 (arXiv:2403.16218)
  citations: 15
- source: https://www.youtube.com/watch?v=fHNTpPpQQBo
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: social-signal
  class: A
  notes: 'Fahd Mirza YouTube: walkthrough of Upsonic Tiger local install as AI agent
    function hub. Third-party walkthrough.'
- source: https://github.com/Upsonic/Upsonic
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: peer-review
  class: A
  notes: 'SkillsMP Community: TestCase scaffolding works well for isolated classes,
    struggles with highly coupled enterprise framework mocking. April 2026.'
verification:
  firstEvidenceAt: '2026-06-19T09:23:55Z'
trustMagnitudeInputHash: 6b3fef7f19fab551c00e99cbf661282004523fb0e79418487fd1fde173a76079
---

## Overview

Unittest Generator is a Claude Code agent shipped with the Upsonic autonomous agent framework. Given a source module (e.g. `auth.py`), it analyses the code, identifies functions and classes, generates a complete `unittest.TestCase` suite, and writes it into a concept-organised `tests/` folder structure. It handles imports, mocking, and edge-case scenarios automatically.

## Key Capabilities

- **TestCase generation**: produces `unittest.TestCase` classes with `setUp`, `tearDown`, and individual test methods
- **Concept-based layout**: groups tests into subfolders that mirror the conceptual structure of the source
- **Edge-case coverage**: identifies boundary conditions and error paths from the source code
- **Autonomous**: runs without per-file prompting once triggered

## Origin

First published by @Upsonic as a prebuilt Claude Code agent. This is the origin implementation for the `generate-test` skill bucket.

Sourced from the SkillsMP marketplace entry for `summarization`/`unittest-generator` (Upsonic/Upsonic, 7 836 stars).
