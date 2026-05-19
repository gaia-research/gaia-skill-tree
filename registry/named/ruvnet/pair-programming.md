---
id: ruvnet/pair-programming
name: Pair Programming
contributor: ruvnet
origin: false
genericSkillRef: subagent-driven-development
status: named
title: "The Coding Companion"
catalogRef: ruvnet-pair-programming
level: "2★"
description: Structures collaborative coding sessions between a primary implementation agent and a review subagent with continuous feedback loops.
links:
  github: https://github.com/ruvnet/ruflo
tags:
  - pair-programming
  - subagent
  - code-review
  - collaborative
  - feedback-loops
createdAt: "2026-05-19"
updatedAt: "2026-05-19"
---

## Overview

Pair Programming establishes a structured two-agent coding pattern within Ruflo: a primary agent implements features while a review subagent simultaneously evaluates code quality, correctness, and style. Continuous feedback loops between agents replicate the benefits of human pair programming — catching bugs early, enforcing standards, and improving overall code quality before task completion.

## Key Capabilities

- **Primary + review agent pairing**: dedicated implementation and review roles operating in tandem
- **Continuous feedback loops**: real-time review cycles that catch issues during implementation
- **Shared context memory**: both agents read and write to the same Ruflo memory namespace
- **Real-time review cycles**: the review agent provides incremental feedback as code is written

## Origin

Published by @ruvnet as a variant implementation for the `subagent-driven-development` skill bucket.

Sourced from the Ruflo platform (ruvnet/ruflo, 34k+ stars).
