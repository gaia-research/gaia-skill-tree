---
id: ruvnet/github-code-review
name: GitHub Code Review
contributor: ruvnet
origin: false
role: variant
genericSkillRef: code-review-pipeline
status: named
title: The PR Surgeon
catalogRef: ruvnet-github-code-review
level: 1★
description: Automates GitHub pull request code review workflows including diff analysis,
  inline comments, review assignments, and approval gating.
links:
  github: https://github.com/ruvnet/ruflo
tags:
- github
- code-review
- pull-request
- automation
createdAt: '2026-05-19'
updatedAt: '2026-09-05'
timeline:
- timestamp: '2026-06-02T23:48:17Z'
  action: demote
  contributor: unknown
  details: Calibrated level from 3★ to 1★
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:20Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:38Z'
  details: TM 0.0 -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:44Z'
  details: TM 0.0 -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- timestamp: '2026-08-29T17:15:58Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM 0.0 -> 0.0, grade ungraded -> ungraded (gaia dev calibrate-trust-magnitude;
    Issue #1600)'
- timestamp: '2026-09-04T18:43:51Z'
  action: recalibrate_trust_magnitude
  contributor: unknown
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
trustMagnitudeInputHash: eeb3ae87eef47ca2683e0c906b12f079210f27b6f3ab50899c267901478edd64
suiteRef: ruvnet/ruflo
---

## Overview

GitHub Code Review automates the full pull request review lifecycle on GitHub. It handles diff analysis for identifying problematic changes, inline comment generation, reviewer assignment based on file ownership, and approval gating workflows. The skill integrates with GitHub Actions for automated review triggers.

## Key Capabilities

- **Automated diff analysis**: identification of problematic changes across pull request diffs
- **Inline PR comments**: targeted comment generation at the file and line level
- **Reviewer assignment**: file-ownership-based routing to appropriate reviewers
- **Approval gating**: workflow enforcement requiring review sign-off before merge

## Origin

Published by @ruvnet as a variant implementation for the `code-review-pipeline` skill bucket.

Sourced from the Ruflo platform (ruvnet/ruflo, 34k+ stars).
