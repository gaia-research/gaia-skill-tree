---
id: mattpocock/improve-codebase-architecture
name: Improve Codebase Architecture
contributor: mattpocock
origin: false
genericSkillRef: refactor-code
status: named
title: The Depth Seeker
catalogRef: mattpocock-improve-codebase-architecture
level: 3★
description: Identifies architectural deepening opportunities in a codebase — shallow
  modules with high interface-to-implementation ratios — using domain-glossary vocabulary
  and the deletion test, then grills the developer on the chosen candidate to design
  a deep-module replacement with better locality and testability.
links:
  github: https://github.com/mattpocock/skills/blob/main/skills/engineering/improve-codebase-architecture/SKILL.md
tags:
- architecture-review
- deep-modules
- refactoring
- locality
- testability
- deletion-test
createdAt: '2026-04-30'
updatedAt: '2026-06-19'
suiteRef: mattpocock/engineering
trustMagnitude: 45.0
overallTrustGrade: C
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
- timestamp: '2026-06-19T12:35:07Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/mattpocock/skills/issues/180 (type:
    peer-review)'
- timestamp: '2026-06-19T12:35:22Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/mattpocock/skills/discussions/287
    (type: peer-review)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T12:53:50Z'
  details: TM 0.0 -> 45.0, grade ungraded -> C (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:38Z'
  details: TM 0.0 -> 45.0, grade ungraded -> C (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:41Z'
  details: TM 0.0 -> 45.0, grade ungraded -> C (direct edit -- CLI gap)
evidence:
- source: https://github.com/mattpocock/skills/issues/180
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: peer-review
  class: A
  notes: GitHub issue about improve-codebase-architecture skill enhancement.
- source: https://github.com/mattpocock/skills/discussions/287
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: peer-review
  class: A
  notes: GitHub discussion about improve-codebase-architecture skill workflow.
verification:
  firstEvidenceAt: '2026-06-19T12:35:07Z'
trustMagnitudeInputHash: a7d3b4e1553ee703b7b7e3258d6e5555323dd1a9451efcabecaa042733d4989b
---

## Overview

Improve Codebase Architecture applies a specific vocabulary of architectural leverage: modules, interfaces, implementations, depth, seams, adapters, and the deletion test. The agent explores the codebase organically looking for shallow modules (interface nearly as complex as the implementation), tightly-coupled modules leaking across seams, and pure functions extracted for testability but hiding the real bugs in their call sites.

Candidate opportunities are presented as a numbered list with files, problem, solution, and benefits framed in terms of locality and leverage. The agent then drops into a grilling loop on the chosen candidate, updating CONTEXT.md as new terms crystallise and offering ADRs only when rejections contain load-bearing reasons a future reviewer would need.

## Origin

Published by @mattpocock (Matt Pocock, Total TypeScript). Named implementation of the `refactor-code` skill bucket for the architecture-analysis-and-deepening use case.

## Installation

This skill is included in the Matt Pocock skills suite. It is highly recommended to install the full suite to enable cross-skill context sharing.

```bash
npx skills@latest add mattpocock/skills
```

No additional setup required beyond the main suite installation.
