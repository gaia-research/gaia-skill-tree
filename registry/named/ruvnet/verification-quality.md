---
id: ruvnet/verification-quality
name: Verification Quality
contributor: ruvnet
origin: false
genericSkillRef: verification-before-completion
status: named
title: "The Quality Sentinel"
catalogRef: ruvnet-verification-quality
level: "2★"
description: Implements structured pre-completion verification checklists ensuring quality gates are met before task finalization.
links:
  github: https://github.com/ruvnet/ruflo/blob/main/.agents/skills/verification-quality/SKILL.md
tags:
  - verification
  - quality
  - checklists
  - quality-gates
  - completion
createdAt: "2026-05-19"
updatedAt: "2026-05-19"
suiteRef: "ruvnet/ruflo"
---

## Overview

Verification Quality enforces structured quality gates at task completion boundaries within Ruflo agent workflows. Rather than allowing agents to finalize tasks without review, it injects pre-completion checklist evaluation, automated test coverage verification, and documentation completeness checks. Only tasks that pass all configured gates are allowed to proceed to final output.

## Key Capabilities

- **Pre-completion checklists**: configurable verification steps that must pass before task finalization
- **Automated quality gates**: programmatic enforcement of quality standards at completion boundaries
- **Test coverage verification**: ensures specified coverage thresholds are met before sign-off
- **Documentation checks**: validates that required documentation is present and complete

## Origin

Published by @ruvnet as a variant implementation for the `verification-before-completion` skill bucket.

Sourced from the Ruflo platform (ruvnet/ruflo, 34k+ stars).
