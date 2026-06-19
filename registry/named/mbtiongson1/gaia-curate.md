---
id: mbtiongson1/gaia-curate
name: Gaia Curate
contributor: mbtiongson1
origin: true
genericSkillRef: registry-curation
status: named
level: 2★
description: Expands the Gaia skill registry with new, fully evidenced AI agent skills
  — researching skill sources, running validation, opening versioned PRs, and appending
  discovered marketplaces to the sources registry in one end-to-end workflow.
createdAt: '2026-05-27'
updatedAt: '2026-06-01'
title: The Registrar
links:
  github: https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-curate/SKILL.md
tags:
- registry-curation
- skill-discovery
- evidence
- validation
- research
timeline:
- timestamp: '2026-05-26T16:36:56Z'
  action: add
  contributor: mbtiongson1
  details: Added named skill mbtiongson1/gaia-curate
- timestamp: '2026-06-01T15:13:07Z'
  action: demote
  contributor: unknown
  details: Calibrated level from 4★ to 2★
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:19Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
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
---

## Overview

Expands the Gaia skill registry with new fully-evidenced AI agent skills: researches skill sources, sources reproducible (Tier B/A) evidence, runs schema and DAG validation, scripts graph updates via `gaia dev add` / `gaia dev link` / `gaia dev evidence`, opens versioned PRs, and appends discovered marketplaces to the sources registry. End-to-end registry-curation playbook.
