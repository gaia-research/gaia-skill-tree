---
id: garrytan/careful
name: Careful
contributor: garrytan
origin: false
genericSkillRef: guardrails
status: named
title: Gstack Careful — Conservative Execution Mode
catalogRef: garrytan-careful
level: 2★
description: Activates a conservative execution profile that pauses before irreversible
  actions, requests explicit confirmation for destructive operations, and logs all
  side effects.
links:
  github: https://github.com/garrytan/gstack/blob/main/careful/SKILL.md
tags:
- guardrails
- safety
- confirmation
createdAt: '2026-05-18'
updatedAt: '2026-06-19'
suiteRef: garrytan/gstack
evidence:
- class: B
  source: https://github.com/garrytan/gstack/blob/main/careful/SKILL.md
  evaluator: mbtiongson1
  date: '2026-06-03'
  notes: 'Public SKILL.md in the garrytan/gstack suite repo (verified live). Activates
    a conservative execution profile that pauses before irreversible actions, requests
    explicit confirmation for destructive operations, and… (backfilled — class-to-type
    migration) (CLI gap: commits+contributors not writable via gaia dev evidence)'
  type: repo
  commits: 323
  contributors: 9
  trustNumber: 70.0
  grade: B
- source: https://github.com/garrytan/gstack/issues/2039
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: peer-review
  class: A
  notes: Bug report for /careful
timeline:
- timestamp: '2026-06-03T05:51:30Z'
  action: evidence_added
  contributor: unknown
  details: Added B evidence from https://github.com/garrytan/gstack/blob/main/careful/SKILL.md
- timestamp: '2026-06-14T12:32:19Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/garrytan/gstack/blob/main/careful/SKILL.md
    as B (trustNumber: 70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:14Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T10:36:26Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- timestamp: '2026-06-19T12:40:26Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/garrytan/gstack/issues/2039 (type:
    peer-review)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T12:53:50Z'
  details: TM 36.0 -> 66.0, grade C -> B (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:37Z'
  details: TM 0.0 -> 66.0, grade ungraded -> B (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:37Z'
  details: TM 0.0 -> 66.0, grade ungraded -> B (direct edit -- CLI gap)
trustMagnitude: 66.0
overallTrustGrade: B
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
trustMagnitudeInputHash: acef969313b71606bc35269a9902f3a4763eba70997c96f08e24c7a39e2ae5a2
---

## Overview

Activates a conservative execution profile that pauses before irreversible actions, requests explicit confirmation for destructive operations, and logs all side effects.
