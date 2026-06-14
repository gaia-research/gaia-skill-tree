---
id: ruvnet/verification-quality
name: Verification Quality
contributor: ruvnet
origin: false
genericSkillRef: verification-before-completion
status: named
title: The Quality Sentinel
catalogRef: ruvnet-verification-quality
level: 2★
description: Implements structured pre-completion verification checklists ensuring
  quality gates are met before task finalization.
links:
  github: https://github.com/ruvnet/ruflo
tags:
- verification
- quality
- checklists
- quality-gates
- completion
createdAt: '2026-05-19'
updatedAt: '2026-06-14'
suiteRef: ruvnet/ruflo
evidence:
- class: B
  source: https://github.com/ruvnet/ruflo
  evaluator: mbtiongson1
  date: '2026-06-10'
  notes: Part of the Ruflo orchestration platform (public repo); pre-completion quality
    gates documented in the suite. (backfilled — class-to-type migration)
  type: repo
  trustNumber: 70.0
  grade: B
timeline:
- timestamp: '2026-06-10T05:38:18Z'
  action: evidence_added
  contributor: unknown
  details: Added B evidence from https://github.com/ruvnet/ruflo
- timestamp: '2026-06-14T12:33:02Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/ruvnet/ruflo as B (trustNumber:
    70.0)'
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
