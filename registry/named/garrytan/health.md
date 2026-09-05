---
id: garrytan/health
name: Health
contributor: garrytan
origin: false
genericSkillRef: automated-testing
status: named
title: Gstack Health — Automated Test Suite Runner
catalogRef: garrytan-health
level: 2★
description: Executes the full automated test suite, collects pass/fail counts and
  coverage deltas, and surfaces any newly introduced failures with concise root-cause
  notes.
links:
  github: https://github.com/garrytan/gstack/blob/main/health/SKILL.md
tags:
- automated-testing
- ci
- quality
createdAt: '2026-05-18'
updatedAt: '2026-08-30'
suiteRef: garrytan/gstack
evidence:
- class: B
  source: https://github.com/garrytan/gstack/blob/main/health/SKILL.md
  evaluator: mbtiongson1
  date: '2026-06-03'
  notes: 'Public SKILL.md in the garrytan/gstack suite repo (verified live). Executes
    the full automated test suite, collects pass/fail counts and coverage deltas,
    and surfaces any newly introduced failures with concise… (backfilled — class-to-type
    migration) (CLI gap: commits+contributors not writable via gaia dev evidence)'
  type: repo
  commits: 323
  contributors: 9
  trustNumber: 70.0
  grade: B
timeline:
- timestamp: '2026-06-03T05:51:27Z'
  action: evidence_added
  contributor: unknown
  details: Added B evidence from https://github.com/garrytan/gstack/blob/main/health/SKILL.md
- timestamp: '2026-06-14T12:32:22Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/garrytan/gstack/blob/main/health/SKILL.md
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
  timestamp: '2026-06-19T13:26:37Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- timestamp: '2026-06-20T06:31:22Z'
  action: demote
  contributor: mbtiongson1
  details: Level updated from 3★ to 2★ per G7 final rankings calibration.
- timestamp: '2026-08-29T17:15:46Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM 36.0 -> 36.0, grade C -> C (gaia dev calibrate-trust-magnitude; Issue
    #1600)'
trustMagnitude: 36.0
overallTrustGrade: C
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
  firstEvidenceAt: '2026-06-03T05:51:27Z'
trustMagnitudeInputHash: dbf7acbfc72cbdcaad5b6ebb5bf23201c81d853f0ccce52387b2a349a9ad5fd5
---

## Overview

Executes the full automated test suite, collects pass/fail counts and coverage deltas, and surfaces any newly introduced failures with concise root-cause notes.
