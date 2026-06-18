---
id: browser-use/browser-harness
name: Browser Harness
contributor: browser-use
origin: false
genericSkillRef: browser-control
status: named
title: The Dom Whispering
level: 2★
description: Self-healing harness for direct browser control via CDP, enabling agents
  to write custom helpers at runtime.
links:
  github: https://github.com/browser-use/browser-harness/blob/main/SKILL.md
tags:
- browser
- cdp
- automation
createdAt: '2026-05-14'
updatedAt: '2026-06-14'
evidence:
- class: B
  source: https://github.com/browser-use/browser-harness
  evaluator: gemini-cli
  date: '2026-05-14'
  notes: Browser Harness -- self-healing harness connecting LLMs to browser via CDP.
    (backfilled — class-to-type migration)
  type: repo
  trustNumber: 70.0
  grade: B
timeline:
- timestamp: '2026-06-02T23:32:59Z'
  action: demote
  contributor: unknown
  details: Origin status removed. Transferred to garrytan/browse.
- timestamp: '2026-06-14T12:32:17Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/browser-use/browser-harness
    as B (trustNumber: 70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:14Z'
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
trustMagnitudeInputHash: 80b954336c6990877bec2de6e17a70e8d721837fa12de3b43e35595cf72eca0c
---

## Overview

Browser Harness provides a low-level, resilient interface for web interaction. Unlike standard automation tools, it focuses on self-healing and runtime extensibility, allowing AI agents to dynamically adapt to UI changes by generating and executing their own browser scripts via the Chrome DevTools Protocol.
