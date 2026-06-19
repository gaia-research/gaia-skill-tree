---
id: mattpocock/personal
name: Personal
contributor: mattpocock
origin: true
title: The Matt Pocock Personal Suite
genericSkillRef: personal
status: named
level: 4★
description: Personal category suite for Matt Pocock's skills. Removed from mattpocock/skills suite in v1.0.1.
createdAt: '2026-05-21'
updatedAt: '2026-06-10'
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
trustMagnitudeInputHash: a5475109344aec0705426f33006e04cce471d96312dfd3df743c910a303d68be
timeline:
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:18Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
suiteRef: "mattpocock/skills"
suiteComponents:
  - mattpocock/edit-article
  - mattpocock/obsidian-vault
---

## Overview

The Matt Pocock Personal Suite groups two skills for individual knowledge work: Edit Article, which models an article as a directed acyclic graph of information dependencies and rewrites it section by section under a 240-character-per-paragraph constraint; and Obsidian Vault Manager, which manages notes and organisational structure in an Obsidian vault using Title Case and wikilinks. Together they cover the two modes of personal knowledge production — writing for an external audience and maintaining an internal knowledge base.

## Installation

This skill is included in the Matt Pocock skills suite. It is highly recommended to install the full suite to enable cross-skill context sharing.

```bash
npx skills@latest add mattpocock/skills
```

No additional setup required beyond the main suite installation.
