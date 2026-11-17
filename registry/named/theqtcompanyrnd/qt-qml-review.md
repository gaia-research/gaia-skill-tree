---
id: theqtcompanyrnd/qt-qml-review
name: qt-qml-review
contributor: theqtcompanyrnd
origin: false
genericSkillRef: code-review-pipeline
status: named
level: 3★
description: Invoke when the user asks to review, check, audit, or look over Qt6 QML
  code -- or suggest before committing. Runs deterministic linting (48+ rules) then
  deep-analysis agents (scaled to the size of the change) covering bindings, layout,
  loaders, delegates, states, and performance. Optionally invokes system qmllint for
  type-level checks. Reports only high-confidence issues (>80/100) with structured
  mitigations. Read-only -- never modifies code.
createdAt: '2026-11-03'
updatedAt: '2026-11-11'
title: Qt Qml Review
links:
  github: https://github.com/TheQtCompanyRnD/agent-skills/blob/main/skills/qt-qml-review/SKILL.md
timeline:
- timestamp: '2026-11-02T21:55:09Z'
  action: add
  contributor: mbtiongson1
  details: Added named skill theqtcompanyrnd/qt-qml-review
- timestamp: '2026-11-02T22:02:27Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/TheQtCompanyRnD/agent-skills/blob/main/skills/qt-qml-review/SKILL.md
    (type: github-stars-own)'
- timestamp: '2026-11-02T22:16:27Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM (none) -> 59.74, grade (none) -> B (gaia dev calibrate-trust-magnitude;
    Issue #1600)'
- timestamp: '2026-11-11T02:55:58Z'
  action: rank_up
  contributor: unknown
  details: Calibrated level from 2★ to 3★
evidence:
- source: https://github.com/TheQtCompanyRnD/agent-skills/blob/main/skills/qt-qml-review/SKILL.md
  evaluator: mbtiongson1
  date: '2026-11-03'
  type: github-stars-own
  notes: 'Stage-1 github-stars-own evidence: verified repository stars at tag'
  stars: 509
  grade: B
verification:
  firstEvidenceAt: '2026-11-02T22:02:26Z'
trustMagnitude: 59.74
overallTrustGrade: B
trustMagnitudeInputHash: ed807409962743c9bee03fc0a04ba727089140e287c78f396b689cfb0a6d9f53
---

## Installation
Add installation instructions here.
