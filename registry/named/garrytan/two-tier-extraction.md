---
id: garrytan/two-tier-extraction
name: two-tier-extraction
contributor: garrytan
origin: false
genericSkillRef: knowledge-harvest
status: named
level: 2★
description: 'Tiered LLM extraction pattern for large corpus processing (email archives,

  document dumps, transcript libraries). A utility-tier model triages and

  classifies at speed; the reasoning tier does the default deep read; the

  deep tier is the escalation for the highest-value content. Prevents

  spending deep-tier money on noise while ensuring the important content

  gets the best eyes. A deterministic privacy wall runs before any LLM call.'
createdAt: '2026-09-23'
updatedAt: '2026-10-30'
title: two-tier-extraction
links:
  github: https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/two-tier-extraction/SKILL.md
timeline:
- timestamp: '2026-09-23T06:08:12Z'
  action: add
  contributor: unknown
  details: Added named skill garrytan/two-tier-extraction
- timestamp: '2026-10-29T16:55:57Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/two-tier-extraction/SKILL.md
    (type: github-stars-own)'
- timestamp: '2026-10-29T16:55:58Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/garrytan/gbrain (type: repo-own)'
- timestamp: '2026-10-29T16:56:48Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM (none) -> 158.36, grade (none) -> A (gaia dev calibrate-trust-magnitude;
    Issue #1600)'
- timestamp: '2026-10-30T13:15:46Z'
  action: suite_ref_set
  contributor: mbtiongson1
  details: Set suiteRef to garrytan/gbrain
- timestamp: '2026-10-30T13:15:47Z'
  action: note
  contributor: mbtiongson1
  details: 'Founder ruling 2026-10-30 (FD-7 suite linking is automatic; sibling cap
    unchanged, audit filed as #2263) and audit correction C1 of PR #2251: suiteRef
    garrytan/gbrain set. Upstream path is inside the suite repo: garrytan/gbrain/blob/v0.51.6.0/plugin/skills/two-tier-extraction/SKILL.md.'
- timestamp: '2026-10-30T13:17:39Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM 158.36 -> 50.0, grade A -> B (gaia dev calibrate-trust-magnitude; Issue
    #1600)'
evidence:
- source: https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/two-tier-extraction/SKILL.md
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
  firstEvidenceAt: '2026-10-29T16:55:57Z'
trustMagnitude: 50.0
overallTrustGrade: B
trustMagnitudeInputHash: dd1a0c6394c0b33212bb0e528534ff1bc94ed0e8ffc418ba6be221e51c1d8728
suiteRef: garrytan/gbrain
---

## Installation
Add installation instructions here.
