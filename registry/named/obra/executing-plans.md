---
id: obra/executing-plans
name: Executing Plans
contributor: obra
origin: true
genericSkillRef: executing-plans
status: named
title: The Faithful Executor
level: 2★
description: Loads a written implementation plan, reviews it critically, executes
  all tasks sequentially, and reports when complete — without improvising beyond the
  plan's scope.
links:
  github: https://github.com/obra/superpowers/blob/main/skills/executing-plans/SKILL.md
tags:
- plan-execution
- sequential-tasks
- implementation
- plan-driven
createdAt: '2026-05-18'
updatedAt: '2026-06-19'
suiteRef: obra/superpowers
evidence:
- class: B
  source: https://github.com/obra/superpowers/blob/main/skills/executing-plans/SKILL.md
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
- source: https://github.com/obra/superpowers/issues/1804
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: peer-review
  class: A
  notes: Promotes using-git-worktrees into Step 0 of executing-plans.
- source: https://github.com/obra/superpowers/issues/1574
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: social-signal
  class: A
  notes: Feature request involves executing-plans in plan-tune coordination.
timeline:
- timestamp: '2026-06-14T12:32:47Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/obra/superpowers/blob/main/skills/executing-plans/SKILL.md
    as B (trustNumber: 70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:19Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T11:07:58Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- timestamp: '2026-06-19T12:46:36Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/obra/superpowers/issues/1804 (type:
    peer-review)'
- timestamp: '2026-06-19T12:46:53Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/obra/superpowers/issues/1574 (type:
    social-signal)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T12:53:50Z'
  details: TM 36.0 -> 66.0, grade C -> B (direct edit -- CLI gap)
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
  firstEvidenceAt: '2026-06-19T12:46:36Z'
---

## Overview

Executing Plans by @obra treats a written plan as a binding contract. The agent loads the plan, reads every task before touching code, flags any ambiguities, then executes each step in order — marking tasks complete as it goes and surfacing blockers rather than improvising around them. Completion is only reported after all tasks are verified done.

## Origin

First published by @obra in the obra/superpowers skill library. This is the origin implementation for the `executing-plans` skill bucket.
