---
id: garrytan/functional-area-resolver
name: functional-area-resolver
contributor: garrytan
origin: false
genericSkillRef: route-intent
status: named
level: 2★
description: 'Compress an agent''s routing file (RESOLVER.md or AGENTS.md) by converting

  granular skill-per-row tables into functional-area dispatchers. Each area

  lists sub-skills in a "(dispatcher for: ...)" clause. The LLM reads one

  area entry and routes to the correct sub-skill. Proven via held-out

  A/B eval: dispatcher pattern outperforms naive pipe-table compression.'
createdAt: '2026-09-23'
updatedAt: '2026-10-30'
title: functional-area-resolver
links:
  github: https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/functional-area-resolver/SKILL.md
timeline:
- timestamp: '2026-09-23T06:08:09Z'
  action: add
  contributor: unknown
  details: Added named skill garrytan/functional-area-resolver
- timestamp: '2026-10-29T16:55:31Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/functional-area-resolver/SKILL.md
    (type: github-stars-own)'
- timestamp: '2026-10-29T16:55:32Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/garrytan/gbrain (type: repo-own)'
- timestamp: '2026-10-29T16:56:48Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM (none) -> 158.36, grade (none) -> A (gaia dev calibrate-trust-magnitude;
    Issue #1600)'
evidence:
- source: https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/functional-area-resolver/SKILL.md
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
  firstEvidenceAt: '2026-10-29T16:55:31Z'
trustMagnitude: 158.36
overallTrustGrade: A
trustMagnitudeInputHash: 3c093957ecede7cb1b8cfdd5460f078552f2be58a0c46947337734ea5c80414e
---

## Installation
Add installation instructions here.
