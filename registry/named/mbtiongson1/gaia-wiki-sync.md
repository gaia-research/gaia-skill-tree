---
id: mbtiongson1/gaia-wiki-sync
name: Gaia Wiki Sync
contributor: mbtiongson1
origin: false
genericSkillRef: registry-curation
status: named
level: 1★
description: Synchronizes the Gaia project wiki with the current registry state —
  updating skill pages, contributor profiles, and changelog entries to reflect the
  latest approved changes.
createdAt: '2026-05-27'
updatedAt: '2026-05-30'
title: The Wiki Keeper
links:
  github: https://github.com/gaia-research/gaia-skill-tree/blob/main/.agents/skills/gaia-wiki-sync/SKILL.md
tags:
- documentation
- wiki
- sync
timeline:
- timestamp: '2026-05-26T16:36:59Z'
  action: add
  contributor: mbtiongson1
  details: Added named skill mbtiongson1/gaia-wiki-sync
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:19Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:38Z'
  details: TM 0.0 -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:42Z'
  details: TM 0.0 -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- timestamp: '2026-06-20T06:31:34Z'
  action: demote
  contributor: mbtiongson1
  details: Level updated from 2★ to 1★ per G7 final rankings calibration.
trustMagnitude: 0.0
overallTrustGrade: ungraded
apexGateStatus:
  aGradedOriginsGte5: false
  sourceTenureDaysGte180AorS: false
  directNestedSuiteGte1: false
  depth2OnlyReachableGte1: false
  overallGradeS: false
  apexPromotionPrSigned: false
  crossOrgVerifier: null
  systemWideCap: null
trustMagnitudeInputHash: 6bd00d97218668b215c54f858da766e9bb638fe008beb71dd7dc89176128ac85
---

## Overview

Synchronizes the Gaia GitHub wiki (`gaia-skill-tree.wiki.git`) with recent merged PRs, README, CONTRIBUTING, and schema changes. Clones the wiki repo adjacent to the workspace (`../gaia-wiki`), updates pages, commits, and pushes from there. Preserves the wiki folder for subsequent updates per CLAUDE.md Wiki Management policy.
