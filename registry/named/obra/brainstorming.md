---
id: obra/brainstorming
name: Brainstorming
contributor: obra
origin: true
genericSkillRef: brainstorming
status: named
title: The Collaborative Blueprint
level: 2★
description: Explores user intent, requirements, and design before implementation.
  Turns ideas into fully formed designs and specs through natural collaborative dialogue.
links:
  github: https://github.com/obra/superpowers/blob/main/skills/brainstorming/SKILL.md
tags:
- brainstorming
- requirements
- design
- collaboration
- pre-implementation
createdAt: '2026-05-18'
updatedAt: '2026-06-14'
suiteRef: obra/superpowers
evidence:
- class: B
  source: https://github.com/obra/superpowers/blob/main/skills/brainstorming/SKILL.md
  evaluator: mbtiongson1
  date: '2026-05-18'
  notes: obra/superpowers — complete software development methodology for coding agents, 196k+ stars, v5.1.0, adopted across Claude Code, Codex CLI, Gemini CLI, OpenCode, Cursor, GitHub Copilot CLI. (backfilled — class-to-type migration)
  type: repo
  trustNumber: 70.0
  grade: B
timeline:
- timestamp: '2026-06-14T12:32:46Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/obra/superpowers/blob/main/skills/brainstorming/SKILL.md
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
trustMagnitudeInputHash: 8bebae4b110070d8e7b64344b057dca63e306a620fd52a8b836bce7d1cb8b42f
---

## Overview

Brainstorming by @obra drives a structured collaborative session that surfaces user intent, uncovers unstated requirements, and produces a coherent design spec before any code is written. Rather than leaping to implementation, the agent asks clarifying questions, maps constraints, and iterates on options with the user until the idea is fully formed.

## Origin

First published by @obra in the obra/superpowers skill library. This is the origin implementation for the `brainstorming` skill bucket.
