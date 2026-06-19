---
id: obra/finishing-a-development-branch
name: Finishing a Development Branch
contributor: obra
origin: false
genericSkillRef: finishing-a-development-branch
status: named
title: The Clean Landing
level: 2★
description: Guides completion of development work by verifying tests first, then
  presenting structured options for merge, PR creation, or cleanup — never declaring
  done without a passing build.
links:
  github: https://github.com/obra/superpowers/blob/main/skills/finishing-a-development-branch/SKILL.md
tags:
- branch-management
- pull-request
- merge
- testing
- completion
createdAt: '2026-05-18'
updatedAt: '2026-06-19'
suiteRef: obra/superpowers
evidence:
- class: B
  source: https://github.com/obra/superpowers/blob/main/skills/finishing-a-development-branch/SKILL.md
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
- source: https://github.com/obra/superpowers/issues/1574
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: social-signal
  class: A
  notes: Feature request involves finishing-a-development-branch in plan-tune coordination.
- source: https://github.com/obra/superpowers/issues/1609
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: social-signal
  class: A
  notes: finishing-a-development-branch Option 2 hardcodes gh pr, fails on non-GitHub
    platforms.
timeline:
- timestamp: '2026-06-02T23:32:59Z'
  action: demote
  contributor: unknown
  details: Origin status removed. Transferred to garrytan/ship.
- timestamp: '2026-06-14T12:32:47Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/obra/superpowers/blob/main/skills/finishing-a-development-branch/SKILL.md
    as B (trustNumber: 70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:19Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T11:07:58Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- timestamp: '2026-06-19T12:48:58Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/obra/superpowers/issues/1574 (type:
    social-signal)'
- timestamp: '2026-06-19T12:49:15Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/obra/superpowers/issues/1609 (type:
    social-signal)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T12:53:50Z'
  details: TM 36.0 -> 36.0, grade C -> C (direct edit -- CLI gap)
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
verification:
  firstEvidenceAt: '2026-06-19T12:48:58Z'
---

## Overview

Finishing a Development Branch by @obra defines the ritual for closing out a feature branch. Before offering any merge or PR option, the agent runs the test suite and confirms it passes. It then presents a structured menu — open a PR, squash-merge directly, or clean up — so the developer makes an informed choice rather than the agent acting unilaterally. The skill prevents the common failure mode of declaring work "done" with a broken build.

## Origin

First published by @obra in the obra/superpowers skill library. This is the origin implementation for the `finishing-a-development-branch` skill bucket.
