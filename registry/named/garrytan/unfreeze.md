---
id: garrytan/unfreeze
name: Unfreeze
contributor: garrytan
origin: false
genericSkillRef: guardrails
status: named
title: Gstack Unfreeze — Change Freeze Lift
catalogRef: garrytan-unfreeze
level: 2★
description: Clears the active change-freeze flag and restores normal merge permissions,
  logging the unfreeze event with a timestamp and justification.
links:
  github: https://github.com/garrytan/gstack/blob/main/unfreeze/SKILL.md
tags:
- guardrails
- freeze
- release-management
createdAt: '2026-05-18'
updatedAt: '2026-06-14'
suiteRef: garrytan/gstack
evidence:
- class: B
  source: https://github.com/garrytan/gstack/blob/main/unfreeze/SKILL.md
  evaluator: mbtiongson1
  date: '2026-06-03'
  notes: 'Public SKILL.md in the garrytan/gstack suite repo (verified live). Clears
    the active change-freeze flag and restores normal merge permissions, logging the
    unfreeze event with a timestamp and justification. (backfilled — class-to-type
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
  details: Added B evidence from https://github.com/garrytan/gstack/blob/main/unfreeze/SKILL.md
- timestamp: '2026-06-14T12:32:27Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/garrytan/gstack/blob/main/unfreeze/SKILL.md
    as B (trustNumber: 70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:16Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T10:36:26Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
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
verification:
  firstEvidenceAt: '2026-06-03T05:51:30Z'
---

## Overview

Clears the active change-freeze flag and restores normal merge permissions, logging the unfreeze event with a timestamp and justification.
