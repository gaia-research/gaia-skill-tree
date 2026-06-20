---
id: mbtiongson1/gaia-bot-curate
name: Gaia Bot Curate
contributor: mbtiongson1
origin: false
genericSkillRef: registry-curation
status: named
level: 1★
description: Runs an automated batch curation pass over the Gaia skill registry —
  scanning for new agent skills, validating evidence, and opening versioned draft
  PRs without human intervention.
createdAt: '2026-05-27'
updatedAt: '2026-06-01'
title: The Automated Curator
links:
  github: https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-bot-curate/SKILL.md
tags:
- registry-curation
- automation
- batch-processing
timeline:
- timestamp: '2026-05-26T16:36:58Z'
  action: add
  contributor: mbtiongson1
  details: Added named skill mbtiongson1/gaia-bot-curate
- timestamp: '2026-06-01T15:13:07Z'
  action: demote
  contributor: unknown
  details: Calibrated level from 3★ to 2★
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:19Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:38Z'
  details: TM 0.0 -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:42Z'
  details: TM 0.0 -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- timestamp: '2026-06-20T06:31:33Z'
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
trustMagnitudeInputHash: 9bb9d2905db22370679e847dce6c1c55cbc7f736d1a648aeb8980a78cb5cc5d0
---

## Overview

Runs an automated batch curation pass over the Gaia skill registry: scans configured `bot/*` crawl branches for new candidate skills, validates evidence classes, normalizes the resulting batch, and opens versioned draft PRs without human intervention. Designed for headless CI use; complements human-driven `gaia-curate`.
