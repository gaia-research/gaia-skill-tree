---
id: garrytan/canary
name: Canary
contributor: garrytan
origin: false
genericSkillRef: detect-anomaly
status: named
title: Gstack Canary
catalogRef: garrytan-canary
level: 4★
description: Post-deployment monitoring that captures pre-release baseline screenshots,
  then continuously watches pages for console errors, performance regressions, and
  broken links — designed to surface failures within the first 10 minutes so problems
  are caught before they reach users at scale.
links:
  github: https://github.com/garrytan/gstack/blob/main/canary/SKILL.md
tags:
- monitoring
- post-deploy
- canary
- anomaly-detection
createdAt: '2026-05-18'
updatedAt: '2026-06-14'
suiteRef: garrytan/gstack
evidence:
- class: B
  source: https://github.com/garrytan/gstack/blob/main/canary/SKILL.md
  evaluator: mbtiongson1
  date: '2026-06-03'
  notes: Public SKILL.md in the garrytan/gstack suite repo (verified live). Post-deployment
    monitoring that captures pre-release baseline screenshots, then continuously watches
    pages for console errors, performance… (backfilled — class-to-type migration)
  type: repo
  trustNumber: 70.0
  grade: B
timeline:
- timestamp: '2026-06-03T05:51:29Z'
  action: evidence_added
  contributor: unknown
  details: Added B evidence from https://github.com/garrytan/gstack/blob/main/canary/SKILL.md
- timestamp: '2026-06-14T12:32:19Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/garrytan/gstack/blob/main/canary/SKILL.md
    as B (trustNumber: 70.0)'
---

## Overview

Gstack Canary establishes a visual and performance baseline before a deploy, then monitors the live application continuously in the critical window after release. It detects console errors, Core Web Vital regressions, and broken links, reporting anomalies within 10 minutes so a rollback decision can be made before traffic scales up.
