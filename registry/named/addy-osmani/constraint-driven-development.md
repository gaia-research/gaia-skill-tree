---
id: addy-osmani/constraint-driven-development
name: constraint-driven-development
contributor: addy-osmani
origin: false
genericSkillRef: guardrails
status: named
level: 2★
description: Establishes a project's quality bar as a written contract and stops agents
  quietly lowering it. Interviews the user on which dimensions matter, supplies sane
  default thresholds when they have no number in mind, records everything in CONSTRAINTS.md,
  and watches the diff for a weakened bar — new @ts-ignore or eslint-disable suppressions,
  skipped or deleted tests, assertions stripped out, unimplemented stubs, thresholds
  edited down. Use when no quality bar is written down, when the user says "set up
  constraints" or "define our standards", when the user wants dimensions they care
  about — accessibility, web performance, coverage — set up as enforced constraints,
  when an agent keeps silencing checks or skipping tests to get to green, when you
  need a coverage or performance threshold and don't know what number to pick, or
  when an agent writes more code than anyone will read.
createdAt: '2026-09-23'
updatedAt: '2026-10-30'
title: constraint-driven-development
links:
  github: https://github.com/addyosmani/agent-skills/blob/0.6.10/skills/constraint-driven-development/SKILL.md
timeline:
- timestamp: '2026-09-23T06:08:03Z'
  action: add
  contributor: unknown
  details: Added named skill addy-osmani/constraint-driven-development
- timestamp: '2026-09-23T06:13:39Z'
  action: suite_ref_set
  contributor: unknown
  details: Set suiteRef to addy-osmani/agent-skills
- timestamp: '2026-10-29T16:54:57Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/addyosmani/agent-skills/blob/0.6.10/skills/constraint-driven-development/SKILL.md
    (type: github-stars-own)'
- timestamp: '2026-10-29T16:54:57Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/addyosmani/agent-skills (type:
    repo-own)'
- timestamp: '2026-10-29T16:56:47Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM (none) -> 177.68, grade (none) -> A (gaia dev calibrate-trust-magnitude;
    Issue #1600)'
evidence:
- source: https://github.com/addyosmani/agent-skills/blob/0.6.10/skills/constraint-driven-development/SKILL.md
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
trustMagnitude: 177.68
overallTrustGrade: A
trustMagnitudeInputHash: f0b2fcd322e31ba9fc98c19b5ae8ac2ce36fb046c9a96864d7cedd607e5dc2dd
---

## Installation
Add installation instructions here.
