---
id: ruvnet/github-workflow-automation
name: GitHub Workflow Automation
contributor: ruvnet
origin: false
role: variant
genericSkillRef: workflow-automation
status: named
title: The Actions Architect
catalogRef: ruvnet-github-workflow-automation
level: 1★
description: Designs and manages GitHub Actions workflows for CI/CD automation, scheduled
  tasks, and event-driven agent triggers.
links:
  github: https://github.com/ruvnet/ruflo
tags:
- github-actions
- ci-cd
- workflow-automation
- event-driven
createdAt: '2026-05-19'
updatedAt: '2026-09-05'
timeline:
- timestamp: '2026-06-02T23:48:21Z'
  action: demote
  contributor: unknown
  details: Calibrated level from 3★ to 1★
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:20Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:39Z'
  details: TM 0.0 -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:44Z'
  details: TM 0.0 -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- timestamp: '2026-08-29T17:15:59Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM 0.0 -> 0.0, grade ungraded -> ungraded (gaia dev calibrate-trust-magnitude;
    Issue #1600)'
- timestamp: '2026-09-04T18:43:51Z'
  action: recalibrate_trust_magnitude
  contributor: unknown
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
trustMagnitudeInputHash: c4f3ed9548c39500f92238e83d62cd588b081a673975063ff72baf5dee8f2cfd
suiteRef: ruvnet/ruflo
---

## Overview

GitHub Workflow Automation covers the full spectrum of GitHub Actions development: CI/CD pipeline design, reusable workflow creation, matrix build strategies, and event-driven triggers for agent tasks. It includes workflow debugging, secret management, and environment promotion patterns.

## Key Capabilities

- **CI/CD pipeline design**: end-to-end pipeline authoring for build, test, and deployment stages
- **Reusable workflows**: modular workflow composition with callable workflow patterns
- **Matrix builds**: parallel multi-version and multi-platform build strategies
- **Event-driven triggers**: workflow activation from push, PR, schedule, and custom dispatch events

## Origin

Published by @ruvnet as a variant implementation for the `workflow-automation` skill bucket.

Sourced from the Ruflo platform (ruvnet/ruflo, 34k+ stars).
