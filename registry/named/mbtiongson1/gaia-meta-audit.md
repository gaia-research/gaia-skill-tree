---
id: mbtiongson1/gaia-meta-audit
name: Gaia Meta Audit
contributor: mbtiongson1
origin: true
genericSkillRef: registry-health-scan
status: named
level: 3★
description: Produces a prioritized review queue of Gaia registry entries needing
  attention — flagging stale evidence, broken links, mis-classified tiers, and naming
  inconsistencies in one structured audit pass.
createdAt: '2026-05-27'
updatedAt: '2026-05-30'
title: The Triage Director
links:
  github: https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-meta-audit/SKILL.md
tags:
- registry-curation
- prioritization
- triage
- quality-control
timeline:
- timestamp: '2026-05-26T16:36:56Z'
  action: add
  contributor: mbtiongson1
  details: Added named skill mbtiongson1/gaia-meta-audit
- timestamp: '2026-05-30T00:00:00Z'
  action: demote
  contributor: mbtiongson1
  details: Demoted 4★ → 3★ to match canonical registry-health-scan generic level
    (named must not exceed generic per META §1).
  previousValue: 4★
  newValue: 3★
---

## Overview

Produces a prioritized review queue of Gaia registry entries needing attention: scans `registry/gaia.json`, `registry/named/**`, and the real-skill catalog for stale evidence, broken links, mis-classified tiers, brand-coupled IDs, missing 3★+ Star Bar implementations, and likely fusion candidates. Output is a P0–P4 table that hands off each accepted candidate to `/gaia-audit`.

The v1.1 workflow (refined during PR #525, the `review/meta/mbtiongson1-audit` cleanup) adds explicit detection for:

- **Brand-coupled generic IDs** (META §1) — generics must be abstract; e.g. `gaia-audit` → `registry-entry-audit`.
- **Mis-attributed `origin: true`** (META §4.1) — only one contributor holds Origin per generic; sort named skills by `createdAt` to verify.
- **Level overshoot** (META §1) — named claim must not exceed canonical generic.
- **Semantic Fusion candidates** (META §6.2) — pairs of named skills that compose two existing Extra generics into one workflow get extracted into a new Extra generic, **not** an Ultimate (which requires ≥10k repo stars).
- **Link-casing 404s** — GitHub raw paths are case-sensitive; standardize on `SKILL.md`.
- **Placeholder bodies / `testuser` timelines** — common artifacts of intake automation.

The skill also documents the `gaia dev` CLI vs direct-YAML-edit map (renames, calibration, evidence add are CLI; `level` / `origin` / `links.github` / body / timeline are direct edits) and the CI/branch-scope mechanics for `review/meta/*` branches (the `skip-scope-check` label is required when generated docs need to ship alongside registry mutations).
