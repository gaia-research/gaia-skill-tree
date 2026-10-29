---
id: garrytan/fact-check
name: fact-check
contributor: garrytan
origin: false
genericSkillRef: grounding
status: named
level: 2★
description: 'Systematic claim-by-claim verification for any content before it ships.

  Modeled on professional fact-checking desks (The New Yorker, ProPublica,

  IFCN standards): extract every verifiable claim, check each against live

  citable sources (never training data), assign a 6-level confidence status,

  apply corrections, and produce a scored pass/fail report. Includes a

  data-derived-claims gate for outputs produced FROM the brain or a database:

  PRODUCER ≠ VERIFIER (re-derive each claim via a different query path) and

  AFFILIATION ≠ AUTHORSHIP (person→thing claims resolve through typed edges),

  with delivery hard-blocked on unsupported claims.'
createdAt: '2026-09-23'
updatedAt: '2026-10-30'
title: fact-check
links:
  github: https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/fact-check/SKILL.md
timeline:
- timestamp: '2026-09-23T06:08:08Z'
  action: add
  contributor: unknown
  details: Added named skill garrytan/fact-check
- timestamp: '2026-10-29T16:55:28Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/fact-check/SKILL.md
    (type: github-stars-own)'
- timestamp: '2026-10-29T16:55:29Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/garrytan/gbrain (type: repo-own)'
- timestamp: '2026-10-29T16:56:47Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM (none) -> 158.36, grade (none) -> A (gaia dev calibrate-trust-magnitude;
    Issue #1600)'
evidence:
- source: https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/fact-check/SKILL.md
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
  firstEvidenceAt: '2026-10-29T16:55:28Z'
trustMagnitude: 158.36
overallTrustGrade: A
trustMagnitudeInputHash: dfcfda1ef2df5cd0d0755e48fd48e51b78b02cedd5d08ffba3b7d28a60e85a72
---

## Installation
Add installation instructions here.
