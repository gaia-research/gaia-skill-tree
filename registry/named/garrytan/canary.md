---
id: garrytan/canary
name: Canary
contributor: garrytan
origin: false
genericSkillRef: detect-anomaly
status: named
title: Gstack Canary
catalogRef: garrytan-canary
level: 4★
description: Post-deployment monitoring that captures pre-release baseline screenshots,
  then continuously watches pages for console errors, performance regressions, and
  broken links — designed to surface failures within the first 10 minutes so problems
  are caught before they reach users at scale.
links:
  github: https://github.com/garrytan/gstack/blob/main/canary/SKILL.md
tags:
- monitoring
- post-deploy
- canary
- anomaly-detection
createdAt: '2026-05-18'
updatedAt: '2026-06-14'
suiteRef: garrytan/gstack
evidence:
- class: B
  source: https://github.com/garrytan/gstack/blob/main/canary/SKILL.md
  evaluator: mbtiongson1
  date: '2026-06-03'
  notes: 'Public SKILL.md in the garrytan/gstack suite repo (verified live). Post-deployment
    monitoring that captures pre-release baseline screenshots, then continuously watches
    pages for console errors, performance… (backfilled — class-to-type migration)
    (CLI gap: commits+contributors not writable via gaia dev evidence)'
  type: repo
  commits: 323
  contributors: 9
  trustNumber: 70.0
  grade: B
timeline:
- timestamp: '2026-06-03T05:51:29Z'
  action: evidence_added
  contributor: unknown
  details: Added B evidence from https://github.com/garrytan/gstack/blob/main/canary/SKILL.md
- timestamp: '2026-06-14T12:32:19Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/garrytan/gstack/blob/main/canary/SKILL.md
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
  firstEvidenceAt: '2026-06-03T05:51:29Z'
trustMagnitudeInputHash: dbae03c2f8ddac91196c952b467c3182b605813b96a50289044ed5dac829665b
---

## Overview

Gstack Canary establishes a visual and performance baseline before a deploy, then monitors the live application continuously in the critical window after release. It detects console errors, Core Web Vital regressions, and broken links, reporting anomalies within 10 minutes so a rollback decision can be made before traffic scales up.
