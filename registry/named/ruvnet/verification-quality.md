---
id: ruvnet/verification-quality
name: Verification Quality
contributor: ruvnet
origin: false
genericSkillRef: verification-before-completion
status: named
title: The Quality Sentinel
catalogRef: ruvnet-verification-quality
level: 2★
description: Implements structured pre-completion verification checklists ensuring
  quality gates are met before task finalization.
links:
  github: https://github.com/ruvnet/ruflo
tags:
- verification
- quality
- checklists
- quality-gates
- completion
createdAt: '2026-05-19'
updatedAt: '2026-06-14'
suiteRef: ruvnet/ruflo
evidence:
- class: B
  source: https://github.com/ruvnet/ruflo
  evaluator: mbtiongson1
  date: '2026-06-10'
  notes: Part of the Ruflo orchestration platform (public repo); pre-completion quality
    gates documented in the suite. (backfilled — class-to-type migration)
  type: repo
  trustNumber: 70.0
  grade: B
  commits: 6899
  contributors: 32
timeline:
- timestamp: '2026-06-10T05:38:18Z'
  action: evidence_added
  contributor: unknown
  details: Added B evidence from https://github.com/ruvnet/ruflo
- timestamp: '2026-06-14T12:33:02Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/ruvnet/ruflo as B (trustNumber:
    70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:21Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T11:07:58Z'
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
  firstEvidenceAt: '2026-06-10T05:38:18Z'
trustMagnitudeInputHash: 8d6db844a06c7f63f568d505bc3446c22ec1fecf315df8bfa405ee4b6f44e4f5
---

## Overview

Verification Quality enforces structured quality gates at task completion boundaries within Ruflo agent workflows. Rather than allowing agents to finalize tasks without review, it injects pre-completion checklist evaluation, automated test coverage verification, and documentation completeness checks. Only tasks that pass all configured gates are allowed to proceed to final output.

## Key Capabilities

- **Pre-completion checklists**: configurable verification steps that must pass before task finalization
- **Automated quality gates**: programmatic enforcement of quality standards at completion boundaries
- **Test coverage verification**: ensures specified coverage thresholds are met before sign-off
- **Documentation checks**: validates that required documentation is present and complete

## Origin

Published by @ruvnet as a variant implementation for the `verification-before-completion` skill bucket.

Sourced from the Ruflo platform (ruvnet/ruflo, 34k+ stars).
