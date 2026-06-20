---
id: langgenius/frontend-testing
name: Frontend Testing
contributor: langgenius
origin: false
genericSkillRef: automated-testing
status: awakened
level: 1★
description: Generate Vitest + React Testing Library tests for Dify frontend components.
createdAt: '2026-05-31'
updatedAt: '2026-06-04'
links:
  github: https://github.com/langgenius/dify/blob/main/.agents/skills/frontend-testing/SKILL.md
timeline:
- timestamp: '2026-05-31T02:07:08Z'
  action: add
  contributor: unknown
  details: Added named skill langgenius/frontend-testing
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:18Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:19:38Z'
  details: TM 0.0 -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- action: migrate_trust_magnitude
  timestamp: '2026-06-19T13:26:40Z'
  details: TM 0.0 -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
- timestamp: '2026-06-20T06:31:30Z'
  action: demote
  contributor: mbtiongson1
  details: Level updated from 2★ to 1★ per G7 final rankings calibration.
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
trustMagnitudeInputHash: 66682d883177ca84aa4aa4cb57dc47c455bb2ff922a4d1f468340e43e67a8ed8
---

## Installation

No additional setup required. Vitest and React Testing Library are pre-configured in Dify.

### Prerequisites

- Node.js and pnpm package manager
- Access to the Dify repository
- Familiarity with React and TypeScript

### Quick Start

The test infrastructure is pre-configured in your Dify workspace:

- **Test runner**: Vitest (configured in `web/vite.config.ts`)
- **Testing library**: React Testing Library
- **Setup file**: `web/vitest.setup.ts` (includes global mocks)

### Core Commands

Run from the `web/` directory. From repo root, prefix with `pnpm -C web`:

```bash
# Execute all tests
pnpm test

# Watch mode for active development
pnpm test --watch

# Run a specific test file
pnpm test path/to/file.spec.tsx

# Generate coverage report
pnpm test --coverage

# Analyze component complexity before testing
pnpm analyze-component <path>
```

### How to Use This Skill

**Apply when you:**
- Write or review frontend component/hook/utility tests
- Work with Vitest, React Testing Library, or spec files
- Improve test coverage
- Follow testing patterns in Dify

**Do NOT apply for:**
- Backend/Python tests
- E2E tests (Cucumber + Playwright)
- Conceptual questions without code

### Key Resource

Refer to `web/docs/test.md` for complete specifications and patterns.
