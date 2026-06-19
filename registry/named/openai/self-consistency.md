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
trustMagnitude: 0.0
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
trustMagnitudeInputHash: 140e60e64eb52479386604e5f0d20a6c86bafc335c6bfb9d89dfd4880b870c81
timeline:
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:19Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- timestamp: '2026-06-19T09:25:06Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://arxiv.org/abs/2203.11171 (type: arxiv)'
evidence:
- source: https://arxiv.org/abs/2203.11171
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: arxiv
  class: A
  notes: Self-Consistency CoT paper (Wang et al. 2022) — ~2000+ citations
verification:
  firstEvidenceAt: '2026-06-19T09:25:06Z'
---

## Overview

Self-Consistency improves chain-of-thought reasoning by sampling diverse paths and finding the consensus. It significantly boosts performance on math and logic tasks.
