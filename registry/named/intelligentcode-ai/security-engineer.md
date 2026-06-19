---
id: intelligentcode-ai/security-engineer
name: Security Engineer
contributor: intelligentcode-ai
origin: false
links:
  github: https://github.com/intelligentcode-ai/skills/blob/main/skills/security-engineer/SKILL.md
genericSkillRef: security-audit
status: named
title: The Bastion's Eye
level: 2★
description: Security architecture specialist — vulnerability assessment, zero-trust
  design, compliance management, and incident response with severity-classified remediation
  guidance.
tags:
- security
- vulnerability
- zero-trust
- compliance
- owasp
- penetration-testing
updatedAt: '2026-06-14'
evidence:
- class: C
  source: https://github.com/intelligentcode-ai/skills/blob/main/skills/security-engineer/SKILL.md
  evaluator: mbtiongson1
  date: '2026-04-30'
  notes: intelligentcode-ai/skills security-engineer — vulnerability assessment and
    security architecture with zero-trust principles and compliance management. (backfilled
    — class-to-type migration)
  type: repo
  commits: 34
  contributors: 1
  trustNumber: 50.0
  grade: C
timeline:
- timestamp: '2026-06-14T12:32:41Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/intelligentcode-ai/skills/blob/main/skills/security-engineer/SKILL.md
    as C (trustNumber: 50.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:17Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T11:10:48Z'
  details: TM 0.0 -> 1.3, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:38Z'
  details: TM 0.0 -> 1.3, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:40Z'
  details: TM 0.0 -> 1.3, grade ungraded -> ungraded (direct edit -- CLI gap)
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
trustMagnitudeInputHash: 6af4c33dd2902f42f03558fe3b2ef4e6ef0a0153e8e985339eab45e540a2010d
---

## Overview

Performs systematic security reviews covering OWASP Top 10, dependency vulnerabilities, secrets in code, authentication/authorisation flaws, and infrastructure misconfigurations. Each finding includes severity (CVSS), reproduction steps, and a fix recommendation.

## Key behaviours

- OWASP Top 10 audit pass on submitted code diff or full codebase
- Dependency vulnerability scan (CVE lookup against lock files)
- Secrets detection (API keys, tokens, credentials in source)
- Zero-trust architecture review for new service integrations

## Source

[intelligentcode-ai/skills — security-engineer/SKILL.md](https://github.com/intelligentcode-ai/skills/blob/main/skills/security-engineer/SKILL.md)
