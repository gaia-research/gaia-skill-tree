---
id: garrytan/qa
name: QA
contributor: garrytan
origin: false
genericSkillRef: e2e-testing
status: named
title: Gstack QA
catalogRef: garrytan-qa
level: 3★
description: Browser-driven web application testing that explores pages as a real
  user, documents bugs with annotated screenshots, fixes issues with atomic commits
  and re-verification, and produces structured reports with before/after evidence
  and health scores showing quality improvement.
links:
  github: https://github.com/garrytan/gstack/blob/main/qa/SKILL.md
tags:
- qa
- browser-testing
- bug-fixing
- e2e
createdAt: '2026-05-18'
updatedAt: '2026-06-21'
suiteRef: garrytan/gstack
evidence:
- class: B
  source: https://github.com/garrytan/gstack/blob/main/qa/SKILL.md
  evaluator: mbtiongson1
  date: '2026-06-03'
  notes: 'Public SKILL.md in the garrytan/gstack suite repo (verified live). Browser-driven
    web application testing that explores pages as a real user, documents bugs with
    annotated screenshots, fixes issues with atomic… (backfilled — class-to-type migration)
    (CLI gap: commits+contributors not writable via gaia dev evidence)'
  type: repo
  commits: 323
  contributors: 9
  trustNumber: 70.0
  grade: B
- source: https://github.com/garrytan/gstack
  evaluator: unknown
  updatedAt: '2026-06-28'
  date: '2026-06-20'
  type: github-stars-own
  trustNumber: 85.0
  grade: C
  notes: gstack suite repo — 110,930 GitHub stars; qa is 1 of 42 named skills (verified
    2026-06-20)
  stars: 117106
  skillCountInRepo: 42
  sourceStartedAt: '2024-01-01'
timeline:
- timestamp: '2026-06-03T05:51:36Z'
  action: evidence_added
  contributor: unknown
  details: Added B evidence from https://github.com/garrytan/gstack/blob/main/qa/SKILL.md
- timestamp: '2026-06-14T12:32:25Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/garrytan/gstack/blob/main/qa/SKILL.md
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
- timestamp: '2026-06-19T16:47:59Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/garrytan/gstack (type: github-stars-own)'
- timestamp: '2026-06-19T16:47:59Z'
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
trustMagnitude: 63.73
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
  firstEvidenceAt: '2026-06-03T05:51:36Z'
trustMagnitudeInputHash: 16c58e0915bb3377d6fe7b76b2809103af83e02de4692c72a948868f55b737c5
---

## Overview

Gstack QA drives a real browser through the application the way a tester would, documenting every defect with a screenshot and severity rating. Discovered bugs are fixed with atomic commits and immediately re-verified in the browser before reporting. The final output is a structured health-score report showing before/after evidence for each fix.
