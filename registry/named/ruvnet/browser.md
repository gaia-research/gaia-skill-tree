---
id: ruvnet/browser
name: Browser
contributor: ruvnet
origin: false
genericSkillRef: browser-automation
status: named
title: The Web Navigator
catalogRef: ruvnet-browser
level: 1★
description: Playwright-based browser automation for web scraping, E2E testing, form
  interaction, and screenshot capture within agent workflows.
links:
  github: https://github.com/ruvnet/ruflo
tags:
- browser
- playwright
- automation
- web-scraping
- e2e-testing
createdAt: '2026-05-19'
updatedAt: '2026-05-19'
suiteRef: ruvnet/ruflo
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
  timestamp: '2026-06-18T11:27:20Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:38Z'
  details: TM 0.0 -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:43Z'
  details: TM 0.0 -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- timestamp: '2026-06-20T06:31:35Z'
  action: demote
  contributor: mbtiongson1
  details: Level updated from 2★ to 1★ per G7 final rankings calibration.
trustMagnitudeInputHash: 2800d300af75cbe7c46f5a2a1021453fe365d4743f0e69e36fd763058958db17
---

## Overview

Browser provides Ruflo agents with full web browsing capabilities via Playwright. Agents can navigate to URLs, interact with page elements, fill forms, capture screenshots, and extract structured data from web pages. Deep integration with the Ruflo memory layer allows scraped content to persist across sessions for later retrieval and analysis.

## Key Capabilities

- **Playwright automation**: full Chromium/Firefox/WebKit browser control from within agent workflows
- **Web scraping**: structured data extraction from dynamic JavaScript-rendered pages
- **Form interaction**: automated form filling, submission, and multi-step web workflow traversal
- **Screenshot capture**: visual page capture for verification, reporting, and vision-model integration
- **Memory integration**: automatic persistence of browsed content to the Ruflo memory subsystem

## Origin

Published by @ruvnet as a variant implementation for the `browser-automation` skill bucket.

Sourced from the Ruflo platform (ruvnet/ruflo, 34k+ stars).

## Installation

This skill is part of the Ruflo orchestration platform.

```bash
npx ruflo@latest init
```

See the [Ruflo (ruvnet/ruflo)](../ruvnet/ruflo.md) capstone for full multi-topology installation options.
