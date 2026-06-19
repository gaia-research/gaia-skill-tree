---
id: mattpocock/triage
name: Triage
contributor: mattpocock
origin: true
genericSkillRef: issue-triage
status: named
title: The State-Machine Triager
catalogRef: mattpocock-triage
level: 3★
description: Moves GitHub issues through a two-category (bug/enhancement) × five-state
  (needs-triage/needs-info/ready-for-agent/ready-for-human/wontfix) state machine.
  Reproduces bugs from issue steps, runs a domain-aware grilling session when needed,
  writes structured agent briefs, and appends AI-generated triage notes with the required
  disclaimer.
links:
  github: https://github.com/mattpocock/skills/blob/main/skills/engineering/triage/SKILL.md
tags:
- issue-triage
- state-machine
- bug-reproduction
- agent-brief
- github-issues
createdAt: '2026-04-30'
updatedAt: '2026-06-14'
suiteRef: mattpocock/engineering
evidence:
- class: B
  source: https://github.com/mattpocock/skills/blob/main/skills/engineering/triage/SKILL.md
  evaluator: mbtiongson1
  date: '2026-04-30'
  notes: "Production triage skill with state-machine workflow, HITL/AFK routing, and\" structured agent-brief output. (backfilled — class-to-type migration) (CLI gap: --commits/--contributors not supported by gaia dev evidence)"
  type: repo
  trustNumber: 70.0
  grade: B
  commits: 137
  contributors: 3
timeline:
- timestamp: '2026-06-14T12:32:44Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/mattpocock/skills/blob/main/skills/engineering/triage/SKILL.md
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
trustMagnitudeInputHash: 069837d2974cd1d37131c79ea042ec49dfdae8d3bb6c70a596f0fb4a8195e64b
---

## Overview

Triage implements a deterministic triage state machine on top of a project issue tracker. The agent reads all existing triage notes to avoid re-asking resolved questions, attempts bug reproduction via code tracing and test execution before any grilling, and applies exactly one category role and one state role per issue.

For `ready-for-agent` issues the skill produces a structured agent brief. For `wontfix` enhancements it writes a `.out-of-scope/*.md` knowledge-base entry and links to it before closing. All comments must start with the AI-generation disclaimer. The maintainer can invoke quick state overrides bypassing grilling.

## Origin

First published by @mattpocock (Matt Pocock, Total TypeScript). This is the origin implementation for the `issue-triage` skill bucket.

## Installation

This skill is included in the Matt Pocock skills suite. It is highly recommended to install the full suite to enable cross-skill context sharing.

```bash
npx skills@latest add mattpocock/skills
```

No additional setup required beyond the main suite installation.
