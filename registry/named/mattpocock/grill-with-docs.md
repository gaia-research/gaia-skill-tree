---
id: mattpocock/grill-with-docs
name: Grill With Docs
contributor: mattpocock
origin: true
genericSkillRef: grill-with-docs
status: named
title: The Domain Sovereign
catalogRef: mattpocock-grill-with-docs
level: 3★
description: The ultimate evolution of the grill pattern. Fuses relentless Socratic
  questioning with deep domain awareness, ensuring every decision is cross-referenced
  against a persistent ubiquitous language and documented via real-time ADR generation.
links:
  github: https://github.com/mattpocock/skills/blob/main/skills/engineering/grill-with-docs/SKILL.md
tags:
- design-review
- domain-model
- ubiquitous-language
- adr
- context-md
- socratic-method
- fusion
createdAt: '2026-04-30'
updatedAt: '2026-06-21'
suiteRef: mattpocock/engineering
evidence:
- class: B
  source: https://github.com/mattpocock/skills/blob/main/skills/engineering/grill-with-docs/SKILL.md
  evaluator: mbtiongson1
  date: '2026-05-15'
  notes: 'Production implementation of the Grill With Docs pattern. (backfilled —
    class-to-type" migration) (CLI gap: --commits/--contributors not supported by
    gaia dev evidence)'
  type: repo
  trustNumber: 70.0
  commits: 137
  contributors: 3
  grade: C
- source: https://github.com/mattpocock/skills/discussions
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: peer-review
  class: A
  notes: 'GitHub Discussions: 5+ threads naming grill-with-docs directly (#275 #293
    #300 #304). Origin implementation for grill pattern. Named-layer.'
  grade: C
- source: https://github.com/mattpocock/skills/issues/341
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: peer-review
  class: A
  notes: 'Issue #341: ''grill-with-docs: resolved answers not traceable through PRD/issues/implementation''
    — 6 comments. Most-engaged grill-with-docs issue. Named-layer.'
  grade: C
- source: https://github.com/mattpocock/skills/issues/299
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: peer-review
  class: A
  notes: 'Issue #299: ''grill-with-docs poisoning docs/adr with unimplemented decisions''
    — 3 comments. Active real-world usage feedback. Named-layer.'
- source: https://www.youtube.com/@mattpocockuk
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: social-signal
  class: A
  notes: Matt Pocock official YouTube channel (Total TypeScript) — creator of grill-with-docs,
    origin implementation. topicalAuthority creator_mult.
timeline:
- timestamp: '2026-06-14T12:32:43Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/mattpocock/skills/blob/main/skills/engineering/grill-with-docs/SKILL.md
    as B (trustNumber: 70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:18Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T11:52:12Z'
  details: TM 0.0 -> 11.21, grade ungraded -> ungraded (direct edit -- CLI gap)
- timestamp: '2026-06-19T12:01:52Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/mattpocock/skills/discussions (type:
    peer-review)'
- timestamp: '2026-06-19T12:02:06Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/mattpocock/skills/issues/341 (type:
    peer-review)'
- timestamp: '2026-06-19T12:02:20Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/mattpocock/skills/issues/299 (type:
    peer-review)'
- timestamp: '2026-06-19T12:02:51Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://www.youtube.com/@mattpocockuk (type: social-signal)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T12:03:11Z'
  details: TM 11.21 -> 63.71, grade ungraded -> B (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:38Z'
  details: TM 0.0 -> 63.71, grade ungraded -> B (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:41Z'
  details: TM 0.0 -> 63.71, grade ungraded -> B (direct edit -- CLI gap)
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
verification:
  firstEvidenceAt: '2026-06-19T12:01:52Z'
trustMagnitudeInputHash: 5ce1a22a9528fc9c688cd2a5f03e22ef55909be45178d3cb7d40193a2eb4cfeb
---

## Overview

Grill With Docs is the ultimate domain-aware variant of the design-grilling pattern, fused with the Ubiquitous Language skill. It begins by locating the project's CONTEXT.md and docs/adr/ (supporting both flat and CONTEXT-MAP.md multi-context repos), then conducts a relentless one-question-at-a-time interview.

During the session the agent actively challenges language: when the user uses a term that conflicts with the glossary it calls it out immediately. It cross-references code to catch contradictions between stated intent and actual behaviour. Decisions are written to CONTEXT.md in real time — not batched — using a strict format. ADRs are offered only when a decision is hard-to-reverse, surprising without context, and the result of a genuine trade-off; all three conditions must hold.

By fusing the raw interrogation of `/grill-me` with the domain discipline of `/ubiquitous-language`, this skill serves as the apex of agentic design alignment.

## Origin

First published by @mattpocock (Matt Pocock, Total TypeScript). This is the origin implementation for the `design-review` skill bucket.

## Installation

This skill is included in the Matt Pocock skills suite. It is highly recommended to install the full suite to enable cross-skill context sharing.

```bash
npx skills@latest add mattpocock/skills
```

No additional setup required beyond the main suite installation.
