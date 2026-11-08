---
id: garrytan/gbrain-upgrade
name: gbrain-upgrade
contributor: garrytan
origin: false
genericSkillRef: framework-upgrade
status: named
level: 2★
description: 'Keep gbrain current. When a `gbrain` invocation prints an `UPGRADE_AVAILABLE
  <old> <new>` marker (or `gbrain self-upgrade --check-only` reports an update), apply
  it per the configured self_upgrade.mode: notify (prompt the operator with a 4-option
  question + snooze) or auto (apply silently). The action is always the hardcoded
  `gbrain self-upgrade` — never a command read from the marker.'
createdAt: '2026-11-03'
updatedAt: '2026-11-09'
title: Gbrain Upgrade
links:
  github: https://github.com/garrytan/gbrain/blob/v0.60.474.0/skills/gbrain-upgrade/SKILL.md
timeline:
- timestamp: '2026-11-02T21:54:37Z'
  action: add
  contributor: mbtiongson1
  details: Added named skill garrytan/gbrain-upgrade
- timestamp: '2026-11-02T21:59:31Z'
  action: suite_ref_set
  contributor: mbtiongson1
  details: Set suiteRef to garrytan/gbrain
- timestamp: '2026-11-02T21:59:35Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/garrytan/gbrain/blob/v0.60.474.0/skills/gbrain-upgrade/SKILL.md
    (type: github-stars-own)'
- timestamp: '2026-11-02T22:15:46Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM (none) -> 50.0, grade (none) -> B (gaia dev calibrate-trust-magnitude;
    Issue #1600)'
- timestamp: '2026-11-08T18:17:42Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM 50.0 -> 49.9, grade B -> C (gaia dev calibrate-trust-magnitude; Issue
    #1600)'
suiteRef: garrytan/gbrain
evidence:
- source: https://github.com/garrytan/gbrain/blob/v0.60.474.0/skills/gbrain-upgrade/SKILL.md
  evaluator: mbtiongson1
  date: '2026-11-03'
  type: github-stars-own
  notes: 'Stage-1 github-stars-own evidence: verified repository stars at tag (subject
    to 50.0 TM suite sibling cap per META §2.1a)'
  stars: 31276
  grade: A
verification:
  firstEvidenceAt: '2026-11-02T21:59:34Z'
trustMagnitude: 49.9
overallTrustGrade: C
trustMagnitudeInputHash: 72e0a6d657e2f5f6ac00cf61856a15f29e64817965f59fa70db5139d747018e6
---

## Installation
Add installation instructions here.
