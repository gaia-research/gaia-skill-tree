---
id: huggingface/hf-cli
name: HF CLI
contributor: huggingface
origin: false
genericSkillRef: api-call
status: named
title: The Hub Operator
catalogRef: huggingface-hf-cli
level: 1★
description: Guides Hugging Face Hub CLI operations for downloading, uploading, managing
  repos, running Jobs, querying datasets, configuring Spaces, and handling Hub authentication.
links:
  github: https://github.com/huggingface/skills/blob/main/skills/hf-cli/SKILL.md
tags:
- huggingface
- hub
- cli
- jobs
- datasets
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
- timestamp: '2026-06-20T06:31:27Z'
  action: demote
  contributor: mbtiongson1
  details: Level updated from 2★ to 1★ per G7 final rankings calibration.
trustMagnitudeInputHash: 42d31e3ccaeefb074f7ba0632a0636d493cf8cb05dfbab3bf5935e6c53265a0c
---

## Overview

HF CLI turns the broad Hugging Face Hub command surface into an agent-ready operations playbook. It covers authentication, model and dataset transfers, repo management, Jobs, Spaces, collections, papers, webhooks, and inference endpoints through the modern `hf` command.

## Origin

Curated from Hugging Face's official `huggingface/skills` repository. This is a named implementation of the `api-call` bucket with secondary catalog mappings to retrieval and shell execution.
