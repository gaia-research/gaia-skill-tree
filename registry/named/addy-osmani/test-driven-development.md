---
id: addy-osmani/test-driven-development
name: Test-Driven Development
contributor: addy-osmani
origin: true
genericSkillRef: test-driven-development
status: named
title: The Red-Green Oath
catalogRef: addy-osmani-test-driven-development
level: 3★
description: Forces the AI agent to follow a strict red-green-refactor TDD workflow
  — explicitly blocking horizontal slicing (all tests first, then all code). Tests
  verify behaviour through public interfaces only, blocking code generation that skips
  the test step, and enforcing coverage thresholds before completing a task.
links:
  github: https://github.com/addyosmani/agent-skills/blob/main/skills/test-driven-development/SKILL.md
tags:
- tdd
- testing
- red-green-refactor
- workflow-enforcement
- software-quality
- vertical-slicing
- tracer-bullet
createdAt: '2026-04-30'
updatedAt: '2026-05-31'
timeline:
- timestamp: '2026-05-31T02:17:00Z'
  action: installation_updated
  contributor: unknown
  details: 'Replaced ## Installation section from /tmp/tdd_install.md'
---

## Overview

TDD is a workflow-enforcement skill that constrains the agent to the classic red-green-refactor cycle. Before writing any implementation, the agent must write a failing test that specifies the desired behavior. It is blocked from proceeding until the test exists and fails for the right reason.

This variant distinguishes itself by making the vertical-slice constraint explicit and enforced. The agent is explicitly blocked from the "horizontal slicing" anti-pattern (writing all tests first, then all code), which produces tests that verify imagined behaviour and become insensitive to real changes. Each cycle follows a tracer-bullet model: one failing test → minimal code to pass → repeat, never anticipating future tests.

## Origin

First published by @addyosmani (Addy Osmani) and expanded with constraints popularised by @mattpocock. This is the origin implementation for the `test-driven-development` skill bucket.

## Installation

Install via [gaia](https://github.com/mbtiongson1/gaia-skill-tree):

```bash
gaia skills install https://github.com/addyosmani/agent-skills/blob/main/skills/test-driven-development/SKILL.md
```

Or copy the raw skill file directly into your agent context:

```
https://github.com/addyosmani/agent-skills/blob/main/skills/test-driven-development/SKILL.md
```

**Usage**: Invoke `/test-driven-development` (Claude Code) to enforce the red-green-refactor TDD cycle. The skill blocks horizontal slicing and enforces coverage thresholds before marking any task complete.
