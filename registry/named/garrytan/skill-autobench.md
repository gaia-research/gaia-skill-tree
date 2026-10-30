---
id: garrytan/skill-autobench
name: skill-autobench
contributor: garrytan
origin: false
genericSkillRef: skill-performance-benchmarking
status: named
level: 2★
description: 'Author an eval for an existing skill from its REAL usage history, not
  its

  spec. Mine invocations from the brain''s conversation archive

  (conversations/) and per-harness session transcripts — a user correction

  after an invocation is the gold signal — then synthesize an eval_contract

  plus 4-8 replayable cases with honesty labels (SPEC-DERIVED vs

  HISTORY-IMPLIED) and stage the result at skills/<name>/eval/autobench-<date>.md

  as PENDING-HUMAN-APPROVAL. Never rewrites SKILL.md. Ships two guard

  companions: panel integrity (multi-model judging must prove each provider

  actually responded) and the fail-improve taxonomy (logged LLM-fallback

  cases convert to deterministic code over time).'
createdAt: '2026-09-23'
updatedAt: '2026-10-30'
title: skill-autobench
links:
  github: https://github.com/garrytan/gbrain/blob/v0.51.6.0/skills/skill-autobench/SKILL.md
timeline:
- timestamp: '2026-09-23T06:08:11Z'
  action: add
  contributor: unknown
  details: Added named skill garrytan/skill-autobench
- timestamp: '2026-10-29T16:55:50Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/garrytan/gbrain/blob/v0.51.6.0/skills/skill-autobench/SKILL.md
    (type: github-stars-own)'
- timestamp: '2026-10-29T16:55:51Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/garrytan/gbrain (type: repo-own)'
- timestamp: '2026-10-29T16:56:48Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM (none) -> 158.36, grade (none) -> A (gaia dev calibrate-trust-magnitude;
    Issue #1600)'
- timestamp: '2026-10-30T13:15:37Z'
  action: suite_ref_set
  contributor: mbtiongson1
  details: Set suiteRef to garrytan/gbrain
- timestamp: '2026-10-30T13:15:38Z'
  action: note
  contributor: mbtiongson1
  details: 'Founder ruling 2026-10-30 (FD-7 suite linking is automatic; sibling cap
    unchanged, audit filed as #2263) and audit correction C1 of PR #2251: suiteRef
    garrytan/gbrain set. Upstream path is inside the suite repo: garrytan/gbrain/blob/v0.51.6.0/skills/skill-autobench/SKILL.md.'
- timestamp: '2026-10-30T13:17:39Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM 158.36 -> 50.0, grade A -> B (gaia dev calibrate-trust-magnitude; Issue
    #1600)'
evidence:
- source: https://github.com/garrytan/gbrain/blob/v0.51.6.0/skills/skill-autobench/SKILL.md
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
  firstEvidenceAt: '2026-10-29T16:55:50Z'
trustMagnitude: 50.0
overallTrustGrade: B
trustMagnitudeInputHash: 931fe60a498c683fa6114ad34ece444ab53630027da4fd1326228b9128e1d3f7
suiteRef: garrytan/gbrain
---

## Installation
Add installation instructions here.
