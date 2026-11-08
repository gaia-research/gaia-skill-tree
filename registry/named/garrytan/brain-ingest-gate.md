---
id: garrytan/brain-ingest-gate
name: brain-ingest-gate
contributor: garrytan
origin: false
genericSkillRef: knowledge-management
status: named
level: 2★
description: 'Pre-write quality gate for content entering the brain. No raw copies:
  a bare cp/mv into the brain repo is a bug. Before any new page lands, resolve named
  entities registry-first (a vector score is a floor for prose, never a gate for named
  things), then run the read-the-top-hit dedup decision tree (clear-dup / plausible-dup
  / clear). Owns dedup; delegates enrichment to the shipped ingestion skills.'
createdAt: '2026-11-03'
updatedAt: '2026-11-09'
title: Brain Ingest Gate
links:
  github: https://github.com/garrytan/gbrain/blob/v0.60.474.0/skills/brain-ingest-gate/SKILL.md
timeline:
- timestamp: '2026-11-02T21:54:10Z'
  action: add
  contributor: mbtiongson1
  details: Added named skill garrytan/brain-ingest-gate
- timestamp: '2026-11-02T21:56:59Z'
  action: suite_ref_set
  contributor: mbtiongson1
  details: Set suiteRef to garrytan/gbrain
- timestamp: '2026-11-02T21:57:02Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/garrytan/gbrain/blob/v0.60.474.0/skills/brain-ingest-gate/SKILL.md
    (type: github-stars-own)'
- timestamp: '2026-11-02T22:15:18Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM (none) -> 50.0, grade (none) -> B (gaia dev calibrate-trust-magnitude;
    Issue #1600)'
- timestamp: '2026-11-08T18:16:48Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM 50.0 -> 49.9, grade B -> C (gaia dev calibrate-trust-magnitude; Issue
    #1600)'
suiteRef: garrytan/gbrain
evidence:
- source: https://github.com/garrytan/gbrain/blob/v0.60.474.0/skills/brain-ingest-gate/SKILL.md
  evaluator: mbtiongson1
  date: '2026-11-03'
  type: github-stars-own
  notes: 'Stage-1 github-stars-own evidence: verified repository stars at tag (subject
    to 50.0 TM suite sibling cap per META §2.1a)'
  stars: 31276
  grade: A
verification:
  firstEvidenceAt: '2026-11-02T21:57:01Z'
trustMagnitude: 49.9
overallTrustGrade: C
trustMagnitudeInputHash: 66867d326626c54064b93a20dc50668af1d579a8bd4fc373707d6df2cb159697
---

## Installation
Add installation instructions here.
