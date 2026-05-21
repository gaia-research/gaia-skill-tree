---
id: mattpocock/zoom-out
name: Zoom Out
contributor: mattpocock
origin: true
genericSkillRef: code-explain
status: named
title: "The Architecture Zoom-Out"
title: "The Abstraction Lift"
catalogRef: mattpocock-zoom-out
level: "2★"
description: Signals the agent to ascend one layer of abstraction and produce a map of all relevant modules, callers, and domain-glossary terms in the unfamiliar code area, without explaining implementation details.
links:
  github: https://github.com/mattpocock/skills/blob/main/skills/engineering/zoom-out/SKILL.md
tags:
  - code-navigation
  - abstraction
  - module-map
  - domain-glossary
  - codebase-orientation
createdAt: "2026-04-30"
updatedAt: "2026-04-30"
suiteRef: "mattpocock/engineering"
---

## Overview

Zoom Out is a lightweight orientation directive: when the agent is unfamiliar with a section of code it triggers a single upward shift in abstraction level. Rather than explaining individual lines, the agent produces a module-and-caller map using the project's domain glossary vocabulary — giving the human (or an orchestrating agent) a navigational overview before drilling down.

The skill is intentionally minimal (`disable-model-invocation: true` in its source) and functions as a meta-signal to reframe from implementation to architecture.

## Origin

First published by @mattpocock (Matt Pocock, Total TypeScript). This is the origin implementation for the `code-explain` skill bucket's orientation/abstraction-lifting use case.
