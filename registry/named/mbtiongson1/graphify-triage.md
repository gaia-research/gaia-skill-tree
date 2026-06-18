---
id: mbtiongson1/graphify-triage
name: Graphify Triage
contributor: mbtiongson1
origin: true
genericSkillRef: graph-driven-issue-triage
status: named
level: 2★
description: Analyzes the Gaia skill dependency graph to surface orphaned nodes, missing
  prerequisites, and structural inconsistencies — producing a prioritized list of
  graph fixes needed.
createdAt: '2026-05-27'
updatedAt: '2026-06-14'
title: The Graph Surgeon
links:
  github: https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/graphify-triage/SKILL.md
tags:
- graph-analysis
- triage
- visualization
- skill-graph
timeline:
- timestamp: '2026-05-26T16:36:59Z'
  action: add
  contributor: mbtiongson1
  details: Added named skill mbtiongson1/graphify-triage
- timestamp: '2026-06-01T15:13:09Z'
  action: demote
  contributor: unknown
  details: Calibrated level from 3★ to 2★
- timestamp: '2026-06-14T12:32:45Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/graphify-triage/SKILL.md
    as B (trustNumber: 70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:19Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
evidence:
- class: B
  source: https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/graphify-triage/SKILL.md
  evaluator: mbtiongson1
  date: '2026-05-30'
  notes: 'Reproducible playbook: graphify-triage script ingests safishamsi/graphify
    GRAPH_REPORT.md output, parses architectural-debt findings, and converts each
    into a tracked GitHub issue via gh issue create. First implementation of the fusion
    generic (graphify + triage). (backfilled — class-to-type migration)'
  type: repo
  trustNumber: 70.0
  grade: B
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
trustMagnitudeInputHash: 1b81b72edb95f86db5b13cc1bb7b9240ecb27f57c25fbe8bcd023cfb2bab8385
---

## Overview

Bridges static architectural analysis with project management. Runs `graphify` to generate a code-or-knowledge dependency graph, parses `graphify-out/GRAPH_REPORT.md` to identify orphaned nodes, missing prerequisites, and structural inconsistencies, then converts each finding into a tracked GitHub issue via `gh issue create`. The first implementation of `graph-driven-issue-triage` (a fusion of `safishamsi/graphify` + `mattpocock/triage`).
