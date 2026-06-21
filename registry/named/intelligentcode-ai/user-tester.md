---
id: intelligentcode-ai/user-tester
name: User Tester
contributor: intelligentcode-ai
origin: false
links:
  github: https://github.com/intelligentcode-ai/skills/blob/main/skills/user-tester/SKILL.md
genericSkillRef: e2e-testing
status: named
title: The Human Lens
level: 1★
description: E2E testing specialist with Puppeteer/Playwright automation — cross-browser
  validation, full user journey simulation, and visual regression detection.
tags:
- e2e
- playwright
- puppeteer
- cross-browser
- user-journey
- visual-regression
updatedAt: '2026-06-21'
evidence:
- class: C
  source: https://github.com/intelligentcode-ai/skills/blob/main/skills/user-tester/SKILL.md
  evaluator: mbtiongson1
  date: '2026-04-30'
  notes: intelligentcode-ai/skills — practical coding agent skills; user-tester provides
    production-ready implementation (trust updated from C=50 to B-equiv=65)
  type: repo
  commits: 34
  contributors: 1
  trustNumber: 65.0
- source: https://github.com/intelligentcode-ai/skills
  evaluator: unknown
  date: '2026-06-20'
  type: self-attestation
  trustNumber: 60.0
  grade: C
  notes: intelligentcode-ai/skills suite self-attested via README description; practical
    agent skill for user-tester domain
  sourceStartedAt: '2025-01-01'
timeline:
- timestamp: '2026-06-14T12:32:41Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/intelligentcode-ai/skills/blob/main/skills/user-tester/SKILL.md
    as C (trustNumber: 50.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:18Z'
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
- timestamp: '2026-06-19T17:10:18Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/intelligentcode-ai/skills/blob/main/skills/user-tester/SKILL.md
    as B (trustNumber: 65.0)'
- timestamp: '2026-06-19T17:10:52Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/intelligentcode-ai/skills (type:
    self-attestation)'
- timestamp: '2026-06-19T17:10:53Z'
  action: evidence_graded
  contributor: unknown
  details: 'Graded evidence from https://github.com/intelligentcode-ai/skills as B
    (trustNumber: 60.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T17:13:03Z'
  details: TM 1.3 -> 6.3, grade ungraded -> ungraded (direct edit -- CLI gap)
- timestamp: '2026-06-20T06:31:29Z'
  action: demote
  contributor: mbtiongson1
  details: Level updated from 2★ to 1★ per G7 final rankings calibration.
trustMagnitude: 6.3
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
trustMagnitudeInputHash: ed010fb59ee82c805db443ff7f60c3aac9b7f86742a45f4d974de2fbf869c35b
verification:
  firstEvidenceAt: '2026-06-19T17:10:52Z'
---

## Overview

Writes and runs end-to-end tests that simulate real user paths from login through core workflows to logout. Captures screenshots at each step, detects visual regressions, and reports failures with full trace.

## Key behaviours

- Generates Playwright scripts from user story descriptions
- Runs tests headlessly in CI and headed locally for debugging
- Cross-browser matrix: Chromium, Firefox, WebKit
- Integrates with CI pipelines; fails fast on first regression

## Source

[intelligentcode-ai/skills — user-tester/SKILL.md](https://github.com/intelligentcode-ai/skills/blob/main/skills/user-tester/SKILL.md)
