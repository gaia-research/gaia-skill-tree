---
id: Manavarya09/design-extract
name: Design Extract
contributor: Manavarya09
origin: false
genericSkillRef: design-system-extraction
status: named
title: The Token Scavenger
level: 2★
description: Extracts complete design systems, Tailwind configs, and Figma variables
  from any live URL.
links:
  github: https://github.com/Manavarya09/design-extract
tags:
- design-system
- tailwind
- scraping
createdAt: '2026-05-14'
updatedAt: '2026-06-14'
evidence:
- class: B
  source: https://github.com/Manavarya09/design-extract
  evaluator: gemini-cli
  date: '2026-05-14'
  notes: 'Design Extract -- extracts complete design systems (Tailwind, Figma variables,
    etc.) from any URL. (backfilled — class-to-type migration) (CLI gap: commits+contributors
    not writable via gaia dev evidence)'
  type: repo
  commits: 262
  contributors: 9
  trustNumber: 70.0
  grade: B
timeline:
- timestamp: '2026-06-02T01:43:00Z'
  action: demote
  contributor: unknown
  details: Origin status set to false.
- timestamp: '2026-06-14T12:32:08Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/Manavarya09/design-extract
    as B (trustNumber: 70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:18Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T10:36:26Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:38Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
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
trustMagnitudeInputHash: e6a67963e6916ea87b9db72e7d37ff0df05305e13129a0084d6ed463ed36ac8e
---

## Overview

Design Extract allows agents to "see" and replicate design languages from existing websites. By driving a headless browser to inspect component anatomy and computed styles, it generates portable design tokens and configuration files that can be used to bootstrap new projects with existing aesthetics.
