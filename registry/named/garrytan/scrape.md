---
id: garrytan/scrape
name: Scrape
contributor: garrytan
origin: false
genericSkillRef: web-scrape
status: named
title: Gstack Scrape — Structured Web Extraction
catalogRef: garrytan-scrape
level: 2★
description: Fetches target URLs with a headless browser, parses structured data from
  rendered HTML, and returns clean JSON or markdown ready for downstream analysis
  or ingestion.
links:
  github: https://github.com/garrytan/gstack/blob/main/scrape/SKILL.md
tags:
- web-scrape
- data-extraction
- automation
createdAt: '2026-05-18'
updatedAt: '2026-08-30'
suiteRef: garrytan/gstack
timeline:
- timestamp: '2026-06-02T23:33:01Z'
  action: rank_up
  contributor: unknown
  details: Origin status set to true.
- timestamp: '2026-06-03T05:51:28Z'
  action: evidence_added
  contributor: unknown
  details: Added B evidence from https://github.com/garrytan/gstack/blob/main/scrape/SKILL.md
- timestamp: '2026-06-14T12:32:25Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/garrytan/gstack/blob/main/scrape/SKILL.md
    as B (trustNumber: 70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:15Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T11:52:12Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:37Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:38Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- timestamp: '2026-06-20T06:31:23Z'
  action: demote
  contributor: mbtiongson1
  details: Level updated from 3★ to 2★ per G7 final rankings calibration.
- timestamp: '2026-08-29T17:15:48Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM 36.0 -> 36.0, grade C -> C (gaia dev calibrate-trust-magnitude; Issue
    #1600)'
evidence:
- class: B
  source: https://github.com/garrytan/gstack/blob/main/scrape/SKILL.md
  evaluator: mbtiongson1
  date: '2026-06-03'
  notes: 'Public SKILL.md in the garrytan/gstack suite repo (verified live). Fetches"
    target URLs with a headless browser, parses structured data from rendered HTML,
    and returns clean JSON or markdown ready for downstream… (backfilled — class-to-type
    migration) (CLI gap: --commits/--contributors not supported by gaia dev evidence)'
  type: repo
  trustNumber: 70.0
  commits: 323
  contributors: 9
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
  firstEvidenceAt: '2026-06-03T05:51:28Z'
trustMagnitudeInputHash: 29ac5dd28fd5b6bbff0abff48af548e4107e608784c270c269fd8f8540e9196b
---

## Overview

Fetches target URLs with a headless browser, parses structured data from rendered HTML, and returns clean JSON or markdown ready for downstream analysis or ingestion.
