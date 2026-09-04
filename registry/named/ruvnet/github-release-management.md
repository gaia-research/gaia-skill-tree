---
id: ruvnet/github-release-management
name: GitHub Release Management
contributor: ruvnet
origin: false
role: variant
genericSkillRef: release-automation
status: named
title: The Release Gatekeeper
catalogRef: ruvnet-github-release-management
level: 1★
description: Automates GitHub release creation, changelog generation, semantic versioning,
  and release note publishing.
links:
  github: https://github.com/ruvnet/ruflo
tags:
- github
- release
- versioning
- changelog
- automation
createdAt: '2026-05-19'
updatedAt: '2026-08-30'
timeline:
- timestamp: '2026-06-02T23:48:18Z'
  action: demote
  contributor: unknown
  details: Calibrated level from 3★ to 1★
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:20Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:39Z'
  details: TM 0.0 -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:44Z'
  details: TM 0.0 -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- timestamp: '2026-08-29T17:15:58Z'
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
trustMagnitudeInputHash: e6be8759ddac3a07d45ea6d61e9ceea52de9b91c8e961034ea190669c3537017
suiteRef: "ruvnet/ruflo"
---

## Overview

GitHub Release Management handles the full release lifecycle: semantic version calculation from conventional commits, automated changelog generation, release branch management, tag creation, and GitHub Releases publishing with generated notes. Integrates with CI/CD for automated release triggers.

## Key Capabilities

- **Semantic versioning**: automatic version calculation from conventional commit history
- **Automated changelog**: generated release notes from commit messages and PR descriptions
- **Release branch management**: branching strategies for stable release isolation
- **GitHub Releases publishing**: automated tag creation and release artifact attachment

## Origin

Published by @ruvnet as a variant implementation for the `release-automation` skill bucket.

Sourced from the Ruflo platform (ruvnet/ruflo, 34k+ stars).
