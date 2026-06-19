---
id: mattpocock/to-prd
name: To PRD
contributor: mattpocock
origin: true
genericSkillRef: prd-generation
status: named
title: The PRD Synthesiser
catalogRef: mattpocock-to-prd
level: 2★
description: Synthesises the current conversation context and codebase knowledge into
  a fully-structured PRD — problem statement, extensive numbered user stories, implementation
  decisions (modules, interfaces, schema), testing decisions, and out-of-scope items
  — then publishes it to the project issue tracker.
links:
  github: https://github.com/mattpocock/skills/blob/main/skills/engineering/to-prd/SKILL.md
tags:
- prd
- requirements
- user-stories
- product-management
- issue-tracker
createdAt: '2026-04-30'
updatedAt: '2026-06-19'
suiteRef: mattpocock/engineering
evidence:
- class: B
  source: https://github.com/mattpocock/skills/blob/main/skills/engineering/to-prd/SKILL.md
  evaluator: mbtiongson1
  date: '2026-04-30'
  notes: Production skill that synthesises live conversation context into a fully-structured
    PRD and publishes it to the issue tracker. (backfilled — class-to-type migration)
  type: repo
  trustNumber: 70.0
  grade: B
  commits: 137
  contributors: 3
- source: https://github.com/mattpocock/skills/issues/156
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: peer-review
  class: A
  notes: GitHub issue about to-prd skill behavior.
- source: https://github.com/mattpocock/skills/issues/212
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: peer-review
  class: A
  notes: GitHub issue about to-prd skill workflow question.
- source: https://github.com/mattpocock/skills/issues/240
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: peer-review
  class: A
  notes: GitHub issue about to-prd skill interaction with grill-me.
- source: https://github.com/mattpocock/skills/discussions/217
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: peer-review
  class: A
  notes: GitHub discussion about to-prd skill workflow.
timeline:
- timestamp: '2026-06-14T12:32:44Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/mattpocock/skills/blob/main/skills/engineering/to-prd/SKILL.md
    as B (trustNumber: 70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:18Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T11:07:58Z'
  details: TM 0.0 -> 11.21, grade ungraded -> ungraded (direct edit -- CLI gap)
- timestamp: '2026-06-19T12:36:40Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/mattpocock/skills/issues/156 (type:
    peer-review)'
- timestamp: '2026-06-19T12:36:55Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/mattpocock/skills/issues/212 (type:
    peer-review)'
- timestamp: '2026-06-19T12:37:11Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/mattpocock/skills/issues/240 (type:
    peer-review)'
- timestamp: '2026-06-19T12:37:26Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/mattpocock/skills/discussions/217
    (type: peer-review)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T12:53:50Z'
  details: TM 11.21 -> 63.71, grade ungraded -> B (direct edit -- CLI gap)
trustMagnitude: 63.71
overallTrustGrade: B
apexGateStatus:
  aGradedOriginsGte5: false
  sourceTenureDaysGte180AorS: false
  directNestedSuiteGte1: false
  depth2OnlyReachableGte1: false
  overallGradeS: false
  apexPromotionPrSigned: false
  crossOrgVerifier: null
  systemWideCap: null
trustMagnitudeInputHash: 3ca06779ae14c7eb91cc81c930ffbd37abc94d5b4578fa843fac16617e26fefc
verification:
  firstEvidenceAt: '2026-06-19T12:36:40Z'
---

## Overview

To PRD does not interview the user — it synthesises what it already knows from the conversation and codebase. The agent reads the domain glossary and existing ADRs, sketches major modules with deep-module opportunities (small interface, deep implementation), confirms module scope with the user, then writes the PRD using a strict template: problem statement → solution → extensive user stories → implementation decisions → testing decisions → out-of-scope → further notes.

The output is published directly to the issue tracker with the `needs-triage` label. Specific file paths and code snippets are intentionally excluded from implementation decisions to prevent fast-rotting documentation.

## Origin

First published by @mattpocock (Matt Pocock, Total TypeScript). This is the origin implementation for the `prd-generation` skill bucket.

## Installation

This skill is included in the Matt Pocock skills suite. It is highly recommended to install the full suite to enable cross-skill context sharing.

```bash
npx skills@latest add mattpocock/skills
```

No additional setup required beyond the main suite installation.
