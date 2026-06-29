---
id: garrytan/plan-devex-review
name: Plan DevEx Review
contributor: garrytan
origin: false
genericSkillRef: ux-audit
status: named
title: Developer Experience Review
catalogRef: garrytan-plan-devex-review
level: 3★
description: Interactive multi-pass DX review for developer-facing products — APIs,
  CLIs, SDKs, and libraries — scoring eight UX dimensions from onboarding to error
  messaging via persona discovery and competitive benchmarking, producing an actionable
  improvement plan rather than just a score.
links:
  github: https://github.com/garrytan/gstack/blob/main/plan-devex-review/SKILL.md
tags:
- developer-experience
- dx
- api-ux
- onboarding
createdAt: '2026-05-18'
updatedAt: '2026-06-21'
suiteRef: garrytan/gstack
evidence:
- class: B
  source: https://github.com/garrytan/gstack/blob/main/plan-devex-review/SKILL.md
  evaluator: mbtiongson1
  date: '2026-06-03'
  notes: 'Public SKILL.md in the garrytan/gstack suite repo (verified live). Interactive
    multi-pass DX review for developer-facing products — APIs, CLIs, SDKs, and libraries
    — scoring eight UX dimensions from onboarding to… (backfilled — class-to-type
    migration) (CLI gap: commits+contributors not writable via gaia dev evidence)'
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
  notes: gstack suite repo — 110,930 GitHub stars; plan-devex-review is 1 of 42 named
    skills (verified 2026-06-20)
  stars: 117106
  skillCountInRepo: 42
  sourceStartedAt: '2024-01-01'
timeline:
- timestamp: '2026-06-03T05:51:32Z'
  action: evidence_added
  contributor: unknown
  details: Added B evidence from https://github.com/garrytan/gstack/blob/main/plan-devex-review/SKILL.md
- timestamp: '2026-06-14T12:32:24Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/garrytan/gstack/blob/main/plan-devex-review/SKILL.md
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
- timestamp: '2026-06-19T16:47:57Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/garrytan/gstack (type: github-stars-own)'
- timestamp: '2026-06-19T16:47:57Z'
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
  firstEvidenceAt: '2026-06-03T05:51:32Z'
trustMagnitudeInputHash: 8580d33277a7f70df855307ee67342509cdefd5d675f6230a7276d50a5823456
---

## Overview

Developer Experience Review applies structured UX thinking to developer-facing surfaces. Eight dimensions are scored — getting started, documentation quality, API ergonomics, error messages, debugging aids, SDK consistency, community health, and upgrade friction — using persona modeling and competitor benchmarking to produce concrete, prioritised improvements.
