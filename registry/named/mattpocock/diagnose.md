---
id: mattpocock/diagnose
name: Diagnose
contributor: mattpocock
origin: false
genericSkillRef: autonomous-debug
status: named
title: "The Debugging Discipline"
title: "The Disciplined Diagnosis Loop"
catalogRef: mattpocock-diagnose
level: "2★"
description: Drives a rigorous five-phase debugging discipline — build a feedback loop, minimise, hypothesise, instrument, fix and regression-test — refusing to proceed until a fast deterministic pass/fail signal exists. Applies to hard bugs and performance regressions.
links:
  github: https://github.com/mattpocock/skills/blob/main/skills/engineering/diagnose/SKILL.md
tags:
  - debugging
  - diagnosis
  - feedback-loop
  - regression
  - root-cause-analysis
createdAt: "2026-04-30"
updatedAt: "2026-04-30"
suiteRef: "mattpocock/engineering"
---

## Overview

Diagnose by Matt Pocock enforces a disciplined debugging workflow structured as five explicit phases: (1) build a feedback loop, (2) minimise the reproduction, (3) generate and rank hypotheses, (4) instrument and test, (5) fix and write a regression test. The defining insight is Phase 1 — the agent spends disproportionate effort constructing a fast, deterministic, agent-runnable pass/fail signal before any other work. Without that signal, no amount of code inspection converges.

The skill covers a wide range of reproduction strategies: failing unit tests, curl/HTTP scripts against a running dev server, CLI invocations diffed against known-good snapshots, headless browser scripts, replay of captured traces, throwaway harnesses, and property/fuzz loops. Phases after Phase 1 are mechanical once the signal exists.

## Origin

First published by @mattpocock (Matt Pocock, Total TypeScript). This is a named implementation of the `autonomous-debug` skill bucket emphasising the feedback-loop-first philosophy.
