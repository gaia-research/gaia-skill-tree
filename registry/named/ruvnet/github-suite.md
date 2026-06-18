---
id: ruvnet/github-suite
name: GitHub Suite
contributor: ruvnet
origin: true
genericSkillRef: git-integration
status: named
title: The GitHub Maestro
catalogRef: ruvnet-github-suite
level: 4★
description: Full GitHub platform automation fused from 5 skills — code review, multi-repo
  coordination, project management, release management, and workflow automation.
links:
  github: https://github.com/ruvnet/ruflo
tags:
- github
- platform-mastery
- code-review
- releases
- automation
createdAt: '2026-05-19'
updatedAt: '2026-06-14'
suiteRef: ruvnet/ruflo
suiteComponents:
- ruvnet/github-code-review
- ruvnet/github-multi-repo
- ruvnet/github-project-management
- ruvnet/github-release-management
- ruvnet/github-workflow-automation
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
timeline:
- timestamp: '2026-06-14T12:32:56Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/ruvnet/ruflo as B (trustNumber:
    70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:20Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
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
trustMagnitudeInputHash: 42d137afbe235dc0ae85e3c1b98d1aa733e630cf1d4e8726eeb6d2eebfb8b70a
---

## Overview

GitHub Suite is a 4★ fusion of the five GitHub discipline skills: `github-code-review`, `github-multi-repo`, `github-project-management`, `github-release-management`, and `github-workflow-automation`. Together they cover the full GitHub platform surface — from automated pull request review through cross-repository coordination, project board management, semantic versioning and changelog generation, to CI/CD workflow design. At 4★, an agent can autonomously manage the complete software delivery lifecycle on GitHub.

## Key Capabilities

- **Automated code review**: AI-driven pull request analysis, inline comment generation, and review quality scoring
- **Multi-repo coordination**: cross-repository dependency tracking, synchronized releases, and monorepo workflow management
- **Project management**: GitHub Projects board automation, milestone tracking, and issue lifecycle orchestration
- **Release management**: semantic version bumping, automated changelog generation, and release artifact publishing
- **Workflow automation**: CI/CD pipeline design, GitHub Actions authoring, and event-driven automation across the full repository lifecycle

## Origin

First published by @ruvnet as part of the Ruflo orchestration platform. This is the origin implementation for the `github-platform-mastery` skill bucket.

This 4★ fusion unites github-code-review + github-multi-repo + github-project-management + github-release-management + github-workflow-automation.

Sourced from the Ruflo platform (ruvnet/ruflo, 34k+ stars).

## Installation

This skill is part of the Ruflo orchestration platform.

```bash
npx ruflo@latest init
```

See the [Ruflo (ruvnet/ruflo)](../ruvnet/ruflo.md) capstone for full multi-topology installation options.
