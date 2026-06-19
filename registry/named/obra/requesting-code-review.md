---
id: obra/requesting-code-review
name: Requesting Code Review
contributor: obra
origin: true
genericSkillRef: requesting-code-review
status: named
title: The Preemptive Review
level: 3★
description: Dispatches a code reviewer subagent with isolated context to catch issues
  before they cascade — producing a structured review report that guides targeted
  fixes.
links:
  github: https://github.com/obra/superpowers/blob/main/skills/requesting-code-review/SKILL.md
tags:
- code-review
- subagent
- quality-gate
- pre-merge
- isolated-context
createdAt: '2026-05-18'
updatedAt: '2026-06-14'
suiteRef: obra/superpowers
evidence:
- class: B
  source: https://github.com/obra/superpowers/blob/main/skills/requesting-code-review/SKILL.md
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
- timestamp: '2026-06-14T12:32:48Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/obra/superpowers/blob/main/skills/requesting-code-review/SKILL.md
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

Requesting Code Review by @obra treats review as a first-class step, not an afterthought. The agent spawns a fresh reviewer subagent that receives only the diff and relevant context, performs an independent evaluation, and returns a structured report covering correctness, edge cases, naming, and potential regressions. The originating agent uses that report to make targeted fixes before opening a PR, intercepting issues that in-context blindness would miss.

## Origin

First published by @obra in the obra/superpowers skill library. This is the origin implementation for the `requesting-code-review` skill bucket.
