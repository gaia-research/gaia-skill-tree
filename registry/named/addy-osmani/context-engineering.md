---
id: addy-osmani/context-engineering
name: context-engineering
contributor: addy-osmani
origin: false
genericSkillRef: agent-environment-setup
status: named
level: 2★
description: Optimizes agent context setup. Use when starting a new session, when
  agent output quality degrades, when switching between tasks, or when you need to
  configure rules files and context for a project.
createdAt: '2026-09-23'
updatedAt: '2026-10-30'
title: context-engineering
links:
  github: https://github.com/addyosmani/agent-skills/blob/0.6.10/skills/context-engineering/SKILL.md
timeline:
- timestamp: '2026-09-23T06:08:00Z'
  action: add
  contributor: unknown
  details: Added named skill addy-osmani/context-engineering
- timestamp: '2026-09-23T06:13:34Z'
  action: suite_ref_set
  contributor: unknown
  details: Set suiteRef to addy-osmani/agent-skills
- timestamp: '2026-10-29T16:54:57Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/addyosmani/agent-skills/blob/0.6.10/skills/context-engineering/SKILL.md
    (type: github-stars-own)'
- timestamp: '2026-10-29T16:54:58Z'
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
- source: https://github.com/addyosmani/agent-skills/blob/0.6.10/skills/context-engineering/SKILL.md
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
  firstEvidenceAt: '2026-10-29T16:54:57Z'
trustMagnitude: 50.0
overallTrustGrade: B
trustMagnitudeInputHash: 8fba615ff9338577c26d101bee33983a07b06635eb89b9c876adcbc0be45d7a3
suiteRef: addy-osmani/agent-skills
---

## Installation
Add installation instructions here.
