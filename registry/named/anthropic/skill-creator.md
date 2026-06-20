---
id: anthropic/skill-creator
name: Skill Creator
contributor: anthropic
origin: false
genericSkillRef: tool-creation
status: named
title: The Skill Forger's Art
catalogRef: anthropic-skill-creator
level: 3★
description: Interviews the user through a structured dialogue to elicit the skill's
  purpose, trigger conditions, and step-by-step instructions, then programmatically
  writes a new SKILL.md file ready for use in a Claude Code or Codex CLI skills directory.
links:
  github: https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md
tags:
- skill-authoring
- meta-agent
- claude-code
- tool-creation
createdAt: '2026-04-30'
updatedAt: '2026-06-19'
timeline:
- timestamp: '2026-06-02T23:33:00Z'
  action: demote
  contributor: unknown
  details: Origin status removed. Transferred to mattpocock/write-a-skill.
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:14Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- timestamp: '2026-06-19T09:22:07Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://arxiv.org/abs/2305.17126 (type: arxiv)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T09:29:08Z'
  details: TM 0.0 -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T09:34:46Z'
  details: TM 0.0 -> 60.0, grade ungraded -> B (direct edit -- CLI gap)
- timestamp: '2026-06-19T10:42:49Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://dev.to/debs_obrien/i-used-skill-creator-v2-to-improve-one-of-my-agent-skills-in-vs-code-fhd
    (type: social-signal)'
- timestamp: '2026-06-19T10:47:43Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md
    (type: peer-review)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T10:52:24Z'
  details: TM 60.0 -> 90.0, grade B -> B (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:37Z'
  details: TM 0.0 -> 90.0, grade ungraded -> B (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:36Z'
  details: TM 0.0 -> 90.0, grade ungraded -> B (direct edit -- CLI gap)
- timestamp: '2026-06-20T06:31:20Z'
  action: rank_up
  contributor: mbtiongson1
  details: Level updated from 2★ to 3★ per G7 final rankings calibration.
trustMagnitude: 90.0
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
evidence:
- source: https://arxiv.org/abs/2305.17126
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: arxiv
  class: A
  notes: Toolformer / self-expanding agent paper — ~300 citations as of 2026-06-19
    (arXiv:2305.17126)
  citations: 300
- source: https://dev.to/debs_obrien/i-used-skill-creator-v2-to-improve-one-of-my-agent-skills-in-vs-code-fhd
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: social-signal
  class: A
  notes: DEV.to article by Debbie O'Brien on using Skill Creator v2 to improve agent
    skills in VS Code. Community practitioner.
- source: https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: peer-review
  class: A
  notes: 'Claude Code community: engineering discipline for prompt engineering praised,
    A/B eval harness noted for overhead on long refinement loops. Mid-2026.'
verification:
  firstEvidenceAt: '2026-06-19T09:22:07Z'
trustMagnitudeInputHash: 3592919611bbbcfc966da0c18437884dd159bd12c456e8a040f74478585295c9
---

## Overview

Skill Creator is a meta-agent skill that turns the agent into an interactive skill author. It conducts a structured interview with the user — asking about the skill's name, trigger phrase, inputs, and expected outputs — then generates a fully-formed `SKILL.md` file. The output is immediately installable in any Claude Code, Cursor, or Codex CLI skills directory.

## Origin

First published by @anthropic. This is the origin implementation for the `tool-creation` skill bucket under the agent-skill-authoring use case.
