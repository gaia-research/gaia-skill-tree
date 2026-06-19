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
updatedAt: '2026-06-19'
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
  commits: 609
  contributors: 36
- source: https://github.com/obra/superpowers/issues/1804
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: peer-review
  class: A
  notes: 'Promotes using-git-worktrees to Step 0 in executing-plans and SDD. Real-world:
    0/4 worktrees without fix.'
- source: https://github.com/obra/superpowers/issues/1801
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: peer-review
  class: A
  notes: 'Fixes #1797 by adding proper variable assignments in Step 1.'
- source: https://github.com/obra/superpowers/issues/1797
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: peer-review
  class: A
  notes: Step 1 uses undefined variables, causing git worktree to run with empty branch.
- source: https://github.com/obra/superpowers/issues/1782
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: peer-review
  class: A
  notes: Fixes ignore-verification logic, tested against 5 adversarial cases.
timeline:
- timestamp: '2026-06-14T12:32:49Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/obra/superpowers/blob/main/skills/using-git-worktrees/SKILL.md
    as B (trustNumber: 70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:19Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T11:07:58Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- timestamp: '2026-06-19T12:44:47Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/obra/superpowers/issues/1804 (type:
    peer-review)'
- timestamp: '2026-06-19T12:45:20Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/obra/superpowers/issues/1801 (type:
    peer-review)'
- timestamp: '2026-06-19T12:45:55Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/obra/superpowers/issues/1797 (type:
    peer-review)'
- timestamp: '2026-06-19T12:46:12Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/obra/superpowers/issues/1782 (type:
    peer-review)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T12:53:51Z'
  details: TM 36.0 -> 88.5, grade C -> B (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:38Z'
  details: TM 0.0 -> 88.5, grade ungraded -> B (direct edit -- CLI gap)
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
  firstEvidenceAt: '2026-06-19T12:44:46Z'
---

## Overview

Using Git Worktrees by @obra enforces the habit of starting every feature in an isolated working directory. If the environment supports `git worktree add`, the agent creates one; otherwise it falls back to the hosting tool's isolation primitive. The goal is to prevent unintended cross-contamination between parallel workstreams and to make it safe to abandon work without touching the primary checkout.

## Origin

First published by @obra in the obra/superpowers skill library. This is the origin implementation for the `using-git-worktrees` skill bucket.
