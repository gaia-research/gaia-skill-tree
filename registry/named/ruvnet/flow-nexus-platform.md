---
id: ruvnet/flow-nexus-platform
name: Flow Nexus Platform
contributor: ruvnet
origin: true
genericSkillRef: cloud-platform-management
status: named
title: Queen Seraphina's Court
catalogRef: ruvnet-flow-nexus-platform
level: 1★
description: 'Full lifecycle management of the Flow Nexus cloud AI platform: user
  authentication, sandbox environments, app store deployment, payment processing,
  and challenge systems with Queen Seraphina AI assistant.'
links:
  github: https://github.com/ruvnet/ruflo
tags:
- cloud-platform
- authentication
- sandbox
- payments
- ai-assistant
createdAt: '2026-05-19'
updatedAt: '2026-06-14'
suiteRef: ruvnet/flow-nexus
evidence:
- class: B
  source: https://github.com/ruvnet/ruflo
  evaluator: mbtiongson1
  date: '2026-05-19'
  notes: Ruflo orchestration platform — 34k+ GitHub stars. (backfilled — class-to-type
    migration)
  type: repo
  trustNumber: 70.0
  grade: B
  commits: 6899
  contributors: 32
timeline:
- timestamp: '2026-06-02T23:48:20Z'
  action: demote
  contributor: unknown
  details: Calibrated level from 3★ to 1★
- timestamp: '2026-06-14T12:32:55Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/ruvnet/ruflo as B (trustNumber:
    70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:20Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T11:07:58Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:38Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
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
---

## Overview

Flow Nexus Platform provides complete lifecycle management for the Flow Nexus cloud AI platform. It covers user authentication and profile management, sandbox environment creation from multiple templates (Node, Python, React, Next.js), app store publishing with revenue sharing, payment processing with multi-tier pricing, and challenge systems with difficulty tiers. The Queen Seraphina AI assistant provides multi-turn conversation support with tool execution for architecture design and deployment tasks.

## Key Capabilities

- **Platform management**: auth, sandbox, app-store, payments, and challenges in a unified lifecycle
- **Queen Seraphina AI assistant**: multi-turn conversation with tool execution for architecture and deployment
- **Real-time subscriptions**: live database subscriptions and storage bucket management
- **Multi-tier pricing**: payment processing with configurable revenue-sharing models

## Origin

First published by @ruvnet as part of the Ruflo orchestration platform. This is the origin implementation for the `cloud-platform-management` skill bucket.

Sourced from the Ruflo platform (ruvnet/ruflo, 34k+ stars).
