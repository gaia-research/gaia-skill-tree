---
id: garrytan/schema-unify
name: schema-unify
contributor: garrytan
origin: false
genericSkillRef: schema-design
status: named
level: 2★
description: Migrate a brain from gbrain-base (or any pack) to gbrain-base-v2's 14-canonical-type
  taxonomy via gbrain onboard --check + the unify-types Minion handler. Collapses
  94 noisy types to 15 canonical with subtypes, alias rows, and link rows. Triggers
  when an agent notices pack_upgrade_available, type_proliferation, or asks "what
  is the canonical taxonomy / how do I clean up my page types".
createdAt: '2026-11-03'
updatedAt: '2026-11-09'
title: Schema Unify
links:
  github: https://github.com/garrytan/gbrain/blob/v0.60.474.0/skills/schema-unify/SKILL.md
timeline:
- timestamp: '2026-11-02T21:54:56Z'
  action: add
  contributor: mbtiongson1
  details: Added named skill garrytan/schema-unify
- timestamp: '2026-11-02T22:01:24Z'
  action: suite_ref_set
  contributor: mbtiongson1
  details: Set suiteRef to garrytan/gbrain
- timestamp: '2026-11-02T22:01:28Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/garrytan/gbrain/blob/v0.60.474.0/skills/schema-unify/SKILL.md
    (type: github-stars-own)'
- timestamp: '2026-11-02T22:16:08Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM (none) -> 50.0, grade (none) -> B (gaia dev calibrate-trust-magnitude;
    Issue #1600)'
- timestamp: '2026-11-08T18:18:21Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM 50.0 -> 49.9, grade B -> C (gaia dev calibrate-trust-magnitude; Issue
    #1600)'
suiteRef: garrytan/gbrain
evidence:
- source: https://github.com/garrytan/gbrain/blob/v0.60.474.0/skills/schema-unify/SKILL.md
  evaluator: mbtiongson1
  date: '2026-11-03'
  type: github-stars-own
  notes: 'Stage-1 github-stars-own evidence: verified repository stars at tag (subject
    to 50.0 TM suite sibling cap per META §2.1a)'
  stars: 31276
  grade: A
verification:
  firstEvidenceAt: '2026-11-02T22:01:26Z'
trustMagnitude: 49.9
overallTrustGrade: C
trustMagnitudeInputHash: cb2f52134d99a5c10bc89ed68c6071ab469a3901612566d5fb73f2633b1c8f61
---

## Installation
Add installation instructions here.
