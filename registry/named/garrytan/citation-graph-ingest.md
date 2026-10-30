---
id: garrytan/citation-graph-ingest
name: citation-graph-ingest
contributor: garrytan
origin: false
genericSkillRef: knowledge-graph-build
status: named
level: 2★
description: 'Build a TYPED citation/reference graph over an ingested corpus — not
  just

  embeddings. Flat similarity retrieval cannot tell you that document A

  *overrules* B, *distinguishes* C, or *relies_on* D. This skill extracts every

  inter-document reference, classifies the edge TYPE with LLM judgment, and

  writes first-class typed edges via `gbrain link`, so `gbrain graph-query

  --type` can walk the argument ("everything this brief relies on, minus

  anything overruled since"). Every cite-heavy corpus is the same shape: law,

  academic papers, patents, regulatory filings, a book''s bibliography.'
createdAt: '2026-09-23'
updatedAt: '2026-10-30'
title: citation-graph-ingest
links:
  github: https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/citation-graph-ingest/SKILL.md
timeline:
- timestamp: '2026-09-23T06:08:06Z'
  action: add
  contributor: unknown
  details: Added named skill garrytan/citation-graph-ingest
- timestamp: '2026-10-29T16:55:16Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/citation-graph-ingest/SKILL.md
    (type: github-stars-own)'
- timestamp: '2026-10-29T16:55:17Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/garrytan/gbrain (type: repo-own)'
- timestamp: '2026-10-29T16:56:47Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM (none) -> 158.36, grade (none) -> A (gaia dev calibrate-trust-magnitude;
    Issue #1600)'
- timestamp: '2026-10-30T13:14:51Z'
  action: suite_ref_set
  contributor: mbtiongson1
  details: Set suiteRef to garrytan/gbrain
- timestamp: '2026-10-30T13:14:53Z'
  action: note
  contributor: mbtiongson1
  details: 'Founder ruling 2026-10-30 (FD-7 suite linking is automatic; sibling cap
    unchanged, audit filed as #2263) and audit correction C1 of PR #2251: suiteRef
    garrytan/gbrain set. Upstream path is inside the suite repo: garrytan/gbrain/blob/v0.51.6.0/plugin/skills/citation-graph-ingest/SKILL.md.'
- timestamp: '2026-10-30T13:17:39Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM 158.36 -> 50.0, grade A -> B (gaia dev calibrate-trust-magnitude; Issue
    #1600)'
evidence:
- source: https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/citation-graph-ingest/SKILL.md
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
  firstEvidenceAt: '2026-10-29T16:55:16Z'
trustMagnitude: 50.0
overallTrustGrade: B
trustMagnitudeInputHash: cbc252cf2c6f92dd7acf09d2ba1cc2a090d35e9fbc6e47a4473dab1aa852c5f9
suiteRef: garrytan/gbrain
---

## Installation
Add installation instructions here.
