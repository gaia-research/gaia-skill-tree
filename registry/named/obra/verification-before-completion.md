---
id: obra/verification-before-completion
name: Verification Before Completion
contributor: obra
origin: true
genericSkillRef: verification-before-completion
status: named
title: "The Completion Gate"
level: "2★"
description: Requires running verification commands and confirming their output before claiming any work is complete, fixed, or passing — no claim without evidence.
links:
  github: https://github.com/obra/superpowers/blob/main/skills/verification-before-completion/SKILL.md
tags:
  - verification
  - completion
  - testing
  - quality-gate
  - discipline
createdAt: "2026-05-18"
updatedAt: "2026-05-18"
suiteRef: "obra/superpowers"
---

## Overview

Verification Before Completion by @obra is the simplest and most broadly applicable skill in the superpowers library: the agent is not allowed to say "done", "fixed", or "passing" without first running the relevant verification command and including its output. This single constraint eliminates an entire class of hallucinated completions and untested "fixes" that create downstream rework.

## Origin

First published by @obra in the obra/superpowers skill library. This is the origin implementation for the `verification-before-completion` skill bucket.
