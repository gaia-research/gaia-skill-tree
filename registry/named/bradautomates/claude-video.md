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
updatedAt: '2026-06-14'
evidence:
- class: B
  source: https://github.com/bradautomates/claude-video
  evaluator: gemini-cli
  date: '2026-05-14'
  notes: Claude Video -- enables AI agents to watch videos by downloading, frame extraction,
    and transcription. (backfilled — class-to-type migration)
  type: repo
  trustNumber: 70.0
  grade: B
timeline:
- timestamp: '2026-06-14T12:32:17Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/bradautomates/claude-video
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
trustMagnitudeInputHash: 849dd3681def81781177344323b0a52d336bd4768f0b39c17a9b633441e6143f
---

## Overview

Claude Video provides a bridge between video content and large language models. It automates the process of fetching video streams, sampling frames at optimal intervals, and using Whisper for high-fidelity audio transcription. This allows agents to reason about video content with both visual and temporal context.
