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
level: 1★
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
updatedAt: '2026-06-21'
evidence:
- class: C
  source: https://github.com/intelligentcode-ai/skills/blob/main/skills/security-engineer/SKILL.md
  evaluator: mbtiongson1
  date: '2026-04-30'
  notes: intelligentcode-ai/skills — practical coding agent skills; security-engineer
    provides production-ready implementation (trust updated from C=50 to B-equiv=65)
  type: repo
  commits: 34
  contributors: 1
  trustNumber: 65.0
- source: https://github.com/intelligentcode-ai/skills
  evaluator: unknown
  date: '2026-06-20'
  type: self-attestation
  trustNumber: 60.0
  grade: C
  notes: intelligentcode-ai/skills suite self-attested via README description; practical
    agent skill for security-engineer domain
  sourceStartedAt: '2025-01-01'
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
- timestamp: '2026-06-19T17:10:17Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/intelligentcode-ai/skills/blob/main/skills/security-engineer/SKILL.md
    as B (trustNumber: 65.0)'
- timestamp: '2026-06-19T17:10:51Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/intelligentcode-ai/skills (type:
    self-attestation)'
- timestamp: '2026-06-19T17:10:51Z'
  action: evidence_graded
  contributor: unknown
  details: 'Graded evidence from https://github.com/intelligentcode-ai/skills as B
    (trustNumber: 60.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T17:13:03Z'
  details: TM 1.3 -> 6.3, grade ungraded -> ungraded (direct edit -- CLI gap)
- timestamp: '2026-06-20T06:31:29Z'
  action: demote
  contributor: mbtiongson1
  details: Level updated from 2★ to 1★ per G7 final rankings calibration.
trustMagnitude: 6.3
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
trustMagnitudeInputHash: 1428c7a9742a7d350c49d372daa26c1f5f71276f43df90b09796e2ca7d568f78
verification:
  firstEvidenceAt: '2026-06-19T17:10:51Z'
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
