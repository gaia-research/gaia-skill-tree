---
id: mattpocock/diagnose
name: Diagnose
contributor: mattpocock
origin: false
genericSkillRef: autonomous-debug
status: named
title: The Disciplined Diagnosis Loop
catalogRef: mattpocock-diagnose
level: 2★
description: Drives a rigorous five-phase debugging discipline — build a feedback
  loop, minimise, hypothesise, instrument, fix and regression-test — refusing to proceed
  until a fast deterministic pass/fail signal exists. Applies to hard bugs and performance
  regressions. Removed from mattpocock/skills suite in v1.0.1.
links:
  github: https://github.com/mattpocock/skills/blob/main/skills/engineering/diagnose/SKILL.md
tags:
- debugging
- diagnosis
- feedback-loop
- regression
- root-cause-analysis
createdAt: '2026-04-30'
updatedAt: '2026-06-14'
evidence:
- class: B
  source: https://github.com/mattpocock/skills/blob/main/skills/engineering/diagnose/SKILL.md
  evaluator: mbtiongson1
  date: '2026-06-10'
  notes: 'Published implementation in Matt Pocock''s skills repository; five-phase
    debugging" discipline documented and reproducible. (backfilled — class-to-type
    migration) (CLI gap: --commits/--contributors not supported by gaia dev evidence)'
  type: repo
  trustNumber: 70.0
  grade: B
  commits: 137
  contributors: 3
timeline:
- timestamp: '2026-06-10T05:38:16Z'
  action: evidence_added
  contributor: unknown
  details: Added B evidence from https://github.com/mattpocock/skills/blob/main/skills/engineering/diagnose/SKILL.md
- timestamp: '2026-06-14T12:32:42Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/mattpocock/skills/blob/main/skills/engineering/diagnose/SKILL.md
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
verification:
  firstEvidenceAt: '2026-06-10T05:38:16Z'
suiteRef: mattpocock/engineering
trustMagnitudeInputHash: 1f6fcb93fe1c868de47375eb417c24f6451ee60328294f5f8001ab64859cbd10
---

## Overview

Diagnose by Matt Pocock enforces a disciplined debugging workflow structured as five explicit phases: (1) build a feedback loop, (2) minimise the reproduction, (3) generate and rank hypotheses, (4) instrument and test, (5) fix and write a regression test. The defining insight is Phase 1 — the agent spends disproportionate effort constructing a fast, deterministic, agent-runnable pass/fail signal before any other work. Without that signal, no amount of code inspection converges.

The skill covers a wide range of reproduction strategies: failing unit tests, curl/HTTP scripts against a running dev server, CLI invocations diffed against known-good snapshots, headless browser scripts, replay of captured traces, throwaway harnesses, and property/fuzz loops. Phases after Phase 1 are mechanical once the signal exists.

## Origin

First published by @mattpocock (Matt Pocock, Total TypeScript). This is a named implementation of the `autonomous-debug` skill bucket emphasising the feedback-loop-first philosophy.

## Installation

This skill is included in the Matt Pocock skills suite. It is highly recommended to install the full suite to enable cross-skill context sharing.

```bash
npx skills@latest add mattpocock/skills
```

No additional setup required beyond the main suite installation.
