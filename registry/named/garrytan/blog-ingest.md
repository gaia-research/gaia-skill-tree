---
id: garrytan/blog-ingest
name: blog-ingest
contributor: garrytan
origin: false
genericSkillRef: knowledge-harvest
status: named
level: 2★
description: 'Feed and whole-publication ingestion: turn an entire blog, newsletter,
  or

  RSS/Atom archive into brain source pages. Covers feed discovery, pagination

  walking, normalization to a common article shape, canonical-URL dedup,

  idempotent re-runs, 429 pacing, and empty-husk repair. This is the

  PUBLICATION-scope skill — a single article URL routes to idea-ingest

  instead. Per-article enrichment hands off to the brain-ingest-gate skill;

  public posts only (gated content is skipped, never worked around).'
createdAt: '2026-09-23'
updatedAt: '2026-10-30'
title: blog-ingest
links:
  github: https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/blog-ingest/SKILL.md
timeline:
- timestamp: '2026-09-23T06:08:05Z'
  action: add
  contributor: unknown
  details: Added named skill garrytan/blog-ingest
- timestamp: '2026-10-29T16:55:09Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/blog-ingest/SKILL.md
    (type: github-stars-own)'
- timestamp: '2026-10-29T16:55:10Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/garrytan/gbrain (type: repo-own)'
- timestamp: '2026-10-29T16:56:47Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM (none) -> 158.36, grade (none) -> A (gaia dev calibrate-trust-magnitude;
    Issue #1600)'
- timestamp: '2026-10-30T13:14:41Z'
  action: suite_ref_set
  contributor: mbtiongson1
  details: Set suiteRef to garrytan/gbrain
- timestamp: '2026-10-30T13:14:42Z'
  action: note
  contributor: mbtiongson1
  details: 'Founder ruling 2026-10-30 (FD-7 suite linking is automatic; sibling cap
    unchanged, audit filed as #2263) and audit correction C1 of PR #2251: suiteRef
    garrytan/gbrain set. Upstream path is inside the suite repo: garrytan/gbrain/blob/v0.51.6.0/plugin/skills/blog-ingest/SKILL.md.'
- timestamp: '2026-10-30T13:17:39Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM 158.36 -> 50.0, grade A -> B (gaia dev calibrate-trust-magnitude; Issue
    #1600)'
evidence:
- source: https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/blog-ingest/SKILL.md
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
  firstEvidenceAt: '2026-10-29T16:55:09Z'
trustMagnitude: 50.0
overallTrustGrade: B
trustMagnitudeInputHash: 7afc17d847178febe6b46dffd8e2c867f4da875f6b0cf652aae39a724be2c5be
suiteRef: garrytan/gbrain
---

## Installation
Add installation instructions here.
