---
id: mattpocock/edit-article
name: Edit Article
contributor: mattpocock
origin: false
genericSkillRef: document-editing
status: named
title: The Section-by-Section Rewrite
catalogRef: mattpocock-edit-article
level: 1★
description: Edits articles by first sectioning them as a DAG of information dependencies,
  confirming the section order, then rewriting each section for clarity and flow with
  a 240-character-per-paragraph constraint.
links:
  github: https://github.com/mattpocock/skills/blob/main/skills/personal/edit-article/SKILL.md
tags:
- article-editing
- prose-rewrite
- information-dag
- section-structure
- clarity
createdAt: '2026-04-30'
updatedAt: '2026-09-04'
timeline:
- timestamp: '2026-06-02T01:42:59Z'
  action: rank_up
  contributor: unknown
  details: Origin status set to true.
- timestamp: '2026-06-10T05:38:17Z'
  action: evidence_added
  contributor: unknown
  details: Added B evidence from https://github.com/mattpocock/skills/blob/main/skills/personal/edit-article/SKILL.md
- timestamp: '2026-06-14T12:32:43Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/mattpocock/skills/blob/main/skills/personal/edit-article/SKILL.md
    as B (trustNumber: 70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:18Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T11:52:12Z'
  details: TM 0.0 -> 11.21, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:38Z'
  details: TM 0.0 -> 11.21, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:41Z'
  details: TM 0.0 -> 11.21, grade ungraded -> ungraded (direct edit -- CLI gap)
- timestamp: '2026-06-19T17:07:30Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/mattpocock/skills (type: github-stars-own)'
- timestamp: '2026-06-19T17:07:30Z'
  action: evidence_graded
  contributor: unknown
  details: 'Graded evidence from https://github.com/mattpocock/skills as A (trustNumber:
    88.0)'
- timestamp: '2026-06-19T17:07:32Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://www.youtube.com/watch?v=EJyuu6zlQCg (type:
    social-signal)'
- timestamp: '2026-06-19T17:07:32Z'
  action: evidence_graded
  contributor: unknown
  details: 'Graded evidence from https://www.youtube.com/watch?v=EJyuu6zlQCg as A
    (trustNumber: 82.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T17:13:03Z'
  details: TM 11.21 -> 90.38, grade ungraded -> B (direct edit -- CLI gap)
- timestamp: '2026-06-20T06:31:31Z'
  action: rank_up
  contributor: mbtiongson1
  details: Level updated from 2★ to 3★ per G7 final rankings calibration.
- timestamp: '2026-08-19T11:49:10Z'
  action: upstream_deprecated
  contributor: unknown
  previousValue: null
  newValue: null
  details: personal/ bucket deleted upstream (v1.2.x); no successor
- timestamp: '2026-08-29T17:15:52Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM 90.38 -> 306.13, grade B -> A (gaia dev calibrate-trust-magnitude;
    Issue #1600)'
- timestamp: '2026-09-02T15:11:39Z'
  action: rank_up
  contributor: unknown
  details: Calibrated level from 3★ to 4★
- timestamp: '2026-09-04T00:00:00Z'
  action: demote
  contributor: mbtiongson1
  previousValue: 4★
  newValue: 1★
  details: Demoted to 1★ due to dead/deprecated blob link under META §2.4
- timestamp: '2026-09-04T10:58:45Z'
  action: recalibrate_trust_magnitude
  contributor: unknown
  details: 'TM 209.65 -> 94.92, grade A -> B (gaia dev calibrate-trust-magnitude;
    Issue #1600)'
evidence:
- class: B
  source: https://github.com/mattpocock/skills/blob/main/skills/personal/edit-article/SKILL.md
  evaluator: mbtiongson1
  date: '2026-06-10'
  notes: 'Published implementation in Matt Pocock''s skills repository; DAG-sectioned"
    rewrite workflow documented and reproducible. (backfilled — class-to-type migration)
    (CLI gap: --commits/--contributors not supported by gaia dev evidence)'
  type: repo
  trustNumber: 70.0
  commits: 137
  contributors: 3
  grade: C
- source: https://github.com/mattpocock/skills
  evaluator: unknown
  updatedAt: '2026-09-01'
  date: '2026-06-20'
  type: github-stars-own
  trustNumber: 88.0
  grade: C
  notes: mattpocock/skills suite — 137k GitHub stars; edit-article is part of this
    repo
  stars: 243413
  skillCountInRepo: 21
  sourceStartedAt: '2025-01-01'
- source: https://www.youtube.com/watch?v=EJyuu6zlQCg
  evaluator: unknown
  date: '2026-06-20'
  type: social-signal
  trustNumber: 82.0
  grade: B
  notes: Matt Pocock — 5 Claude Code skills I use every single day; 412K views; covers
    mattpocock/skills repo (verified 2026-06-20)
  views: 412000
  sourceStartedAt: '2025-01-01'
trustMagnitude: 94.92
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
  firstEvidenceAt: '2026-06-10T05:38:17Z'
trustMagnitudeInputHash: bece26c8f9a7ae5c1985083a8a34b53463c9f0f5c0e14e209225d895272439be
installable: false
suiteRef: "mattpocock/skills"
---

## Overview

Edit Article models an article as a directed acyclic graph of information dependencies: each section can only introduce concepts that prior sections have established. Before rewriting anything, the agent divides the article into dependency-ordered sections and confirms the structure with the author. It then rewrites section by section, enforcing a 240-character maximum per paragraph to keep prose dense and scannable.

## Origin

Published by @mattpocock (Matt Pocock, Total TypeScript). Named implementation of the `document-editing` skill bucket for long-form article editing (origin: anthropic/pptx).

## Installation

This skill is included in the Matt Pocock skills suite. It is highly recommended to install the full suite to enable cross-skill context sharing.

```bash
npx skills@latest add mattpocock/skills
```

No additional setup required beyond the main suite installation.
