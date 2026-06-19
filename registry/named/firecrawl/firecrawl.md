---
id: firecrawl/firecrawl
name: Firecrawl
contributor: firecrawl
origin: false
genericSkillRef: web-scrape
status: named
title: The Web Infuser
catalogRef: firecrawl-firecrawl
level: 2★
description: Open-source API for AI-oriented web search, scraping, crawling, and structured
  extraction from websites.
links:
  github: https://github.com/firecrawl/firecrawl
tags:
- web-scrape
- search
- extraction
- crawler
createdAt: '2026-05-17'
updatedAt: '2026-06-19'
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
- source: https://www.youtube.com/watch?v=kY0hN5-xK8U
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: social-signal
  class: A
  notes: 'Tyler AI YouTube: "Firecrawl Full Beginner Course | Let''s Scrape EVERYTHING."
    Comprehensive tutorial. Third-party validated.'
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
trustMagnitudeInputHash: 90c0823722780cb6ce523dca4ace8738d12d62e2f0ff49a1a5d4c660b4ff41e2
---

## Overview

Firecrawl is an API to search, scrape, and interact with the web for AI. It converts websites into LLM-ready markdown or structured data.

## Origin

Developed by the Firecrawl team as a foundational tool for agentic web interaction.
