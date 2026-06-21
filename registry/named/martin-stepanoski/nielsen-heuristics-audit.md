---
id: martin-stepanoski/nielsen-heuristics-audit
name: Nielsen Heuristics Audit
contributor: martin-stepanoski
origin: false
genericSkillRef: ux-audit
status: named
title: The Ten Laws of Sight
catalogRef: martin-stepanoski-nielsen-heuristics-audit
level: 3★
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
updatedAt: '2026-06-21'
evidence:
- class: B
  source: https://github.com/mastepanoski/claude-skills/blob/main/skills/nielsen-heuristics-audit/SKILL.md
  evaluator: mbtiongson1
  date: '2026-04-30'
  notes: 'Martin Stepanoski @mastepanoski/claude-skills -- /nielsen-heuristics-audit"
    audits UI against Nielsen 10 usability heuristics step-by-step. (backfilled —
    class-to-type migration) (CLI gap: --commits/--contributors not supported by gaia
    dev evidence)'
  type: repo
  trustNumber: 70.0
  commits: 32
  contributors: 2
- source: https://www.nngroup.com/articles/ten-usability-heuristics/
  evaluator: unknown
  date: '2026-06-20'
  type: peer-review
  trustNumber: 80.0
  grade: S
  notes: NNGroup — Nielsen's 10 Usability Heuristics; foundational UX evaluation framework
    (original 1994 publication by Jakob Nielsen); this skill implements the canonical
    heuristic audit methodology
  reviewers: 3
  sourceStartedAt: '1995-01-01'
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
trustMagnitude: 94.9
overallTrustGrade: B
apexGateStatus:
  aGradedOriginsGte5: false
  sourceTenureDaysGte180AorS: true
  directNestedSuiteGte1: false
  depth2OnlyReachableGte1: false
  overallGradeS: false
  apexPromotionPrSigned: false
  crossOrgVerifier: null
  systemWideCap: null
trustMagnitudeInputHash: ebebef54c32e30f7a3ebec75974b18d77cd03c054deca8e3748cb0480d4ab0d8
verification:
  firstEvidenceAt: '2026-06-19T17:09:30Z'
---

## Overview

Nielsen Heuristics Audit by Martin Stepanoski applies Jakob Nielsen's 10 usability heuristics as a structured evaluation checklist. For each heuristic — visibility of system status, match between system and real world, user control and freedom, consistency, error prevention, recognition over recall, flexibility, aesthetics, error recovery, and help — the agent assesses the interface, assigns a severity score, and documents specific violations. The final output is a prioritized remediation report.

## Origin

First published by @mastepanoski (Martin Stepanoski) as an NPM package. This is the origin implementation for the `ux-audit` skill bucket.
