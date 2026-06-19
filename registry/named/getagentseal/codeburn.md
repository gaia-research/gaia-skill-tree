---
id: getagentseal/codeburn
name: CodeBurn
contributor: getagentseal
origin: true
genericSkillRef: token-observability
status: named
title: The Ledger of Light
level: 2★
description: Cost and token observability tool for tracking AI coding agent spending
  across models and projects.
links:
  github: https://github.com/getagentseal/codeburn
tags:
- observability
- cost
- tokens
createdAt: '2026-05-14'
updatedAt: '2026-06-14'
evidence:
- class: B
  source: https://github.com/getagentseal/codeburn
  evaluator: gemini-cli
  date: '2026-05-14'
  notes: 'CodeBurn -- provides cost and token observability for AI coding tools; integrated"
    with 20 AI tools. Includes TUI dashboard, macOS menubar, optimization and yield
    analysis commands. (backfilled — class-to-type migration) (CLI gap: --commits/--contributors
    not supported by gaia dev evidence)'
  type: repo
  trustNumber: 70.0
  grade: B
  commits: 721
  contributors: 45
timeline:
- timestamp: '2026-06-14T12:32:27Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/getagentseal/codeburn as B
    (trustNumber: 70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:16Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T11:52:12Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:37Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
trustMagnitude: 36.0
overallTrustGrade: C
apexGateStatus:
  aGradedOriginsGte5: false
  sourceTenureDaysGte180AorS: false
  directNestedSuiteGte1: false
  depth2OnlyReachableGte1: false
  overallGradeS: false
  apexPromotionPrSigned: false
  crossOrgVerifier: null
  systemWideCap: null
trustMagnitudeInputHash: fed10b7235b3ffa4e485f54f4f888ce10942520a42c4de78e170d73da7ba822e
---

## Overview

CodeBurn provides real-time visibility into the operational costs of AI development. By reading local agent session logs, it attributes token usage and API costs to specific tasks and projects, helping developers and teams manage their AI budgets effectively.
