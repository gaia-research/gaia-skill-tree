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
updatedAt: '2026-06-14'
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
timeline:
- timestamp: '2026-06-14T12:32:47Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/obra/superpowers/blob/main/skills/executing-plans/SKILL.md
    as B (trustNumber: 70.0)'
---

## Overview

Executing Plans by @obra treats a written plan as a binding contract. The agent loads the plan, reads every task before touching code, flags any ambiguities, then executes each step in order — marking tasks complete as it goes and surfacing blockers rather than improvising around them. Completion is only reported after all tasks are verified done.

## Origin

First published by @obra in the obra/superpowers skill library. This is the origin implementation for the `executing-plans` skill bucket.
