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
updatedAt: '2026-06-14'
evidence:
- class: C
  source: https://github.com/intelligentcode-ai/skills/blob/main/skills/release/SKILL.md
  evaluator: mbtiongson1
  date: '2026-04-30'
  notes: intelligentcode-ai/skills release — automates semantic versioning, CHANGELOG
    updates, PR merging, git tagging, and GitHub release creation with verification
    gates. (backfilled — class-to-type migration)
  type: repo
  commits: 34
  contributors: 1
  trustNumber: 50.0
  grade: C
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
