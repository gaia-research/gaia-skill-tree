---
id: laravel/upgrade-laravel-v13
name: Upgrade Laravel v13
contributor: laravel
origin: false
genericSkillRef: framework-upgrade
status: named
title: The Versionist's Trial
catalogRef: laravel-upgrade-laravel-v13
level: 2★
description: Guides an AI agent through upgrading a Laravel 12 application to Laravel
  13 safely, covering breaking changes, dependency updates, config migrations, and
  post-upgrade test validation.
tags:
- laravel
- php
- framework-upgrade
- migration
createdAt: '2026-04-30'
updatedAt: '2026-09-04'
evidence: []
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
trustMagnitudeInputHash: 91d49986f363f2adcc80b2fb47dbb4b7bba964704c3dcc8473d47b0e237fe001
installable: false
---

## Overview

This named skill implements the `framework-upgrade` generic skill for the Laravel 12 → 13 migration path. The agent follows a structured checklist: audits breaking changes in the Laravel 13 changelog, updates `composer.json` dependencies, migrates config files, runs `php artisan migrate`, and executes the full test suite before marking the upgrade complete.

## Origin

First published by the @laravel team. This is the origin implementation for the `framework-upgrade` skill bucket.
