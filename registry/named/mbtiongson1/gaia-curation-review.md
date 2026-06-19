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
updatedAt: '2026-06-14'
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
- timestamp: '2026-06-10T05:38:17Z'
  action: evidence_added
  contributor: unknown
  details: Added B evidence from https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-curation-review/SKILL.md
- timestamp: '2026-06-14T12:32:45Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-curation-review/SKILL.md
    as B (trustNumber: 70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:19Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T10:36:26Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
evidence:
- class: B
  source: https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-curation-review/SKILL.md
  evaluator: mbtiongson1
  date: '2026-06-10'
  notes: 'Project-local agent skill used for curation PR review in this repository;
    implementation public at SKILL.md. (backfilled — class-to-type migration) (CLI
    gap: commits+contributors not writable via gaia dev evidence)'
  type: repo
  commits: 90
  contributors: 10
  trustNumber: 70.0
  grade: B
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
verification:
  firstEvidenceAt: '2026-06-10T05:38:17Z'
---

## Overview

Reviews an open curation PR (or branch) to determine exactly what it adds to the registry, surfaces quality issues against META standards (evidence class thresholds, naming conventions, tier accuracy, brand-coupled IDs), and recommends `merge` / `close` / `needs-work`. Optimized for stale Jules-generated PRs where the GitHub diff is buried in generated-file noise. A `registry-entry-audit` variant focused on PR-level review.
