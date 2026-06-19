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
updatedAt: '2026-06-20'
evidence:
- class: B
  source: https://github.com/browser-use/browser-harness
  evaluator: gemini-cli
  date: '2026-05-14'
  notes: 'Browser Harness -- self-healing harness connecting LLMs to browser via CDP.
    (backfilled — class-to-type migration) (CLI gap: commits+contributors not writable
    via gaia dev evidence)'
  type: repo
  commits: 400
  contributors: 59
  trustNumber: 70.0
  grade: B
- source: https://browser-use.com/posts/online-mind2web-benchmark
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: benchmark-result
  class: A
  notes: 'BU Bench V1 (100 verified tasks from WebArena/Mind2Web): 78-97% task success
    rate using bu-ultra/max. 80% using Claude Fable 5 (Mid-2026).'
  trustNumber: 85.0
  grade: A
- source: https://www.youtube.com/watch?v=XQn6yGq6oN8
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: social-signal
  class: A
  notes: 'Codex Developer YouTube: demo of browser-use CDP library for AI agent browser
    automation. Third-party developer showcase (view count est. 50K+).'
  trustNumber: 80.0
  grade: A
  views: 50000
- source: https://github.com/browser-use/browser-harness
  evaluator: mbtiongson1
  date: '2026-06-19'
  type: peer-review
  class: A
  notes: 'AI Agent Developer Community: commended as lightweight CDP bridge, self-healing
    via runtime agent_helpers.py, steeper learning curve than Playwright. Mid-2026.'
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
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T10:36:26Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- timestamp: '2026-06-19T10:39:17Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://browser-use.com/posts/online-mind2web-benchmark
    (type: benchmark-result)'
- timestamp: '2026-06-19T10:41:47Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://www.youtube.com/watch?v=XQn6yGq6oN8 (type:
    social-signal)'
- timestamp: '2026-06-19T10:47:25Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/browser-use/browser-harness (type:
    peer-review)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T10:52:24Z'
  details: TM 36.0 -> 36.0, grade C -> C (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:37Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:36Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- timestamp: '2026-06-19T17:01:43Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://browser-use.com/posts/online-mind2web-benchmark
    as A (trustNumber: 85.0)'
- timestamp: '2026-06-19T17:01:44Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://www.youtube.com/watch?v=XQn6yGq6oN8 as
    A (trustNumber: 80.0)'
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
verification:
  firstEvidenceAt: '2026-06-19T10:39:17Z'
trustMagnitudeInputHash: 82dc8fee9df833fbea019d280dbbd45ff9803cc16ef9c09f4e463a0910138baf
---

## Overview

Browser Harness provides a low-level, resilient interface for web interaction. Unlike standard automation tools, it focuses on self-healing and runtime extensibility, allowing AI agents to dynamically adapt to UI changes by generating and executing their own browser scripts via the Chrome DevTools Protocol.
