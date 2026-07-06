---
type: "AI Agent Skill"
title: "Generate Test"
description: "Produces comprehensive unit, integration, and edge-case test suites from source code."
resource: "https://gaiaskilltree.com/codex.html#generate-test"
tags: ["gaia-skill-tree", "basic-skill"]
timestamp: "2026-06-21T00:00:00Z"
---

# Generate Test

## Description

Analyzes source code or natural-language specifications to identify functions, classes, and their dependencies, and generates thorough, maintainable test suites. It handles test case structuring, setup and teardown fixtures, mocking external dependencies, and validating normal operation alongside boundary and error conditions.

## Use Case

A developer just finished writing an authentication module (`auth.py`) and needs comprehensive unit tests. The skill is invoked to create properly structured tests using the `unittest.TestCase` format, handling edge-case validation and mock generation without requiring explicit per-file prompting.

## Directives

Tests must use established frameworks (e.g., `unittest.TestCase` format) with proper naming conventions (e.g., 'test_' prefix). Tests should be organized into concept-based subfolders within a `tests/` directory (e.g., `tests/auth/`). Ensure test coverage includes happy paths, boundary conditions, and error paths, utilizing appropriate assertions and mocking techniques to maintain test independence.

## Derivatives

- [Automated Testing](/skills/extra/automated-testing.md)

