---
id: ruvnet/flow-nexus-neural
name: Flow Nexus Neural
contributor: ruvnet
origin: true
genericSkillRef: distributed-neural-training
status: named
title: The Neural Conductor
catalogRef: ruvnet-flow-nexus-neural
level: 2★
description: Trains neural networks across distributed E2B sandbox clusters with support
  for feedforward, LSTM, GAN, autoencoder, and transformer architectures, federated
  learning, and a model marketplace.
links:
  github: https://github.com/ruvnet/ruflo
tags:
- neural-training
- distributed
- federated-learning
- e2b
- model-marketplace
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
- timestamp: '2026-06-14T12:32:54Z'
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
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:43Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- timestamp: '2026-06-20T06:31:36Z'
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
trustMagnitudeInputHash: ad671594b94fa16a919d95ff6f0bded34de640331989687c6d97086130120b41
---

## Overview

Flow Nexus Neural enables training and deployment of neural networks in distributed E2B sandbox environments. Users can train across multiple architectures (feedforward, LSTM, GAN, autoencoder, transformer) with five resource tiers, deploy distributed training clusters using mesh/ring/star/hierarchical topologies, and publish trained models to the template marketplace. Federated learning keeps data localized on nodes while enabling collaborative training.

## Key Capabilities

- **Multi-architecture neural training**: feedforward, LSTM, GAN, autoencoder, and transformer (5 types)
- **Distributed cluster training**: mesh, ring, star, and hierarchical topology options across E2B sandboxes
- **Federated learning**: data-localized collaborative training across distributed nodes
- **Model marketplace publishing**: trained model deployment and template sharing

## Origin

First published by @ruvnet as part of the Ruflo orchestration platform. This is the origin implementation for the `distributed-neural-training` skill bucket.

Sourced from the Ruflo platform (ruvnet/ruflo, 34k+ stars).
