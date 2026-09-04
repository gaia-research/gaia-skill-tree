---
id: huggingface/huggingface-vision-trainer
name: Hugging Face Vision Trainer
contributor: huggingface
origin: false
genericSkillRef: object-detection
status: named
title: The Vision Forge
catalogRef: huggingface-vision-trainer
level: 1★
description: Trains and fine-tunes object detection, image classification, and SAM/SAM2
  segmentation models on Hugging Face Jobs or locally with dataset validation, metrics,
  Trackio, and Hub persistence.
links:
  github: https://github.com/huggingface/skills/blob/main/skills/huggingface-vision-trainer/SKILL.md
tags:
- huggingface
- vision
- object-detection
- segmentation
- fine-tuning
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
trustMagnitudeInputHash: 71a712396b0b1922b00967d041b6e89ce6f2ec18b7d2c6fead4c9cbfcc12f757
---

## Overview

Hugging Face Vision Trainer specializes model training for object detection, image classification, and SAM/SAM2 segmentation. It adds concrete validation rules for image, label, bounding-box, and mask datasets, plus training metrics, Trackio monitoring, hardware planning, and Hub persistence.

## Origin

Curated from Hugging Face's official `huggingface/skills` repository. This is a named implementation of the `object-detection` bucket with catalog mappings to fine-tuning and ML pipelines.
