---
id: 0xdarkmatter/pytest-patterns
name: Pytest Patterns
contributor: 0xdarkmatter
origin: true
genericSkillRef: automated-testing
status: named
title: The Quality Guardian
catalogRef: 0xdarkmatter-pytest-patterns
level: 3★
description: Comprehensive pytest skill covering modern patterns for Python test automation
  including fixtures, parametrize, async testing, mocking, coverage strategies, integration
  tests, and conftest organisation for pytest 7.0+ projects.
links:
  github: https://github.com/aiskillstore/marketplace/blob/main/skills/0xdarkmatter/python-pytest-patterns/SKILL.md
tags:
- pytest
- python
- test-automation
- fixtures
- async-testing
- coverage
- mocking
createdAt: '2026-04-30'
updatedAt: '2026-04-30'
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
trustMagnitudeInputHash: 2f3e1ba5002985e006b783ad926dd2f680c0ab51116a1f7d4be9758d61940b00
timeline:
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:13Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
---

## Overview

Pytest Patterns is a security-audited skill published in the AI Skill Store marketplace. It codifies modern pytest best practices for Python 3.9+ projects targeting pytest 7.0+. The skill covers the full testing lifecycle: test structure and naming, fixture design (simple, factory, and parametrised fixtures), `pytest.mark` strategies, async testing with `pytest-asyncio`, mocking with `pytest-mock`, coverage analysis, and integration test patterns.

## Key Patterns

- **Fixtures**: simple, factory, parametrised, session-scoped, and `conftest.py` layout
- **Parametrize**: data-driven tests with `@pytest.mark.parametrize`
- **Async**: `pytest-asyncio` for testing coroutines and async context managers
- **Mocking**: `pytest-mock` MagicMock, patch decorators, and spy usage
- **Coverage**: `pytest-cov` configuration, branch coverage, and reporting
- **Integration**: database fixtures, HTTP client stubs, and test isolation strategies

## Compatibility

`pytest 7.0+`, `Python 3.9+`. Optional: `pytest-asyncio`, `pytest-mock`, `pytest-cov`.

## Origin

First published by @0xdarkmatter in the AI Skill Store security-audited marketplace. This is the origin implementation for the `automated-testing` skill bucket.

Sourced from the SkillsMP marketplace entry for `python-pytest-patterns` (aiskillstore/marketplace, 263 stars).
