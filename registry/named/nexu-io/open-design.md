---
id: nexu-io/open-design
name: Open Design
contributor: nexu-io
origin: true
genericSkillRef: design-generation
status: named
title: The Artisan's Forge
level: 1★
description: Local-first design engine for generating high-fidelity UI/UX prototypes
  and brand assets from structured intent.
links:
  github: https://github.com/nexu-io/open-design
tags:
- design
- ui
- ux
- generation
createdAt: '2026-05-14'
updatedAt: '2026-06-14'
evidence:
- class: B
  source: https://github.com/nexu-io/open-design
  evaluator: gemini-cli
  date: '2026-05-14'
  notes: 'Open Design -- local-first design engine generating high-fidelity prototypes"
    and brand assets. (backfilled — class-to-type migration) (CLI gap: --commits/--contributors
    not supported by gaia dev evidence)'
  type: repo
  trustNumber: 70.0
  grade: B
  commits: 2382
  contributors: 332
timeline:
- timestamp: '2026-06-02T23:48:19Z'
  action: demote
  contributor: unknown
  details: Calibrated level from 3★ to 1★
- timestamp: '2026-06-14T12:32:46Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/nexu-io/open-design as B (trustNumber:
    70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:19Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T11:52:12Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
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

Open Design provides a production-grade UI generation workflow for coding agents. It utilizes a discovery-based approach to lock in design requirements before generating Tailwind-powered prototypes, ensuring that AI-generated frontends meet professional aesthetic and accessibility standards.
