---
id: mattpocock/grill-me
name: Grill Me
contributor: mattpocock
origin: false
genericSkillRef: grill-me
status: named
title: The Relentless Interviewer
catalogRef: mattpocock-grill-me
level: 4★
description: Conducts a relentless one-question-at-a-time interview about a plan or
  design, walking every branch of the decision tree with a recommended answer per
  question, resolving dependencies in order, and substituting codebase exploration
  wherever a question can be answered empirically.
links:
  github: https://github.com/mattpocock/skills/blob/main/skills/productivity/grill-me/SKILL.md
tags:
- design-review
- decision-tree
- socratic-method
- plan-stress-test
- one-question-at-a-time
createdAt: '2026-04-30'
updatedAt: '2026-05-15'
suiteRef: mattpocock/productivity
evidence:
- class: B
  source: https://github.com/mattpocock/skills/blob/main/skills/productivity/grill-me/SKILL.md
  evaluator: mbtiongson1
  date: '2026-05-15'
  notes: Original implementation by Matt Pocock; viral engineering pattern for disciplined
    agent alignment.
---

## Overview

Grill Me is the lightweight, documentation-free variant of the design-grilling pattern. It does not require a CONTEXT.md or ADR infrastructure. The agent interviews the user about every aspect of their plan, resolving decision-tree branches one dependency at a time. Each question comes paired with the agent's recommended answer to keep the conversation actionable.

Where a question can be answered by reading the codebase directly, the agent explores the codebase instead of asking. This substitution prevents unnecessary back-and-forth on empirically determinable facts.

## Origin

Second named implementation of the `design-review` skill bucket (origin: mattpocock/grill-with-docs). Grill Me is the simpler variant — no domain-model integration or documentation side effects.

## Installation

This skill is included in the Matt Pocock skills suite. It is highly recommended to install the full suite to enable cross-skill context sharing.

```bash
npx skills@latest add mattpocock/skills
```

No additional setup required beyond the main suite installation.
