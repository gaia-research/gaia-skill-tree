---
id: karpathy/autoresearch
name: AutoResearch
contributor: karpathy
origin: true
genericSkillRef: autonomous-web-research
status: named
title: The Scholar's Compass
catalogRef: karpathy-autoresearch
level: 3★
description: Autonomous research agent that iteratively searches, reads, and synthesizes
  academic papers into structured summaries.
links:
  github: https://github.com/balukosuri/Andrej-Karpathy-s-Autoresearch-As-a-Universal-Skill/blob/main/SKILL.md
tags:
- research
- autonomous
- paper-synthesis
createdAt: '2026-04-29'
updatedAt: '2026-06-14'
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
  grade: B
  commits: 36
  contributors: 9
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
trustMagnitudeInputHash: fc9b0a2b3ee407e4112f851596a03d6d00844cbbebdc0aa4814e93e6200311de
---

## Overview

AutoResearch is an autonomous agent that performs iterative literature review by searching academic databases, reading papers, extracting key findings, and producing structured research summaries.

## Origin

First published by @karpathy. This is the origin implementation for the "autonomous-research-agent" skill bucket.
