---
id: devin-ai/autonomous-swe
name: Autonomous SWE
contributor: devin-ai
origin: true
genericSkillRef: autonomous-debug
status: named
title: The Codebreaker's Will
catalogRef: devin-ai-autonomous-swe
level: 1★
description: Autonomous software engineering agent capable of end-to-end debugging,
  code generation, and self-correction across complex multi-file codebases.
links:
  github: https://github.com/cognition-labs/devin
tags:
- software-engineering
- autonomous
- debugging
- code-generation
- self-correction
createdAt: '2026-04-29'
updatedAt: '2026-06-19'
evidence:
- class: B
  source: https://github.com/cognition-labs/devin
  evaluator: mbtiongson1
  date: '2026-05-17'
  notes: 'Replaced missing seed evidence with live repository from real-skills catalog.
    (backfilled — class-to-type migration) repo not found on GitHub as of 2026-06-19
    (CLI gap: commits+contributors not writable via gaia dev evidence)'
  type: repo
  commits: 0
  contributors: 0
  trustNumber: 70.0
  grade: B
- source: https://arxiv.org/abs/2403.02128
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: benchmark-result
  class: A
  notes: 'SWE-bench unassisted: 13.86% resolved (2294 real-world GitHub issues, March
    2024). Previous SOTA was 1.96%. Score: 13.86'
- source: https://www.youtube.com/watch?v=fjyAWpz3Qm8
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: social-signal
  class: A
  notes: 'Official Cognition YouTube: "Introducing Devin, the first AI software engineer."
    Channel: Cognition (official). Massive viral reach, millions of views.'
- source: https://www.youtube.com/watch?v=tNzgM37BUTo
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: peer-review
  class: A
  notes: 'Karl Brown (Internet of Bugs): frame-by-frame analysis of Devin Upwork demo.
    Documents staged demos, autonomy loops, context withholding. April 2024.'
timeline:
- timestamp: '2026-06-02T23:48:17Z'
  action: demote
  contributor: unknown
  details: Calibrated level from 3★ to 1★
- timestamp: '2026-06-14T12:32:17Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/cognition-labs/devin as B (trustNumber:
    70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:14Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- timestamp: '2026-06-19T10:34:41Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://arxiv.org/abs/2403.02128 (type: benchmark-result)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T10:36:26Z'
  details: TM 0.0 -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- timestamp: '2026-06-19T10:41:11Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://www.youtube.com/watch?v=fjyAWpz3Qm8 (type:
    social-signal)'
- timestamp: '2026-06-19T10:46:49Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://www.youtube.com/watch?v=tNzgM37BUTo (type:
    peer-review)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T10:52:24Z'
  details: TM 0.0 -> 30.0, grade ungraded -> C (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:37Z'
  details: TM 0.0 -> 30.0, grade ungraded -> C (direct edit -- CLI gap)
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
verification:
  firstEvidenceAt: '2026-06-19T10:34:41Z'
---

## Overview

Autonomous SWE is an autonomous software engineering agent that combines debugging, code generation, and self-correction to resolve issues end-to-end. It navigates complex, multi-file repositories, identifies root causes, proposes and applies fixes, runs tests, and iterates until the problem is resolved—without human intervention.

## Origin

First published by @devin-ai (Cognition Labs). This is the origin implementation for the "autonomous-debug" skill bucket.
