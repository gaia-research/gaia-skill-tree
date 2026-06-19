---
id: mattpocock/grill-me
name: Grill Me
contributor: mattpocock
origin: false
genericSkillRef: grill-me
status: named
title: The Relentless Interviewer
catalogRef: mattpocock-grill-me
level: 4★
description: Conducts a relentless one-question-at-a-time interview about a plan or
  design, walking every branch of the decision tree with a recommended answer per
  question, resolving dependencies in order, and substituting codebase exploration
  wherever a question can be answered empirically.
links:
  github: https://github.com/mattpocock/skills/blob/main/skills/productivity/grill-me/SKILL.md
tags:
- design-review
- decision-tree
- socratic-method
- plan-stress-test
- one-question-at-a-time
createdAt: '2026-04-30'
updatedAt: '2026-06-14'
suiteRef: mattpocock/productivity
evidence:
- class: B
  source: https://github.com/mattpocock/skills/blob/main/skills/productivity/grill-me/SKILL.md
  evaluator: mbtiongson1
  date: '2026-05-15'
  notes: "Original implementation by Matt Pocock; viral engineering pattern for disciplined\" agent alignment. (backfilled — class-to-type migration) (CLI gap: --commits/--contributors not supported by gaia dev evidence)"
  type: repo
  trustNumber: 70.0
  grade: B
  commits: 137
  contributors: 3
timeline:
- timestamp: '2026-06-14T12:32:43Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/mattpocock/skills/blob/main/skills/productivity/grill-me/SKILL.md
    as B (trustNumber: 70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:18Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
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
trustMagnitudeInputHash: 90f863093ccde55b568743eb8c28bcc7ab1c5b3e82627d14a2484e6080a07111
---

## Overview

Grill Me is the lightweight, documentation-free variant of the design-grilling pattern. It does not require a CONTEXT.md or ADR infrastructure. The agent interviews the user about every aspect of their plan, resolving decision-tree branches one dependency at a time. Each question comes paired with the agent's recommended answer to keep the conversation actionable.

Where a question can be answered by reading the codebase directly, the agent explores the codebase instead of asking. This substitution prevents unnecessary back-and-forth on empirically determinable facts.

## Origin

Second named implementation of the `design-review` skill bucket (origin: mattpocock/grill-with-docs). Grill Me is the simpler variant — no domain-model integration or documentation side effects.

## Installation

This skill is included in the Matt Pocock skills suite. It is highly recommended to install the full suite to enable cross-skill context sharing.

```bash
npx skills@latest add mattpocock/skills
```

No additional setup required beyond the main suite installation.
