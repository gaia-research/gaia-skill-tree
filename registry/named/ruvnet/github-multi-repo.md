---
id: ruvnet/github-multi-repo
name: GitHub Multi-Repo
contributor: ruvnet
origin: true
genericSkillRef: multi-repo-coordination
status: named
title: The Repository Conductor
catalogRef: ruvnet-github-multi-repo
level: 2★
description: Manages synchronized operations across multiple GitHub repositories including
  cross-repo PRs, dependency tracking, and bulk workflow automation.
links:
  github: https://github.com/ruvnet/ruflo
tags:
- github
- multi-repo
- cross-repo
- dependency-tracking
- bulk-operations
createdAt: '2026-05-19'
updatedAt: '2026-06-14'
suiteRef: ruvnet/github-suite
evidence:
- class: B
  source: https://github.com/ruvnet/ruflo
  evaluator: mbtiongson1
  date: '2026-05-19'
  notes: Ruflo orchestration platform — 34k+ GitHub stars. (backfilled — class-to-type
    migration)
  type: repo
  trustNumber: 70.0
  grade: B
  commits: 6899
  contributors: 32
timeline:
- timestamp: '2026-06-14T12:32:56Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/ruvnet/ruflo as B (trustNumber:
    70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:20Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T11:07:58Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:39Z'
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
trustMagnitudeInputHash: 5ce3e6dd80720f11e7031bc6a7033d3decf1abe93dbea92633b788756344a09f
---

## Overview

GitHub Multi-Repo provides coordination across multiple repositories simultaneously. It handles cross-repository pull requests, dependency version tracking, bulk issue operations, and coordinated workflow triggers across repository sets. Useful for monorepo migrations and microservice fleet management.

## Key Capabilities

- **Cross-repo PR management**: coordinated pull requests spanning multiple repositories
- **Dependency tracking**: version synchronization and dependency graph management across repos
- **Bulk workflow triggers**: coordinated GitHub Actions execution across repository sets
- **Coordinated tagging and releases**: synchronized version tagging and release publishing

## Origin

First published by @ruvnet as part of the Ruflo orchestration platform. This is the origin implementation for the `multi-repo-coordination` skill bucket.

Sourced from the Ruflo platform (ruvnet/ruflo, 34k+ stars).
