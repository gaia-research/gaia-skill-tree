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
updatedAt: '2026-06-02'
suiteRef: ruvnet/github-suite
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
trustMagnitudeInputHash: 88b4c8260a3013c0af3f5e7051e99b782e403eb210798c25704bc64d9eb7a367
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
