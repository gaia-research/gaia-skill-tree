---
id: garrytan/codex
name: Codex
contributor: garrytan
origin: false
genericSkillRef: multi-agent-debate
status: named
title: Gstack Codex — Multi-Agent Code Debate
catalogRef: garrytan-codex
level: 3★
description: Spins up a structured Claude-versus-Codex debate over a proposed implementation,
  with each agent mounting adversarial critiques, to surface hidden design flaws before
  code lands.
links:
  github: https://github.com/garrytan/gstack/blob/main/codex/SKILL.md
tags:
- multi-agent-debate
- code-review
- adversarial
createdAt: '2026-05-18'
updatedAt: '2026-06-14'
suiteRef: garrytan/gstack
evidence:
- class: B
  source: https://github.com/garrytan/gstack/blob/main/codex/SKILL.md
  evaluator: mbtiongson1
  date: '2026-06-03'
  notes: 'Public SKILL.md in the garrytan/gstack suite repo (verified live). Spins
    up a structured Claude-versus-Codex debate over a proposed implementation, with
    each agent mounting adversarial critiques, to surface hidden… (backfilled — class-to-type
    migration) (CLI gap: commits+contributors not writable via gaia dev evidence)'
  type: repo
  commits: 323
  contributors: 9
  trustNumber: 70.0
  grade: B
timeline:
- timestamp: '2026-06-03T05:51:31Z'
  action: evidence_added
  contributor: unknown
  details: Added B evidence from https://github.com/garrytan/gstack/blob/main/codex/SKILL.md
- timestamp: '2026-06-14T12:32:19Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/garrytan/gstack/blob/main/codex/SKILL.md
    as B (trustNumber: 70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:14Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T10:36:26Z'
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
verification:
  firstEvidenceAt: '2026-06-03T05:51:31Z'
trustMagnitudeInputHash: 84970de7eedc57d4f2736b37fc3682f900d042390ba6215e5949be9c4764c0c6
---

## Overview

Spins up a structured Claude-versus-Codex debate over a proposed implementation, with each agent mounting adversarial critiques, to surface hidden design flaws before code lands.
