---
id: anthropic/pptx
name: PPTX Editor
contributor: anthropic
origin: false
genericSkillRef: document-editing
status: named
title: The Slide Artisan
catalogRef: anthropic-pptx
level: 2★
description: Extracts slide content from PowerPoint (.pptx) files using markitdown,
  applies edits or design principles in-place, and repacks the file — enabling agents
  to read, modify, and write structured presentation files without a GUI.
links:
  github: https://github.com/anthropics/skills/blob/main/skills/pptx/SKILL.md
tags:
- pptx
- powerpoint
- document-editing
- markitdown
- presentations
createdAt: '2026-04-30'
updatedAt: '2026-06-02'
evidence:
- class: B
  source: https://github.com/anthropics/skills/blob/main/skills/pptx/SKILL.md
  evaluator: mbtiongson1
  date: '2026-04-30'
  notes: Anthropic /pptx slash command -- extracts, edits, packs, and applies design
    principles to PowerPoint files using markitdown.
timeline:
- timestamp: '2026-06-02T01:42:58Z'
  action: demote
  contributor: unknown
  details: Origin status removed. Transferred to mattpocock/edit-article.
---

## Overview

PPTX Editor by Anthropic uses the `markitdown` library to extract text and layout from `.pptx` files into a structured intermediate representation. The agent can then edit content, reorder slides, apply design rules, or generate new slides programmatically — then pack the result back into a valid `.pptx` file.

## Origin

First published by @anthropic. This is the origin implementation for the `document-editing` skill bucket.
