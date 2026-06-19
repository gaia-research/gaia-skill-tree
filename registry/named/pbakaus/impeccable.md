---
id: pbakaus/impeccable
name: Impeccable
contributor: pbakaus
origin: true
genericSkillRef: ux-audit
status: named
title: The Aesthetic Shield
level: 4★
description: Elite design vocabulary and audit tool for polishing AI-generated frontend
  code.
links:
  github: https://github.com/pbakaus/impeccable/blob/main/.agents/skills/impeccable/SKILL.md
tags:
- design
- audit
- frontend
- polishing
createdAt: '2026-05-14'
updatedAt: '2026-06-19'
evidence:
- class: B
  source: https://github.com/pbakaus/impeccable
  evaluator: mbtiongson1
  date: '2026-05-14'
  notes: Paul Bakaus /impeccable -- Elite design vocabulary and audit tool with 23
    specialized polishing commands. (backfilled — class-to-type migration)
  type: repo
  trustNumber: 70.0
  grade: B
- source: https://github.com/pbakaus/impeccable/stargazers
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: github-stars-own
  class: A
  notes: 38,000 GitHub stars as of 2026-06-19 (verified via firecrawl validation report;
    standalone skill)
  stars: 38000
- source: https://arxiv.org/abs/2411.01606
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: arxiv
  class: A
  notes: Design systems / UI automation paper — ~19 citations as of 2026-06-19 (arXiv:2411.01606)
  citations: 19
timeline:
- timestamp: '2026-06-02T01:42:59Z'
  action: rank_up
  contributor: unknown
  details: Origin status set to true.
- timestamp: '2026-06-14T12:32:50Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/pbakaus/impeccable as B (trustNumber:
    70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:19Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- timestamp: '2026-06-19T09:20:18Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/pbakaus/impeccable (type: github-stars-own)'
- timestamp: '2026-06-19T09:23:05Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://arxiv.org/abs/2411.01606 (type: arxiv)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T09:29:08Z'
  details: TM 0.0 -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T09:34:47Z'
  details: TM 0.0 -> 41.8, grade ungraded -> C (direct edit -- CLI gap)
trustMagnitude: 41.8
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
verification:
  firstEvidenceAt: '2026-06-19T09:20:18Z'
trustMagnitudeInputHash: ce59d68021db89999e77ee93975fad82f4e8841b4f427bee9b3b234756a39424
---

## Overview

Impeccable is a comprehensive design skill that empowers agents to perform high-fidelity frontend audits. With 23 specialized commands like `/polish` and `/harden`, it enforces design best practices and ensures that generated code is visually and structurally "impeccable." This implementation serves as the foundational evidence for the `ux-audit` Unique skill.
