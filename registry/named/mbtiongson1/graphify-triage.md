---
id: mbtiongson1/graphify-triage
name: Graphify Triage
contributor: mbtiongson1
origin: true
genericSkillRef: graph-driven-issue-triage
status: named
level: 3★
description: Analyzes the Gaia skill dependency graph to surface orphaned nodes, missing
  prerequisites, and structural inconsistencies — producing a prioritized list of
  graph fixes needed.
createdAt: '2026-05-27'
updatedAt: '2026-05-30'
title: The Graph Surgeon
links:
  github: https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/graphify-triage/SKILL.md
tags:
- graph-analysis
- triage
- visualization
- skill-graph
timeline:
- timestamp: '2026-05-26T16:36:59Z'
  action: add
  contributor: mbtiongson1
  details: Added named skill mbtiongson1/graphify-triage
evidence:
- class: B
  source: https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/graphify-triage/SKILL.md
  evaluator: mbtiongson1
  date: '2026-05-30'
  notes: 'Reproducible playbook: graphify-triage script ingests safishamsi/graphify
    GRAPH_REPORT.md output, parses architectural-debt findings, and converts each
    into a tracked GitHub issue via gh issue create. First implementation of the fusion
    generic (graphify + triage).'
---

## Overview

Bridges static architectural analysis with project management. Runs `graphify` to generate a code-or-knowledge dependency graph, parses `graphify-out/GRAPH_REPORT.md` to identify orphaned nodes, missing prerequisites, and structural inconsistencies, then converts each finding into a tracked GitHub issue via `gh issue create`. The first implementation of `graph-driven-issue-triage` (a fusion of `safishamsi/graphify` + `mattpocock/triage`).
