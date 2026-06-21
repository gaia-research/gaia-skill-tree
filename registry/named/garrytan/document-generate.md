---
id: garrytan/document-generate
name: Document Generate
contributor: garrytan
origin: true
genericSkillRef: document-editing
status: named
title: Diataxis Doc Generator
catalogRef: garrytan-document-generate
level: 3★
description: Generates structured documentation using the Diataxis framework — tutorials,
  how-to guides, reference materials, and explanations — by thoroughly researching
  the codebase before writing, tailored to the needs of different reader types.
links:
  github: https://github.com/garrytan/gstack/blob/main/document-generate/SKILL.md
tags:
- documentation
- diataxis
- tutorials
- reference-docs
createdAt: '2026-05-18'
updatedAt: '2026-06-21'
suiteRef: garrytan/gstack
timeline:
- timestamp: '2026-06-02T01:43:00Z'
  action: rank_up
  contributor: unknown
  details: Origin status set to true (highest-rated in document-editing bucket).
- timestamp: '2026-06-03T05:51:27Z'
  action: evidence_added
  contributor: unknown
  details: Added B evidence from https://github.com/garrytan/gstack/blob/main/document-generate/SKILL.md
- timestamp: '2026-06-14T12:32:21Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/garrytan/gstack/blob/main/document-generate/SKILL.md
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
- timestamp: '2026-06-19T16:47:40Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/garrytan/gstack (type: github-stars-own)'
- timestamp: '2026-06-19T16:47:40Z'
  action: evidence_graded
  contributor: unknown
  details: 'Graded evidence from https://github.com/garrytan/gstack as A (trustNumber:
    85.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T17:13:01Z'
  details: TM 36.0 -> 63.73, grade C -> B (direct edit -- CLI gap)
- timestamp: '2026-06-20T06:31:22Z'
  action: demote
  contributor: mbtiongson1
  details: Level updated from 4★ to 3★ per G7 final rankings calibration.
evidence:
- class: B
  source: https://github.com/garrytan/gstack/blob/main/document-generate/SKILL.md
  evaluator: mbtiongson1
  date: '2026-06-03'
  notes: 'Public SKILL.md in the garrytan/gstack suite repo (verified live). Generates
    structured documentation using the Diataxis framework — tutorials, how-to guides,
    reference materials, and explanations — by thoroughly… (backfilled — class-to-type
    migration) (CLI gap: commits+contributors not writable via gaia dev evidence)'
  type: repo
  commits: 323
  contributors: 9
  trustNumber: 70.0
  grade: B
- source: https://github.com/garrytan/gstack
  evaluator: unknown
  date: '2026-06-20'
  type: github-stars-own
  trustNumber: 85.0
  grade: C
  notes: gstack suite repo — 110,930 GitHub stars; document-generate is 1 of 42 named
    skills (verified 2026-06-20)
  stars: 110930
  skillCountInRepo: 42
  sourceStartedAt: '2024-01-01'
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
  firstEvidenceAt: '2026-06-03T05:51:27Z'
trustMagnitudeInputHash: 9a183ef2d178af58b29d15dddffe7a618a3bfa827b6e3594f4aa80c48f6e428c
---

## Overview

Diataxis Doc Generator researches code thoroughly before writing a single word, then produces structured documentation in four Diataxis quadrants: tutorials for learning, how-to guides for tasks, reference for lookup, and explanation for understanding. Output is calibrated to the reader's knowledge level and intent rather than defaulting to a single monolithic README.
