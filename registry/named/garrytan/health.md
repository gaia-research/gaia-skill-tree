---
id: garrytan/health
name: Health
contributor: garrytan
origin: false
genericSkillRef: automated-testing
status: named
title: Gstack Health — Automated Test Suite Runner
catalogRef: garrytan-health
level: 3★
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
updatedAt: '2026-06-14'
suiteRef: garrytan/gstack
evidence:
- class: B
  source: https://github.com/garrytan/gstack/blob/main/health/SKILL.md
  evaluator: mbtiongson1
  date: '2026-06-03'
  notes: Public SKILL.md in the garrytan/gstack suite repo (verified live). Executes
    the full automated test suite, collects pass/fail counts and coverage deltas,
    and surfaces any newly introduced failures with concise… (backfilled — class-to-type
    migration) (CLI gap: commits+contributors not writable via gaia dev evidence)
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
trustMagnitudeInputHash: f7cc8e7aee67b2a8c2b7d4bb78ba19680960eaba651053704c791efc7dadf773
verification:
  firstEvidenceAt: '2026-06-03T05:51:27Z'
---

## Overview

Executes the full automated test suite, collects pass/fail counts and coverage deltas, and surfaces any newly introduced failures with concise root-cause notes.
