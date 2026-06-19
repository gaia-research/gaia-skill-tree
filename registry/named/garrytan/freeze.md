---
id: garrytan/freeze
name: Freeze
contributor: garrytan
origin: false
genericSkillRef: guardrails
status: named
title: Gstack Freeze — Change Freeze Enforcement
catalogRef: garrytan-freeze
level: 2★
description: Sets a change-freeze flag that blocks non-critical commits and PR merges
  until explicitly lifted, protecting release branches or post-incident windows.
links:
  github: https://github.com/garrytan/gstack/blob/main/freeze/SKILL.md
tags:
- guardrails
- freeze
- release-management
createdAt: '2026-05-18'
updatedAt: '2026-06-14'
suiteRef: garrytan/gstack
evidence:
- class: B
  source: https://github.com/garrytan/gstack/blob/main/freeze/SKILL.md
  evaluator: mbtiongson1
  date: '2026-06-03'
  notes: 'Public SKILL.md in the garrytan/gstack suite repo (verified live). Sets
    a change-freeze flag that blocks non-critical commits and PR merges until explicitly
    lifted, protecting release branches or post-incident… (backfilled — class-to-type
    migration) (CLI gap: commits+contributors not writable via gaia dev evidence)'
  type: repo
  commits: 323
  contributors: 9
  trustNumber: 70.0
  grade: B
timeline:
- timestamp: '2026-06-03T05:51:30Z'
  action: evidence_added
  contributor: unknown
  details: Added B evidence from https://github.com/garrytan/gstack/blob/main/freeze/SKILL.md
- timestamp: '2026-06-14T12:32:21Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/garrytan/gstack/blob/main/freeze/SKILL.md
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
  firstEvidenceAt: '2026-06-03T05:51:30Z'
trustMagnitudeInputHash: b21ee081b26f05409c5ef5962762130d88157d5a1d5edef73c750db686447bf9
---

## Overview

Sets a change-freeze flag that blocks non-critical commits and PR merges until explicitly lifted, protecting release branches or post-incident windows.
