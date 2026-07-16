---
id: openai/few-shot-learning
name: Few-Shot Learning
contributor: openai
origin: true
genericSkillRef: few-shot-learning
status: named
title: The In-Context Learner
catalogRef: openai-few-shot-learning
level: 4★
description: Conditions the model on a small set of examples within the prompt to
  adapt to new tasks without weight updates.
links:
  installable: false
  arxiv: https://arxiv.org/abs/2005.14165
tags:
- few-shot
- icl
- prompt-engineering
- gpt-3
- unique
createdAt: '2026-05-15'
updatedAt: '2026-07-16'
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
- timestamp: '2026-06-19T09:24:47Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://arxiv.org/abs/2005.14165 (type: arxiv)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T09:29:08Z'
  details: TM 0.0 -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T09:34:47Z'
  details: TM 0.0 -> 100.0, grade ungraded -> A (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:38Z'
  details: TM 0.0 -> 100.0, grade ungraded -> A (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:43Z'
  details: TM 0.0 -> 100.0, grade ungraded -> A (direct edit -- CLI gap)
- timestamp: '2026-06-20T06:31:35Z'
  action: rank_up
  contributor: mbtiongson1
  details: Level updated from 2★ to 4★ per G7 final rankings calibration.
- timestamp: '2026-07-04T22:34:46Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://huggingface.co/spaces/HuggingFaceH4/open_llm_leaderboard
    (type: benchmark-result)'
- timestamp: '2026-07-16T08:36:44Z'
  action: type_change
  contributor: mbtiongson1
  details: 'Generic parent ''few-shot-learning'' type: basic (unchanged; Yggdrasil
    II taxonomy migration #997)'
evidence:
- source: https://arxiv.org/abs/2005.14165
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: arxiv
  class: A
  notes: GPT-3 few-shot learning paper (Brown et al. 2020) — foundational, 50k+ citations
  citations: 50000
  grade: S
- source: https://huggingface.co/spaces/HuggingFaceH4/open_llm_leaderboard
  evaluator: unknown
  date: '2026-07-05'
  type: benchmark-result
  benchmarkId: mmlu@2024-03
  score: 86.4
  unit: pct
  runAt: '2024-03-01T00:00:00Z'
  provenance: mirrored
  attestor: https://huggingface.co/spaces/HuggingFaceH4/open_llm_leaderboard
  datasetHash: ab313191b8c989dea045d52eeb8896a4646eb66140b0f7723b8f0ebebea43eb5
  benchmarkInputHash: ededff463522c1793c65ce5c79411e4c1f5bbf4c7f369466a8dafbb61a9faca4
verification:
  firstEvidenceAt: '2026-06-19T09:24:47Z'
trustMagnitudeInputHash: 408d42e006dd910b5242b50e03126276ff7961527565125dd179b17b8cfb14dd
---

## Overview

Few-Shot Learning is the ability of an agent to perform a task after seeing only a few examples of that task in its context window. This implementation follows the patterns established by OpenAI in the GPT-3 paper.
