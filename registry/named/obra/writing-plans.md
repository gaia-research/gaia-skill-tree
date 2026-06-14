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
updatedAt: '2026-06-14'
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
timeline:
- timestamp: '2026-06-14T12:32:49Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/obra/superpowers/blob/main/skills/writing-plans/SKILL.md
    as B (trustNumber: 70.0)'
---

## Overview

Writing Plans by @obra mandates that complex tasks begin with a written plan, not with code. The agent decomposes the goal into a flat, ordered list of sub-tasks sized small enough that each can be executed and verified independently. The plan is written to a file so it can be handed to an executor (human or subagent) without loss of context. Crucially, plan-writing is a separate phase — the agent does not start implementing while still planning.

## Origin

First published by @obra in the obra/superpowers skill library. This is the origin implementation for the `writing-plans` skill bucket.
