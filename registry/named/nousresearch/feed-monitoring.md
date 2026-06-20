---
id: nousresearch/feed-monitoring
name: Feed Monitoring
contributor: nousresearch
origin: true
genericSkillRef: feed-monitoring
status: named
title: The Signal Scout
catalogRef: nousresearch-feed-monitoring
level: 2★
description: Continuous monitoring of content feeds with intelligent discovery and
  state tracking.
links:
  github: https://github.com/NousResearch/hermes-agent
tags:
- rss
- feeds
- monitoring
- signal-discovery
- unique
createdAt: '2026-05-15'
updatedAt: '2026-06-14'
evidence:
- class: B
  source: https://github.com/NousResearch/hermes-agent/blob/main/skills/research/blogwatcher/SKILL.md
  evaluator: openai-codex
  date: '2026-05-06'
  notes: 'Hermes Agent blogwatcher skill monitors blogs and RSS/Atom feeds with feed
    discovery, scraping fallback, OPML import, and read/unread article management.
    (backfilled — class-to-type migration) (CLI gap: commits+contributors not writable
    via gaia dev evidence)'
  type: repo
  commits: 66
  contributors: 100
  trustNumber: 70.0
  grade: B
timeline:
- timestamp: '2026-06-02T23:48:19Z'
  action: demote
  contributor: unknown
  details: Calibrated level from 4★ to 1★
- timestamp: '2026-06-14T12:32:46Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/NousResearch/hermes-agent/blob/main/skills/research/blogwatcher/SKILL.md
    as B (trustNumber: 70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:19Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T10:36:26Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:38Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:42Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- timestamp: '2026-06-20T06:31:34Z'
  action: rank_up
  contributor: mbtiongson1
  details: Level updated from 1★ to 2★ per G7 final rankings calibration.
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
trustMagnitudeInputHash: f876256aec3e5b099c8f4416932011859c902fd03e09d2978cd8b659ef173fc4
---

## Overview

Signal Scout monitors RSS, Atom, and other web feeds, extracting updates and maintaining read state for downstream processing.
