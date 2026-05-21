---
id: mattpocock/to-issues
name: To Issues
contributor: mattpocock
origin: true
genericSkillRef: vertical-slice-planning
status: named
title: "The Vertical Slicer"
title: "The Vertical Slicer"
catalogRef: mattpocock-to-issues
level: "3★"
description: Breaks a plan, spec, or PRD into independently-grabbable GitHub issues as tracer-bullet vertical slices that each cut through all integration layers end-to-end. Classifies each slice HITL or AFK, maps dependency chains, quizzes the user on granularity, and publishes structured issues with acceptance criteria in dependency order.
links:
  github: https://github.com/mattpocock/skills/blob/main/skills/engineering/to-issues/SKILL.md
tags:
  - vertical-slicing
  - issue-decomposition
  - tracer-bullet
  - hitl
  - afk
  - acceptance-criteria
createdAt: "2026-04-30"
updatedAt: "2026-04-30"
suiteRef: "mattpocock/engineering"
---

## Overview

To Issues decomposes a plan into vertical slices — thin cuts through every integration layer (schema, API, UI, tests) that are each independently demoable or verifiable. It explicitly rejects horizontal slicing (doing all of one layer before the next).

Each proposed issue is classified as HITL (requires human judgment, design decisions, or external access) or AFK (can be implemented and merged autonomously). The agent presents the breakdown for user review, iterates on granularity and dependency correctness, then publishes issues in dependency order so blocking tickets receive real identifiers before blocked tickets reference them.

## Origin

First published by @mattpocock (Matt Pocock, Total TypeScript). This is the origin implementation for the `vertical-slice-planning` skill bucket.
