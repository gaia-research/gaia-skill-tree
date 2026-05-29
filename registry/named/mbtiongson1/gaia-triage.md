---
id: mbtiongson1/gaia-triage
name: Gaia Triage
contributor: mbtiongson1
origin: false
genericSkillRef: issue-triage
status: named
level: 2★
description: Triages incoming skill proposals and issues against the Gaia registry
  backlog — sorting by impact, feasibility, and dependency order to produce an actionable
  prioritized work queue.
createdAt: '2026-05-27'
updatedAt: '2026-05-30'
title: The Issue Sorter
links:
  github: https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-triage/SKILL.md
tags:
- registry-curation
- triage
- prioritization
timeline:
- timestamp: '2026-05-26T16:37:01Z'
  action: add
  contributor: mbtiongson1
  details: Added named skill mbtiongson1/gaia-triage
---

## Overview

Triages and audits GitHub issues for the Gaia Skill Tree project: identifies stale issues, gathers evidence from the codebase, manages the issue lifecycle via the `gh` CLI, and bulk-applies labels/closures based on rule-based classification. A project-specific implementation of `issue-triage` for registry-curation backlog management.
