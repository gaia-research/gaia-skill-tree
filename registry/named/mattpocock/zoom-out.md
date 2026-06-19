---
id: mattpocock/zoom-out
name: Zoom Out
contributor: mattpocock
origin: true
genericSkillRef: code-explain
status: named
title: The Abstraction Lift
catalogRef: mattpocock-zoom-out
level: 2★
description: Signals the agent to ascend one layer of abstraction and produce a map
  of all relevant modules, callers, and domain-glossary terms in the unfamiliar code
  area, without explaining implementation details. Removed from mattpocock/skills suite in v1.0.1.
links:
  github: https://github.com/mattpocock/skills/blob/main/skills/engineering/zoom-out/SKILL.md
tags:
- code-navigation
- abstraction
- module-map
- domain-glossary
- codebase-orientation
createdAt: '2026-04-30'
updatedAt: '2026-04-30'
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
trustMagnitudeInputHash: 2d68edb314be3bd508fa140c4d61b80f43a6b67f52ddb9dc2fe6e11a04f68661
timeline:
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:18Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
suiteRef: "mattpocock/engineering"
---

## Overview

Zoom Out is a lightweight orientation directive: when the agent is unfamiliar with a section of code it triggers a single upward shift in abstraction level. Rather than explaining individual lines, the agent produces a module-and-caller map using the project's domain glossary vocabulary — giving the human (or an orchestrating agent) a navigational overview before drilling down.

The skill is intentionally minimal (`disable-model-invocation: true` in its source) and functions as a meta-signal to reframe from implementation to architecture.

## Origin

First published by @mattpocock (Matt Pocock, Total TypeScript). This is the origin implementation for the `code-explain` skill bucket's orientation/abstraction-lifting use case.

## Installation

This skill is included in the Matt Pocock skills suite. It is highly recommended to install the full suite to enable cross-skill context sharing.

```bash
npx skills@latest add mattpocock/skills
```

No additional setup required beyond the main suite installation.
