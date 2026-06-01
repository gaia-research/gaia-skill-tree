---
id: mbtiongson1/gaia-integrity
name: Gaia Integrity
contributor: mbtiongson1
origin: false
genericSkillRef: registry-curation
status: named
level: 2★
description: Validates the structural integrity of the Gaia registry — checking schema
  compliance, detecting duplicate IDs, verifying cross-references, and reporting any
  inconsistencies that would break build or generation.
createdAt: '2026-05-27'
updatedAt: '2026-06-01'
title: The Schema Sentinel
links:
  github: https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-integrity/SKILL.md
tags:
- registry-curation
- integrity
- validation
- schema
timeline:
- timestamp: '2026-05-26T16:37:00Z'
  action: add
  contributor: mbtiongson1
  details: Added named skill mbtiongson1/gaia-integrity
- timestamp: '2026-06-01T15:13:08Z'
  action: demote
  contributor: unknown
  details: Calibrated level from 3★ to 2★
---

## Overview

Validates the structural integrity of the Gaia registry: runs `gaia validate`, checks schema compliance, detects duplicate IDs, verifies cross-references between `registry/nodes/` and `registry/skills/`, and surfaces orphan documentation. Includes safe-archival of stale `.md` files via timestamped `registry/archive/`. Run before submitting a PR or after large registry shifts.
