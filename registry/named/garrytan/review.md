---
id: garrytan/review
name: Review
contributor: garrytan
origin: false
genericSkillRef: code-review-pipeline
status: named
title: Gstack Code Review
catalogRef: garrytan-review
level: 4★
description: Pre-landing code review combining structured checklist analysis with
  specialist subagents covering testing, security, and performance — plus adversarial
  review from both Claude and Codex — to catch SQL safety issues, LLM trust boundary
  violations, conditional side effects, and structural problems before merging.
links:
  github: https://github.com/garrytan/gstack/blob/main/review/SKILL.md
tags:
- code-review
- security
- multi-agent
- adversarial-review
createdAt: '2026-05-18'
updatedAt: '2026-06-03'
suiteRef: garrytan/gstack
evidence:
- class: B
  source: https://github.com/garrytan/gstack/blob/main/review/SKILL.md
  evaluator: mbtiongson1
  date: '2026-06-03'
  notes: Public SKILL.md in the garrytan/gstack suite repo (verified live). Pre-landing
    code review combining structured checklist analysis with specialist subagents
    covering testing, security, and performance — plus…
timeline:
- timestamp: '2026-06-03T05:51:35Z'
  action: evidence_added
  contributor: unknown
  details: Added B evidence from https://github.com/garrytan/gstack/blob/main/review/SKILL.md
---

## Overview

Gstack Code Review runs the full diff through a multi-layered review pipeline before any branch lands. A structured checklist covers SQL safety, LLM trust boundaries, and conditional side effects; specialist subagents handle testing, security, and performance in parallel; a final adversarial pass from both Claude and Codex surfaces issues that a single reviewer would miss.
