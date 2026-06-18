---
id: huggingface/huggingface-vision-trainer
name: Hugging Face Vision Trainer
contributor: huggingface
origin: false
genericSkillRef: object-detection
status: named
title: The Vision Forge
catalogRef: huggingface-vision-trainer
level: 3★
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
trustMagnitudeInputHash: 9c1399eed3413efcf51d9478aee5d8f1c6b7c642899701954c4a48cf7b099bc4
timeline:
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:17Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
---

## Overview

Hugging Face Vision Trainer specializes model training for object detection, image classification, and SAM/SAM2 segmentation. It adds concrete validation rules for image, label, bounding-box, and mask datasets, plus training metrics, Trackio monitoring, hardware planning, and Hub persistence.

## Origin

Curated from Hugging Face's official `huggingface/skills` repository. This is a named implementation of the `object-detection` bucket with catalog mappings to fine-tuning and ML pipelines.
