---
id: openai/self-consistency
name: Self-Consistency
contributor: openai
origin: false
genericSkillRef: self-consistency
status: named
title: The Majority Consensus
catalogRef: openai-self-consistency
level: 2★
description: Samples multiple reasoning paths and selects the most consistent answer
  by majority vote.
links:
  installable: false
  arxiv: https://arxiv.org/abs/2203.11171
tags:
- self-consistency
- reasoning
- ensemble
- cot
- unique
createdAt: '2026-05-15'
updatedAt: '2026-06-19'
trustMagnitude: 100.0
overallTrustGrade: A
apexGateStatus:
  aGradedOriginsGte5: false
  sourceTenureDaysGte180AorS: false
  directNestedSuiteGte1: false
  depth2OnlyReachableGte1: false
  overallGradeS: false
  apexPromotionPrSigned: false
  crossOrgVerifier: null
  systemWideCap: null
timeline:
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:19Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- timestamp: '2026-06-19T09:25:06Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://arxiv.org/abs/2203.11171 (type: arxiv)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T09:29:08Z'
  details: TM 0.0 -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T09:34:47Z'
  details: TM 0.0 -> 100.0, grade ungraded -> A (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:38Z'
  details: TM 0.0 -> 100.0, grade ungraded -> A (direct edit -- CLI gap)
evidence:
- source: https://arxiv.org/abs/2203.11171
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: arxiv
  class: A
  notes: Self-Consistency CoT paper (Wang et al. 2022) — ~2000+ citations
  citations: 2000
verification:
  firstEvidenceAt: '2026-06-19T09:25:06Z'
trustMagnitudeInputHash: d23306f7b62a1ac700203a79421bbf217c5704eeaafe0ccb952ffda85a17e19d
---

## Overview

Self-Consistency improves chain-of-thought reasoning by sampling diverse paths and finding the consensus. It significantly boosts performance on math and logic tasks.
