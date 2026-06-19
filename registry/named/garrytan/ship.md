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
updatedAt: '2026-06-20'
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
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:37Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:38Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- timestamp: '2026-06-19T16:48:02Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/garrytan/gstack (type: github-stars-own)'
- timestamp: '2026-06-19T16:48:02Z'
  action: evidence_graded
  contributor: unknown
  details: 'Graded evidence from https://github.com/garrytan/gstack as A (trustNumber:
    85.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T17:13:01Z'
  details: TM 36.0 -> 63.73, grade C -> B (direct edit -- CLI gap)
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
- source: https://github.com/garrytan/gstack
  evaluator: unknown
  date: '2026-06-20'
  type: github-stars-own
  trustNumber: 85.0
  grade: A
  notes: gstack suite repo — 110,930 GitHub stars; ship is 1 of 42 named skills (verified
    2026-06-20)
  stars: 110930
  skillCountInRepo: 42
  sourceStartedAt: '2024-01-01'
trustMagnitude: 63.73
overallTrustGrade: B
apexGateStatus:
  aGradedOriginsGte5: false
  sourceTenureDaysGte180AorS: true
  directNestedSuiteGte1: false
  depth2OnlyReachableGte1: false
  overallGradeS: false
  apexPromotionPrSigned: false
  crossOrgVerifier: null
  systemWideCap: null
verification:
  firstEvidenceAt: '2026-06-03T05:51:37Z'
trustMagnitudeInputHash: cd424c47cab4fab0d5809899aa0fa439b80ed5db43075612b29ce4fb0555bde9
---

## Overview

Gstack Ship automates the entire last-mile shipping ritual. On hearing "ship it", "create a PR", or "deploy this", it detects and merges the base branch, executes tests, reviews the diff for regressions, increments the VERSION file, writes a CHANGELOG entry, commits the release artifacts, pushes, and opens a pull request — all without manual steps.
