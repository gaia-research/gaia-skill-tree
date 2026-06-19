---
id: mattpocock/productivity
name: Productivity
contributor: mattpocock
origin: true
title: The Matt Pocock Productivity Suite
genericSkillRef: productivity
status: named
level: 4★
description: Productivity category suite for Matt Pocock's skills. Removed from mattpocock/skills
  suite in v1.0.1.
createdAt: '2026-05-21'
updatedAt: '2026-06-10'
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
timeline:
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:18Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:38Z'
  details: TM 0.0 -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
suiteRef: mattpocock/skills
suiteComponents:
- mattpocock/caveman
- mattpocock/grill-me
- mattpocock/handoff
- mattpocock/write-a-skill
---

## Overview

The Matt Pocock Productivity Suite bundles four skills that optimise the agent-developer feedback loop: Caveman Mode compresses communication to save tokens by dropping articles and filler words; Grill Me conducts a one-question-at-a-time design interview, substituting codebase exploration for empirically answerable questions; Handoff compacts the current conversation into a summary ready for a fresh agent context; and Write a Skill scaffolds new agent skills through a structured interview that produces a trigger-aware SKILL.md with progressive-disclosure layout. The suite covers the cognitive overhead of working with agents — prompt economy, design clarity, context continuity, and skill authoring.

## Installation

This skill is included in the Matt Pocock skills suite. It is highly recommended to install the full suite to enable cross-skill context sharing.

```bash
npx skills@latest add mattpocock/skills
```

No additional setup required beyond the main suite installation.
