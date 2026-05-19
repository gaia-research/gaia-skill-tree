---
id: obra/systematic-debugging
name: Systematic Debugging
contributor: obra
origin: true
genericSkillRef: systematic-debugging
status: named
title: "The Root Cause Hunter"
level: "3★"
description: Finds the root cause before attempting any fix — building a minimal reproduction, forming ranked hypotheses, and instrumenting to confirm before writing a single corrective line.
links:
  github: https://github.com/obra/superpowers/blob/main/skills/systematic-debugging/SKILL.md
tags:
  - debugging
  - root-cause
  - hypothesis-driven
  - instrumentation
  - reproduction
createdAt: "2026-05-18"
updatedAt: "2026-05-18"
---

## Overview

Systematic Debugging by @obra prohibits speculative fixes. When a bug or test failure appears, the agent first confirms it can reproduce the issue deterministically, then minimises the reproduction to its essential form. It generates a ranked list of hypotheses, selects the most probable, instruments the code to test that hypothesis, and only writes a fix once the root cause is confirmed. Patches without a prior confirmed hypothesis are explicitly rejected.

## Origin

First published by @obra in the obra/superpowers skill library. This is the origin implementation for the `systematic-debugging` skill bucket.
