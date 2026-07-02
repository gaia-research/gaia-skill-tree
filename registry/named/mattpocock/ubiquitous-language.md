---
id: mattpocock/ubiquitous-language
name: Ubiquitous Language
contributor: mattpocock
origin: false
genericSkillRef: ubiquitous-language
status: named
title: The Domain Linguist
catalogRef: mattpocock-ubiquitous-language
level: 3★
description: Extracts and formalises a project's domain terminology into a shared
  glossary, enforcing consistent naming across code and conversations to eliminate
  ambiguity. Removed from mattpocock/skills suite in v1.0.1.
links:
  github: https://github.com/mattpocock/skills/blob/main/skills/engineering/ubiquitous-language/SKILL.md
tags:
- domain-driven-design
- ddd
- ubiquitous-language
- glossary
- terminology
- alignment
createdAt: '2026-05-15'
updatedAt: '2026-06-21'
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
  updatedAt: '2026-07-01'
  date: '2026-06-20'
  type: github-stars-own
  trustNumber: 88.0
  grade: C
  notes: mattpocock/skills suite repo — 137k GitHub stars; ubiquitous-language was
    part of this suite (removed in v1.0.1 but authored by Matt Pocock)
  stars: 152357
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
trustMagnitude: 90.38
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
suiteRef: mattpocock/engineering
trustMagnitudeInputHash: 93c720242a46b215789bae724573d16cd95c9b5acb9a4ed1a137fa308cdb34f8
verification:
  firstEvidenceAt: '2026-06-19T16:57:17Z'
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
