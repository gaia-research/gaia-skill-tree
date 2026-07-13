---
id: firecrawl/firecrawl-skills
name: Firecrawl Skills
contributor: firecrawl
origin: false
genericSkillRef: firecrawl
status: named
title: The Web Infuser
catalogRef: firecrawl-firecrawl
level: 4★
description: 'Suite of Firecrawl skills for web scraping, search, browser interaction,
  environment setup, and research. Install all skills: `npx -y firecrawl-cli@latest
  init --all --browser`'
links:
  github: https://github.com/firecrawl/firecrawl
  docs: https://docs.firecrawl.dev/sdks/cli
tags:
- web-scrape
- search
- extraction
- crawler
createdAt: '2026-05-17'
updatedAt: '2026-07-13'
timeline:
- timestamp: '2026-06-02T23:33:01Z'
  action: demote
  contributor: unknown
  details: Origin status removed. Transferred to garrytan/scrape.
- timestamp: '2026-06-10T05:38:16Z'
  action: evidence_added
  contributor: unknown
  details: Added B evidence from https://github.com/firecrawl/firecrawl
- timestamp: '2026-06-14T12:32:18Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/firecrawl/firecrawl as B (trustNumber:
    70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:14Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T10:36:26Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- timestamp: '2026-06-19T10:40:05Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/firecrawl/firecrawl (type: benchmark-result)'
- timestamp: '2026-06-19T10:42:24Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://www.youtube.com/watch?v=kY0hN5-xK8U (type:
    social-signal)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T10:52:24Z'
  details: TM 36.0 -> 36.0, grade C -> C (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:37Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:36Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- timestamp: '2026-07-13T06:22:34Z'
  action: suite_ref_set
  contributor: unknown
  details: Set suiteRef=firecrawl/firecrawl, genericSkillRef=firecrawl via `gaia dev
    fuse`.
- timestamp: '2026-07-13T06:22:37Z'
  action: note
  contributor: unknown
  details: Updated GitHub link to https://github.com/firecrawl/firecrawl/blob/main/README.md
- timestamp: '2026-07-13T06:22:38Z'
  action: rank_up
  contributor: unknown
  details: Calibrated level from 2★ to 4★
- timestamp: '2026-07-13T06:24:28Z'
  action: suite_ref_set
  contributor: unknown
  details: Set suiteRef=firecrawl/firecrawl, genericSkillRef=firecrawl via `gaia dev
    fuse`.
evidence:
- class: B
  source: https://github.com/firecrawl/firecrawl
  evaluator: mbtiongson1
  date: '2026-06-10'
  notes: 'Origin repository — open-source web search/scrape/crawl API for LLM agents;
    reproducible public implementation with documented usage. (backfilled — class-to-type
    migration) (CLI gap: commits+contributors not writable via gaia dev evidence)'
  type: repo
  commits: 5679
  contributors: 150
  trustNumber: 70.0
  grade: B
- source: https://github.com/firecrawl/firecrawl
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: benchmark-result
  class: A
  notes: 'scrape-content-dataset-v1 (1000 URLs): >95% dynamic page scrape success,
    P95 latency ~3.4s. JS-heavy SPAs and anti-bot protected sites (May 2026).'
- type: github-stars-own
  source: https://github.com/firecrawl/firecrawl/stargazers
  stars: 150087
  skillCountInRepo: 6
  grade: B
  evaluator: mbtiongson1
  date: '2026-07-13'
trustMagnitude: 36.0
overallTrustGrade: C
apexGateStatus:
  aGradedOriginsGte5: false
  sourceTenureDaysGte180AorS: false
  directNestedSuiteGte1: false
  depth2OnlyReachableGte1: false
  overallGradeS: false
  apexPromotionPrSigned: false
  crossOrgVerifier: null
  systemWideCap: null
verification:
  firstEvidenceAt: '2026-06-10T05:38:16Z'
trustMagnitudeInputHash: 884be262d5d5ab382aed51e452e0ce7498fb4667d542b11adfd4d9cbd2063a2a
suiteComponents:
  - firecrawl/firecrawl-build-interact
  - firecrawl/firecrawl-build-onboarding
  - firecrawl/firecrawl-build-scrape
  - firecrawl/firecrawl-build-search
  - firecrawl/firecrawl-research-index
---

## Overview

Firecrawl is an API to search, scrape, and interact with the web for AI. It converts websites into LLM-ready markdown or structured data.

## Origin

Developed by the Firecrawl team as a foundational tool for agentic web interaction.
