---
id: mbtiongson1/gaia-docs-sync
name: Gaia Docs Sync
contributor: mbtiongson1
origin: false
genericSkillRef: registry-curation
status: named
level: 2★
description: Keeps the generated Gaia documentation site in sync with the registry
  — rebuilding HTML pages, updating skill indexes, and regenerating badges when registry
  content changes.
createdAt: '2026-05-27'
updatedAt: '2026-05-30'
title: The Docs Steward
links:
  github: https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-docs-sync/SKILL.md
tags:
- documentation
- docs
- sync
timeline:
- timestamp: '2026-05-26T16:37:00Z'
  action: add
  contributor: mbtiongson1
  details: Added named skill mbtiongson1/gaia-docs-sync
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:19Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:38Z'
  details: TM 0.0 -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:42Z'
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
trustMagnitudeInputHash: 2f1c083b8af5d7a431caa2d166ca4710ea7e94f8bcf8a110b1feb1e1412c084a
---

## Overview

Synchronizes the generated Gaia documentation site with the current registry state: rebuilds HTML pages, updates skill indexes, regenerates badges, and pushes both the main repo and the adjacent wiki repo so all surfaces stay in sync. Run after registry mutations to prevent the `Schema + DAG + Integrity Checks` CI job from failing on stale `docs/graph/named/index.json` or contributor profiles.
