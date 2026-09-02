---
id: mbtiongson1/gaia-integrity
name: Gaia Integrity
contributor: mbtiongson1
origin: false
genericSkillRef: registry-curation
status: named
level: 1★
description: Validates the structural integrity of the Gaia registry — checking schema
  compliance, detecting duplicate IDs, verifying cross-references, and reporting any
  inconsistencies that would break build or generation.
createdAt: '2026-05-27'
updatedAt: '2026-08-30'
title: The Schema Sentinel
links:
  github: https://github.com/gaia-research/gaia-skill-tree/blob/main/.agents/skills/gaia-integrity/SKILL.md
tags:
- registry-curation
- integrity
- validation
- schema
timeline:
- timestamp: '2026-05-26T16:37:00Z'
  action: add
  contributor: mbtiongson1
  details: Added named skill mbtiongson1/gaia-integrity
- timestamp: '2026-06-01T15:13:08Z'
  action: demote
  contributor: unknown
  details: Calibrated level from 3★ to 2★
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:19Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:38Z'
  details: TM 0.0 -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:42Z'
  details: TM 0.0 -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- timestamp: '2026-06-20T06:31:34Z'
  action: demote
  contributor: mbtiongson1
  details: Level updated from 2★ to 1★ per G7 final rankings calibration.
- timestamp: '2026-08-29T17:15:55Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM 0.0 -> 0.0, grade ungraded -> ungraded (gaia dev calibrate-trust-magnitude;
    Issue #1600)'
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
trustMagnitudeInputHash: 345367cc1e231782d259170040976560761f75ff2e5e6eae68c0f6a93b36d9be
---

## Overview

Validates the structural integrity of the Gaia registry: runs `gaia validate`, checks schema compliance, detects duplicate IDs, verifies cross-references between `registry/nodes/` and `registry/skills/`, and surfaces orphan documentation. Includes safe-archival of stale `.md` files via timestamped `registry/archive/`. Run before submitting a PR or after large registry shifts.
