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
updatedAt: '2026-06-14'
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
trustMagnitude: 1.22
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
trustMagnitudeInputHash: e56318149ba55f7176dc825480b36688ac1a80737801f420a45b204948231fb1
---

## Overview

README Generator by GLINCKER inspects the project tree, reads `package.json`, `pyproject.toml`, or equivalent manifests, and infers the project's purpose, dependencies, and entry points. It then produces a structured README.md with badges, installation steps, usage examples, and a contributing section — calibrated to the project's actual technology stack.

## Origin

First published by @GLINCKER via the Claude Code Marketplace. This is the origin implementation for the `write-report` skill bucket under the documentation generation use case.
