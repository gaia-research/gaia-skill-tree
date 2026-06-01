# [upsonic](../../../docs/u/upsonic/)/unittest-generator  [2★]
**ID:** generate-test  
**Type:** Basic Skill  
**Rank:** _rank-less generic reference — stars are earned by named implementations_  
**Top named variant:** 2★  
**Skill Call:** `/generate-test`

---

**Summary:** Produces comprehensive unit, integration, and edge-case test suites from source code.

## Description
Analyzes source code or natural-language specifications to identify functions, classes, and their dependencies, and generates thorough, maintainable test suites. It handles test case structuring, setup and teardown fixtures, mocking external dependencies, and validating normal operation alongside boundary and error conditions.

## Use Case
A developer just finished writing an authentication module (`auth.py`) and needs comprehensive unit tests. The skill is invoked to create properly structured tests using the `unittest.TestCase` format, handling edge-case validation and mock generation without requiring explicit per-file prompting.

## Directives
Tests must use established frameworks (e.g., `unittest.TestCase` format) with proper naming conventions (e.g., 'test_' prefix). Tests should be organized into concept-based subfolders within a `tests/` directory (e.g., `tests/auth/`). Ensure test coverage includes happy paths, boundary conditions, and error paths, utilizing appropriate assertions and mocking techniques to maintain test independence.

## Prerequisites
_None._

## Unlocks
- [Automated Testing](../extra/automated-testing.md)

## Named Implementations
| Named Skill | Contributor | Stars | Evidence |
|---|---|---|---|
| upsonic/unittest-generator ⭑ | upsonic | 2★ | 0 |

## Evidence (inherited capability)
_Capability-level evidence for this generic reference. Every named implementation above inherits it._

| Class | Source | Evaluator | Date |
|---|---|---|---|
| A | https://arxiv.org/abs/2107.03374 | mbtiongson1 | 2026-04-28 |

## Known Agents
_None verified yet._

---
