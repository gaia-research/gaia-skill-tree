---
id: obra/systematic-debugging
name: Systematic Debugging
contributor: obra
origin: false
genericSkillRef: systematic-debugging
status: named
title: The Root Cause Hunter
level: 3★
description: Finds the root cause before attempting any fix — building a minimal reproduction,
  forming ranked hypotheses, and instrumenting to confirm before writing a single
  corrective line.
links:
  github: https://github.com/obra/superpowers/blob/main/skills/systematic-debugging/SKILL.md
tags:
- debugging
- root-cause
- hypothesis-driven
- instrumentation
- reproduction
createdAt: '2026-05-18'
updatedAt: '2026-06-19'
suiteRef: obra/superpowers
evidence:
- class: B
  source: https://github.com/obra/superpowers/blob/main/skills/systematic-debugging/SKILL.md
  evaluator: mbtiongson1
  date: '2026-05-18'
  notes: obra/superpowers — complete software development methodology for coding agents,
    196k+ stars, v5.1.0, adopted across Claude Code, Codex CLI, Gemini CLI, OpenCode,
    Cursor, GitHub Copilot CLI. (backfilled — class-to-type migration)
  type: repo
  trustNumber: 70.0
  grade: B
  commits: 609
  contributors: 36
- source: https://github.com/obra/superpowers/issues/1795
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: social-signal
  class: A
  notes: Mentions systematic-debugging as candidate for nested subagents.
- source: https://www.youtube.com/watch?v=6YltXh12W-g
  evaluator: unknown
  date: '2026-06-19'
  type: social-signal
  class: A
  notes: 'Larridin podcast: Jesse Vincent explains obra/superpowers methodology covering
    brainstorming, plans, subagents, debugging, and git worktrees. 4,402 views (2026-06-19).'
  views: 4402
- source: https://www.youtube.com/watch?v=6YltXh12W-g
  evaluator: unknown
  date: '2026-06-19'
timeline:
- timestamp: '2026-06-02T23:33:00Z'
  action: demote
  contributor: unknown
  details: Origin status removed. Transferred to garrytan/investigate.
- timestamp: '2026-06-14T12:32:48Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/obra/superpowers/blob/main/skills/systematic-debugging/SKILL.md
    as B (trustNumber: 70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:19Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T11:07:58Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- timestamp: '2026-06-19T12:47:17Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/obra/superpowers/issues/1795 (type:
    social-signal)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T12:53:51Z'
  details: TM 36.0 -> 36.0, grade C -> C (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:38Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:43Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- timestamp: '2026-06-19T14:26:03Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://www.youtube.com/watch?v=6YltXh12W-g (type:
    social-signal)'
- timestamp: '2026-06-19T14:27:53Z'
  action: evidence_added
  contributor: unknown
  details: Added evidence from https://www.youtube.com/watch?v=6YltXh12W-g
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T14:31:47Z'
  details: TM 36.0 -> 65.15, grade C -> B (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T14:32:19Z'
  details: TM 65.15 -> 65.15, grade B -> B (direct edit -- CLI gap)
trustMagnitude: 65.15
overallTrustGrade: B
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
  firstEvidenceAt: '2026-06-19T12:47:17Z'
trustMagnitudeInputHash: 7502b9e6c33f69005e59784db2861df220a6ff50d26c9552c8376b18625e4874
---

## Overview

Systematic Debugging by @obra prohibits speculative fixes. When a bug or test failure appears, the agent first confirms it can reproduce the issue deterministically, then minimises the reproduction to its essential form. It generates a ranked list of hypotheses, selects the most probable, instruments the code to test that hypothesis, and only writes a fix once the root cause is confirmed. Patches without a prior confirmed hypothesis are explicitly rejected.

## Origin

First published by @obra in the obra/superpowers skill library. This is the origin implementation for the `systematic-debugging` skill bucket.
