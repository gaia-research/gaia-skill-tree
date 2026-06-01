---
id: browser-use/browser-harness
name: Browser Harness
contributor: browser-use
origin: true
genericSkillRef: browser-control
status: named
title: The Dom Whispering
level: 2★
description: Self-healing harness for direct browser control via CDP, enabling agents
  to write custom helpers at runtime.
links:
  github: https://github.com/browser-use/browser-harness
tags:
- browser
- cdp
- automation
createdAt: '2026-05-14'
updatedAt: '2026-05-14'
evidence:
- class: B
  source: https://github.com/browser-use/browser-harness
  evaluator: gemini-cli
  date: '2026-05-14'
  notes: Browser Harness -- self-healing harness connecting LLMs to browser via CDP.
---

## Overview

Browser Harness provides a low-level, resilient interface for web interaction. Unlike standard automation tools, it focuses on self-healing and runtime extensibility, allowing AI agents to dynamically adapt to UI changes by generating and executing their own browser scripts via the Chrome DevTools Protocol.
