---
id: intelligentcode-ai/database-engineer
name: Database Engineer
contributor: intelligentcode-ai
origin: false
links:
  github: https://github.com/intelligentcode-ai/skills/blob/main/skills/database-engineer/SKILL.md
genericSkillRef: schema-design
status: named
title: The Database Oracle
level: 2★
description: Schema design and query optimization expert across relational, NoSQL,
  graph, time-series, and data warehouse stores with sub-second response targets.
tags:
- database
- schema
- sql
- nosql
- graph-db
- time-series
- normalization
updatedAt: '2026-06-20'
evidence:
- class: C
  source: https://github.com/intelligentcode-ai/skills/blob/main/skills/database-engineer/SKILL.md
  evaluator: mbtiongson1
  date: '2026-04-30'
  notes: intelligentcode-ai/skills — practical coding agent skills; database-engineer
    provides production-ready implementation (trust updated from C=50 to B-equiv=65)
  type: repo
  trustNumber: 65.0
  grade: B
  commits: 34
  contributors: 1
- source: https://github.com/intelligentcode-ai/skills
  evaluator: unknown
  date: '2026-06-20'
  type: self-attestation
  trustNumber: 60.0
  grade: B
  notes: intelligentcode-ai/skills suite self-attested via README description; practical
    agent skill for database-engineer domain
  sourceStartedAt: '2025-01-01'
timeline:
- timestamp: '2026-06-14T12:32:41Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/intelligentcode-ai/skills/blob/main/skills/database-engineer/SKILL.md
    as C (trustNumber: 50.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:17Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T11:52:12Z'
  details: TM 0.0 -> 1.3, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:38Z'
  details: TM 0.0 -> 1.3, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:40Z'
  details: TM 0.0 -> 1.3, grade ungraded -> ungraded (direct edit -- CLI gap)
- timestamp: '2026-06-19T17:10:07Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/intelligentcode-ai/skills/blob/main/skills/database-engineer/SKILL.md
    as B (trustNumber: 65.0)'
- timestamp: '2026-06-19T17:10:42Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/intelligentcode-ai/skills (type:
    self-attestation)'
- timestamp: '2026-06-19T17:10:42Z'
  action: evidence_graded
  contributor: unknown
  details: 'Graded evidence from https://github.com/intelligentcode-ai/skills as B
    (trustNumber: 60.0)'
trustMagnitude: 1.3
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
trustMagnitudeInputHash: c18b17a39a03032a37868b41821a025ac3bc0f5ecb683bd306b1e994d28e1e3d
verification:
  firstEvidenceAt: '2026-06-19T17:10:42Z'
---

## Overview

Designs data models from requirements, applying normalization (up to 3NF/BCNF), choosing storage engines, and planning index strategies. Covers migration scripts and rollback plans.

## Key behaviours

- Produces ER diagrams and DDL for relational databases (PostgreSQL, MySQL, SQLite)
- Recommends document vs. relational vs. graph storage based on access patterns
- Designs time-series schemas with partitioning and retention policies
- Writes migration scripts with up/down rollback

## Source

[intelligentcode-ai/skills — database-engineer/SKILL.md](https://github.com/intelligentcode-ai/skills/blob/main/skills/database-engineer/SKILL.md)
