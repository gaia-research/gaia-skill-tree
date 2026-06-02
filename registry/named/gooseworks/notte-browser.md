---
id: gooseworks/notte-browser
name: Notte Browser
contributor: gooseworks
origin: true
genericSkillRef: browser-automation
status: named
title: The Digital Navigator
catalogRef: gooseworks-notte-browser
level: 1★
description: AI-first browser automation using the Notte Browser API to control browser
  sessions, scrape pages, fill forms, take screenshots, and run autonomous web agents
  with managed credential handling.
links:
  github: https://github.com/gooseworks-ai/goose-skills
tags:
- browser
- automation
- web-agent
- scraping
- notte
createdAt: '2026-04-30'
updatedAt: '2026-06-02'
timeline:
- timestamp: '2026-06-02T23:48:17Z'
  action: demote
  contributor: unknown
  details: Calibrated level from 3★ to 1★
---

## Overview

Notte Browser is an AI-first browser automation skill that wraps the Notte Browser API. It manages authenticated browser sessions, navigates pages, extracts structured data, fills forms, and captures screenshots. Unlike raw Playwright scripting, it exposes a high-level agentic interface suited for autonomous task execution in web environments.

## Key Capabilities

- **Session management**: create, monitor, and terminate browser sessions via REST API
- **Page interaction**: click, type, scroll, and fill forms with element targeting
- **Content extraction**: scrape structured data and take screenshots
- **Autonomous agents**: run AI agent tasks inside managed browser contexts

## Setup

Requires `~/.gooseworks/credentials.json` with an API key from `npx gooseworks login`.

## Origin

First published by @gooseworks as part of the goose-skills GTM toolkit. This is the origin implementation for the `browser-automation` skill bucket.

Sourced from the SkillsMP marketplace entry for `browser-automation-notte` (goose-skills, 625 stars).
