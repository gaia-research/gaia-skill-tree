---
id: garrytan/data-loss-gate
name: data-loss-gate
contributor: garrytan
origin: false
genericSkillRef: guardrails
status: named
level: 2★
description: Confirmation gate before any bulk delete, cleanup, or destructive operation
  that could result in data loss — shell-level (rm -rf, git rm, bulk sed) or brain-level
  (bulk forget, delete sweeps, purge-deleted, source removal, raw-SQL truncation).
  Presents a recoverability card and requires an explicit "yes" from the user before
  proceeding. Routing convention, not an operation-boundary enforcement.
createdAt: '2026-11-03'
updatedAt: '2026-11-09'
title: Data Loss Gate
links:
  github: https://github.com/garrytan/gbrain/blob/v0.60.474.0/skills/data-loss-gate/SKILL.md
timeline:
- timestamp: '2026-11-02T21:54:30Z'
  action: add
  contributor: mbtiongson1
  details: Added named skill garrytan/data-loss-gate
- timestamp: '2026-11-02T21:58:44Z'
  action: suite_ref_set
  contributor: mbtiongson1
  details: Set suiteRef to garrytan/gbrain
- timestamp: '2026-11-02T21:58:48Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/garrytan/gbrain/blob/v0.60.474.0/skills/data-loss-gate/SKILL.md
    (type: github-stars-own)'
- timestamp: '2026-11-02T22:15:39Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM (none) -> 50.0, grade (none) -> B (gaia dev calibrate-trust-magnitude;
    Issue #1600)'
- timestamp: '2026-11-08T18:17:23Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM 50.0 -> 49.9, grade B -> C (gaia dev calibrate-trust-magnitude; Issue
    #1600)'
suiteRef: garrytan/gbrain
evidence:
- source: https://github.com/garrytan/gbrain/blob/v0.60.474.0/skills/data-loss-gate/SKILL.md
  evaluator: mbtiongson1
  date: '2026-11-03'
  type: github-stars-own
  notes: 'Stage-1 github-stars-own evidence: verified repository stars at tag (subject
    to 50.0 TM suite sibling cap per META §2.1a)'
  stars: 31276
  grade: A
verification:
  firstEvidenceAt: '2026-11-02T21:58:47Z'
trustMagnitude: 49.9
overallTrustGrade: C
trustMagnitudeInputHash: 48b0c8c8c75845e3d110b6339ec620ce45d8d1c473e6c38510271ec1e034ac4e
---

## Installation
Add installation instructions here.
