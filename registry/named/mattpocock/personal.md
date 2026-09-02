---
id: mattpocock/personal
name: Personal
contributor: mattpocock
origin: true
title: The Matt Pocock Personal Suite
genericSkillRef: personal
status: named
level: 3★
description: Personal category suite for Matt Pocock's skills. Removed from mattpocock/skills
  suite in v1.0.1.
createdAt: '2026-05-21'
updatedAt: '2026-08-30'
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
timeline:
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:18Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:38Z'
  details: TM 0.0 -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:41Z'
  details: TM 0.0 -> 60.0, grade ungraded -> B (direct edit -- CLI gap)
- timestamp: '2026-06-20T06:31:32Z'
  action: demote
  contributor: mbtiongson1
  details: Level updated from 4★ to 3★ per G7 final rankings calibration.
- timestamp: '2026-08-19T11:49:11Z'
  action: upstream_deprecated
  contributor: unknown
  previousValue: null
  newValue: null
  details: personal/ bucket removed entirely upstream; no successor bucket
- timestamp: '2026-08-29T17:15:53Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM 60.0 -> 0.0, grade B -> ungraded (gaia dev calibrate-trust-magnitude;
    Issue #1600)'
suiteRef: mattpocock/skills
suiteComponents:
- mattpocock/edit-article
- mattpocock/obsidian-vault
trustMagnitudeInputHash: 2f3c9a354b9a90d67d9e547eb3fdbc822f8ffc9216a802a4e0df690331abd5ff
installable: false
---

## Overview

The Matt Pocock Personal Suite groups two skills for individual knowledge work: Edit Article, which models an article as a directed acyclic graph of information dependencies and rewrites it section by section under a 240-character-per-paragraph constraint; and Obsidian Vault Manager, which manages notes and organisational structure in an Obsidian vault using Title Case and wikilinks. Together they cover the two modes of personal knowledge production — writing for an external audience and maintaining an internal knowledge base.

## Installation

This skill is included in the Matt Pocock skills suite. It is highly recommended to install the full suite to enable cross-skill context sharing.

```bash
npx skills@latest add mattpocock/skills
```

No additional setup required beyond the main suite installation.
