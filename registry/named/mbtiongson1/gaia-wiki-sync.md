---
id: mbtiongson1/gaia-wiki-sync
name: Gaia Wiki Sync
contributor: mbtiongson1
origin: false
genericSkillRef: registry-curation
status: named
level: 2★
description: Synchronizes the Gaia project wiki with the current registry state —
  updating skill pages, contributor profiles, and changelog entries to reflect the
  latest approved changes.
createdAt: '2026-05-27'
updatedAt: '2026-05-30'
title: The Wiki Keeper
links:
  github: https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-wiki-sync/SKILL.md
tags:
- documentation
- wiki
- sync
timeline:
- timestamp: '2026-05-26T16:36:59Z'
  action: add
  contributor: mbtiongson1
  details: Added named skill mbtiongson1/gaia-wiki-sync
---

## Overview

Synchronizes the Gaia GitHub wiki (`gaia-skill-tree.wiki.git`) with recent merged PRs, README, CONTRIBUTING, and schema changes. Clones the wiki repo adjacent to the workspace (`../gaia-wiki`), updates pages, commits, and pushes from there. Preserves the wiki folder for subsequent updates per CLAUDE.md Wiki Management policy.
