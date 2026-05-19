---
id: obra/subagent-driven-development
name: Subagent-Driven Development
contributor: obra
origin: true
genericSkillRef: subagent-driven-development
status: named
title: "The Swarm Architect"
level: "4★"
description: Executes plans by dispatching a fresh subagent per task with a two-stage review (spec compliance then code quality), keeping the orchestrator context clean throughout.
links:
  github: https://github.com/obra/superpowers/blob/main/skills/subagent-driven-development/SKILL.md
tags:
  - subagent
  - orchestration
  - plan-execution
  - two-stage-review
  - multi-agent
createdAt: "2026-05-18"
updatedAt: "2026-05-18"
suiteRef: "obra/superpowers"
---

## Overview

Subagent-Driven Development by @obra is the high-autonomy execution pattern: rather than carrying out plan tasks itself and accumulating context debt, the orchestrating agent spawns a dedicated subagent for every task. Each subagent gets a clean context window, executes its task, and returns results. A two-stage review then checks spec compliance first and code quality second before the result is accepted. This architecture allows multi-step projects to run at scale without the orchestrator's reasoning degrading.

## Origin

First published by @obra in the obra/superpowers skill library. This is the origin implementation for the `subagent-driven-development` skill bucket.
