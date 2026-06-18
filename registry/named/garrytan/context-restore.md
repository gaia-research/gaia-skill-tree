---
id: garrytan/context-restore
name: Context Restore
contributor: garrytan
origin: false
genericSkillRef: context-compression
status: named
title: Gstack Context Restore — Session State Recovery
catalogRef: garrytan-context-restore
level: 2★
description: Reads a saved context snapshot and reconstructs a warm session state,
  surfacing the last decision point and pending tasks so work can resume without recap.
links:
  github: https://github.com/garrytan/gstack/blob/main/context-restore/SKILL.md
tags:
- context-compression
- session
- continuity
createdAt: '2026-05-18'
updatedAt: '2026-06-14'
suiteRef: garrytan/gstack
evidence:
- class: B
  source: https://github.com/garrytan/gstack/blob/main/context-restore/SKILL.md
  evaluator: mbtiongson1
  date: '2026-06-03'
  notes: Public SKILL.md in the garrytan/gstack suite repo (verified live). Reads
    a saved context snapshot and reconstructs a warm session state, surfacing the
    last decision point and pending tasks so work can resume… (backfilled — class-to-type
    migration)
  type: repo
  trustNumber: 70.0
  grade: B
timeline:
- timestamp: '2026-06-03T05:51:31Z'
  action: evidence_added
  contributor: unknown
  details: Added B evidence from https://github.com/garrytan/gstack/blob/main/context-restore/SKILL.md
- timestamp: '2026-06-14T12:32:19Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/garrytan/gstack/blob/main/context-restore/SKILL.md
    as B (trustNumber: 70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:14Z'
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
trustMagnitudeInputHash: 3853d4dc897b7a750348e721e768d51a372fc00f2dbdc84be0d0f6febcbc8366
verification:
  firstEvidenceAt: '2026-06-03T05:51:31Z'
---

## Overview

Reads a saved context snapshot and reconstructs a warm session state, surfacing the last decision point and pending tasks so work can resume without recap.
