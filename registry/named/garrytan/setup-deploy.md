---
id: garrytan/setup-deploy
name: Setup Deploy
contributor: garrytan
origin: false
genericSkillRef: deployment-automation
status: named
title: Gstack Setup Deploy — Deployment Environment Init
catalogRef: garrytan-setup-deploy
level: 2★
description: Provisions the deployment environment by creating secrets, configuring
  environment variables, and running infrastructure-as-code init steps before the
  first deploy.
links:
  github: https://github.com/garrytan/gstack/blob/main/setup-deploy/SKILL.md
tags:
- deployment-automation
- setup
- infrastructure
createdAt: '2026-05-18'
updatedAt: '2026-06-14'
suiteRef: garrytan/gstack
evidence:
- class: B
  source: https://github.com/garrytan/gstack/blob/main/setup-deploy/SKILL.md
  evaluator: mbtiongson1
  date: '2026-06-03'
  notes: 'Public SKILL.md in the garrytan/gstack suite repo (verified live). Provisions
    the deployment environment by creating secrets, configuring environment variables,
    and running infrastructure-as-code init steps before… (backfilled — class-to-type
    migration) (CLI gap: commits+contributors not writable via gaia dev evidence)'
  type: repo
  commits: 323
  contributors: 9
  trustNumber: 70.0
  grade: B
timeline:
- timestamp: '2026-06-03T05:51:34Z'
  action: evidence_added
  contributor: unknown
  details: Added B evidence from https://github.com/garrytan/gstack/blob/main/setup-deploy/SKILL.md
- timestamp: '2026-06-14T12:32:26Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/garrytan/gstack/blob/main/setup-deploy/SKILL.md
    as B (trustNumber: 70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:15Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T10:36:26Z'
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
  firstEvidenceAt: '2026-06-03T05:51:34Z'
trustMagnitudeInputHash: 590e36924c0d8903168062c538a7e0e2d545e896db5744150503a4010bde3107
---

## Overview

Provisions the deployment environment by creating secrets, configuring environment variables, and running infrastructure-as-code init steps before the first deploy.
