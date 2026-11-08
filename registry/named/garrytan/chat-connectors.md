---
id: garrytan/chat-connectors
name: chat-connectors
contributor: garrytan
origin: false
genericSkillRef: mcp-integration
status: named
level: 2★
description: Connect a ChatGPT or Claude account and sync its conversation history
  into the brain automatically. Cookie paste-in is the primary lane; sync is incremental
  (watermark + trailing-window gap-heal), and can run on a schedule via autopilot
  or host cron. Distinct from the export-file lane (that lives in conversation-archive)
  — this is the LIVE, account-connected, auto-scraping path.
createdAt: '2026-11-03'
updatedAt: '2026-11-09'
title: Chat Connectors
links:
  github: https://github.com/garrytan/gbrain/blob/v0.60.474.0/skills/chat-connectors/SKILL.md
timeline:
- timestamp: '2026-11-02T21:54:18Z'
  action: add
  contributor: mbtiongson1
  details: Added named skill garrytan/chat-connectors
- timestamp: '2026-11-02T21:57:37Z'
  action: suite_ref_set
  contributor: mbtiongson1
  details: Set suiteRef to garrytan/gbrain
- timestamp: '2026-11-02T21:57:41Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/garrytan/gbrain/blob/v0.60.474.0/skills/chat-connectors/SKILL.md
    (type: github-stars-own)'
- timestamp: '2026-11-02T22:15:25Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM (none) -> 50.0, grade (none) -> B (gaia dev calibrate-trust-magnitude;
    Issue #1600)'
- timestamp: '2026-11-08T18:17:02Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM 50.0 -> 49.9, grade B -> C (gaia dev calibrate-trust-magnitude; Issue
    #1600)'
suiteRef: garrytan/gbrain
evidence:
- source: https://github.com/garrytan/gbrain/blob/v0.60.474.0/skills/chat-connectors/SKILL.md
  evaluator: mbtiongson1
  date: '2026-11-03'
  type: github-stars-own
  notes: 'Stage-1 github-stars-own evidence: verified repository stars at tag (subject
    to 50.0 TM suite sibling cap per META §2.1a)'
  stars: 31276
  grade: A
verification:
  firstEvidenceAt: '2026-11-02T21:57:40Z'
trustMagnitude: 49.9
overallTrustGrade: C
trustMagnitudeInputHash: 81ed21d4a4cf16ca91ab4425dd865a240ccac4c2c41cdf9a3c317fda9315a3ae
---

## Installation
Add installation instructions here.
