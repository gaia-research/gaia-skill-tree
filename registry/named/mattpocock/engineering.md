---
id: mattpocock/engineering
name: Engineering
contributor: mattpocock
origin: true
title: The Matt Pocock Engineering Discipline
genericSkillRef: engineering-discipline
status: named
level: 5★
description: Engineering category suite for Matt Pocock's skills. Removed from mattpocock/skills
  suite in v1.0.1.
createdAt: '2026-05-21'
updatedAt: '2026-06-10'
trustMagnitude: 270.0
overallTrustGrade: A
apexGateStatus:
  aGradedOriginsGte5: false
  sourceTenureDaysGte180AorS: false
  directNestedSuiteGte1: false
  depth2OnlyReachableGte1: false
  overallGradeS: false
  apexPromotionPrSigned: false
  crossOrgVerifier: null
  systemWideCap: null
timeline:
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:18Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:38Z'
  details: TM 0.0 -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:41Z'
  details: TM 0.0 -> 270.0, grade ungraded -> A (direct edit -- CLI gap)
suiteRef: mattpocock/skills
suiteComponents:
- mattpocock/diagnose
- mattpocock/grill-with-docs
- mattpocock/improve-codebase-architecture
- mattpocock/prototype
- mattpocock/setup-matt-pocock-skills
- mattpocock/to-issues
- mattpocock/to-prd
- mattpocock/triage
- mattpocock/ubiquitous-language
- mattpocock/zoom-out
trustMagnitudeInputHash: 4c0c7b233e624b41fc0b52204b68f31891b2e5d33b311a17b288573ab2927bca
---

## Overview

The Matt Pocock Engineering Discipline is a suite of ten complementary skills that cover the full engineering workflow: orientation (Zoom Out, Triage), diagnosis (Diagnose), design review (Grill with Docs, Improve Codebase Architecture), decomposition (To PRD, To Issues), domain modelling (Ubiquitous Language), rapid validation (Prototype), and onboarding (Setup Matt Pocock Skills). The skills are designed to be used together — Zoom Out and Triage orient the agent, Diagnose drives a feedback-loop-first debugging discipline, To PRD and To Issues decompose work into tracked units, and Improve Codebase Architecture deepens modules using the domain glossary produced by Ubiquitous Language.

The defining principle across the suite is incremental grounding: every skill surfaces the domain vocabulary and constraints before generating output, so the agent's reasoning stays anchored to the actual codebase rather than to generic patterns.

## Installation

This skill is included in the Matt Pocock skills suite. It is highly recommended to install the full suite to enable cross-skill context sharing.

```bash
npx skills@latest add mattpocock/skills
```

No additional setup required beyond the main suite installation.
