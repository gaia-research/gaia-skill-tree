---
id: leonxlnx/output-skill
name: output-skill
contributor: leonxlnx
origin: false
genericSkillRef: format-output
status: named
level: 3★
description: Anti-truncation execution directive preventing LLMs from skipping code
  blocks, omitting sections, or using placeholder comments.
createdAt: '2026-08-22'
updatedAt: '2026-11-03'
title: Full Output Enforcement
links:
  github: https://github.com/leonxlnx/taste-skill/blob/main/skills/output-skill/SKILL.md
timeline:
- timestamp: '2026-08-22T08:07:46Z'
  action: add
  contributor: mbtiongson1
  details: Added named skill leonxlnx/output-skill
- timestamp: '2026-08-22T08:08:26Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/leonxlnx/taste-skill/blob/main/skills/output-skill/SKILL.md
    (type: github-stars-own)'
- timestamp: '2026-08-22T08:08:27Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/leonxlnx/taste-skill (type: repo-own)'
- timestamp: '2026-08-22T08:08:40Z'
  action: suite_ref_set
  contributor: mbtiongson1
  details: Set suiteRef to leonxlnx/taste-skill
- timestamp: '2026-08-29T17:15:51Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM (none) -> 50.0, grade (none) -> B (gaia dev calibrate-trust-magnitude;
    Issue #1600)'
- timestamp: '2026-09-02T15:11:38Z'
  action: rank_up
  contributor: unknown
  details: Calibrated level from 2★ to 3★
- timestamp: '2026-10-30T04:58:33Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM 50.0 -> 50.0, grade B -> B (gaia dev calibrate-trust-magnitude; Issue
    #1600)'
- timestamp: '2026-10-30T13:09:08Z'
  action: evidence_removed
  contributor: mbtiongson1
  details: 'Removed dead/invalid evidence: https://github.com/leonxlnx/taste-skill/blob/main/skills/output-skill/SKILL.md'
- timestamp: '2026-10-30T13:09:10Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM 50.0 -> 36.0, grade B -> C (gaia dev calibrate-trust-magnitude; Issue
    #1600)'
- timestamp: '2026-10-30T13:09:11Z'
  action: upstream_deprecated
  contributor: mbtiongson1
  previousValue: null
  newValue: null
  details: 'founder ruling 2026-10-30 (r3-fd17-leftovers): removed upstream. Leonxlnx/taste-skill
    deleted skills/output-skill in v2.1.1 (f6831c5df8) and the skill (full-output-enforcement)
    is listed as ''Removed'' in README and CHANGELOG; the only pointer is a different
    skill, Leonxlnx/unlazy. Dead evidence row removed; links kept, installable false'
- timestamp: '2026-11-03T11:30:32Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Restored evidence https://github.com/leonxlnx/taste-skill/blob/main/skills/output-skill/SKILL.md
    (type: github-stars-own), removed at the 2026-10-30 freeze. Founder ruling 2026-11-03:
    frozen skills keep their stars, evidence and calibration. Hand-edited under the
    founder''s explicit 2026-11-03 waiver of the Programmatic-First rule, because no
    gaia dev verb can write a frozen record. Row restored byte-for-byte from commit
    777ea33c6; the freeze event, links and installable:false are unchanged.'
- timestamp: '2026-11-03T11:30:33Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM 36.0 -> 50.0, grade C -> B (restored pre-freeze lock; recomputed with
    the engine, input hash cde644fe4d04...; hand-edited under the founder''s 2026-11-03
    waiver)'
evidence:
- source: https://github.com/leonxlnx/taste-skill/blob/main/skills/output-skill/SKILL.md
  updatedAt: '2026-10-01'
  evaluator: mbtiongson1
  date: '2026-08-22'
  type: github-stars-own
  notes: 79.0k stars on Leonxlnx/taste-skill suite component
  stars: 91660
  sourceStartedAt: '2026-02-19'
  grade: A
- source: https://github.com/leonxlnx/taste-skill
  evaluator: mbtiongson1
  date: '2026-08-22'
  type: repo-own
  notes: 152 commits, 6 contributors, MIT license
  commits: 152
  contributors: 6
  sourceStartedAt: '2026-02-19'
  grade: B
verification:
  firstEvidenceAt: '2026-08-22T08:08:26Z'
suiteRef: leonxlnx/taste-skill
trustMagnitude: 50.0
overallTrustGrade: B
trustMagnitudeInputHash: cde644fe4d047e0ff1e8526631f36a84354f606551431654c6ddc18f03f13e64
installable: false
---

## Installation
Add installation instructions here.
