---
type: "AI Agent Skill"
title: "Browser Control"
description: "A foundational skill for interacting directly with the web browser using Chrome DevTools Protocol (CDP)."
resource: "https://gaiaskilltree.com/codex.html#browser-control"
tags: ["gaia-skill-tree", "basic-skill"]
timestamp: "2026-06-01T00:00:00Z"
---

# Browser Control

## Description

Directly controls a web browser via low-level protocols (like CDP) to manipulate the DOM, manage cookies, intercept network traffic, and simulate user interactions (clicking via coordinates, taking screenshots) without relying on heavy wrapper frameworks like Playwright or Puppeteer.

## Use Case

When an agent needs to autonomously browse web pages, extract visual and structural information via screenshots or DOM parsing, and interact with the page by firing synthetic mouse and keyboard events using the browser's compositor level.

## Directives

- Prioritize visual verification via screenshots before executing clicks or DOM interactions.
- Use coordinate-based interactions rather than complex selector-based DOM queries when possible.
- Rely on HTTP requests for bulk data fetching rather than browser navigation when applicable.
- Assume the browser runs either via a local debug connection (CDP on port 9222) or through a remote session using Browser Use.

## Derivatives

- [Browser Automation](/skills/extra/browser-automation.md)
- [Founder Mode](/skills/ultimate/founder-mode-orchestration.md)

