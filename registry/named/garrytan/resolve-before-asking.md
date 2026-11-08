---
id: garrytan/resolve-before-asking
name: resolve-before-asking
contributor: garrytan
origin: false
genericSkillRef: guardrails
status: named
level: 2★
description: 'Gate on identity questions to the user. Before any "who is X?" (or role
  / relationship question) reaches the user, exhaust the brain''s lookup chain: think
  → search + page read → mounted sources → timeline/graph → web. If escalation survives
  the chain, ask WITH a hypothesis, never a bare unknown. Also owns the no-placeholders-at-ingest
  rule: pages created during bulk ingestion get their relationshi'
createdAt: '2026-11-03'
updatedAt: '2026-11-09'
title: Resolve Before Asking
links:
  github: https://github.com/garrytan/gbrain/blob/v0.60.474.0/skills/resolve-before-asking/SKILL.md
timeline:
- timestamp: '2026-11-02T21:54:54Z'
  action: add
  contributor: mbtiongson1
  details: Added named skill garrytan/resolve-before-asking
- timestamp: '2026-11-02T22:01:09Z'
  action: suite_ref_set
  contributor: mbtiongson1
  details: Set suiteRef to garrytan/gbrain
- timestamp: '2026-11-02T22:01:12Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/garrytan/gbrain/blob/v0.60.474.0/skills/resolve-before-asking/SKILL.md
    (type: github-stars-own)'
- timestamp: '2026-11-02T22:16:05Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM (none) -> 50.0, grade (none) -> B (gaia dev calibrate-trust-magnitude;
    Issue #1600)'
- timestamp: '2026-11-08T18:18:17Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM 50.0 -> 49.9, grade B -> C (gaia dev calibrate-trust-magnitude; Issue
    #1600)'
suiteRef: garrytan/gbrain
evidence:
- source: https://github.com/garrytan/gbrain/blob/v0.60.474.0/skills/resolve-before-asking/SKILL.md
  evaluator: mbtiongson1
  date: '2026-11-03'
  type: github-stars-own
  notes: 'Stage-1 github-stars-own evidence: verified repository stars at tag (subject
    to 50.0 TM suite sibling cap per META §2.1a)'
  stars: 31276
  grade: A
verification:
  firstEvidenceAt: '2026-11-02T22:01:11Z'
trustMagnitude: 49.9
overallTrustGrade: C
trustMagnitudeInputHash: b3278dbdb99fcb4661ca8e5d478dba32302cebea9d4c538eb6a3169305e0aee8
---

## Installation
Add installation instructions here.
