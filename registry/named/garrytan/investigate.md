---
id: garrytan/investigate
name: Investigate
contributor: garrytan
origin: true
genericSkillRef: systematic-debugging
status: named
title: Gstack Investigate
catalogRef: garrytan-investigate
level: 4★
description: 'Systematic root-cause debugging enforcing an Iron Law — no fix without
  first identifying root cause — guiding through four phases: investigation, analysis,
  hypothesis formation, and verified implementation with evidence gathering and pattern
  matching before any code changes.'
links:
  github: https://github.com/garrytan/gstack/blob/main/investigate/SKILL.md
tags:
- debugging
- root-cause
- investigation
- systematic
createdAt: '2026-05-18'
updatedAt: '2026-06-20'
suiteRef: garrytan/gstack
timeline:
- timestamp: '2026-06-02T23:33:00Z'
  action: rank_up
  contributor: unknown
  details: Origin status set to true.
- timestamp: '2026-06-03T05:51:33Z'
  action: evidence_added
  contributor: unknown
  details: Added B evidence from https://github.com/garrytan/gstack/blob/main/investigate/SKILL.md
- timestamp: '2026-06-14T12:32:22Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/garrytan/gstack/blob/main/investigate/SKILL.md
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
- timestamp: '2026-06-19T16:47:41Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/garrytan/gstack (type: github-stars-own)'
- timestamp: '2026-06-19T16:47:41Z'
  action: evidence_graded
  contributor: unknown
  details: 'Graded evidence from https://github.com/garrytan/gstack as A (trustNumber:
    85.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T17:13:01Z'
  details: TM 36.0 -> 63.73, grade C -> B (direct edit -- CLI gap)
evidence:
- class: B
  source: https://github.com/garrytan/gstack/blob/main/investigate/SKILL.md
  evaluator: mbtiongson1
  date: '2026-06-03'
  notes: 'Public SKILL.md in the garrytan/gstack suite repo (verified live). Systematic
    root-cause debugging enforcing an Iron Law — no fix without first identifying
    root cause — guiding through four phases: investigation,… (backfilled — class-to-type
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
  grade: A
  notes: gstack suite repo — 110,930 GitHub stars; investigate is 1 of 42 named skills
    (verified 2026-06-20)
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
  firstEvidenceAt: '2026-06-03T05:51:33Z'
trustMagnitudeInputHash: 3197d16ad889cab97d211ef4fc622f420478b7435caa0a0fa12025f85f5e8d31
---

## Overview

Gstack Investigate enforces the Iron Law: no fix is permitted without first proving root cause. It guides the agent through four structured phases — systematic evidence gathering, pattern matching and analysis, hypothesis generation and testing, and only then verified implementation — eliminating the class of bugs created by "fixing" symptoms rather than causes.
