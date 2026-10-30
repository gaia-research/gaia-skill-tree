---
id: huggingface/huggingface-datasets
name: Hugging Face Datasets
contributor: huggingface
origin: false
genericSkillRef: data-analysis
status: named
title: The Dataset Cartographer
catalogRef: huggingface-datasets
level: 1★
description: Explores Hugging Face datasets through the Dataset Viewer API, resolving
  configs and splits, previewing rows, paginating records, searching text, filtering
  rows, and retrieving parquet metadata.
links:
  github: https://github.com/huggingface/skills/blob/main/skills/huggingface-datasets/SKILL.md
tags:
- huggingface
- datasets
- dataset-viewer
- parquet
- data-analysis
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
trustMagnitudeInputHash: 67fa5c1a3769a91a9cbdafb1e3d506a3c6b3f48a40d81fe2f89e64ca6c22e893
---

## Overview

Hugging Face Datasets makes dataset exploration reproducible through read-only Dataset Viewer API calls. It gives agents a precise workflow for resolving subsets and splits, previewing and paginating rows, searching text columns, filtering rows, discovering parquet shards, and checking size or statistics.

## Origin

Curated from Hugging Face's official `huggingface/skills` repository. This is a named implementation of the `data-analysis` bucket with additional catalog mappings to retrieval and web scraping.
