---
id: huggingface/transformers-js
name: Transformers.js
contributor: huggingface
origin: false
genericSkillRef: multimodal-reasoning
status: named
title: The Browser Modelwright
catalogRef: huggingface-transformers-js
level: 1★
description: Runs Hugging Face Transformers.js models directly in JavaScript and TypeScript
  across browser and server runtimes for NLP, vision, audio, and multimodal inference
  with WebGPU or WASM.
links:
  github: https://github.com/huggingface/skills/blob/main/skills/transformers-js/SKILL.md
tags:
- huggingface
- transformers-js
- javascript
- webgpu
- inference
createdAt: '2026-05-03'
updatedAt: '2026-08-30'
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
  details: Level updated from 2★ to 1★ per G7 final rankings calibration.
- timestamp: '2026-08-29T17:15:49Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM 0.0 -> 0.0, grade ungraded -> ungraded (gaia dev calibrate-trust-magnitude;
    Issue #1600)'
trustMagnitudeInputHash: 9093a93e611a848c80ec9f6040e52c7473660a0840c18176edf7e1c73aa34254
---

## Overview

Transformers.js brings machine-learning inference into JavaScript and TypeScript runtimes. The skill is concrete about pipeline setup, model selection, browser and server execution, WebGPU and WASM fallbacks, and cleanup patterns for NLP, vision, audio, and multimodal workloads.

## Origin

Curated from Hugging Face's official `huggingface/skills` repository. This is a named implementation of the `multimodal-reasoning` bucket with catalog mappings to code generation and object detection.
