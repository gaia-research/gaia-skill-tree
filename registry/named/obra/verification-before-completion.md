---
id: obra/verification-before-completion
name: Verification Before Completion
contributor: obra
origin: true
genericSkillRef: verification-before-completion
status: named
title: The Completion Gate
level: 2★
description: Requires running verification commands and confirming their output before
  claiming any work is complete, fixed, or passing — no claim without evidence.
links:
  github: https://github.com/obra/superpowers/blob/main/skills/verification-before-completion/SKILL.md
tags:
- verification
- completion
- testing
- quality-gate
- discipline
createdAt: '2026-05-18'
updatedAt: '2026-06-14'
suiteRef: obra/superpowers
evidence:
- class: B
  source: https://github.com/obra/superpowers/blob/main/skills/verification-before-completion/SKILL.md
  evaluator: mbtiongson1
  date: '2026-05-18'
  notes: obra/superpowers — complete software development methodology for coding agents, 196k+ stars, v5.1.0, adopted across Claude Code, Codex CLI, Gemini CLI, OpenCode, Cursor, GitHub Copilot CLI. (backfilled — class-to-type migration)
  type: repo
  trustNumber: 70.0
  grade: B
timeline:
- timestamp: '2026-06-14T12:32:49Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/obra/superpowers/blob/main/skills/verification-before-completion/SKILL.md
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
trustMagnitudeInputHash: ebee612b016560457e8ba4faf5f42d20db61731ca408ed89b38fc6caa00a0737
---

## Overview

Verification Before Completion by @obra is the simplest and most broadly applicable skill in the superpowers library: the agent is not allowed to say "done", "fixed", or "passing" without first running the relevant verification command and including its output. This single constraint eliminates an entire class of hallucinated completions and untested "fixes" that create downstream rework.

## Origin

First published by @obra in the obra/superpowers skill library. This is the origin implementation for the `verification-before-completion` skill bucket.
