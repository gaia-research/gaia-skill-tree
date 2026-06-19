---
id: mattpocock/edit-article
name: Edit Article
contributor: mattpocock
origin: false
genericSkillRef: document-editing
status: named
title: The Section-by-Section Rewrite
catalogRef: mattpocock-edit-article
level: 2★
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
updatedAt: '2026-06-14'
suiteRef: mattpocock/personal
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
  grade: B
  commits: 137
  contributors: 3
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
verification:
  firstEvidenceAt: '2026-06-10T05:38:17Z'
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
