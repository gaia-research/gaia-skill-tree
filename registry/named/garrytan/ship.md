---
id: garrytan/ship
name: Ship
contributor: garrytan
origin: true
genericSkillRef: finishing-a-development-branch
status: named
title: Gstack Ship
catalogRef: garrytan-ship
level: 4★
description: Automated end-to-end deployment workflow that merges the base branch,
  runs tests, reviews the diff, bumps the VERSION file, updates the CHANGELOG, commits,
  pushes to the remote, and creates a pull request in a single command.
links:
  github: https://github.com/garrytan/gstack/blob/main/ship/SKILL.md
tags:
- ship
- deploy
- pr-automation
- release
createdAt: '2026-05-18'
updatedAt: '2026-06-14'
suiteRef: garrytan/gstack
timeline:
- timestamp: '2026-06-02T23:32:59Z'
  action: rank_up
  contributor: unknown
  details: Origin status set to true.
- timestamp: '2026-06-03T05:51:37Z'
  action: evidence_added
  contributor: unknown
  details: Added B evidence from https://github.com/garrytan/gstack/blob/main/ship/SKILL.md
- timestamp: '2026-06-14T12:32:26Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/garrytan/gstack/blob/main/ship/SKILL.md
    as B (trustNumber: 70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:16Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T10:36:26Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
evidence:
- class: B
  source: https://github.com/garrytan/gstack/blob/main/ship/SKILL.md
  evaluator: mbtiongson1
  date: '2026-06-03'
  notes: 'Public SKILL.md in the garrytan/gstack suite repo (verified live). Automated
    end-to-end deployment workflow that merges the base branch, runs tests, reviews
    the diff, bumps the VERSION file, updates the CHANGELOG,… (backfilled — class-to-type
    migration) (CLI gap: commits+contributors not writable via gaia dev evidence)'
  type: repo
  commits: 323
  contributors: 9
  trustNumber: 70.0
  grade: B
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
  firstEvidenceAt: '2026-06-03T05:51:37Z'
trustMagnitudeInputHash: e764ac08e8cac9e313e956b40ebbd8bfc97e279d9cf174fdd48ecd3a9629578f
---

## Overview

Gstack Ship automates the entire last-mile shipping ritual. On hearing "ship it", "create a PR", or "deploy this", it detects and merges the base branch, executes tests, reviews the diff for regressions, increments the VERSION file, writes a CHANGELOG entry, commits the release artifacts, pushes, and opens a pull request — all without manual steps.
