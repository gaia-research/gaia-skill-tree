---
id: intelligentcode-ai/release
name: Release
contributor: intelligentcode-ai
origin: false
links:
  github: https://github.com/intelligentcode-ai/skills/blob/main/skills/release/SKILL.md
genericSkillRef: release-automation
status: named
title: The Shipwright's Will
level: 2★
description: Automates the full release cycle — semantic version bump, CHANGELOG update,
  PR merge, git tag, and GitHub release creation with multiple verification gates.
tags:
- release
- semver
- changelog
- git-tag
- github-release
- automation
updatedAt: '2026-06-20'
evidence:
- class: C
  source: https://github.com/intelligentcode-ai/skills/blob/main/skills/release/SKILL.md
  evaluator: mbtiongson1
  date: '2026-04-30'
  notes: intelligentcode-ai/skills — practical coding agent skills; release provides
    production-ready implementation (trust updated from C=50 to B-equiv=65)
  type: repo
  commits: 34
  contributors: 1
  trustNumber: 65.0
  grade: B
- source: https://github.com/intelligentcode-ai/skills
  evaluator: unknown
  date: '2026-06-20'
  type: self-attestation
  trustNumber: 60.0
  grade: B
  notes: intelligentcode-ai/skills suite self-attested via README description; practical
    agent skill for release domain
  sourceStartedAt: '2025-01-01'
timeline:
- timestamp: '2026-06-14T12:32:41Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/intelligentcode-ai/skills/blob/main/skills/release/SKILL.md
    as C (trustNumber: 50.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:17Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T11:10:48Z'
  details: TM 0.0 -> 1.3, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:38Z'
  details: TM 0.0 -> 1.3, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:40Z'
  details: TM 0.0 -> 1.3, grade ungraded -> ungraded (direct edit -- CLI gap)
- timestamp: '2026-06-19T17:10:13Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/intelligentcode-ai/skills/blob/main/skills/release/SKILL.md
    as B (trustNumber: 65.0)'
- timestamp: '2026-06-19T17:10:48Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/intelligentcode-ai/skills (type:
    self-attestation)'
- timestamp: '2026-06-19T17:10:48Z'
  action: evidence_graded
  contributor: unknown
  details: 'Graded evidence from https://github.com/intelligentcode-ai/skills as B
    (trustNumber: 60.0)'
trustMagnitude: 1.3
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
trustMagnitudeInputHash: 5346f585d2c4cd77c10607ed220c72f6829522d27b43e8c9df9e0582397e561a
verification:
  firstEvidenceAt: '2026-06-19T17:10:48Z'
---

## Overview

Drives a release from a merged feature branch to a published GitHub release. Determines the correct semantic version from commit messages (conventional commits), updates CHANGELOG.md, creates and pushes the tag, and publishes a release with auto-generated notes.

## Key behaviours

- Conventional commits parser to determine major/minor/patch bump
- CHANGELOG.md update following Keep-a-Changelog format
- Git tag creation with signed commits where configured
- GitHub Release API call with release notes derived from commit log

## Source

[intelligentcode-ai/skills — release/SKILL.md](https://github.com/intelligentcode-ai/skills/blob/main/skills/release/SKILL.md)
