---
id: addy-osmani/documentation-and-adrs
name: documentation-and-adrs
contributor: addy-osmani
origin: false
genericSkillRef: write-report
status: named
level: 2★
description: Records decisions and documentation. Use when you need to document an
  architecture decision (ADR) or the reasoning behind a design choice, when changing
  public APIs, shipping features, or when you need to record context that future engineers
  and agents will need to understand the codebase.
createdAt: '2026-09-23'
updatedAt: '2026-10-30'
title: documentation-and-adrs
links:
  github: https://github.com/addyosmani/agent-skills/blob/0.6.10/skills/documentation-and-adrs/SKILL.md
timeline:
- timestamp: '2026-09-23T06:08:01Z'
  action: add
  contributor: unknown
  details: Added named skill addy-osmani/documentation-and-adrs
- timestamp: '2026-09-23T06:13:35Z'
  action: suite_ref_set
  contributor: unknown
  details: Set suiteRef to addy-osmani/agent-skills
- timestamp: '2026-10-29T16:54:59Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/addyosmani/agent-skills/blob/0.6.10/skills/documentation-and-adrs/SKILL.md
    (type: github-stars-own)'
- timestamp: '2026-10-29T16:54:59Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/addyosmani/agent-skills (type:
    repo-own)'
- timestamp: '2026-10-29T16:56:47Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM (none) -> 177.68, grade (none) -> A (gaia dev calibrate-trust-magnitude;
    Issue #1600)'
- timestamp: '2026-10-30T06:21:27Z'
  action: suite_ref_set
  contributor: mbtiongson1
  details: Set suiteRef to addy-osmani/agent-skills
- timestamp: '2026-10-30T06:21:36Z'
  action: note
  contributor: mbtiongson1
  details: 'Audit correction C1 of PR #2251: suiteRef addy-osmani/agent-skills restored;
    it matches the existing 2026-09-23 suite_ref_set event that never persisted (the
    docs generator erased directly set suiteRef values; fixed in PR #2260). Caps host-repo
    evidence at the suite-component bound. Founder ruling 2026-10-30 FD-7.'
- timestamp: '2026-10-30T06:22:47Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM 177.68 -> 50.0, grade A -> B (gaia dev calibrate-trust-magnitude; Issue
    #1600)'
evidence:
- source: https://github.com/addyosmani/agent-skills/blob/0.6.10/skills/documentation-and-adrs/SKILL.md
  evaluator: mbtiongson1
  date: '2026-10-29'
  type: github-stars-own
  notes: 'GitHub REST stargazers_count of addyosmani/agent-skills at 2026-10-29 (host
    suite repo); skill-file blob link verified HTTP 200 at its pinned ref. Founder
    ruling 2026-10-30 FD-7: skill was added at intake (2026-09-23) with no evidence
    rows.'
  stars: 111664
  skillCountInRepo: 25
  sourceStartedAt: '2026-02-15'
  grade: A
- source: https://github.com/addyosmani/agent-skills
  evaluator: mbtiongson1
  date: '2026-10-29'
  type: repo-own
  notes: GitHub REST default-branch commit count and contributor count of addyosmani/agent-skills
    at 2026-10-29; host-repository maintenance, not independent quality evidence.
    Founder ruling 2026-10-30 FD-7.
  commits: 772
  contributors: 83
  sourceStartedAt: '2026-02-15'
  grade: B
verification:
  firstEvidenceAt: '2026-10-29T16:54:59Z'
trustMagnitude: 50.0
overallTrustGrade: B
trustMagnitudeInputHash: 911e5372736aaef27345be0495f276c0ff185851bcec5d91392effe3a31e2b35
suiteRef: addy-osmani/agent-skills
---

## Installation
Add installation instructions here.
