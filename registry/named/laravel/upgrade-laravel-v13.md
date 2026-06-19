---
id: laravel/upgrade-laravel-v13
name: Upgrade Laravel v13
contributor: laravel
origin: true
genericSkillRef: framework-upgrade
status: named
title: The Versionist's Trial
catalogRef: laravel-upgrade-laravel-v13
level: 2★
description: Guides an AI agent through upgrading a Laravel 12 application to Laravel
  13 safely, covering breaking changes, dependency updates, config migrations, and
  post-upgrade test validation.
links:
  github: https://github.com/laravel/boost/issues/698
tags:
- laravel
- php
- framework-upgrade
- migration
createdAt: '2026-04-30'
updatedAt: '2026-06-14'
evidence:
- class: B
  source: https://github.com/laravel/boost/issues/698
  evaluator: mbtiongson1
  date: '2026-04-30'
  notes: 'Laravel /upgrade-laravel-v13 slash command -- real-world agentic framework"
    upgrade workflow published by the Laravel team. (backfilled — class-to-type migration)
    (CLI gap: --commits/--contributors not supported by gaia dev evidence)'
  type: repo
  trustNumber: 70.0
  grade: B
  commits: 965
  contributors: 107
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

This named skill implements the `framework-upgrade` generic skill for the Laravel 12 → 13 migration path. The agent follows a structured checklist: audits breaking changes in the Laravel 13 changelog, updates `composer.json` dependencies, migrates config files, runs `php artisan migrate`, and executes the full test suite before marking the upgrade complete.

## Origin

First published by the @laravel team. This is the origin implementation for the `framework-upgrade` skill bucket.
