---
id: obra/dispatching-parallel-agents
name: Dispatching Parallel Agents
contributor: obra
origin: true
genericSkillRef: dispatching-parallel-agents
status: named
title: The Parallel Dispatch
level: 3★
description: Delegates independent tasks to specialized agents with isolated context
  to work concurrently, dramatically reducing wall-clock time on multi-part problems.
links:
  github: https://github.com/obra/superpowers/blob/main/skills/dispatching-parallel-agents/SKILL.md
tags:
- parallel-agents
- concurrency
- delegation
- multi-agent
- subagent
createdAt: '2026-05-18'
updatedAt: '2026-06-21'
suiteRef: obra/superpowers
evidence:
- class: B
  source: https://github.com/obra/superpowers/blob/main/skills/dispatching-parallel-agents/SKILL.md
  evaluator: mbtiongson1
  date: '2026-05-18'
  notes: obra/superpowers — complete software development methodology for coding agents,
    196k+ stars, v5.1.0, adopted across Claude Code, Codex CLI, Gemini CLI, OpenCode,
    Cursor, GitHub Copilot CLI. (backfilled — class-to-type migration)
  type: repo
  trustNumber: 70.0
  commits: 609
  contributors: 36
  grade: B
- source: https://github.com/obra/superpowers
  evaluator: unknown
  date: '2026-06-20'
  type: github-stars-own
  trustNumber: 88.0
  grade: B
  notes: obra/superpowers — 233k GitHub stars, complete AI coding methodology adopted
    across Claude Code, Codex CLI, Gemini CLI (verified 2026-06-20)
  stars: 233000
  skillCountInRepo: 13
  sourceStartedAt: '2023-01-01'
timeline:
- timestamp: '2026-06-14T12:32:47Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/obra/superpowers/blob/main/skills/dispatching-parallel-agents/SKILL.md
    as B (trustNumber: 70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:19Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T11:07:58Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:38Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:42Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- timestamp: '2026-06-19T16:48:24Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/obra/superpowers (type: github-stars-own)'
- timestamp: '2026-06-19T16:48:25Z'
  action: evidence_graded
  contributor: unknown
  details: 'Graded evidence from https://github.com/obra/superpowers as A (trustNumber:
    88.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T17:13:03Z'
  details: TM 36.0 -> 86.0, grade C -> B (direct edit -- CLI gap)
- timestamp: '2026-06-20T06:31:34Z'
  action: demote
  contributor: mbtiongson1
  details: Level updated from 4★ to 3★ per G7 final rankings calibration.
trustMagnitude: 86.0
overallTrustGrade: B
apexGateStatus:
  aGradedOriginsGte5: false
  sourceTenureDaysGte180AorS: true
  directNestedSuiteGte1: false
  depth2OnlyReachableGte1: false
  overallGradeS: false
  apexPromotionPrSigned: false
  crossOrgVerifier: null
  systemWideCap: null
trustMagnitudeInputHash: 6e8062f6ddf3e6c27847a65d11b3d94b686e8c1916f4a66d04e13951bdd65054
verification:
  firstEvidenceAt: '2026-06-19T16:48:24Z'
---

## Overview

Dispatching Parallel Agents by @obra establishes the pattern of breaking a problem into independent sub-tasks and assigning each to a freshly-spawned, context-isolated agent running concurrently. The dispatching agent coordinates results rather than doing the work sequentially, yielding significant throughput gains on tasks that naturally decompose across files, services, or domains.

## Origin

First published by @obra in the obra/superpowers skill library. This is the origin implementation for the `dispatching-parallel-agents` skill bucket.
