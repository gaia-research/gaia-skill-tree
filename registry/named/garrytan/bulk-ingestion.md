---
id: garrytan/bulk-ingestion
name: bulk-ingestion
contributor: garrytan
origin: false
genericSkillRef: knowledge-harvest
status: named
level: 2★
description: 'End-to-end discipline for turning any large data source (audio libraries,

  email takeouts, document corpora, chat exports, API dumps) into brain pages

  at scale. The lifecycle spine: SCHEMA → ACCESS → TRIAL → EVALUATE → IMPROVE

  → CODIFY → TEST → SKILLIFY → BULK → MONITOR. State is tracked in a durable

  JSON manifest (see MANIFEST-PATTERN.md) so any crash, session boundary, or

  subagent fan-out resumes from ground truth instead of memory.'
createdAt: '2026-09-23'
updatedAt: '2026-10-30'
title: bulk-ingestion
links:
  github: https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/bulk-ingestion/SKILL.md
timeline:
- timestamp: '2026-09-23T06:08:06Z'
  action: add
  contributor: unknown
  details: Added named skill garrytan/bulk-ingestion
- timestamp: '2026-10-29T16:55:14Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/bulk-ingestion/SKILL.md
    (type: github-stars-own)'
- timestamp: '2026-10-29T16:55:15Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/garrytan/gbrain (type: repo-own)'
- timestamp: '2026-10-29T16:56:47Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM (none) -> 158.36, grade (none) -> A (gaia dev calibrate-trust-magnitude;
    Issue #1600)'
- timestamp: '2026-10-30T13:14:47Z'
  action: suite_ref_set
  contributor: mbtiongson1
  details: Set suiteRef to garrytan/gbrain
- timestamp: '2026-10-30T13:14:49Z'
  action: note
  contributor: mbtiongson1
  details: 'Founder ruling 2026-10-30 (FD-7 suite linking is automatic; sibling cap
    unchanged, audit filed as #2263) and audit correction C1 of PR #2251: suiteRef
    garrytan/gbrain set. Upstream path is inside the suite repo: garrytan/gbrain/blob/v0.51.6.0/plugin/skills/bulk-ingestion/SKILL.md.'
- timestamp: '2026-10-30T13:17:39Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM 158.36 -> 50.0, grade A -> B (gaia dev calibrate-trust-magnitude; Issue
    #1600)'
evidence:
- source: https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/bulk-ingestion/SKILL.md
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
  firstEvidenceAt: '2026-10-29T16:55:14Z'
trustMagnitude: 50.0
overallTrustGrade: B
trustMagnitudeInputHash: 2a3e74783f1107b587cbd3a5ae339e67d22401297ead194a1b9564a14461516c
suiteRef: garrytan/gbrain
---

## Installation
Add installation instructions here.
