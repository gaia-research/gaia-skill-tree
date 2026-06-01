---
id: mattpocock/to-prd
name: To PRD
contributor: mattpocock
origin: true
genericSkillRef: prd-generation
status: named
title: The PRD Synthesiser
catalogRef: mattpocock-to-prd
level: 2★
description: Synthesises the current conversation context and codebase knowledge into
  a fully-structured PRD — problem statement, extensive numbered user stories, implementation
  decisions (modules, interfaces, schema), testing decisions, and out-of-scope items
  — then publishes it to the project issue tracker.
links:
  github: https://github.com/mattpocock/skills/blob/main/skills/engineering/to-prd/SKILL.md
tags:
- prd
- requirements
- user-stories
- product-management
- issue-tracker
createdAt: '2026-04-30'
updatedAt: '2026-04-30'
suiteRef: mattpocock/engineering
evidence:
- class: B
  source: https://github.com/mattpocock/skills/blob/main/skills/engineering/to-prd/SKILL.md
  evaluator: mbtiongson1
  date: '2026-04-30'
  notes: Production skill that synthesises live conversation context into a fully-structured
    PRD and publishes it to the issue tracker.
---

## Overview

To PRD does not interview the user — it synthesises what it already knows from the conversation and codebase. The agent reads the domain glossary and existing ADRs, sketches major modules with deep-module opportunities (small interface, deep implementation), confirms module scope with the user, then writes the PRD using a strict template: problem statement → solution → extensive user stories → implementation decisions → testing decisions → out-of-scope → further notes.

The output is published directly to the issue tracker with the `needs-triage` label. Specific file paths and code snippets are intentionally excluded from implementation decisions to prevent fast-rotting documentation.

## Origin

First published by @mattpocock (Matt Pocock, Total TypeScript). This is the origin implementation for the `prd-generation` skill bucket.
