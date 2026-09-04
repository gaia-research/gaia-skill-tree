---
id: mattpocock/engineering
name: Engineering
contributor: mattpocock
origin: true
title: The Matt Pocock Engineering Discipline
genericSkillRef: engineering-discipline
status: named
level: 4★
description: Engineering category suite for Matt Pocock's skills. Removed from mattpocock/skills
  suite in v1.0.1.
createdAt: '2026-05-21'
updatedAt: '2026-08-20'
trustMagnitude: 351.96
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
- timestamp: '2026-06-20T06:31:31Z'
  action: demote
  contributor: mbtiongson1
  details: Level updated from 5★ to 4★ per G7 final rankings calibration.
- timestamp: '2026-07-20T18:16:45Z'
  action: type_change
  contributor: mbtiongson1
  details: 'Generic parent ''engineering-discipline'' type: extra/ultimate → fusion
    (Yggdrasil II taxonomy migration #997)'
  metaEpoch: yggdrasil-ii
  migrationBatch: yggdrasil-ii@2026-07-20
- timestamp: '2026-08-20T04:49:27Z'
  action: suite_ref_set
  contributor: mbtiongson1
  details: Set suiteRef=mattpocock/engineering, genericSkillRef=engineering-discipline
    via `gaia dev fuse`.
- timestamp: '2026-08-20T04:52:44Z'
  action: suite_ref_set
  contributor: mbtiongson1
  details: Set suiteRef to mattpocock/skills
- timestamp: '2026-08-20T09:30:05Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM 270.0 -> 351.96, grade A -> A (gaia dev calibrate-trust-magnitude;
    Issue #1600)'
suiteRef: mattpocock/skills
trustMagnitudeInputHash: 84bb03bde46f1e5dbf730b2f8ee2abbfd93c5cd04481b6dcb983bfbe04e0a6b4
suiteComponents:
- mattpocock/code-review
- mattpocock/diagnose
- mattpocock/grill-with-docs
- mattpocock/improve-codebase-architecture
- mattpocock/prototype
- mattpocock/research
- mattpocock/setup-matt-pocock-skills
- mattpocock/to-spec
- mattpocock/to-tickets
- mattpocock/triage
- mattpocock/ubiquitous-language
- mattpocock/wayfinder
- mattpocock/wizard
- mattpocock/zoom-out
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
