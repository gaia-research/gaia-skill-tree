---
id: addy-osmani/observability-and-instrumentation
name: observability-and-instrumentation
contributor: addy-osmani
origin: false
genericSkillRef: observability-instrumentation
status: named
level: 2★
description: Instruments code so production behavior is visible and diagnosable. Use
  when adding logging, metrics, tracing, or alerting. Use when shipping any feature
  that runs in production and you need evidence it works. Use when production issues
  are reported but you can't tell what happened from the available data.
createdAt: '2026-09-23'
updatedAt: '2026-10-30'
title: observability-and-instrumentation
links:
  github: https://github.com/addyosmani/agent-skills/blob/0.6.10/skills/observability-and-instrumentation/SKILL.md
timeline:
- timestamp: '2026-09-23T06:08:02Z'
  action: add
  contributor: unknown
  details: Added named skill addy-osmani/observability-and-instrumentation
- timestamp: '2026-09-23T06:13:37Z'
  action: suite_ref_set
  contributor: unknown
  details: Set suiteRef to addy-osmani/agent-skills
- timestamp: '2026-10-29T16:55:01Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/addyosmani/agent-skills/blob/0.6.10/skills/observability-and-instrumentation/SKILL.md
    (type: github-stars-own)'
- timestamp: '2026-10-29T16:55:01Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/addyosmani/agent-skills (type:
    repo-own)'
- timestamp: '2026-10-29T16:56:47Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM (none) -> 177.68, grade (none) -> A (gaia dev calibrate-trust-magnitude;
    Issue #1600)'
- timestamp: '2026-10-30T06:21:28Z'
  action: suite_ref_set
  contributor: mbtiongson1
  details: Set suiteRef to addy-osmani/agent-skills
- timestamp: '2026-10-30T06:21:37Z'
  action: note
  contributor: mbtiongson1
  details: 'Audit correction C1 of PR #2251: suiteRef addy-osmani/agent-skills restored;
    it matches the existing 2026-09-23 suite_ref_set event that never persisted (the
    docs generator erased directly set suiteRef values; fixed in PR #2260). Caps host-repo
    evidence at the suite-component bound. Founder ruling 2026-10-30 FD-7.'
- timestamp: '2026-10-30T06:22:48Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM 177.68 -> 50.0, grade A -> B (gaia dev calibrate-trust-magnitude; Issue
    #1600)'
evidence:
- source: https://github.com/addyosmani/agent-skills/blob/0.6.10/skills/observability-and-instrumentation/SKILL.md
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
  firstEvidenceAt: '2026-10-29T16:55:01Z'
trustMagnitude: 50.0
overallTrustGrade: B
trustMagnitudeInputHash: e44c0fca2acf4247b00480669a688693c782e471b5a9e20f967b24a1ca5d9382
suiteRef: addy-osmani/agent-skills
---

## Installation
Add installation instructions here.
