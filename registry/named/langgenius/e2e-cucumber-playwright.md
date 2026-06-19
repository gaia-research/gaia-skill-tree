---
id: langgenius/e2e-cucumber-playwright
name: E2E Cucumber Playwright
contributor: langgenius
origin: false
genericSkillRef: e2e-testing
status: awakened
level: 2★
description: Write, update, or review Dify end-to-end tests under e2e/ that use Cucumber,
  Gherkin, and Playwright.
createdAt: '2026-05-31'
updatedAt: '2026-06-04'
links:
  github: https://github.com/langgenius/dify/blob/main/.agents/skills/e2e-cucumber-playwright/SKILL.md
timeline:
- timestamp: '2026-05-31T02:07:01Z'
  action: add
  contributor: unknown
  details: Added named skill langgenius/e2e-cucumber-playwright
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:18Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:38Z'
  details: TM 0.0 -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
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
trustMagnitudeInputHash: 964628827f5d8ad831c8ea7aeffd354a80ff28a5e97e0359ed3a301c606bc714
---

## Installation

No additional setup required beyond accessing the Dify E2E test suite.

### Prerequisites

- Access to the Dify repository
- Node.js and pnpm installed
- Familiarity with Cucumber, Gherkin syntax, and Playwright

### Validation

Validate your E2E test configuration and changes:

```bash
pnpm -C e2e check
```

### How to Use

**Start here:** Read `e2e/AGENTS.md` for the canonical guide on local architecture and conventions.

**Then examine these files in order:**

1. Target `.feature` files under `e2e/features/`
2. Related step definitions in `e2e/features/step-definitions/`
3. Session and state files: `hooks.ts` and `world.ts` (if lifecycle matters)
4. Execution config: `run-cucumber.ts` and `cucumber.config.ts` (if tags or flow matter)

### Writing Scenarios

- Use Behavior-Driven Development (BDD) syntax with Given-When-Then structure
- Reuse existing step definitions when possible
- Prefer user-facing locators over implementation details
- Validate narrowly before broadening verification
- Reference Playwright best practices for locators, assertions, and waiting strategies

### Key Principles

- Keep scenarios readable and business-focused
- Maintain step definition reusability
- Test user workflows, not implementation details
- Use Cucumber best practices for scenario wording and step design
