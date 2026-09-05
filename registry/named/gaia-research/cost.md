---
id: gaia-research/cost
name: Cost
contributor: gaia-research
origin: false
genericSkillRef: token-observability
status: named
level: 1★
description: CLI + agent skill invoked via /cost. Reads JSONL session logs from pi,
  Claude Code, Codex, opencode; prices every turn against BerriAI/litellm's catalog;
  auto-refreshes prices.
createdAt: '2026-07-30'
updatedAt: '2026-08-30'
title: Cost
links:
  github: https://github.com/gaia-research/skill-cost/blob/main/SKILL.md
timeline:
- timestamp: '2026-07-29T20:14:21Z'
  action: add
  contributor: unknown
  details: Added named skill gaia-research/skill-cost
- timestamp: '2026-07-29T20:17:30Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/gaia-research/skill-cost (type:
    repo-own)'
- timestamp: '2026-07-29T20:17:30Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://research.gaiaskilltree.com/ (type: self-attestation)'
- timestamp: '2026-07-29T20:34:55Z'
  action: demote
  contributor: unknown
  details: Calibrated level from 2★ to 1★
- timestamp: '2026-08-05T06:29:00Z'
  action: rename
  contributor: unknown
  details: Renamed named skill from gaia-research/skill-cost to gaia-research/cost
- timestamp: '2026-08-29T17:15:45Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM (none) -> 5.0, grade (none) -> ungraded (gaia dev calibrate-trust-magnitude;
    Issue #1600)'
evidence:
- source: https://github.com/gaia-research/skill-cost
  evaluator: unknown
  date: '2026-07-30'
  type: repo-own
  notes: Repo 1 star, 0 forks. stdlib-only cost.py parsing session JSONL from pi,
    Claude Code, Codex, opencode, Hermes. Prices via LiteLLM catalog. SKILL.md at
    blob/ path. Stage-1.
  stars: 1
  skillCountInRepo: 1
  sourceStartedAt: '2026-07-30'
- source: https://research.gaiaskilltree.com/
  evaluator: unknown
  date: '2026-07-30'
  type: self-attestation
  notes: Gaia Research lab page lists skill-cost as published installable skill. Owner-org
    self-attestation.
  sourceStartedAt: '2026-07-30'
  grade: C
verification:
  firstEvidenceAt: '2026-07-29T20:17:29Z'
trustMagnitude: 5.0
overallTrustGrade: ungraded
trustMagnitudeInputHash: e0e0c85af22fe0d72a8aeefe6b7dfbef3fefd188bef9985bca6407912f95e1fd
---

## Installation
Add installation instructions here.
