---
id: garrytan/cso
name: CSO
contributor: garrytan
origin: true
genericSkillRef: security-audit
status: named
title: Chief Security Officer Mode
catalogRef: garrytan-cso
level: 4★
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
updatedAt: '2026-06-14'
suiteRef: garrytan/garrytan
evidence:
- class: B
  source: https://github.com/garrytan/gstack/blob/main/cso/SKILL.md
  evaluator: mbtiongson1
  date: '2026-06-03'
  notes: Public SKILL.md in the garrytan/gstack suite repo (verified live). Infrastructure-first
    security audit focusing on secrets archaeology, dependency supply chain, and CI/CD
    security. Includes OWASP Top 10, STRIDE… (backfilled — class-to-type migration) (CLI gap: commits+contributors not writable via gaia dev evidence)
  type: repo
  commits: 323
  contributors: 9
  trustNumber: 70.0
  grade: B
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
trustMagnitudeInputHash: 785ad467878c05429ff87435ea15a0af0f7baa4b8027f16395e012bb1eb3c7b0
verification:
  firstEvidenceAt: '2026-06-03T05:51:31Z'
---

## Overview

The CSO skill provides an opinionated security posture focused on the entire supply chain and infrastructure. It goes beyond simple code scanning to include secrets detection, dependency analysis, and active threat modeling, maintaining a persistent history of audit trends.
