---
id: obra/requesting-code-review
name: Requesting Code Review
contributor: obra
origin: true
genericSkillRef: requesting-code-review
status: named
title: "The Preemptive Review"
level: "3★"
description: Dispatches a code reviewer subagent with isolated context to catch issues before they cascade — producing a structured review report that guides targeted fixes.
links:
  github: https://github.com/obra/superpowers/blob/main/skills/requesting-code-review/SKILL.md
tags:
  - code-review
  - subagent
  - quality-gate
  - pre-merge
  - isolated-context
createdAt: "2026-05-18"
updatedAt: "2026-05-18"
suiteRef: "obra/superpowers"
---

## Overview

Requesting Code Review by @obra treats review as a first-class step, not an afterthought. The agent spawns a fresh reviewer subagent that receives only the diff and relevant context, performs an independent evaluation, and returns a structured report covering correctness, edge cases, naming, and potential regressions. The originating agent uses that report to make targeted fixes before opening a PR, intercepting issues that in-context blindness would miss.

## Origin

First published by @obra in the obra/superpowers skill library. This is the origin implementation for the `requesting-code-review` skill bucket.
