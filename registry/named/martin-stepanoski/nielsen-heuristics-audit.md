---
id: martin-stepanoski/nielsen-heuristics-audit
name: Nielsen Heuristics Audit
contributor: martin-stepanoski
origin: false
genericSkillRef: ux-audit
status: named
title: The Ten Laws of Sight
catalogRef: martin-stepanoski-nielsen-heuristics-audit
level: 2★
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
updatedAt: '2026-06-14'
evidence:
- class: B
  source: https://github.com/mastepanoski/claude-skills/blob/main/skills/nielsen-heuristics-audit/SKILL.md
  evaluator: mbtiongson1
  date: '2026-04-30'
  notes: Martin Stepanoski @mastepanoski/claude-skills -- /nielsen-heuristics-audit
    audits UI against Nielsen 10 usability heuristics step-by-step. (backfilled —
    class-to-type migration) (CLI gap: --commits/--contributors not supported by gaia dev evidence)
  type: repo
  trustNumber: 70.0
  grade: B
  commits: 32
  contributors: 2
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
trustMagnitude: 0.0
overallTrustGrade: ungraded
apexGateStatus:
  aGradedOriginsGte5: false
  sourceTenureDaysGte180AorS: false
  directNestedSuiteGte1: false
  depth2OnlyReachableGte1: false
  overallGradeS: false
  apexPromotionPrSigned: false
  crossOrgVerifier: null
  systemWideCap: null
trustMagnitudeInputHash: 939993febaef44a14d5522e1df36595de64071fe7e4d98347f187ea3b353edfd
---

## Overview

Nielsen Heuristics Audit by Martin Stepanoski applies Jakob Nielsen's 10 usability heuristics as a structured evaluation checklist. For each heuristic — visibility of system status, match between system and real world, user control and freedom, consistency, error prevention, recognition over recall, flexibility, aesthetics, error recovery, and help — the agent assesses the interface, assigns a severity score, and documents specific violations. The final output is a prioritized remediation report.

## Origin

First published by @mastepanoski (Martin Stepanoski) as an NPM package. This is the origin implementation for the `ux-audit` skill bucket.
