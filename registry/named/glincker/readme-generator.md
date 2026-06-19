---
id: glincker/readme-generator
name: README Generator
contributor: glincker
origin: false
genericSkillRef: write-report
status: named
title: The Document Weaver
catalogRef: glincker-readme-generator
level: 2★
description: Analyzes a project's directory structure, dependency manifests, and configuration
  files to generate a professional README.md covering installation, usage, API reference,
  and contributing guidelines.
links:
  github: https://github.com/GLINCKER/claude-code-marketplace/blob/main/skills/documentation/readme-generator/SKILL.md
tags:
- documentation
- readme
- code-analysis
- project-structure
createdAt: '2026-04-30'
updatedAt: '2026-06-20'
timeline:
- timestamp: '2026-06-02T23:33:02Z'
  action: demote
  contributor: unknown
  details: Origin status removed. Transferred to garrytan/retro.
- timestamp: '2026-06-10T05:38:16Z'
  action: evidence_added
  contributor: unknown
  details: Added B evidence from https://github.com/GLINCKER/claude-code-marketplace/blob/main/skills/documentation/readme-generator/SKILL.md
- timestamp: '2026-06-14T12:32:27Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/GLINCKER/claude-code-marketplace/blob/main/skills/documentation/readme-generator/SKILL.md
    as B (trustNumber: 70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:16Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T10:36:26Z'
  details: TM 0.0 -> 1.22, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:37Z'
  details: TM 0.0 -> 1.22, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:38Z'
  details: TM 0.0 -> 1.22, grade ungraded -> ungraded (direct edit -- CLI gap)
- timestamp: '2026-06-19T17:12:31Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/GLINCKER/claude-code-marketplace
    (type: self-attestation)'
- timestamp: '2026-06-19T17:12:31Z'
  action: evidence_graded
  contributor: unknown
  details: 'Graded evidence from https://github.com/GLINCKER/claude-code-marketplace
    as B (trustNumber: 60.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T17:13:01Z'
  details: TM 1.22 -> 6.22, grade ungraded -> ungraded (direct edit -- CLI gap)
evidence:
- class: B
  source: https://github.com/GLINCKER/claude-code-marketplace/blob/main/skills/documentation/readme-generator/SKILL.md
  evaluator: mbtiongson1
  date: '2026-06-10'
  notes: 'Published implementation in the GLINCKER Claude Code Marketplace; reproducible
    from SKILL.md. (backfilled — class-to-type migration) (CLI gap: commits+contributors
    not writable via gaia dev evidence)'
  type: repo
  commits: 8
  contributors: 1
  trustNumber: 70.0
  grade: B
- source: https://github.com/GLINCKER/claude-code-marketplace
  evaluator: unknown
  date: '2026-06-20'
  type: self-attestation
  trustNumber: 60.0
  grade: B
  notes: GLINCKER claude-code-marketplace — 32 GitHub stars; readme-generator skill
    included in marketplace
  sourceStartedAt: '2025-01-01'
trustMagnitude: 6.22
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
verification:
  firstEvidenceAt: '2026-06-10T05:38:16Z'
trustMagnitudeInputHash: 07ab0eb5da249713d7bf31d24b345a2451e7cacd5eae1369b8955f6a03e0da2c
---

## Overview

README Generator by GLINCKER inspects the project tree, reads `package.json`, `pyproject.toml`, or equivalent manifests, and infers the project's purpose, dependencies, and entry points. It then produces a structured README.md with badges, installation steps, usage examples, and a contributing section — calibrated to the project's actual technology stack.

## Origin

First published by @GLINCKER via the Claude Code Marketplace. This is the origin implementation for the `write-report` skill bucket under the documentation generation use case.
