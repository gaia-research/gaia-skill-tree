---
id: ruvnet/flow-nexus-swarm
name: Flow Nexus Swarm
contributor: ruvnet
origin: false
genericSkillRef: multi-agent-orchestration-v
status: named
title: The Grand Conductor's Blueprint
catalogRef: ruvnet-flow-nexus-swarm
level: 1★
description: Cloud-based AI swarm orchestration platform supporting hierarchical,
  mesh, ring, and star topologies with event-driven workflows, message queue processing,
  and intelligent agent assignment.
links:
  github: https://github.com/ruvnet/ruflo
tags:
- multi-agent
- swarm
- orchestration
- event-driven
- workflow
createdAt: '2026-04-30'
updatedAt: '2026-08-30'
timeline:
- timestamp: '2026-06-02T23:48:21Z'
  action: demote
  contributor: unknown
  details: Calibrated level from 3★ to 1★
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:20Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:38Z'
  details: TM 0.0 -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:44Z'
  details: TM 0.0 -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- timestamp: '2026-08-29T17:15:58Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM 0.0 -> 0.0, grade ungraded -> ungraded (gaia dev calibrate-trust-magnitude;
    Issue #1600)'
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
trustMagnitudeInputHash: 3f2f7662fc11748d1c1bc140bd091168e2a5c50e79fc648c7a69683ea428422b
suiteRef: "ruvnet/ruflo"
---

## Overview

Flow Nexus Swarm is a cloud-based orchestration skill for deploying and managing AI agent swarms. It supports four network topologies (hierarchical, mesh, ring, star), event-driven workflows via message queues, and a template library of pre-built swarm configurations. The platform handles intelligent agent assignment, async execution, and multi-agent coordination across distributed environments.

## Key Capabilities

- **Multi-topology swarms**: hierarchical, mesh, ring, and star agent networks
- **Event-driven execution**: message queue processing with async task dispatch
- **Template library**: pre-built swarm configurations for common orchestration patterns
- **Intelligent assignment**: vector-similarity-based agent routing

## Origin

First published by @ruvnet as part of the Ruflo orchestration platform. This is the origin implementation for the `multi-agent-orchestration-v` skill bucket.

Sourced from the SkillsMP marketplace entry for `flow-nexus-swarm` (ruflo, 34k+ stars).
