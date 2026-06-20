---
id: mbtiongson1/gaia-triage
name: Gaia Triage
contributor: mbtiongson1
origin: false
genericSkillRef: issue-triage
status: named
level: 1★
description: Triages incoming skill proposals and issues against the Gaia registry
  backlog — sorting by impact, feasibility, and dependency order to produce an actionable
  prioritized work queue.
createdAt: '2026-05-27'
updatedAt: '2026-05-30'
title: The Issue Sorter
links:
  github: https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-triage/SKILL.md
tags:
- registry-curation
- triage
- prioritization
timeline:
- timestamp: '2026-05-26T16:37:01Z'
  action: add
  contributor: mbtiongson1
  details: Added named skill mbtiongson1/gaia-triage
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
trustMagnitudeInputHash: 6aa82723598307419d928a2b34244c79fffacfb545741b68124a9c153ca6f5ce
---

## Overview

Triages and audits GitHub issues for the Gaia Skill Tree project: identifies stale issues, gathers evidence from the codebase, manages the issue lifecycle via the `gh` CLI, and bulk-applies labels/closures based on rule-based classification. A project-specific implementation of `issue-triage` for registry-curation backlog management.
