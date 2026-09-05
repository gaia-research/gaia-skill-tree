---
id: mattpocock/ubiquitous-language
name: Ubiquitous Language
contributor: mattpocock
origin: false
genericSkillRef: ubiquitous-language
status: named
title: The Domain Linguist
catalogRef: mattpocock-ubiquitous-language
level: 1★
description: Extracts and formalises a project's domain terminology into a shared
  glossary, enforcing consistent naming across code and conversations to eliminate
  ambiguity. Removed from mattpocock/skills suite in v1.0.1.
links:
  github: https://github.com/mattpocock/skills/blob/main/skills/deprecated/ubiquitous-language/SKILL.md
tags:
- domain-driven-design
- ddd
- ubiquitous-language
- glossary
- terminology
- alignment
createdAt: '2026-05-15'
updatedAt: '2026-09-04'
evidence:
- class: B
  source: https://github.com/mattpocock/skills/blob/main/skills/engineering/ubiquitous-language/SKILL.md
  evaluator: mbtiongson1
  date: '2026-05-15'
  notes: 'Original implementation by Matt Pocock; formalizes DDD principles for AI"
    agent contexts. (backfilled — class-to-type migration) (CLI gap: --commits/--contributors
    not supported by gaia dev evidence)'
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
  notes: mattpocock/skills suite repo — 137k GitHub stars; ubiquitous-language was
    part of this suite (removed in v1.0.1 but authored by Matt Pocock)
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
    mattpocock/skills suite that includes ubiquitous-language (verified 2026-06-20)
  views: 412000
  sourceStartedAt: '2025-01-01'
timeline:
- timestamp: '2026-06-14T12:32:44Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/mattpocock/skills/blob/main/skills/engineering/ubiquitous-language/SKILL.md
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
  timestamp: '2026-06-19T13:26:42Z'
  details: TM 0.0 -> 11.21, grade ungraded -> ungraded (direct edit -- CLI gap)
- timestamp: '2026-06-19T16:57:17Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/mattpocock/skills (type: github-stars-own)'
- timestamp: '2026-06-19T16:57:17Z'
  action: evidence_graded
  contributor: unknown
  details: 'Graded evidence from https://github.com/mattpocock/skills as A (trustNumber:
    88.0)'
- timestamp: '2026-06-19T16:57:18Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://www.youtube.com/watch?v=EJyuu6zlQCg (type:
    social-signal)'
- timestamp: '2026-06-19T16:57:19Z'
  action: evidence_graded
  contributor: unknown
  details: 'Graded evidence from https://www.youtube.com/watch?v=EJyuu6zlQCg as A
    (trustNumber: 82.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T17:13:03Z'
  details: TM 11.21 -> 90.38, grade ungraded -> B (direct edit -- CLI gap)
- timestamp: '2026-06-20T06:31:33Z'
  action: demote
  contributor: mbtiongson1
  details: Level updated from 4★ to 3★ per G7 final rankings calibration.
- timestamp: '2026-08-05T06:27:16Z'
  action: note
  contributor: unknown
  details: Updated GitHub link to https://github.com/mattpocock/skills/blob/main/skills/deprecated/ubiquitous-language/SKILL.md
- timestamp: '2026-08-19T11:49:11Z'
  action: upstream_deprecated
  contributor: unknown
  previousValue: null
  newValue: null
  details: superseded by mattpocock/domain-modeling upstream (folded in v1.2.x)
- timestamp: '2026-08-29T17:15:54Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM 90.38 -> 306.13, grade B -> A (gaia dev calibrate-trust-magnitude;
    Issue #1600)'
- timestamp: '2026-09-02T15:11:40Z'
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
trustMagnitudeInputHash: b07d195722f1666c41a3fe7b12fc71f87b1ec951727c7f5d6c4fdb357263e5bd
verification:
  firstEvidenceAt: '2026-06-19T16:57:17Z'
installable: false
suiteRef: "mattpocock/skills"
---

## Overview

Ubiquitous Language brings Domain-Driven Design (DDD) principles to the AI agent workflow. The agent scans the conversation and codebase to identify domain-relevant nouns and verbs, proposing a canonical glossary that is persisted to `CONTEXT.md`.

Once established, the agent uses this language as a "source of truth," ensuring that new code, variable names, and architectural decisions align with the business domain. This reduces token waste by eliminating the need for repeated explanations and prevents "software entropy" where jargon diverges from intent.

## Origin

Released by @mattpocock as part of the "Skills for Real Engineers" suite.

## Installation

This skill is included in the Matt Pocock skills suite. It is highly recommended to install the full suite to enable cross-skill context sharing.

```bash
npx skills@latest add mattpocock/skills
```

No additional setup required beyond the main suite installation.
