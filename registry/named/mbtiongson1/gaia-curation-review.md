---
id: mbtiongson1/gaia-curation-review
name: Gaia Curation Review
contributor: mbtiongson1
origin: false
genericSkillRef: registry-entry-audit
status: named
level: 2★
description: Reviews pending skill submissions against registry standards — checking
  evidence class thresholds, naming conventions, and tier accuracy before approving
  or requesting revisions.
createdAt: '2026-05-27'
updatedAt: '2026-06-01'
title: The Quality Gate
links:
  github: https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-curation-review/SKILL.md
tags:
- registry-curation
- review
- quality-gate
timeline:
- timestamp: '2026-05-26T16:36:59Z'
  action: add
  contributor: mbtiongson1
  details: Added named skill mbtiongson1/gaia-curation-review
- timestamp: '2026-06-01T15:13:08Z'
  action: demote
  contributor: unknown
  details: Calibrated level from 3★ to 2★
---

## Overview

Reviews an open curation PR (or branch) to determine exactly what it adds to the registry, surfaces quality issues against META standards (evidence class thresholds, naming conventions, tier accuracy, brand-coupled IDs), and recommends `merge` / `close` / `needs-work`. Optimized for stale Jules-generated PRs where the GitHub diff is buried in generated-file noise. A `registry-entry-audit` variant focused on PR-level review.
