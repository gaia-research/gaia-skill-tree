---
id: garrytan/gstack-upgrade
name: GStack Upgrade
contributor: garrytan
origin: false
genericSkillRef: workspace-automation
status: named
title: Gstack Upgrade — Workspace Dependency Upgrade
catalogRef: garrytan-gstack-upgrade
level: 2★
description: Scans the workspace for outdated dependencies, runs upgrades within semver-compatible
  bounds, re-runs tests, and commits a clean dependency bump PR.
links:
  github: https://github.com/garrytan/gstack/blob/main/gstack-upgrade/SKILL.md
tags:
- workspace-automation
- dependencies
- maintenance
createdAt: '2026-05-18'
updatedAt: '2026-06-14'
suiteRef: garrytan/gstack
evidence:
- class: B
  source: https://github.com/garrytan/gstack/blob/main/gstack-upgrade/SKILL.md
  evaluator: mbtiongson1
  date: '2026-06-03'
  notes: 'Public SKILL.md in the garrytan/gstack suite repo (verified live). Scans
    the workspace for outdated dependencies, runs upgrades within semver-compatible
    bounds, re-runs tests, and commits a clean dependency bump PR. (backfilled — class-to-type
    migration) (CLI gap: commits+contributors not writable via gaia dev evidence)'
  type: repo
  commits: 323
  contributors: 9
  trustNumber: 70.0
  grade: B
timeline:
- timestamp: '2026-06-03T05:51:33Z'
  action: evidence_added
  contributor: unknown
  details: Added B evidence from https://github.com/garrytan/gstack/blob/main/gstack-upgrade/SKILL.md
- timestamp: '2026-06-14T12:32:21Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/garrytan/gstack/blob/main/gstack-upgrade/SKILL.md
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
  firstEvidenceAt: '2026-06-03T05:51:33Z'
trustMagnitudeInputHash: ad3f44c4a0039a5afdd714b86f44ce6383fdcfbbf85e0154029f5d441ce8a0c3
---

## Overview

Scans the workspace for outdated dependencies, runs upgrades within semver-compatible bounds, re-runs tests, and commits a clean dependency bump PR.
