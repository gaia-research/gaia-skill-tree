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
updatedAt: '2026-06-14'
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
---

## Overview

Systematic Debugging by @obra prohibits speculative fixes. When a bug or test failure appears, the agent first confirms it can reproduce the issue deterministically, then minimises the reproduction to its essential form. It generates a ranked list of hypotheses, selects the most probable, instruments the code to test that hypothesis, and only writes a fix once the root cause is confirmed. Patches without a prior confirmed hypothesis are explicitly rejected.

## Origin

First published by @obra in the obra/superpowers skill library. This is the origin implementation for the `systematic-debugging` skill bucket.
