---
id: mattpocock/to-tickets
name: To Tickets
contributor: mattpocock
origin: false
genericSkillRef: vertical-slice-planning
status: named
title: The Vertical Slicer
catalogRef: mattpocock-to-issues
level: 4★
description: Breaks a plan, spec, or PRD into independently-grabbable GitHub issues
  as tracer-bullet vertical slices that each cut through all integration layers end-to-end.
  Classifies each slice HITL or AFK, maps dependency chains, quizzes the user on granularity,
  and publishes structured issues with acceptance criteria in dependency order.
links:
  github: https://github.com/mattpocock/skills/blob/main/skills/engineering/to-tickets/SKILL.md
tags:
- vertical-slicing
- issue-decomposition
- tracer-bullet
- hitl
- afk
- acceptance-criteria
createdAt: '2026-04-30'
updatedAt: '2026-09-04'
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
  updatedAt: '2026-09-01'
  date: '2026-06-20'
  type: github-stars-own
  trustNumber: 88.0
  grade: C
  notes: mattpocock/skills suite — 137k GitHub stars; to-issues is part of this repo
  stars: 243413
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
- timestamp: '2026-08-05T06:27:10Z'
  action: note
  contributor: unknown
  details: Updated GitHub link to https://github.com/mattpocock/skills/blob/main/skills/engineering/to-tickets/SKILL.md
- timestamp: '2026-08-19T11:49:27Z'
  action: rename
  contributor: unknown
  details: Renamed named skill from mattpocock/to-issues to mattpocock/to-tickets
- timestamp: '2026-08-19T11:49:27Z'
  action: note
  contributor: unknown
  details: Updated GitHub link to https://github.com/mattpocock/skills/blob/main/skills/engineering/to-tickets/SKILL.md
- timestamp: '2026-08-29T17:15:54Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM 90.38 -> 306.13, grade B -> A (gaia dev calibrate-trust-magnitude;
    Issue #1600)'
- timestamp: '2026-09-02T15:11:40Z'
  action: rank_up
  contributor: unknown
  details: Calibrated level from 3★ to 4★
- timestamp: '2026-09-04T10:58:45Z'
  action: recalibrate_trust_magnitude
  contributor: unknown
  details: 'TM 306.13 -> 94.92, grade A -> B (gaia dev calibrate-trust-magnitude;
    Issue #1600)'
trustMagnitude: 94.92
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
trustMagnitudeInputHash: f60ba86f4827a9866a6f332f4250bb2650c817fcc63b6cef5ce4854da59f5e22
verification:
  firstEvidenceAt: '2026-06-19T17:07:36Z'
suiteRef: "mattpocock/skills"
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
