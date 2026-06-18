---
id: huggingface/huggingface-papers
name: Hugging Face Papers
contributor: huggingface
origin: false
genericSkillRef: literature-review
status: named
title: The Paper Indexer
catalogRef: huggingface-papers
level: 2★
description: Looks up Hugging Face paper pages and arXiv IDs, fetching markdown paper
  content and structured metadata such as authors, linked models, datasets, Spaces,
  GitHub repos, and project pages.
links:
  github: https://github.com/huggingface/skills/blob/main/skills/huggingface-papers/SKILL.md
tags:
- huggingface
- papers
- arxiv
- metadata
- research
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
trustMagnitudeInputHash: 599e87473e2579557701861c44e82339f3ce490cf83fae97e013992c0c90945e
timeline:
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:17Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
---

## Overview

Hugging Face Papers gives agents a consistent way to parse Hugging Face paper URLs and arXiv identifiers, fetch markdown paper content, and retrieve structured metadata from the paper API. It is useful when research work needs citations, author metadata, linked models, datasets, Spaces, GitHub repositories, or project pages.

## Origin

Curated from Hugging Face's official `huggingface/skills` repository. This is a named implementation of the `literature-review` bucket with secondary mappings to research and source citation.
