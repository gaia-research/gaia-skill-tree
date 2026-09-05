---
id: anthropic/pptx
name: PPTX Editor
contributor: anthropic
origin: false
genericSkillRef: document-editing
status: named
title: The Slide Artisan
catalogRef: anthropic-pptx
level: 2★
description: Extracts slide content from PowerPoint (.pptx) files using markitdown,
  applies edits or design principles in-place, and repacks the file — enabling agents
  to read, modify, and write structured presentation files without a GUI.
links:
  github: https://github.com/anthropics/skills/blob/main/skills/pptx/SKILL.md
tags:
- pptx
- powerpoint
- document-editing
- markitdown
- presentations
createdAt: '2026-04-30'
updatedAt: '2026-08-30'
evidence:
- class: B
  source: https://github.com/anthropics/skills/blob/main/skills/pptx/SKILL.md
  evaluator: mbtiongson1
  date: '2026-04-30'
  notes: 'Anthropic /pptx slash command -- extracts, edits, packs, and applies design
    principles to PowerPoint files using markitdown. (backfilled — class-to-type migration)
    (CLI gap: commits+contributors not writable via gaia dev evidence)'
  type: repo
  commits: 41
  contributors: 16
  trustNumber: 70.0
  grade: B
timeline:
- timestamp: '2026-06-02T01:42:58Z'
  action: demote
  contributor: unknown
  details: Origin status removed. Transferred to mattpocock/edit-article.
- timestamp: '2026-06-14T12:32:17Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/anthropics/skills/blob/main/skills/pptx/SKILL.md
    as B (trustNumber: 70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:14Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T10:36:26Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:37Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:36Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- timestamp: '2026-08-29T17:15:43Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM 36.0 -> 36.0, grade C -> C (gaia dev calibrate-trust-magnitude; Issue
    #1600)'
trustMagnitude: 36.0
overallTrustGrade: C
apexGateStatus:
  aGradedOriginsGte5: false
  sourceTenureDaysGte180AorS: false
  directNestedSuiteGte1: false
  depth2OnlyReachableGte1: false
  overallGradeS: false
  apexPromotionPrSigned: false
  crossOrgVerifier: null
  systemWideCap: null
trustMagnitudeInputHash: 09948a85e8eae40f82e23f52d9a5f711f9fcc0a501f60bb053c02bb592a74360
---

## Overview

PPTX Editor by Anthropic uses the `markitdown` library to extract text and layout from `.pptx` files into a structured intermediate representation. The agent can then edit content, reorder slides, apply design rules, or generate new slides programmatically — then pack the result back into a valid `.pptx` file.

## Origin

First published by @anthropic. This is the origin implementation for the `document-editing` skill bucket.
