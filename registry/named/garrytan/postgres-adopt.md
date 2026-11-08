---
id: garrytan/postgres-adopt
name: postgres-adopt
contributor: garrytan
origin: false
genericSkillRef: postgres-best-practices
status: named
level: 3★
description: Detect which gbrain engine is in use (PGLite vs Postgres), prefer Postgres
  for agent-harness installs, install/provision Postgres (Supabase discovery via SUPABASE_ACCESS_TOKEN,
  local Postgres, opt-in Docker), and move an existing PGLite brain to Postgres with
  its history (plan, ask, run). Detection is one engine-free command; the install
  ladder is one flag.
createdAt: '2026-11-03'
updatedAt: '2026-11-08'
title: Postgres Adopt
links:
  github: https://github.com/garrytan/gbrain/blob/v0.60.474.0/skills/postgres-adopt/SKILL.md
timeline:
- timestamp: '2026-11-02T21:54:47Z'
  action: add
  contributor: mbtiongson1
  details: Added named skill garrytan/postgres-adopt
- timestamp: '2026-11-02T22:00:25Z'
  action: suite_ref_set
  contributor: mbtiongson1
  details: Set suiteRef to garrytan/gbrain
- timestamp: '2026-11-02T22:00:30Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/garrytan/gbrain/blob/v0.60.474.0/skills/postgres-adopt/SKILL.md
    (type: github-stars-own)'
- timestamp: '2026-11-02T22:15:57Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM (none) -> 55.0, grade (none) -> B (gaia dev calibrate-trust-magnitude;
    Issue #1600)'
- timestamp: '2026-11-08T08:26:48Z'
  action: rank_up
  contributor: mbtiongson1
  details: Calibrated level from 2★ to 3★
suiteRef: garrytan/gbrain
evidence:
- source: https://github.com/garrytan/gbrain/blob/v0.60.474.0/skills/postgres-adopt/SKILL.md
  evaluator: mbtiongson1
  date: '2026-11-03'
  type: github-stars-own
  notes: 'Stage-1 github-stars-own evidence: verified repository stars at tag (subject
    to 50.0 TM suite sibling cap per META §2.1a)'
  stars: 31276
  grade: A
verification:
  firstEvidenceAt: '2026-11-02T22:00:28Z'
trustMagnitude: 55.0
overallTrustGrade: B
trustMagnitudeInputHash: 6157d791d5079dceb29d84e6a7fd90128f4c33d4cb92d1d6c7dafd1298621741
---

## Installation
Add installation instructions here.
