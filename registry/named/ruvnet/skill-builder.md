---
id: ruvnet/skill-builder
name: Skill Builder
contributor: ruvnet
origin: false
genericSkillRef: skill-authoring
status: named
title: The Skill Forger
catalogRef: ruvnet-skill-builder
level: 1★
description: Guides creation of new Ruflo skills through templating, testing, and
  publishing workflows.
links:
  github: https://github.com/ruvnet/ruflo
tags:
- skill-authoring
- templating
- publishing
- skill-development
- testing
createdAt: '2026-05-19'
updatedAt: '2026-05-19'
suiteRef: ruvnet/ruflo
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
timeline:
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:21Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:39Z'
  details: TM 0.0 -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:44Z'
  details: TM 0.0 -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- timestamp: '2026-06-20T06:31:37Z'
  action: demote
  contributor: mbtiongson1
  details: Level updated from 2★ to 1★ per G7 final rankings calibration.
trustMagnitudeInputHash: b74ce526083c08bfdf6d38ed44abe89c9007cd1af91e02680c4735fff1e392cb
---

## Overview

Skill Builder provides a complete guided workflow for creating, testing, and publishing new Ruflo skills. It generates opinionated skill templates, scaffolds SKILL.md documentation, creates test fixtures, and walks through the marketplace publishing process step by step. Both first-time skill authors and experienced contributors benefit from the standardized structure it enforces.

## Key Capabilities

- **Skill template generation**: scaffolds new skills from standardized Ruflo skill templates
- **SKILL.md authoring**: guides structured documentation of capabilities, inputs, and outputs
- **Test scaffolding**: generates test fixtures and harness code for new skills
- **Marketplace publishing workflow**: step-by-step publishing to the Ruflo skill marketplace

## Origin

Published by @ruvnet as a variant implementation for the `skill-authoring` skill bucket.

Sourced from the Ruflo platform (ruvnet/ruflo, 34k+ stars).
