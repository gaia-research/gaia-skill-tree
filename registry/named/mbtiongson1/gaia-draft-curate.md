---
id: mbtiongson1/gaia-draft-curate
name: Gaia Draft Curate
contributor: mbtiongson1
origin: false
genericSkillRef: registry-curation
status: named
level: 2★
description: Creates structured draft skill entries for registry review — staging
  new discoveries with placeholder evidence and flagging fields that need human validation
  before promotion.
createdAt: '2026-05-27'
updatedAt: '2026-06-01'
title: The Draft Architect
links:
  github: https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-draft-curate/SKILL.md
tags:
- registry-curation
- draft
- workflow
timeline:
- timestamp: '2026-05-26T16:36:58Z'
  action: add
  contributor: mbtiongson1
  details: Added named skill mbtiongson1/gaia-draft-curate
- timestamp: '2026-06-01T15:13:08Z'
  action: demote
  contributor: unknown
  details: Calibrated level from 3★ to 2★
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:19Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:38Z'
  details: TM 0.0 -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
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
trustMagnitudeInputHash: d69cc350eb1236b06240f0f63a22048e205e4ff0c90ec79ec4c278d9e9b79ea4
---

## Overview

Reviews pending Gaia draft skill intake batches in `registry-for-review/skill-batches/` and opens draft PRs. Classifies each proposed skill (`accept` / `rename` / `duplicate` / `needs-evidence` / `reject`) without touching `registry/gaia.json` directly. Optionally triggers a promotion PR for accepted skills via `gaia promote`.
