---
id: obra/using-git-worktrees
name: Using Git Worktrees
contributor: obra
origin: true
genericSkillRef: using-git-worktrees
status: named
title: The Isolated Workspace
level: 2★
description: Ensures every piece of feature work begins in an isolated workspace —
  creating a native git worktree when available, falling back to tool-provided isolation
  otherwise.
links:
  github: https://github.com/obra/superpowers/blob/main/skills/using-git-worktrees/SKILL.md
tags:
- git-worktrees
- isolation
- workspace
- branching
- safety
createdAt: '2026-05-18'
updatedAt: '2026-06-14'
suiteRef: obra/superpowers
evidence:
- class: B
  source: https://github.com/obra/superpowers/blob/main/skills/using-git-worktrees/SKILL.md
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
  details: 'Re-graded evidence from https://github.com/obra/superpowers/blob/main/skills/using-git-worktrees/SKILL.md
    as B (trustNumber: 70.0)'
---

## Overview

Using Git Worktrees by @obra enforces the habit of starting every feature in an isolated working directory. If the environment supports `git worktree add`, the agent creates one; otherwise it falls back to the hosting tool's isolation primitive. The goal is to prevent unintended cross-contamination between parallel workstreams and to make it safe to abandon work without touching the primary checkout.

## Origin

First published by @obra in the obra/superpowers skill library. This is the origin implementation for the `using-git-worktrees` skill bucket.
