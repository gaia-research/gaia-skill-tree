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
level: 2★
description: E2E testing specialist with Puppeteer/Playwright automation — cross-browser
  validation, full user journey simulation, and visual regression detection.
tags:
- e2e
- playwright
- puppeteer
- cross-browser
- user-journey
- visual-regression
updatedAt: '2026-06-14'
evidence:
- class: C
  source: https://github.com/intelligentcode-ai/skills/blob/main/skills/user-tester/SKILL.md
  evaluator: mbtiongson1
  date: '2026-04-30'
  notes: intelligentcode-ai/skills user-tester — E2E testing specialist with Puppeteer/Playwright automation and cross-browser user journey validation. (backfilled — class-to-type migration)
  type: repo
  trustNumber: 50.0
  grade: C
timeline:
- timestamp: '2026-06-14T12:32:41Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/intelligentcode-ai/skills/blob/main/skills/user-tester/SKILL.md
    as C (trustNumber: 50.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:18Z'
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
trustMagnitudeInputHash: 5c2bde2c36d41380fac68a7fe69ee324bf9df70896760c5dfad3e69694bbe508
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
