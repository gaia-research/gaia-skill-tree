---
id: garrytan/conversation-archive
name: conversation-archive
contributor: garrytan
origin: false
genericSkillRef: personal-knowledge-management
status: named
level: 2★
description: 'Import AI-assistant chat exports (ChatGPT, Claude, Perplexity) and agent
  session transcripts into the brain as one dated page per conversation under conversations/,
  validate each page against the native conversation parser, extract facts via the
  native conversation-facts flow, and keep the archive gap-free with a detect-and-backfill
  loop. Then answer archive questions: "when did I first discuss X", trace how an
  idea evolved across past conversations, pull a specific thread.'
createdAt: '2026-09-23'
updatedAt: '2026-10-30'
title: conversation-archive
links:
  github: https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/conversation-archive/SKILL.md
timeline:
- timestamp: '2026-09-23T06:08:07Z'
  action: add
  contributor: unknown
  details: Added named skill garrytan/conversation-archive
- timestamp: '2026-10-29T16:55:21Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/conversation-archive/SKILL.md
    (type: github-stars-own)'
- timestamp: '2026-10-29T16:55:22Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/garrytan/gbrain (type: repo-own)'
- timestamp: '2026-10-29T16:56:47Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM (none) -> 158.36, grade (none) -> A (gaia dev calibrate-trust-magnitude;
    Issue #1600)'
- timestamp: '2026-10-30T13:14:57Z'
  action: suite_ref_set
  contributor: mbtiongson1
  details: Set suiteRef to garrytan/gbrain
- timestamp: '2026-10-30T13:14:58Z'
  action: note
  contributor: mbtiongson1
  details: 'Founder ruling 2026-10-30 (FD-7 suite linking is automatic; sibling cap
    unchanged, audit filed as #2263) and audit correction C1 of PR #2251: suiteRef
    garrytan/gbrain set. Upstream path is inside the suite repo: garrytan/gbrain/blob/v0.51.6.0/plugin/skills/conversation-archive/SKILL.md.'
- timestamp: '2026-10-30T13:17:39Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM 158.36 -> 50.0, grade A -> B (gaia dev calibrate-trust-magnitude; Issue
    #1600)'
evidence:
- source: https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/conversation-archive/SKILL.md
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
  firstEvidenceAt: '2026-10-29T16:55:21Z'
trustMagnitude: 50.0
overallTrustGrade: B
trustMagnitudeInputHash: a634955413945eb6393066e6c93ecb8ced507a6113298843c002934bb2d7ed46
suiteRef: garrytan/gbrain
---

## Installation
Add installation instructions here.
