---
id: garrytan/document-generate
name: Document Generate
contributor: garrytan
origin: true
genericSkillRef: document-editing
status: named
title: Diataxis Doc Generator
catalogRef: garrytan-document-generate
level: 4★
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
updatedAt: '2026-06-14'
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
trustMagnitudeInputHash: bf8b1376d2e28e35115798fc3d8c263aee391cc9bfd81b068b5f5bd83067ec24
---

## Overview

Diataxis Doc Generator researches code thoroughly before writing a single word, then produces structured documentation in four Diataxis quadrants: tutorials for learning, how-to guides for tasks, reference for lookup, and explanation for understanding. Output is calibrated to the reader's knowledge level and intent rather than defaulting to a single monolithic README.
