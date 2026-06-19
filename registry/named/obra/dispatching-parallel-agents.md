---
id: obra/dispatching-parallel-agents
name: Dispatching Parallel Agents
contributor: obra
origin: true
genericSkillRef: dispatching-parallel-agents
status: named
title: The Parallel Dispatch
level: 4★
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
updatedAt: '2026-06-14'
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
  grade: B
  commits: 609
  contributors: 36
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
trustMagnitudeInputHash: 69e3bffa5ac7f7bffc76b98d6693be21356b252816f68d474f3e683a3dbec690
---

## Overview

Dispatching Parallel Agents by @obra establishes the pattern of breaking a problem into independent sub-tasks and assigning each to a freshly-spawned, context-isolated agent running concurrently. The dispatching agent coordinates results rather than doing the work sequentially, yielding significant throughput gains on tasks that naturally decompose across files, services, or domains.

## Origin

First published by @obra in the obra/superpowers skill library. This is the origin implementation for the `dispatching-parallel-agents` skill bucket.
