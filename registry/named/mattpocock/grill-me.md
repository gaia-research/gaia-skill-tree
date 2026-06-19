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
updatedAt: '2026-06-19'
suiteRef: mattpocock/productivity
evidence:
- class: B
  source: https://github.com/mattpocock/skills/blob/main/skills/productivity/grill-me/SKILL.md
  evaluator: mbtiongson1
  date: '2026-05-15'
  notes: 'Original implementation by Matt Pocock; viral engineering pattern for disciplined"
    agent alignment. (backfilled — class-to-type migration) (CLI gap: --commits/--contributors
    not supported by gaia dev evidence)'
  type: repo
  trustNumber: 70.0
  grade: B
  commits: 137
  contributors: 3
- source: https://github.com/mattpocock/skills/discussions
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: peer-review
  class: A
  notes: 'GitHub Discussions: 7+ threads naming grill-me directly (usage patterns,
    cross-skill combos, model behaviour). 136k-star suite, 24.8k-follower creator.
    Named-layer: skill referenced by name.'
- source: https://github.com/mattpocock/skills/issues/240
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: peer-review
  class: A
  notes: 'Issue #240: ''GPT 5.5 jumps to implementation after /grill-me'' — 11 comments,
    highest-engagement grill-me issue. Cross-model adoption signal. Named-layer.'
- source: https://github.com/mattpocock/skills/issues/311
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: peer-review
  class: A
  notes: 'Issue #311: ''grill-me: no durable output artifact'' — 5 comments, active
    users reporting real-world usage gaps. Named-layer.'
- source: https://www.youtube.com/@mattpocockuk
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: social-signal
  class: A
  notes: 'Matt Pocock official YouTube channel (Total TypeScript) — creator of grill-me.
    Skills suite featured on channel, 136k-star repo. topicalAuthority creator_mult:
    creator is the named contributor.'
timeline:
- timestamp: '2026-06-14T12:32:43Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/mattpocock/skills/blob/main/skills/productivity/grill-me/SKILL.md
    as B (trustNumber: 70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:18Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T11:52:12Z'
  details: TM 0.0 -> 11.21, grade ungraded -> ungraded (direct edit -- CLI gap)
- timestamp: '2026-06-19T12:00:20Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/mattpocock/skills/discussions (type:
    peer-review)'
- timestamp: '2026-06-19T12:01:12Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/mattpocock/skills/issues/240 (type:
    peer-review)'
- timestamp: '2026-06-19T12:01:26Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/mattpocock/skills/issues/311 (type:
    peer-review)'
- timestamp: '2026-06-19T12:02:36Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://www.youtube.com/@mattpocockuk (type: social-signal)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T12:03:11Z'
  details: TM 11.21 -> 63.71, grade ungraded -> B (direct edit -- CLI gap)
trustMagnitude: 63.71
overallTrustGrade: B
apexGateStatus:
  aGradedOriginsGte5: false
  sourceTenureDaysGte180AorS: false
  directNestedSuiteGte1: false
  depth2OnlyReachableGte1: false
  overallGradeS: false
  apexPromotionPrSigned: false
  crossOrgVerifier: null
  systemWideCap: null
trustMagnitudeInputHash: 30bc9817067da539afe196bfd380ce60d5440ec35463b0ee9314833b27bbfaae
verification:
  firstEvidenceAt: '2026-06-19T12:00:13Z'
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
