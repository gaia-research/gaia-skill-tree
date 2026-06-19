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
updatedAt: '2026-06-14'
suiteRef: obra/superpowers
evidence:
- class: B
  source: https://github.com/obra/superpowers/blob/main/skills/subagent-driven-development/SKILL.md
  evaluator: mbtiongson1
  date: '2026-05-18'
  notes: obra/superpowers — complete software development methodology for coding agents, 196k+ stars, v5.1.0, adopted across Claude Code, Codex CLI, Gemini CLI, OpenCode, Cursor, GitHub Copilot CLI. (backfilled — class-to-type migration)
  type: repo
  trustNumber: 70.0
  grade: B
  commits: 609
  contributors: 36
timeline:
- timestamp: '2026-06-14T12:32:48Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/obra/superpowers/blob/main/skills/subagent-driven-development/SKILL.md
    as B (trustNumber: 70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:19Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
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
trustMagnitudeInputHash: f7e77293b8bf52d41a681f9b445a664246acd2e7ed065976d54a48af29a46066
---

## Overview

Subagent-Driven Development by @obra is the high-autonomy execution pattern: rather than carrying out plan tasks itself and accumulating context debt, the orchestrating agent spawns a dedicated subagent for every task. Each subagent gets a clean context window, executes its task, and returns results. A two-stage review then checks spec compliance first and code quality second before the result is accepted. This architecture allows multi-step projects to run at scale without the orchestrator's reasoning degrading.

## Origin

First published by @obra in the obra/superpowers skill library. This is the origin implementation for the `subagent-driven-development` skill bucket.
