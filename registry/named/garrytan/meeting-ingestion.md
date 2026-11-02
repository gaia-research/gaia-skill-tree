---
id: garrytan/meeting-ingestion
name: meeting-ingestion
contributor: garrytan
origin: false
genericSkillRef: personal-knowledge-management
status: named
level: 2★
description: 'Ingest meeting transcripts from ANY meeting recorder into brain pages
  with

  attendee enrichment, entity propagation, and timeline merge. One unified

  pipeline: normalize the source into a standard transcript record, split

  multi-meeting recordings, resolve speakers by evidence, create the page,

  pass every surprising claim through the consistency check (transcript +

  brain + plausibility), enrich every entity, then run the verification

  checklist — substance AND sequence. A meeting is NOT fully ingested until

  the enrich skill has processed every entity AND the verification checklist

  passes, including the sequence verify (PASS or explicit user waive).'
createdAt: '2026-09-23'
updatedAt: '2026-10-30'
title: meeting-ingestion
links:
  github: https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/meeting-ingestion/SKILL.md
timeline:
- timestamp: '2026-09-23T06:08:10Z'
  action: add
  contributor: unknown
  details: Added named skill garrytan/meeting-ingestion
- timestamp: '2026-10-29T16:55:38Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/meeting-ingestion/SKILL.md
    (type: github-stars-own)'
- timestamp: '2026-10-29T16:55:39Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/garrytan/gbrain (type: repo-own)'
- timestamp: '2026-10-29T16:56:48Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM (none) -> 158.36, grade (none) -> A (gaia dev calibrate-trust-magnitude;
    Issue #1600)'
- timestamp: '2026-10-30T13:15:18Z'
  action: suite_ref_set
  contributor: mbtiongson1
  details: Set suiteRef to garrytan/gbrain
- timestamp: '2026-10-30T13:15:20Z'
  action: note
  contributor: mbtiongson1
  details: 'Founder ruling 2026-10-30 (FD-7 suite linking is automatic; sibling cap
    unchanged, audit filed as #2263) and audit correction C1 of PR #2251: suiteRef
    garrytan/gbrain set. Upstream path is inside the suite repo: garrytan/gbrain/blob/v0.51.6.0/plugin/skills/meeting-ingestion/SKILL.md.'
- timestamp: '2026-10-30T13:17:39Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM 158.36 -> 50.0, grade A -> B (gaia dev calibrate-trust-magnitude; Issue
    #1600)'
evidence:
- source: https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/meeting-ingestion/SKILL.md
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
  firstEvidenceAt: '2026-10-29T16:55:38Z'
trustMagnitude: 50.0
overallTrustGrade: B
trustMagnitudeInputHash: 2ae72c0f6ed9bab7940701e7fae19de6a349bf25204161d74d057c7b6a900cbd
suiteRef: garrytan/gbrain
---

## Installation
Add installation instructions here.
