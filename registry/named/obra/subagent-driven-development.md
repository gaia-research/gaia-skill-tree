---
id: obra/subagent-driven-development
name: Subagent-Driven Development
contributor: obra
origin: true
genericSkillRef: subagent-driven-development
status: named
title: The Swarm Architect
level: 4★
description: Executes plans by dispatching a fresh subagent per task with a two-stage
  review (spec compliance then code quality), keeping the orchestrator context clean
  throughout.
links:
  github: https://github.com/obra/superpowers/blob/main/skills/subagent-driven-development/SKILL.md
tags:
- subagent
- orchestration
- plan-execution
- two-stage-review
- multi-agent
createdAt: '2026-05-18'
updatedAt: '2026-06-19'
suiteRef: obra/superpowers
evidence:
- class: B
  source: https://github.com/obra/superpowers/blob/main/skills/subagent-driven-development/SKILL.md
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
- source: https://github.com/obra/superpowers/issues/1809
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: peer-review
  class: A
  notes: 'Fixes #1799 by adding -C DIR flag to review-package script to allow better
    harness allowlisting.'
- source: https://github.com/obra/superpowers/issues/1804
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: peer-review
  class: A
  notes: 'SDD: treatment arm 3/3 correct, control arm 0/3.'
- source: https://github.com/obra/superpowers/issues/1799
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: peer-review
  class: A
  notes: SDD review-package friction with worktree workflows, resolved by -C DIR flag.
- source: https://github.com/obra/superpowers/issues/1772
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: peer-review
  class: A
  notes: Fixes task-brief path collision in SDD; repeated runs overwrite previous
    briefs.
timeline:
- timestamp: '2026-06-14T12:32:48Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/obra/superpowers/blob/main/skills/subagent-driven-development/SKILL.md
    as B (trustNumber: 70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:19Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T11:07:58Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- timestamp: '2026-06-19T12:41:59Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/obra/superpowers/issues/1809 (type:
    peer-review)'
- timestamp: '2026-06-19T12:42:16Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/obra/superpowers/issues/1804 (type:
    peer-review)'
- timestamp: '2026-06-19T12:42:32Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/obra/superpowers/issues/1799 (type:
    peer-review)'
- timestamp: '2026-06-19T12:42:48Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/obra/superpowers/issues/1772 (type:
    peer-review)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T12:53:50Z'
  details: TM 36.0 -> 88.5, grade C -> B (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:38Z'
  details: TM 0.0 -> 88.5, grade ungraded -> B (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:43Z'
  details: TM 0.0 -> 88.5, grade ungraded -> B (direct edit -- CLI gap)
trustMagnitude: 88.5
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
  firstEvidenceAt: '2026-06-19T12:41:58Z'
trustMagnitudeInputHash: c575bffd567703ce55f60ef4bfe8d2e540eca566bab9e878aceefaeaa512bee5
---

## Overview

Subagent-Driven Development by @obra is the high-autonomy execution pattern: rather than carrying out plan tasks itself and accumulating context debt, the orchestrating agent spawns a dedicated subagent for every task. Each subagent gets a clean context window, executes its task, and returns results. A two-stage review then checks spec compliance first and code quality second before the result is accepted. This architecture allows multi-step projects to run at scale without the orchestrator's reasoning degrading.

## Origin

First published by @obra in the obra/superpowers skill library. This is the origin implementation for the `subagent-driven-development` skill bucket.
