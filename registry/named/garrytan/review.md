---
id: garrytan/review
name: Review
contributor: garrytan
origin: false
genericSkillRef: code-review-pipeline
status: named
title: "Gstack Code Review"
catalogRef: garrytan-review
level: "4★"
description: Pre-landing code review combining structured checklist analysis with specialist subagents covering testing, security, and performance — plus adversarial review from both Claude and Codex — to catch SQL safety issues, LLM trust boundary violations, conditional side effects, and structural problems before merging.
links:
  github: https://github.com/garrytan/gstack/blob/main/review/SKILL.md
tags:
  - code-review
  - security
  - multi-agent
  - adversarial-review
suiteRef: "garrytan/gstack"
createdAt: "2026-05-18"
updatedAt: "2026-05-18"
---

## Overview

Gstack Code Review runs the full diff through a multi-layered review pipeline before any branch lands. A structured checklist covers SQL safety, LLM trust boundaries, and conditional side effects; specialist subagents handle testing, security, and performance in parallel; a final adversarial pass from both Claude and Codex surfaces issues that a single reviewer would miss.
