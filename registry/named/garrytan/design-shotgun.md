---
id: garrytan/design-shotgun
name: Design Shotgun
contributor: garrytan
origin: false
genericSkillRef: design-review
status: named
title: Design Shotgun
catalogRef: garrytan-design-shotgun
level: 3★
description: Rapid design exploration that generates multiple AI design variants,
  opens a comparison board for the user, collects structured feedback, and iterates
  until a preferred visual direction is reached.
links:
  github: https://github.com/garrytan/gstack/blob/main/design-shotgun/SKILL.md
tags:
- ui-ux
- design-exploration
- prototyping
- visual-qa
createdAt: '2026-05-12'
updatedAt: '2026-08-30'
suiteRef: garrytan/gstack
evidence:
- class: B
  source: https://github.com/garrytan/gstack/blob/main/design-shotgun/SKILL.md
  evaluator: mbtiongson1
  date: '2026-06-03'
  notes: 'Public SKILL.md in the garrytan/gstack suite repo (verified live). Rapid
    design exploration that generates multiple AI design variants, opens a comparison
    board for the user, collects structured feedback, and… (backfilled — class-to-type
    migration) (CLI gap: commits+contributors not writable via gaia dev evidence)'
  type: repo
  commits: 323
  contributors: 9
  trustNumber: 70.0
  grade: B
- source: https://github.com/garrytan/gstack
  evaluator: unknown
  updatedAt: '2026-08-01'
  date: '2026-06-20'
  type: github-stars-own
  trustNumber: 85.0
  grade: C
  notes: gstack suite repo — 110,930 GitHub stars; design-shotgun is 1 of 42 named
    skills (verified 2026-06-20)
  stars: 125610
  skillCountInRepo: 42
  sourceStartedAt: '2024-01-01'
timeline:
- timestamp: '2026-06-03T05:51:33Z'
  action: evidence_added
  contributor: unknown
  details: Added B evidence from https://github.com/garrytan/gstack/blob/main/design-shotgun/SKILL.md
- timestamp: '2026-06-14T12:32:20Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/garrytan/gstack/blob/main/design-shotgun/SKILL.md
    as B (trustNumber: 70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:14Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T10:36:26Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:37Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:37Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- timestamp: '2026-06-19T16:47:38Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/garrytan/gstack (type: github-stars-own)'
- timestamp: '2026-06-19T16:47:39Z'
  action: evidence_graded
  contributor: unknown
  details: 'Graded evidence from https://github.com/garrytan/gstack as A (trustNumber:
    85.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T17:13:01Z'
  details: TM 36.0 -> 63.73, grade C -> B (direct edit -- CLI gap)
- timestamp: '2026-06-20T06:31:21Z'
  action: demote
  contributor: mbtiongson1
  details: Level updated from 4★ to 3★ per G7 final rankings calibration.
- timestamp: '2026-08-25T13:17:09Z'
  action: recalibrate_trust_magnitude
  contributor: unknown
  details: 'TM 63.73 -> 67.4, grade B -> B (gaia dev calibrate-trust-magnitude; Issue
    #1600)'
- timestamp: '2026-08-29T17:15:46Z'
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
  firstEvidenceAt: '2026-06-03T05:51:33Z'
trustMagnitudeInputHash: 488671856a4a74d79cf129b3c12fb49d1cb57d12d65aab1fdb1860581b5c1768
---

## Overview

Design Shotgun is a specialized exploration tool that bypasses the linear design process by firing multiple aesthetic variants at once. It leverages a structured feedback loop to quickly narrow down user preferences for UI components and layouts.
