---
id: obra/writing-plans
name: Writing Plans
contributor: obra
origin: true
genericSkillRef: writing-plans
status: named
title: The Blueprint Writer
level: 2★
description: Writes comprehensive implementation plans that break multi-step tasks
  into bite-sized, independently executable sub-tasks before any code is touched.
links:
  github: https://github.com/obra/superpowers/blob/main/skills/writing-plans/SKILL.md
tags:
- planning
- decomposition
- implementation-plan
- pre-coding
- task-breakdown
createdAt: '2026-05-18'
updatedAt: '2026-06-19'
suiteRef: obra/superpowers
evidence:
- class: B
  source: https://github.com/obra/superpowers/blob/main/skills/writing-plans/SKILL.md
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
- source: https://github.com/obra/superpowers/issues/1808
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: peer-review
  class: A
  notes: Requires writing-plans outputs to start with WHAT/WHY bullets.
- source: https://github.com/obra/superpowers/issues/1803
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: social-signal
  class: A
  notes: Detailed Phase 4 checkpoint and Phase 5 adversarial review workflow across
    90+ sessions.
- source: https://github.com/obra/superpowers/issues/1746
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: peer-review
  class: A
  notes: Adds Global Constraints and per-task Interfaces to writing-plans template.
- source: https://github.com/obra/superpowers/issues/1690
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: social-signal
  class: A
  notes: Security concern shows widespread writing-plans usage and integration.
- source: https://github.com/obra/superpowers/issues/1574
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: social-signal
  class: A
  notes: Enhancement to coordinate plan-tune preferences across writing-plans, finishing-a-development-branch,
    executing-plans.
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
- timestamp: '2026-06-14T12:32:49Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/obra/superpowers/blob/main/skills/writing-plans/SKILL.md
    as B (trustNumber: 70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:19Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T11:07:58Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- timestamp: '2026-06-19T12:43:14Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/obra/superpowers/issues/1808 (type:
    peer-review)'
- timestamp: '2026-06-19T12:43:29Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/obra/superpowers/issues/1803 (type:
    social-signal)'
- timestamp: '2026-06-19T12:43:46Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/obra/superpowers/issues/1746 (type:
    peer-review)'
- timestamp: '2026-06-19T12:44:03Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/obra/superpowers/issues/1690 (type:
    social-signal)'
- timestamp: '2026-06-19T12:44:19Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/obra/superpowers/issues/1574 (type:
    social-signal)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T12:53:51Z'
  details: TM 36.0 -> 81.0, grade C -> B (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:38Z'
  details: TM 0.0 -> 81.0, grade ungraded -> B (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:43Z'
  details: TM 0.0 -> 81.0, grade ungraded -> B (direct edit -- CLI gap)
- timestamp: '2026-06-19T14:25:54Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://www.youtube.com/watch?v=6YltXh12W-g (type:
    social-signal)'
- timestamp: '2026-06-19T14:26:28Z'
  action: evidence_added
  contributor: unknown
  details: Added evidence from https://www.youtube.com/watch?v=6YltXh12W-g
trustMagnitude: 81.0
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
  firstEvidenceAt: '2026-06-19T12:43:14Z'
trustMagnitudeInputHash: c33fb8be67217531f1c55a0ff0c57d9cc95199dd38811f6b40b0274bc0b2d7ae
---

## Overview

Writing Plans by @obra mandates that complex tasks begin with a written plan, not with code. The agent decomposes the goal into a flat, ordered list of sub-tasks sized small enough that each can be executed and verified independently. The plan is written to a file so it can be handed to an executor (human or subagent) without loss of context. Crucially, plan-writing is a separate phase — the agent does not start implementing while still planning.

## Origin

First published by @obra in the obra/superpowers skill library. This is the origin implementation for the `writing-plans` skill bucket.
