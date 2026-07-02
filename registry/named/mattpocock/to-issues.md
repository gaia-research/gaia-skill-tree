---
id: mattpocock/to-issues
name: To Issues
contributor: mattpocock
origin: false
genericSkillRef: vertical-slice-planning
status: named
title: The Vertical Slicer
catalogRef: mattpocock-to-issues
level: 3★
description: Breaks a plan, spec, or PRD into independently-grabbable GitHub issues
  as tracer-bullet vertical slices that each cut through all integration layers end-to-end.
  Classifies each slice HITL or AFK, maps dependency chains, quizzes the user on granularity,
  and publishes structured issues with acceptance criteria in dependency order.
links:
  github: https://github.com/mattpocock/skills/blob/main/skills/engineering/to-issues/SKILL.md
tags:
- vertical-slicing
- issue-decomposition
- tracer-bullet
- hitl
- afk
- acceptance-criteria
createdAt: '2026-04-30'
updatedAt: '2026-06-21'
suiteRef: mattpocock/engineering
evidence:
- class: B
  source: https://github.com/mattpocock/skills/blob/main/skills/engineering/to-issues/SKILL.md
  evaluator: mbtiongson1
  date: '2026-04-30'
  notes: 'Production skill implementing tracer-bullet vertical slicing with HITL/AFK"
    classification and issue-tracker publication. (backfilled — class-to-type migration)
    (CLI gap: --commits/--contributors not supported by gaia dev evidence)'
  type: repo
  trustNumber: 70.0
  commits: 137
  contributors: 3
  grade: C
- source: https://github.com/mattpocock/skills
  evaluator: unknown
  updatedAt: '2026-07-01'
  date: '2026-06-20'
  type: github-stars-own
  trustNumber: 88.0
  grade: C
  notes: mattpocock/skills suite — 137k GitHub stars; to-issues is part of this repo
  stars: 152357
  skillCountInRepo: 21
  sourceStartedAt: '2025-01-01'
- source: https://www.youtube.com/watch?v=EJyuu6zlQCg
  evaluator: unknown
  date: '2026-06-20'
  type: social-signal
  trustNumber: 82.0
  grade: B
  notes: Matt Pocock — 5 Claude Code skills I use every single day; 412K views; covers
    mattpocock/skills repo (verified 2026-06-20)
  views: 412000
  sourceStartedAt: '2025-01-01'
timeline:
- timestamp: '2026-06-02T23:33:00Z'
  action: demote
  contributor: unknown
  details: Origin status removed. Transferred to garrytan/garrytan.
- timestamp: '2026-06-14T12:32:44Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/mattpocock/skills/blob/main/skills/engineering/to-issues/SKILL.md
    as B (trustNumber: 70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:18Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T11:52:12Z'
  details: TM 0.0 -> 11.21, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:38Z'
  details: TM 0.0 -> 11.21, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:41Z'
  details: TM 0.0 -> 11.21, grade ungraded -> ungraded (direct edit -- CLI gap)
- timestamp: '2026-06-19T17:07:36Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/mattpocock/skills (type: github-stars-own)'
- timestamp: '2026-06-19T17:07:37Z'
  action: evidence_graded
  contributor: unknown
  details: 'Graded evidence from https://github.com/mattpocock/skills as A (trustNumber:
    88.0)'
- timestamp: '2026-06-19T17:07:38Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://www.youtube.com/watch?v=EJyuu6zlQCg (type:
    social-signal)'
- timestamp: '2026-06-19T17:07:38Z'
  action: evidence_graded
  contributor: unknown
  details: 'Graded evidence from https://www.youtube.com/watch?v=EJyuu6zlQCg as A
    (trustNumber: 82.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T17:13:03Z'
  details: TM 11.21 -> 90.38, grade ungraded -> B (direct edit -- CLI gap)
trustMagnitude: 90.38
overallTrustGrade: B
apexGateStatus:
  aGradedOriginsGte5: false
  sourceTenureDaysGte180AorS: true
  directNestedSuiteGte1: false
  depth2OnlyReachableGte1: false
  overallGradeS: false
  apexPromotionPrSigned: false
  crossOrgVerifier: null
  systemWideCap: null
trustMagnitudeInputHash: 848d74165305557c250a81ef7bdaa739c61a32f9474a7823d247db12b83549d7
verification:
  firstEvidenceAt: '2026-06-19T17:07:36Z'
---

## Overview

To Issues decomposes a plan into vertical slices — thin cuts through every integration layer (schema, API, UI, tests) that are each independently demoable or verifiable. It explicitly rejects horizontal slicing (doing all of one layer before the next).

Each proposed issue is classified as HITL (requires human judgment, design decisions, or external access) or AFK (can be implemented and merged autonomously). The agent presents the breakdown for user review, iterates on granularity and dependency correctness, then publishes issues in dependency order so blocking tickets receive real identifiers before blocked tickets reference them.

## Origin

First published by @mattpocock (Matt Pocock, Total TypeScript). This is the origin implementation for the `vertical-slice-planning` skill bucket.

## Installation

This skill is included in the Matt Pocock skills suite. It is highly recommended to install the full suite to enable cross-skill context sharing.

```bash
npx skills@latest add mattpocock/skills
```

No additional setup required beyond the main suite installation.
