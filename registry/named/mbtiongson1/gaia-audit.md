---
id: mbtiongson1/gaia-audit
name: Gaia Audit
contributor: mbtiongson1
origin: true
genericSkillRef: registry-entry-audit
status: named
level: 2★
description: Performs a focused source-level correction for one target registry entry
  — verifying links, checking evidence classes, and filing an inline-diff fix PR with
  full citations.
createdAt: '2026-05-27'
updatedAt: '2026-06-14'
title: The Source Detective
links:
  github: https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-audit/SKILL.md
tags:
- registry-curation
- source-verification
- evidence
- correction
timeline:
- timestamp: '2026-05-26T16:36:57Z'
  action: add
  contributor: mbtiongson1
  details: Added named skill mbtiongson1/gaia-audit
- timestamp: '2026-06-01T15:13:07Z'
  action: demote
  contributor: unknown
  details: Calibrated level from 3★ to 2★
- timestamp: '2026-06-14T12:32:44Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-audit/skill.md
    as C (trustNumber: 50.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:19Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T10:36:26Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
evidence:
- class: C
  source: https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-audit/skill.md
  evaluator: mbtiongson1
  date: '2026-05-20'
  notes: 'Self-referential implementation doc inside the gaia repo (seed evidence).
    Downgraded A->C per META §2.4 — seed / self-referential links are insufficient
    for Class A — by the 2026-06-02 meta sweep. Credible demo of the codified 7-phase
    audit workflow. (backfilled — class-to-type migration) (CLI gap: commits+contributors
    not writable via gaia dev evidence)'
  type: repo
  commits: 90
  contributors: 10
  trustNumber: 50.0
  grade: C
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

Performs a focused source-level correction for one target registry entry — verifying links, checking evidence classes, validating taxonomy mapping, and filing an inline-diff fix PR with full citations. The 7-phase audit discipline includes evidence re-verification, demotion checks, and automatic asset regeneration via `gaia dev`. Used after `gaia-meta-audit` produces a prioritized queue.
