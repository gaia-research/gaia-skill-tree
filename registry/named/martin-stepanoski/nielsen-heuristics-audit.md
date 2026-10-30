---
id: martin-stepanoski/nielsen-heuristics-audit
name: Nielsen Heuristics Audit
contributor: martin-stepanoski
origin: false
genericSkillRef: ux-audit
status: named
title: The Ten Laws of Sight
catalogRef: martin-stepanoski-nielsen-heuristics-audit
level: 1★
description: Audits a UI interface against Jakob Nielsen's 10 usability heuristics
  step-by-step, scoring each heuristic, surfacing violations, and producing a prioritized
  remediation report.
links:
  github: https://github.com/mastepanoski/claude-skills/blob/main/skills/nielsen-heuristics-audit/SKILL.md
tags:
- ux
- usability
- nielsen
- heuristics
- accessibility
createdAt: '2026-04-30'
updatedAt: '2026-10-30'
evidence:
- class: B
  source: https://github.com/mastepanoski/claude-skills/blob/main/skills/nielsen-heuristics-audit/SKILL.md
  evaluator: mbtiongson1
  date: '2026-10-29'
  notes: 'Martin Stepanoski @mastepanoski/claude-skills -- /nielsen-heuristics-audit"
    audits UI against Nielsen 10 usability heuristics step-by-step. (backfilled —
    class-to-type migration) (CLI gap: --commits/--contributors not supported by gaia
    dev evidence)'
  type: repo
  trustNumber: 70.0
  commits: 51
  contributors: 2
- source: https://www.npmjs.com/package/@mastepanoski/claude-skills
  evaluator: mbtiongson1
  date: '2026-10-29'
  type: npm-downloads
  notes: npm registry downloads API last-week (2026-10-22..2026-10-28) for @mastepanoski/claude-skills
    (whole 13-skill bundle, v1.9.3, repository git+https://github.com/mastepanoski/claude-skills).
    Founder ruling 2026-10-30 FD-14.
  downloads: 57
  sourceStartedAt: '2026-02-05'
- source: https://github.com/mastepanoski/claude-skills
  evaluator: mbtiongson1
  date: '2026-10-29'
  type: github-stars-own
  notes: GitHub REST stargazers_count of mastepanoski/claude-skills at 2026-10-29
    (13 skills in repo; skill-file blob URL for this skill verified HTTP 200). Recorded
    at the repo root because the existing legacy repo row already occupies the skill
    blob URL and the production evidence merge drops same-URL cross-type rows (src/gaia_cli/evidence.py
    merge_evidence). Founder ruling 2026-10-30 FD-14.
  stars: 59
  skillCountInRepo: 13
  sourceStartedAt: '2026-02-05'
  grade: C
timeline:
- timestamp: '2026-06-02T01:42:59Z'
  action: demote
  contributor: unknown
  details: Origin status removed. Transferred to pbakaus/impeccable.
- timestamp: '2026-06-14T12:32:42Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/mastepanoski/claude-skills/blob/main/skills/nielsen-heuristics-audit/SKILL.md
    as B (trustNumber: 70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:18Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T11:52:12Z'
  details: TM 0.0 -> 4.9, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:38Z'
  details: TM 0.0 -> 4.9, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:40Z'
  details: TM 0.0 -> 4.9, grade ungraded -> ungraded (direct edit -- CLI gap)
- timestamp: '2026-06-19T17:09:30Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://www.nngroup.com/articles/ten-usability-heuristics/
    (type: peer-review)'
- timestamp: '2026-06-19T17:09:31Z'
  action: evidence_graded
  contributor: unknown
  details: 'Graded evidence from https://www.nngroup.com/articles/ten-usability-heuristics/
    as A (trustNumber: 80.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T17:13:03Z'
  details: TM 4.9 -> 94.9, grade ungraded -> B (direct edit -- CLI gap)
- timestamp: '2026-06-20T06:31:30Z'
  action: rank_up
  contributor: mbtiongson1
  details: Level updated from 2★ to 3★ per G7 final rankings calibration.
- timestamp: '2026-08-29T17:15:51Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM 94.9 -> 94.9, grade B -> B (gaia dev calibrate-trust-magnitude; Issue
    #1600)'
- timestamp: '2026-09-09T20:31:08Z'
  action: demote
  contributor: mbtiongson1
  details: Calibrated level from 3★ to 1★
- timestamp: '2026-10-29T16:58:48Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/mastepanoski/claude-skills/blob/main/skills/nielsen-heuristics-audit/SKILL.md
    (type: github-stars-own)'
- timestamp: '2026-10-29T16:58:49Z'
  action: evidence_graded
  contributor: mbtiongson1
  details: 'Updated evidence #0 metadata from https://github.com/mastepanoski/claude-skills/blob/main/skills/nielsen-heuristics-audit/SKILL.md;
    changed commits, date'
- timestamp: '2026-10-29T16:58:50Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://www.npmjs.com/package/@mastepanoski/claude-skills
    (type: npm-downloads)'
- timestamp: '2026-10-29T16:59:36Z'
  action: evidence_removed
  contributor: mbtiongson1
  details: 'Removed dead/invalid evidence: https://github.com/mastepanoski/claude-skills/blob/main/skills/nielsen-heuristics-audit/SKILL.md'
- timestamp: '2026-10-29T16:59:37Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/mastepanoski/claude-skills (type:
    github-stars-own)'
- timestamp: '2026-10-29T16:59:48Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM 4.9 -> 31.93, grade ungraded -> C (gaia dev calibrate-trust-magnitude;
    Issue #1600)'
trustMagnitude: 31.93
overallTrustGrade: C
apexGateStatus:
  aGradedOriginsGte5: false
  sourceTenureDaysGte180AorS: true
  directNestedSuiteGte1: false
  depth2OnlyReachableGte1: false
  overallGradeS: false
  apexPromotionPrSigned: false
  crossOrgVerifier: null
  systemWideCap: null
trustMagnitudeInputHash: 56455d0946732a254ac5a96ba4f747f51deaaee4721ff276fd0a413c6d258756
verification:
  firstEvidenceAt: '2026-06-19T17:09:30Z'
---

## Overview

Nielsen Heuristics Audit by Martin Stepanoski applies Jakob Nielsen's 10 usability heuristics as a structured evaluation checklist. For each heuristic — visibility of system status, match between system and real world, user control and freedom, consistency, error prevention, recognition over recall, flexibility, aesthetics, error recovery, and help — the agent assesses the interface, assigns a severity score, and documents specific violations. The final output is a prioritized remediation report.

## Origin

First published by @mastepanoski (Martin Stepanoski) as an NPM package. This is the origin implementation for the `ux-audit` skill bucket.
