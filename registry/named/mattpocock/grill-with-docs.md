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
updatedAt: '2026-06-14'
suiteRef: mattpocock/engineering
evidence:
- class: B
  source: https://github.com/mattpocock/skills/blob/main/skills/engineering/grill-with-docs/SKILL.md
  evaluator: mbtiongson1
  date: '2026-05-15'
  notes: Production implementation of the Grill With Docs pattern. (backfilled — class-to-type
    migration)
  type: repo
  trustNumber: 70.0
  grade: B
timeline:
- timestamp: '2026-06-14T12:32:43Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/mattpocock/skills/blob/main/skills/engineering/grill-with-docs/SKILL.md
    as B (trustNumber: 70.0)'
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
