---
id: garrytan/review
name: Review
contributor: garrytan
origin: false
genericSkillRef: code-review-pipeline
status: named
title: Gstack Code Review
catalogRef: garrytan-review
level: 4★
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
updatedAt: '2026-06-20'
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
  date: '2026-06-20'
  type: github-stars-own
  trustNumber: 85.0
  grade: A
  notes: gstack suite repo — 110,930 GitHub stars; review is 1 of 42 named skills
    (verified 2026-06-20)
  stars: 110930
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
  firstEvidenceAt: '2026-06-03T05:51:35Z'
trustMagnitudeInputHash: d05461d6047b43d9575fb62202ae943bd850440376a3541a5f97193f31dc067e
---

## Overview

Gstack Code Review runs the full diff through a multi-layered review pipeline before any branch lands. A structured checklist covers SQL safety, LLM trust boundaries, and conditional side effects; specialist subagents handle testing, security, and performance in parallel; a final adversarial pass from both Claude and Codex surfaces issues that a single reviewer would miss.
