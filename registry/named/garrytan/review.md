---
id: garrytan/review
name: Review
contributor: garrytan
origin: false
genericSkillRef: code-review-pipeline
status: named
title: Gstack Code Review
catalogRef: garrytan-review
level: 3★
description: Pre-landing code review combining structured checklist analysis with
  specialist subagents covering testing, security, and performance — plus adversarial
  review from both Claude and Codex — to catch SQL safety issues, LLM trust boundary
  violations, conditional side effects, and structural problems before merging.
links:
  github: https://github.com/garrytan/gstack/blob/main/review/SKILL.md
tags:
- code-review
- security
- multi-agent
- adversarial-review
createdAt: '2026-05-18'
updatedAt: '2026-08-30'
suiteRef: garrytan/gstack
evidence:
- class: B
  source: https://github.com/garrytan/gstack/blob/main/review/SKILL.md
  evaluator: mbtiongson1
  date: '2026-06-03'
  notes: 'Public SKILL.md in the garrytan/gstack suite repo (verified live). Pre-landing
    code review combining structured checklist analysis with specialist subagents
    covering testing, security, and performance — plus… (backfilled — class-to-type
    migration) (CLI gap: commits+contributors not writable via gaia dev evidence)'
  type: repo
  commits: 323
  contributors: 9
  trustNumber: 70.0
  grade: B
- source: https://github.com/garrytan/gstack
  evaluator: unknown
  updatedAt: '2026-09-01'
  date: '2026-06-20'
  type: github-stars-own
  trustNumber: 85.0
  grade: C
  notes: gstack suite repo — 110,930 GitHub stars; review is 1 of 42 named skills
    (verified 2026-06-20)
  stars: 130700
  skillCountInRepo: 42
  sourceStartedAt: '2024-01-01'
timeline:
- timestamp: '2026-06-03T05:51:35Z'
  action: evidence_added
  contributor: unknown
  details: Added B evidence from https://github.com/garrytan/gstack/blob/main/review/SKILL.md
- timestamp: '2026-06-14T12:32:25Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/garrytan/gstack/blob/main/review/SKILL.md
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
- timestamp: '2026-06-19T16:48:00Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/garrytan/gstack (type: github-stars-own)'
- timestamp: '2026-06-19T16:48:00Z'
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
- timestamp: '2026-08-25T13:17:09Z'
  action: recalibrate_trust_magnitude
  contributor: unknown
  details: 'TM 63.73 -> 67.4, grade B -> B (gaia dev calibrate-trust-magnitude; Issue
    #1600)'
- timestamp: '2026-08-29T17:15:48Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM 67.4 -> 50.0, grade B -> B (gaia dev calibrate-trust-magnitude; Issue
    #1600)'
trustMagnitude: 50.0
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
  firstEvidenceAt: '2026-06-03T05:51:35Z'
trustMagnitudeInputHash: 1d1f145b63801df366380eb9be00f0a6db16e5738b4e64d7602ea83f68195207
---

## Overview

Gstack Code Review runs the full diff through a multi-layered review pipeline before any branch lands. A structured checklist covers SQL safety, LLM trust boundaries, and conditional side effects; specialist subagents handle testing, security, and performance in parallel; a final adversarial pass from both Claude and Codex surfaces issues that a single reviewer would miss.
