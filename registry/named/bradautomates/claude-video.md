---
id: bradautomates/claude-video
name: Claude Video
contributor: bradautomates
origin: true
genericSkillRef: video-intelligence
status: named
title: The Temporal Eye
level: 2★
description: Enables AI agents to watch videos by downloading them, extracting frames,
  and transcribing audio for multimodal analysis.
links:
  github: https://github.com/bradautomates/claude-video/blob/main/SKILL.md
tags:
- video
- multimodal
- vision
createdAt: '2026-05-14'
updatedAt: '2026-06-20'
evidence:
- class: B
  source: https://github.com/bradautomates/claude-video
  evaluator: gemini-cli
  date: '2026-05-14'
  notes: 'Claude Video -- enables AI agents to watch videos by downloading, frame
    extraction, and transcription. (backfilled — class-to-type migration) (CLI gap:
    commits+contributors not writable via gaia dev evidence)'
  type: repo
  commits: 6
  contributors: 1
  trustNumber: 70.0
  grade: B
- source: https://www.youtube.com/watch?v=QZMljuD10sU
  evaluator: unknown
  date: '2026-06-20'
  type: social-signal
  trustNumber: 78.0
  grade: B
  notes: Brad | AI & Automation — Give Claude the ability to watch any video (/watch
    skill); 34K views; demonstrates claude-video skill functionality (verified 2026-06-20)
  views: 34000
  sourceStartedAt: '2025-01-01'
timeline:
- timestamp: '2026-06-14T12:32:17Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/bradautomates/claude-video
    as B (trustNumber: 70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:14Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T10:36:26Z'
  details: TM 0.0 -> 1.22, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:37Z'
  details: TM 0.0 -> 1.22, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:36Z'
  details: TM 0.0 -> 1.22, grade ungraded -> ungraded (direct edit -- CLI gap)
- timestamp: '2026-06-19T17:12:30Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://www.youtube.com/watch?v=QZMljuD10sU (type:
    social-signal)'
- timestamp: '2026-06-19T17:12:30Z'
  action: evidence_graded
  contributor: unknown
  details: 'Graded evidence from https://www.youtube.com/watch?v=QZMljuD10sU as B
    (trustNumber: 78.0)'
trustMagnitude: 1.22
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
trustMagnitudeInputHash: 2e0ec01eaaa7d47db85a777dbd233d4a8425cb114b632e9c09c00d9aa46d0b90
verification:
  firstEvidenceAt: '2026-06-19T17:12:29Z'
---

## Overview

Claude Video provides a bridge between video content and large language models. It automates the process of fetching video streams, sampling frames at optimal intervals, and using Whisper for high-fidelity audio transcription. This allows agents to reason about video content with both visual and temporal context.
