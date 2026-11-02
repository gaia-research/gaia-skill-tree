---
id: laravel/upgrade-laravel-v13
name: Upgrade Laravel v13
contributor: laravel
origin: false
genericSkillRef: framework-upgrade
status: named
title: The Versionist's Trial
catalogRef: laravel-upgrade-laravel-v13
level: 1★
description: Guides an AI agent through upgrading a Laravel 12 application to Laravel
  13 safely, covering breaking changes, dependency updates, config migrations, and
  post-upgrade test validation.
tags:
- laravel
- php
- framework-upgrade
- migration
createdAt: '2026-04-30'
updatedAt: '2026-10-30'
evidence:
- source: https://github.com/laravel/boost/blob/main/src/Mcp/Prompts/UpgradeLaravelv13/UpgradeLaravelV13.php
  evaluator: mbtiongson1
  date: '2026-10-29'
  type: github-stars-own
  notes: 'Source of the /upgrade-laravel-v13 prompt (name = ''upgrade-laravel-v13'')
    in the first-party laravel/boost MCP server, one of 10 prompts under src/Mcp/Prompts;
    blob URL verified HTTP 200. Stars: GitHub REST stargazers_count of laravel/boost
    at 2026-10-29. Also referenced by the official Laravel 13 upgrade guide (laravel/docs
    upgrade.md). Founder ruling 2026-10-30 FD-14.'
  stars: 3670
  skillCountInRepo: 10
  sourceStartedAt: '2025-07-15'
  grade: A
- source: https://github.com/laravel/boost
  evaluator: mbtiongson1
  date: '2026-10-29'
  type: repo-own
  notes: GitHub REST default-branch commit count and contributor count of laravel/boost
    at 2026-10-29; host-repository maintenance, not independent quality evidence.
    Founder ruling 2026-10-30 FD-14.
  commits: 1125
  contributors: 140
  sourceStartedAt: '2025-07-15'
  grade: B
- source: https://www.youtube.com/watch?v=CH8y8nR_uTI
  evaluator: mbtiongson1
  date: '2026-10-29'
  type: social-signal
  notes: Laravel Daily (independent creator) hands-on test of the Laravel Boost /upgrade
    command (upgrade-laravel-v13) against Laravel Shift; 5,094 views and 115 likes
    retrieved via firecrawl scrape 2026-10-29, uploaded 2026-03-23. Founder ruling
    2026-10-30 FD-14.
  views: 5094
  likes: 115
  sourceStartedAt: '2026-03-23'
  grade: B
timeline:
- timestamp: '2026-06-14T12:32:42Z'
  action: evidence_graded
  contributor: unknown
  details: 'Re-graded evidence from https://github.com/laravel/boost/issues/698 as
    B (trustNumber: 70.0)'
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:18Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T11:52:12Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:38Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:40Z'
  details: TM 0.0 -> 36.0, grade ungraded -> C (direct edit -- CLI gap)
- timestamp: '2026-08-06T04:54:18Z'
  action: note
  contributor: unknown
  details: Set installable to false
- timestamp: '2026-08-29T17:15:51Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM 36.0 -> 36.0, grade C -> C (gaia dev calibrate-trust-magnitude; Issue
    #1600)'
- timestamp: '2026-09-09T20:31:07Z'
  action: demote
  contributor: mbtiongson1
  details: Calibrated level from 2★ to 1★
- timestamp: '2026-10-29T16:57:43Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/laravel/boost/blob/main/src/Mcp/Prompts/UpgradeLaravelv13/UpgradeLaravelV13.php
    (type: github-stars-own)'
- timestamp: '2026-10-29T16:57:44Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://github.com/laravel/boost (type: repo-own)'
- timestamp: '2026-10-29T16:58:47Z'
  action: evidence_added
  contributor: mbtiongson1
  details: 'Added evidence from https://www.youtube.com/watch?v=CH8y8nR_uTI (type:
    social-signal)'
- timestamp: '2026-10-29T16:59:48Z'
  action: recalibrate_trust_magnitude
  contributor: mbtiongson1
  details: 'TM 0.0 -> 159.24, grade ungraded -> A (gaia dev calibrate-trust-magnitude;
    Issue #1600)'
trustMagnitude: 159.24
overallTrustGrade: A
apexGateStatus:
  aGradedOriginsGte5: false
  sourceTenureDaysGte180AorS: false
  directNestedSuiteGte1: false
  depth2OnlyReachableGte1: false
  overallGradeS: false
  apexPromotionPrSigned: false
  crossOrgVerifier: null
  systemWideCap: null
trustMagnitudeInputHash: 5ff51c677b6a29221af9a24ca8410f23cf2b79804bdaca356ed5a0f3455069f6
installable: false
verification:
  firstEvidenceAt: '2026-10-29T16:57:43Z'
---

## Overview

This named skill implements the `framework-upgrade` generic skill for the Laravel 12 → 13 migration path. The agent follows a structured checklist: audits breaking changes in the Laravel 13 changelog, updates `composer.json` dependencies, migrates config files, runs `php artisan migrate`, and executes the full test suite before marking the upgrade complete.

## Origin

First published by the @laravel team. This is the origin implementation for the `framework-upgrade` skill bucket.
