---
id: garrytan/cross-modal-review
name: cross-modal-review
contributor: garrytan
origin: false
genericSkillRef: adversarial-review
status: named
level: 2★
description: 'Quality gate via second model. Spawn a different AI model to review
  work before committing. Includes refusal routing: if one model refuses, switch silently
  to the next. Extended in v0.25.1 with structured review-mode gating (when to invoke
  vs not) and a Codex code-review handoff for the diff-review case.'
createdAt: '2026-11-03'
updatedAt: '2026-11-09'
title: Cross Modal Review
links:
  github: https://github.com/garrytan/gbrain/blob/v0.60.474.0/skills/cross-modal-review/SKILL.md
timeline:
- timestamp: '2026-11-02T21:54:26Z'
  action: add
  contributor: mbtiongson1
  details: Added named skill garrytan/cross-modal-review
- timestamp: '2026-11-02T21:58:22Z'
  action: suite_ref_set
  contributor: mbtiongson1
  details: Set suiteRef to garrytan/gbrain
- timestamp: '2026-11-02T21:58:25Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/garrytan/gbrain/blob/v0.60.474.0/skills/cross-modal-review/SKILL.md
    (type: github-stars-own)'
- timestamp: '2026-11-02T22:15:34Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM (none) -> 50.0, grade (none) -> B (gaia dev calibrate-trust-magnitude;
    Issue #1600)'
- timestamp: '2026-11-08T18:17:17Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM 50.0 -> 49.9, grade B -> C (gaia dev calibrate-trust-magnitude; Issue
    #1600)'
suiteRef: garrytan/gbrain
evidence:
- source: https://github.com/garrytan/gbrain/blob/v0.60.474.0/skills/cross-modal-review/SKILL.md
  evaluator: mbtiongson1
  date: '2026-11-03'
  type: github-stars-own
  notes: 'Stage-1 github-stars-own evidence: verified repository stars at tag (subject
    to 50.0 TM suite sibling cap per META §2.1a)'
  stars: 31276
  grade: A
verification:
  firstEvidenceAt: '2026-11-02T21:58:24Z'
trustMagnitude: 49.9
overallTrustGrade: C
trustMagnitudeInputHash: e113ef2e73b4ded77eec091f243f8954f710d089f3b976a9f58e339cec9cfc3d
---

## Installation
Add installation instructions here.
