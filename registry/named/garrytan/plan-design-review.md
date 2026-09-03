---
id: garrytan/plan-design-review
name: Plan Design Review
contributor: garrytan
origin: false
genericSkillRef: ux-audit
status: named
title: Design Plan Review
catalogRef: garrytan-plan-design-review
level: 3★
description: Interactive, designer-led audit of UI/UX plans rating seven dimensions
  — information architecture, interaction states, user journey, AI slop risk, design
  system alignment, responsive/accessibility, and unresolved decisions — before implementation
  begins, with optional visual mockup generation.
links:
  github: https://github.com/garrytan/gstack/blob/main/plan-design-review/SKILL.md
tags:
- ux
- design-audit
- plan-review
- ui-ux
createdAt: '2026-05-18'
updatedAt: '2026-08-30'
suiteRef: garrytan/gstack
evidence:
- class: B
  source: https://github.com/garrytan/gstack/blob/main/plan-design-review/SKILL.md
  evaluator: mbtiongson1
  date: '2026-06-03'
  notes: 'Public SKILL.md in the garrytan/gstack suite repo (verified live). Interactive,
    designer-led audit of UI/UX plans rating seven dimensions — information architecture,
    interaction states, user journey, AI slop risk,… (backfilled — class-to-type migration)
    (CLI gap: commits+contributors not writable via gaia dev evidence)'
  type: repo
  commits: 323
  contributors: 9
  trustNumber: 70.0
  grade: B
- source: https://github.com/garrytan/gstack
  evaluator: unknown
  updatedAt: '2026-09-01'
  date: '2026-06-20'
  type: github-stars-own
  trustNumber: 85.0
  grade: C
  notes: gstack suite repo — 110,930 GitHub stars; plan-design-review is 1 of 42 named
    skills (verified 2026-06-20)
  stars: 130700
  skillCountInRepo: 42
  sourceStartedAt: '2024-01-01'
timeline:
- timestamp: '2026-06-03T05:51:32Z'
  action: evidence_added
  contributor: unknown
  details: Added B evidence from https://github.com/garrytan/gstack/blob/main/plan-design-review/SKILL.md
- timestamp: '2026-06-14T12:32:24Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/garrytan/gstack/blob/main/plan-design-review/SKILL.md
    as B (trustNumber: 70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:15Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T10:36:26Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:37Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:38Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- timestamp: '2026-06-19T16:47:56Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/garrytan/gstack (type: github-stars-own)'
- timestamp: '2026-06-19T16:47:56Z'
  action: evidence_graded
  contributor: unknown
  details: 'Graded evidence from https://github.com/garrytan/gstack as A (trustNumber:
    85.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T17:13:01Z'
  details: TM 36.0 -> 63.73, grade C -> B (direct edit -- CLI gap)
- timestamp: '2026-06-20T06:31:23Z'
  action: demote
  contributor: mbtiongson1
  details: Level updated from 4★ to 3★ per G7 final rankings calibration.
- timestamp: '2026-08-25T13:17:09Z'
  action: recalibrate_trust_magnitude
  contributor: unknown
  details: 'TM 63.73 -> 67.4, grade B -> B (gaia dev calibrate-trust-magnitude; Issue
    #1600)'
- timestamp: '2026-08-29T17:15:47Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM 67.4 -> 50.0, grade B -> B (gaia dev calibrate-trust-magnitude; Issue
    #1600)'
trustMagnitude: 50.0
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
verification:
  firstEvidenceAt: '2026-06-03T05:51:32Z'
trustMagnitudeInputHash: 708b600ab59cfc429d4d4847e7ea5b628b7d53688807598ebaa123a769231216
---

## Overview

Design Plan Review applies a seven-dimension design lens to a plan before any implementation begins. It rates information architecture, interaction states, user journey mapping, AI slop risk, design system alignment, responsive/accessibility coverage, and open decisions — then collaboratively refines the plan and generates visual mockups where helpful.
