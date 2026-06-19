---
id: santifer/career-ops
name: Career-Ops
contributor: santifer
origin: true
genericSkillRef: career-operations
status: named
title: The Professional's Edge
level: 3★
description: Agentic job search pipeline that automates scanning, fit scoring, and
  CV tailoring.
links:
  github: https://github.com/santifer/career-ops/blob/main/.agents/skills/career-ops/SKILL.md
tags:
- career
- job-search
- automation
createdAt: '2026-05-14'
updatedAt: '2026-06-14'
evidence:
- class: B
  source: https://github.com/santifer/career-ops
  evaluator: gemini-cli
  date: '2026-05-14'
  notes: 'Career-Ops -- AI-powered job search system with CV tailoring and dashboard."
    (backfilled — class-to-type migration) (CLI gap: --commits/--contributors not
    supported by gaia dev evidence)'
  type: repo
  trustNumber: 70.0
  grade: B
  commits: 360
  contributors: 103
timeline:
- timestamp: '2026-06-14T12:33:02Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/santifer/career-ops as B (trustNumber:
    70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:21Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T11:52:12Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:39Z'
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
trustMagnitudeInputHash: db5e5fe407e1d3eddc4c12ec7d832aa90879d4912de57076e5017d183e2f42e0
---

## Overview

Career-Ops transforms the job application process into an automated workflow. It handles the tedious aspects of career management—from monitoring job boards to generating ATS-optimized resumes—allowing users to focus on high-value interactions while the agent manages the pipeline.
