---
id: mattpocock/ubiquitous-language
name: Ubiquitous Language
contributor: mattpocock
origin: false
genericSkillRef: ubiquitous-language
status: named
title: The Domain Linguist
catalogRef: mattpocock-ubiquitous-language
level: 4★
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
updatedAt: '2026-06-14'
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
  grade: B
  commits: 137
  contributors: 3
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
trustMagnitude: 11.21
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
suiteRef: mattpocock/engineering
trustMagnitudeInputHash: c36651da83163fc4d55f128ed930b3847afc7e8289d59b8bc977abf2cab1cc3b
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
