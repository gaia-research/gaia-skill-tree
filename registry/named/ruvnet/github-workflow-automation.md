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
updatedAt: '2026-06-02'
suiteRef: ruvnet/github-suite
timeline:
- timestamp: '2026-06-02T23:48:21Z'
  action: demote
  contributor: unknown
  details: Calibrated level from 3★ to 1★
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:20Z'
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
