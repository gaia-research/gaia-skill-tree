---
id: ruvnet/agentic-jujutsu
name: Agentic Jujutsu
contributor: ruvnet
origin: true
genericSkillRef: git-diff-risk-analysis
status: named
title: The Risk Whisperer
catalogRef: ruvnet-agentic-jujutsu
level: 2★
description: Analyzes git diffs for complexity, churn, and risk scores to prioritize
  review attention and flag dangerous changes.
links:
  github: https://github.com/ruvnet/ruflo/blob/main/.agents/skills/agentic-jujutsu/SKILL.md
tags:
- git
- diff-analysis
- risk-scoring
- code-review
- churn
createdAt: '2026-05-19'
updatedAt: '2026-05-19'
suiteRef: ruvnet/ruflo
evidence:
- class: B
  source: https://github.com/ruvnet/ruflo
  evaluator: mbtiongson1
  date: '2026-05-19'
  notes: Ruflo orchestration platform — 34k+ GitHub stars.
---

## Overview

Agentic Jujutsu applies judo-style leverage to code review: instead of reviewing everything equally, it identifies the highest-risk changes and focuses attention there. By scoring diffs for complexity, historical churn, and structural risk, it helps reviewers spend effort where it matters most and surfaces dangerous changes that might otherwise slip through.

## Key Capabilities

- **Diff complexity scoring**: quantifies cyclomatic and structural complexity introduced by each change
- **Churn analysis**: tracks file-level change frequency to identify historically volatile areas
- **Historical risk correlation**: matches current changes against past bug-introducing patterns
- **Per-file risk breakdown**: produces file-by-file risk reports with prioritized review queues
- **Review prioritization**: ranks changes so reviewers tackle the riskiest items first

## Origin

First published by @ruvnet as part of the Ruflo orchestration platform. This is the origin implementation for the `git-diff-risk-analysis` skill bucket.

Sourced from the Ruflo platform (ruvnet/ruflo, 34k+ stars).
