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
updatedAt: '2026-06-14'
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
evidence:
- class: B
  source: https://github.com/firecrawl/firecrawl
  evaluator: mbtiongson1
  date: '2026-06-10'
  notes: Origin repository — open-source web search/scrape/crawl API for LLM agents;
    reproducible public implementation with documented usage. (backfilled — class-to-type
    migration)
  type: repo
  trustNumber: 70.0
  grade: B
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
trustMagnitudeInputHash: 90c0823722780cb6ce523dca4ace8738d12d62e2f0ff49a1a5d4c660b4ff41e2
verification:
  firstEvidenceAt: '2026-06-10T05:38:16Z'
---

## Overview

Firecrawl is an API to search, scrape, and interact with the web for AI. It converts websites into LLM-ready markdown or structured data.

## Origin

Developed by the Firecrawl team as a foundational tool for agentic web interaction.
