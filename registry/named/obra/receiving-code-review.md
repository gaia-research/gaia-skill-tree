---
id: obra/receiving-code-review
name: Receiving Code Review
contributor: obra
origin: true
genericSkillRef: receiving-code-review
status: named
title: The Rigorous Revision
level: 2★
description: Processes code review feedback with technical rigor and verification
  before implementation — questioning unclear feedback and confirming fixes with tests
  rather than blindly applying suggestions.
links:
  github: https://github.com/obra/superpowers/blob/main/skills/receiving-code-review/SKILL.md
tags:
- code-review
- feedback
- verification
- quality
- collaboration
createdAt: '2026-05-18'
updatedAt: '2026-06-14'
suiteRef: obra/superpowers
evidence:
- class: B
  source: https://github.com/obra/superpowers/blob/main/skills/receiving-code-review/SKILL.md
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
  details: 'Re-graded evidence from https://github.com/obra/superpowers/blob/main/skills/receiving-code-review/SKILL.md
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
trustMagnitudeInputHash: 1e5b1bec8cc30c52fe9d1c8096457c5aaebdcc5de48eff84a18c2c6c3ed3b4b6
---

## Overview

Receiving Code Review by @obra inverts the passive "apply and move on" instinct. When review feedback arrives, the agent reads every comment fully before touching code, questions anything technically ambiguous or contradictory, proposes counter-suggestions where appropriate, then implements accepted changes with explicit test verification. The skill stops the cycle of repeated back-and-forth caused by incomplete or misunderstood revisions.

## Origin

First published by @obra in the obra/superpowers skill library. This is the origin implementation for the `receiving-code-review` skill bucket.
