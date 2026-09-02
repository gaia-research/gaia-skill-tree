---
id: garrytan/cso
name: CSO
contributor: garrytan
origin: true
genericSkillRef: security-audit
status: named
title: Chief Security Officer Mode
catalogRef: garrytan-cso
level: 3★
description: Infrastructure-first security audit focusing on secrets archaeology,
  dependency supply chain, and CI/CD security. Includes OWASP Top 10, STRIDE threat
  modeling, and active verification with daily (zero-noise) and monthly (comprehensive)
  scan modes.
links:
  github: https://github.com/garrytan/gstack/blob/main/cso/SKILL.md
tags:
- security
- infrastructure
- audit
- threat-modeling
- cso
createdAt: '2026-05-12'
updatedAt: '2026-08-30'
suiteRef: garrytan/garrytan
evidence:
- class: B
  source: https://github.com/garrytan/gstack/blob/main/cso/SKILL.md
  evaluator: mbtiongson1
  date: '2026-06-03'
  notes: 'Public SKILL.md in the garrytan/gstack suite repo (verified live). Infrastructure-first
    security audit focusing on secrets archaeology, dependency supply chain, and CI/CD
    security. Includes OWASP Top 10, STRIDE… (backfilled — class-to-type migration)
    (CLI gap: commits+contributors not writable via gaia dev evidence)'
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
  notes: gstack suite repo — 110,930 GitHub stars; cso is 1 of 42 named skills (verified
    2026-06-20)
  stars: 130700
  skillCountInRepo: 42
  sourceStartedAt: '2024-01-01'
timeline:
- timestamp: '2026-06-03T05:51:31Z'
  action: evidence_added
  contributor: unknown
  details: Added B evidence from https://github.com/garrytan/gstack/blob/main/cso/SKILL.md
- timestamp: '2026-06-14T12:32:20Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/garrytan/gstack/blob/main/cso/SKILL.md
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
- timestamp: '2026-06-19T16:47:24Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/garrytan/gstack (type: github-stars-own)'
- timestamp: '2026-06-19T16:47:24Z'
  action: evidence_graded
  contributor: unknown
  details: 'Graded evidence from https://github.com/garrytan/gstack as A (trustNumber:
    85.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T17:13:00Z'
  details: TM 36.0 -> 63.73, grade C -> B (direct edit -- CLI gap)
- timestamp: '2026-06-20T06:31:21Z'
  action: demote
  contributor: mbtiongson1
  details: Level updated from 4★ to 3★ per G7 final rankings calibration.
- timestamp: '2026-08-25T13:17:09Z'
  action: recalibrate_trust_magnitude
  contributor: unknown
  details: 'TM 63.73 -> 67.4, grade B -> B (gaia dev calibrate-trust-magnitude; Issue
    #1600)'
- timestamp: '2026-08-29T17:15:45Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM 67.4 -> 286.0, grade B -> A (gaia dev calibrate-trust-magnitude; Issue
    #1600)'
trustMagnitude: 286.0
overallTrustGrade: A
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
  firstEvidenceAt: '2026-06-03T05:51:31Z'
trustMagnitudeInputHash: 5ddd6ebebe5ab9264c9cba36429ad7a3e00c4ad46fb0bb4709cff6e7f57492d0
---

## Overview

The CSO skill provides an opinionated security posture focused on the entire supply chain and infrastructure. It goes beyond simple code scanning to include secrets detection, dependency analysis, and active threat modeling, maintaining a persistent history of audit trends.
