---
id: mbtiongson1/gaia-audit
name: Gaia Audit
contributor: mbtiongson1
origin: true
genericSkillRef: registry-entry-audit
status: named
level: 3★
description: Performs a focused source-level correction for one target registry entry
  — verifying links, checking evidence classes, and filing an inline-diff fix PR with
  full citations.
createdAt: '2026-05-27'
updatedAt: '2026-05-27'
title: The Source Detective
links:
  github: https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-audit/SKILL.md
tags:
- registry-curation
- source-verification
- evidence
- correction
timeline:
- timestamp: '2026-05-26T16:36:57Z'
  action: add
  contributor: mbtiongson1
  details: Added named skill mbtiongson1/gaia-audit
evidence:
- class: A
  source: https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-audit/skill.md
  evaluator: mbtiongson1
  date: '2026-05-20'
  notes: Codified audit skill with 7-phase workflow, demotion rules, and registry-sync
    automation. Powers the gaia-meta-audit process.
---

## Overview

Performs a focused source-level correction for one target registry entry — verifying links, checking evidence classes, validating taxonomy mapping, and filing an inline-diff fix PR with full citations. The 7-phase audit discipline includes evidence re-verification, demotion checks, and automatic asset regeneration via `gaia dev`. Used after `gaia-meta-audit` produces a prioritized queue.
