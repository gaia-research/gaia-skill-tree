---
id: huggingface/huggingface-datasets
name: Hugging Face Datasets
contributor: huggingface
origin: false
genericSkillRef: data-analysis
status: named
title: The Dataset Cartographer
catalogRef: huggingface-datasets
level: 2★
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
trustMagnitudeInputHash: 019a6f5d4b7f006329654997bedec28a7c94b028414f1d7b2e66ec54ae3cd09b
---

## Overview

Hugging Face Datasets makes dataset exploration reproducible through read-only Dataset Viewer API calls. It gives agents a precise workflow for resolving subsets and splits, previewing and paginating rows, searching text columns, filtering rows, discovering parquet shards, and checking size or statistics.

## Origin

Curated from Hugging Face's official `huggingface/skills` repository. This is a named implementation of the `data-analysis` bucket with additional catalog mappings to retrieval and web scraping.
