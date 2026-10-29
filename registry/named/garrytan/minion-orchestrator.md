---
id: garrytan/minion-orchestrator
name: minion-orchestrator
contributor: garrytan
origin: false
genericSkillRef: multi-agent-orchestration-v
status: named
level: 2★
description: 'Unified Minions skill for both deterministic shell jobs and LLM subagent

  orchestration. Replaces the older `gbrain-jobs` routing intent. Use when:

  submitting gbrain jobs, shell/background tasks, spawning subagents,

  checking progress, steering running work, pausing/resuming, parallel

  fan-out. One durable, observable, steerable queue interface. Also carries

  the durable-execution doctrine for any operation expected to exceed ~2

  minutes: capability ladder, deadman checks that verify the result was

  reported, and content-addressed stage checkpoints for expensive pipelines.'
createdAt: '2026-09-23'
updatedAt: '2026-10-30'
title: minion-orchestrator
links:
  github: https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/minion-orchestrator/SKILL.md
timeline:
- timestamp: '2026-09-23T06:08:10Z'
  action: add
  contributor: unknown
  details: Added named skill garrytan/minion-orchestrator
- timestamp: '2026-10-29T16:55:40Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/minion-orchestrator/SKILL.md
    (type: github-stars-own)'
- timestamp: '2026-10-29T16:55:41Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/garrytan/gbrain (type: repo-own)'
- timestamp: '2026-10-29T16:56:48Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM (none) -> 158.36, grade (none) -> A (gaia dev calibrate-trust-magnitude;
    Issue #1600)'
evidence:
- source: https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/minion-orchestrator/SKILL.md
  evaluator: mbtiongson1
  date: '2026-10-29'
  type: github-stars-own
  notes: 'GitHub REST stargazers_count of garrytan/gbrain at 2026-10-29 (host suite
    repo); skill-file blob link verified HTTP 200 at its pinned ref. Founder ruling
    2026-10-30 FD-7: skill was added at intake (2026-09-23) with no evidence rows.'
  stars: 31330
  skillCountInRepo: 71
  sourceStartedAt: '2026-04-05'
  grade: A
- source: https://github.com/garrytan/gbrain
  evaluator: mbtiongson1
  date: '2026-10-29'
  type: repo-own
  notes: GitHub REST default-branch commit count and contributor count of garrytan/gbrain
    at 2026-10-29; host-repository maintenance, not independent quality evidence.
    Founder ruling 2026-10-30 FD-7.
  commits: 11443
  contributors: 136
  sourceStartedAt: '2026-04-05'
  grade: B
verification:
  firstEvidenceAt: '2026-10-29T16:55:40Z'
trustMagnitude: 158.36
overallTrustGrade: A
trustMagnitudeInputHash: 96390b60b2a24db676d249485895e63aa40cb1e758625187c84fa25aed5d8c2f
---

## Installation
Add installation instructions here.
