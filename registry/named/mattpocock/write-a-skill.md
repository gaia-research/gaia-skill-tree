---
id: mattpocock/write-a-skill
name: Write a Skill
contributor: mattpocock
origin: true
genericSkillRef: tool-creation
status: named
title: The Skill Scaffolder
catalogRef: mattpocock-write-a-skill
level: 2★
description: Guides creation of new agent skills through a structured requirements
  interview, then produces a SKILL.md with a trigger-aware description, progressive-disclosure
  layout, and optional bundled scripts or reference files — ready for installation
  in any Claude Code, Cursor, or Codex CLI skills directory. Removed from mattpocock/skills
  suite in v1.0.1.
links:
  github: https://github.com/mattpocock/skills/blob/main/skills/productivity/write-a-skill/SKILL.md
tags:
- skill-authoring
- meta-agent
- claude-code
- skill-scaffolding
- progressive-disclosure
createdAt: '2026-04-30'
updatedAt: '2026-06-19'
timeline:
- timestamp: '2026-06-02T23:33:00Z'
  action: rank_up
  contributor: unknown
  details: Origin status set to true.
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:18Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- timestamp: '2026-06-19T12:38:21Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/mattpocock/skills/issues/271 (type:
    peer-review)'
- timestamp: '2026-06-19T12:38:37Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/mattpocock/skills/discussions/246
    (type: peer-review)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T12:53:50Z'
  details: TM 0.0 -> 45.0, grade ungraded -> C (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:38Z'
  details: TM 0.0 -> 45.0, grade ungraded -> C (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:42Z'
  details: TM 0.0 -> 45.0, grade ungraded -> C (direct edit -- CLI gap)
- timestamp: '2026-06-20T06:31:33Z'
  action: demote
  contributor: mbtiongson1
  details: Level updated from 3★ to 2★ per G7 final rankings calibration.
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
evidence:
- source: https://github.com/mattpocock/skills/issues/271
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: peer-review
  class: A
  notes: GitHub issue about write-a-skill skill documentation contradiction.
- source: https://github.com/mattpocock/skills/discussions/246
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: peer-review
  class: A
  notes: GitHub discussion comparing write-a-skill skill with skill-creator.
verification:
  firstEvidenceAt: '2026-06-19T12:38:21Z'
suiteRef: mattpocock/productivity
trustMagnitudeInputHash: 1d906afe9a855f5ede2526bbb6693737df6c39405057dbb08ba7d96fa6abd8c5
---

## Overview

Write a Skill is a meta-agent skill that walks the author through a structured interview (task domain, use cases, need for scripts, reference materials) before generating a SKILL.md. The output follows progressive-disclosure principles: the description field is crafted as the sole trigger signal visible to the agent at selection time (max 1024 chars, "use when…" pattern), and the body is split across SKILL.md, REFERENCE.md, and EXAMPLES.md when content exceeds 100 lines.

The skill also codifies the decision rules for when to bundle scripts (deterministic operations that would otherwise be regenerated each turn) and when to split files (distinct domains, rarely-needed advanced features).

## Origin

Second named implementation of the `tool-creation` skill bucket (origin: anthropic/skill-creator). Matt Pocock's version emphasises progressive disclosure, the trigger-description contract, and the scripts-vs-instructions decision rubric.

## Installation

This skill is included in the Matt Pocock skills suite. It is highly recommended to install the full suite to enable cross-skill context sharing.

```bash
npx skills@latest add mattpocock/skills
```

No additional setup required beyond the main suite installation.
