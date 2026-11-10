---
id: garrytan/smoke-test
name: smoke-test
contributor: garrytan
origin: false
genericSkillRef: automated-testing
status: named
level: 2★
description: Health smoke tests + auto-fix for gbrain installs (and OpenClaw services
  when present). Run after machine/container restarts or whenever something seems
  broken. Tests critical services, auto-fixes bounded local issues, and reports worker
  topology without starting daemons. Extensible via user-defined test scripts in ~/.gbrain/smoke-tests.d/*.sh.
createdAt: '2026-11-03'
updatedAt: '2026-11-09'
title: Smoke Test
links:
  github: https://github.com/garrytan/gbrain/blob/v0.60.474.0/skills/smoke-test/SKILL.md
timeline:
- timestamp: '2026-11-02T21:55:00Z'
  action: add
  contributor: mbtiongson1
  details: Added named skill garrytan/smoke-test
- timestamp: '2026-11-02T22:01:47Z'
  action: suite_ref_set
  contributor: mbtiongson1
  details: Set suiteRef to garrytan/gbrain
- timestamp: '2026-11-02T22:01:50Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/garrytan/gbrain/blob/v0.60.474.0/skills/smoke-test/SKILL.md
    (type: github-stars-own)'
- timestamp: '2026-11-02T22:16:12Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM (none) -> 50.0, grade (none) -> B (gaia dev calibrate-trust-magnitude;
    Issue #1600)'
- timestamp: '2026-11-08T18:18:34Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM 50.0 -> 49.9, grade B -> C (gaia dev calibrate-trust-magnitude; Issue
    #1600)'
suiteRef: garrytan/gbrain
evidence:
- source: https://github.com/garrytan/gbrain/blob/v0.60.474.0/skills/smoke-test/SKILL.md
  evaluator: mbtiongson1
  date: '2026-11-03'
  type: github-stars-own
  notes: 'Stage-1 github-stars-own evidence: verified repository stars at tag (subject
    to 50.0 TM suite sibling cap per META §2.1a)'
  stars: 31276
  grade: A
verification:
  firstEvidenceAt: '2026-11-02T22:01:49Z'
trustMagnitude: 49.9
overallTrustGrade: C
trustMagnitudeInputHash: 7707c571d38338cd23ba9d62b26948c474f5e99caa4f8a26454c008a17f31b2b
---

## Installation
Add installation instructions here.
