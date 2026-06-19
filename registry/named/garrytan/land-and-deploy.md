---
id: garrytan/land-and-deploy
name: Land and Deploy
contributor: garrytan
origin: false
genericSkillRef: deployment-automation
status: named
title: Land and Deploy
catalogRef: garrytan-land-and-deploy
level: 4★
description: Automates the final production shipping stages — merging a PR, monitoring
  CI/deploy completion, and verifying live site health through canary checks — picking
  up where /ship leaves off with safety gates at each step to prevent broken deployments
  reaching users.
links:
  github: https://github.com/garrytan/gstack/blob/main/land-and-deploy/SKILL.md
tags:
- deployment
- production
- merge
- canary
createdAt: '2026-05-18'
updatedAt: '2026-06-14'
suiteRef: garrytan/gstack
evidence:
- class: B
  source: https://github.com/garrytan/gstack/blob/main/land-and-deploy/SKILL.md
  evaluator: mbtiongson1
  date: '2026-06-03'
  notes: 'Public SKILL.md in the garrytan/gstack suite repo (verified live). Automates
    the final production shipping stages — merging a PR, monitoring CI/deploy completion,
    and verifying live site health through canary… (backfilled — class-to-type migration)
    (CLI gap: commits+contributors not writable via gaia dev evidence)'
  type: repo
  commits: 323
  contributors: 9
  trustNumber: 70.0
  grade: B
timeline:
- timestamp: '2026-06-03T05:51:34Z'
  action: evidence_added
  contributor: unknown
  details: Added B evidence from https://github.com/garrytan/gstack/blob/main/land-and-deploy/SKILL.md
- timestamp: '2026-06-14T12:32:22Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/garrytan/gstack/blob/main/land-and-deploy/SKILL.md
    as B (trustNumber: 70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:15Z'
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
  firstEvidenceAt: '2026-06-03T05:51:34Z'
---

## Overview

Land and Deploy handles the production handoff that /ship leaves at the PR stage. It makes the merge decision, monitors CI pipeline completion, waits for the deploy to propagate, then runs canary health checks against the live site — with safety gates throughout to halt and alert rather than silently shipping a broken build.
