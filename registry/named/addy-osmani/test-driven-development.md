---
id: addy-osmani/test-driven-development
name: Test-Driven Development
contributor: addy-osmani
origin: true
genericSkillRef: test-driven-development
status: named
title: The Red-Green Oath
catalogRef: addy-osmani-test-driven-development
level: 2★
description: Forces the AI agent to follow a strict red-green-refactor TDD workflow
  — explicitly blocking horizontal slicing (all tests first, then all code). Tests
  verify behaviour through public interfaces only, blocking code generation that skips
  the test step, and enforcing coverage thresholds before completing a task.
links:
  github: https://github.com/addyosmani/agent-skills/blob/main/skills/test-driven-development/SKILL.md
tags:
- tdd
- testing
- red-green-refactor
- workflow-enforcement
- software-quality
- vertical-slicing
- tracer-bullet
createdAt: '2026-04-30'
updatedAt: '2026-07-03'
timeline:
- timestamp: '2026-05-31T02:17:00Z'
  action: installation_updated
  contributor: unknown
  details: 'Replaced ## Installation section from /tmp/tdd_install.md'
- timestamp: '2026-06-14T12:32:16Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/addyosmani/agent-skills/blob/main/skills/test-driven-development/SKILL.md
    as B (trustNumber: 70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:14Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T10:36:25Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:37Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:36Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- timestamp: '2026-06-20T06:31:20Z'
  action: demote
  contributor: mbtiongson1
  details: Level updated from 3★ to 2★ per G7 final rankings calibration.
- timestamp: '2026-07-02T18:42:38Z'
  action: suite_ref_set
  contributor: unknown
  details: Set suiteRef to addy-osmani/agent-skills
evidence:
- class: B
  source: https://github.com/addyosmani/agent-skills/blob/main/skills/test-driven-development/SKILL.md
  evaluator: mbtiongson1
  date: '2026-04-30'
  notes: 'Addy Osmani /test-driven-development slash command -- forces strict TDD
    workflow, stopping agents from skipping tests. (backfilled — class-to-type migration)
    (CLI gap: commits+contributors not writable via gaia dev evidence)'
  type: repo
  commits: 260
  contributors: 36
  trustNumber: 70.0
  grade: B
trustMagnitude: 36.0
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
trustMagnitudeInputHash: 650f0466e751f4446ba928c959d5b8aa50cb4ff5b844c60a905f3f41f4286fa0
suiteRef: "addy-osmani/agent-skills"
---

## Overview

TDD is a workflow-enforcement skill that constrains the agent to the classic red-green-refactor cycle. Before writing any implementation, the agent must write a failing test that specifies the desired behavior. It is blocked from proceeding until the test exists and fails for the right reason.

This variant distinguishes itself by making the vertical-slice constraint explicit and enforced. The agent is explicitly blocked from the "horizontal slicing" anti-pattern (writing all tests first, then all code), which produces tests that verify imagined behaviour and become insensitive to real changes. Each cycle follows a tracer-bullet model: one failing test → minimal code to pass → repeat, never anticipating future tests.

## Origin

First published by @addyosmani (Addy Osmani) and expanded with constraints popularised by @mattpocock. This is the origin implementation for the `test-driven-development` skill bucket.

## Installation

This skill is included in the Addy Osmani agent skills suite. Install the suite with:

```bash
/plugin marketplace add addyosmani/agent-skills
/plugin install agent-skills@addy-agent-skills
```

Invoke the matching slash command from the installed suite.
