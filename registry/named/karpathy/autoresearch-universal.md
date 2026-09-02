---
id: karpathy/autoresearch-universal
name: AutoResearch
contributor: karpathy
origin: false
genericSkillRef: autonomous-web-research
status: named
title: The Scholar's Compass
catalogRef: karpathy-autoresearch
level: 2★
description: Autonomous research agent that iteratively searches, reads, and synthesizes
  academic papers into structured summaries.
links:
  github: https://github.com/balukosuri/Andrej-Karpathy-s-Autoresearch-As-a-Universal-Skill/blob/main/SKILL.md
tags:
- research
- autonomous
- paper-synthesis
createdAt: '2026-04-29'
updatedAt: '2026-08-30'
evidence:
- class: B
  source: https://github.com/karpathy/autoresearch
  evaluator: mbtiongson1
  date: '2026-06-02'
  notes: 'Karpathy''s autoresearch repo serving as the evidence/inspiration for the"
    skill. (backfilled — class-to-type migration) (CLI gap: --commits/--contributors
    not supported by gaia dev evidence)'
  type: repo
  trustNumber: 70.0
  commits: 36
  contributors: 9
  grade: B
timeline:
- timestamp: '2026-06-14T12:32:42Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/karpathy/autoresearch as B
    (trustNumber: 70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:18Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T11:52:12Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:38Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:40Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- timestamp: '2026-06-20T06:31:29Z'
  action: demote
  contributor: mbtiongson1
  details: Level updated from 3★ to 2★ per G7 final rankings calibration.
- timestamp: '2026-07-30T06:11:15Z'
  action: demote
  contributor: mbtiongson1
  details: Origin status set to false.
- timestamp: '2026-08-05T06:29:13Z'
  action: rename
  contributor: unknown
  details: Renamed named skill from karpathy/autoresearch to karpathy/autoresearch-universal
- timestamp: '2026-08-29T17:15:51Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM 36.0 -> 36.0, grade C -> C (gaia dev calibrate-trust-magnitude; Issue
    #1600)'
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
trustMagnitudeInputHash: a3ed93ef0507dd2310b19b343d07968b5dfedb7be355f6493c68c1690ccac0a6
---

## Overview

AutoResearch is an autonomous agent that performs iterative literature review by searching academic databases, reading papers, extracting key findings, and producing structured research summaries.

## Origin

First published by @karpathy. Implementation for the "autonomous-web-research" skill bucket (see issue #1393 for dedicated generic bucket re-homing).
