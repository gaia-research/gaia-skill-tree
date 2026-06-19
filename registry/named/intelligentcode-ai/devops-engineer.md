---
id: intelligentcode-ai/devops-engineer
name: DevOps Engineer
contributor: intelligentcode-ai
origin: false
links:
  github: https://github.com/intelligentcode-ai/skills/blob/main/skills/devops-engineer/SKILL.md
genericSkillRef: deployment-automation
status: named
title: The DevOps Sentinel
level: 2★
description: CI/CD pipeline design and deployment automation specialist — build systems,
  artifact publishing, environment promotion, and rollback strategies.
tags:
- cicd
- deployment
- pipeline
- docker
- kubernetes
- terraform
- rollback
updatedAt: '2026-06-20'
evidence:
- class: C
  source: https://github.com/intelligentcode-ai/skills/blob/main/skills/devops-engineer/SKILL.md
  evaluator: mbtiongson1
  date: '2026-04-30'
  notes: intelligentcode-ai/skills — practical coding agent skills; devops-engineer
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
    agent skill for devops-engineer domain
  sourceStartedAt: '2025-01-01'
timeline:
- timestamp: '2026-06-14T12:32:41Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/intelligentcode-ai/skills/blob/main/skills/devops-engineer/SKILL.md
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
- timestamp: '2026-06-19T17:10:08Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/intelligentcode-ai/skills/blob/main/skills/devops-engineer/SKILL.md
    as B (trustNumber: 65.0)'
- timestamp: '2026-06-19T17:10:43Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/intelligentcode-ai/skills (type:
    self-attestation)'
- timestamp: '2026-06-19T17:10:44Z'
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
trustMagnitudeInputHash: 91973af4d09b24b51a4ec1b88013a7fbf70f1631f08453154627cc9c2c8fee35
verification:
  firstEvidenceAt: '2026-06-19T17:10:43Z'
---

## Overview

Designs and executes end-to-end CI/CD pipelines: from code push through build, test, containerisation, artifact registry push, environment promotion (dev → staging → prod), and rollback on failure.

## Key behaviours

- CI pipeline authoring for GitHub Actions, GitLab CI, or Buildkite
- Docker image build, tag, and push to configured registry
- Kubernetes deployment with rolling update and health check gates
- Automated rollback trigger on failed health checks

## Source

[intelligentcode-ai/skills — devops-engineer/SKILL.md](https://github.com/intelligentcode-ai/skills/blob/main/skills/devops-engineer/SKILL.md)
