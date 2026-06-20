---
id: huggingface/huggingface-llm-trainer
name: Hugging Face LLM Trainer
contributor: huggingface
origin: false
genericSkillRef: fine-tune
status: named
title: The Cloud Fine-Tuner
catalogRef: huggingface-llm-trainer
level: 1★
description: Runs LLM fine-tuning on Hugging Face Jobs using TRL or Unsloth, covering
  SFT, DPO, GRPO, reward modeling, dataset validation, hardware selection, Trackio
  monitoring, and Hub persistence.
links:
  github: https://github.com/huggingface/skills/blob/main/skills/huggingface-llm-trainer/SKILL.md
tags:
- huggingface
- fine-tuning
- trl
- jobs
- trackio
createdAt: '2026-05-03'
updatedAt: '2026-05-03'
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
timeline:
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:17Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:38Z'
  details: TM 0.0 -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:40Z'
  details: TM 0.0 -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- timestamp: '2026-06-20T06:31:28Z'
  action: demote
  contributor: mbtiongson1
  details: Level updated from 3★ to 1★ per G7 final rankings calibration.
trustMagnitudeInputHash: 9f90e8e3531489b02d3d65baeb703c83b098717f52d332c8a684aefe3ddbd10a
---

## Overview

Hugging Face LLM Trainer packages the full cloud fine-tuning path: method selection, dataset validation, hardware and cost planning, Trackio monitoring, Hub authentication, and permanent model persistence. It is broader than generic fine-tuning because it explicitly covers Hugging Face Jobs and modern TRL workflows such as SFT, DPO, GRPO, and reward modeling.

## Origin

Curated from Hugging Face's official `huggingface/skills` repository. This is a named implementation of the `fine-tune` bucket with catalog mappings to ML pipelines and reward modeling.
