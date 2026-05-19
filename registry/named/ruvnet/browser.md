---
id: ruvnet/browser
name: Browser
contributor: ruvnet
origin: false
genericSkillRef: browser-automation
status: named
title: "The Web Navigator"
catalogRef: ruvnet-browser
level: "2★"
description: Playwright-based browser automation for web scraping, E2E testing, form interaction, and screenshot capture within agent workflows.
links:
  github: https://github.com/ruvnet/ruflo
tags:
  - browser
  - playwright
  - automation
  - web-scraping
  - e2e-testing
createdAt: "2026-05-19"
updatedAt: "2026-05-19"
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
