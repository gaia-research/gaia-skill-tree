---
id: obra/executing-plans
name: Executing Plans
contributor: obra
origin: true
genericSkillRef: executing-plans
status: named
title: "The Faithful Executor"
level: "2★"
description: Loads a written implementation plan, reviews it critically, executes all tasks sequentially, and reports when complete — without improvising beyond the plan's scope.
links:
  github: https://github.com/obra/superpowers/blob/main/skills/executing-plans/SKILL.md
tags:
  - plan-execution
  - sequential-tasks
  - implementation
  - plan-driven
createdAt: "2026-05-18"
updatedAt: "2026-05-18"
suiteRef: "obra/superpowers"
---

## Overview

Executing Plans by @obra treats a written plan as a binding contract. The agent loads the plan, reads every task before touching code, flags any ambiguities, then executes each step in order — marking tasks complete as it goes and surfacing blockers rather than improvising around them. Completion is only reported after all tasks are verified done.

## Origin

First published by @obra in the obra/superpowers skill library. This is the origin implementation for the `executing-plans` skill bucket.
