---
id: langgenius/component-refactoring
name: Component Refactoring
contributor: langgenius
origin: false
genericSkillRef: refactor-code
status: awakened
level: 2★
description: Refactor high-complexity React components in Dify frontend.
createdAt: '2026-05-31'
updatedAt: '2026-06-04'
links:
  github: https://github.com/langgenius/dify/blob/main/.agents/skills/component-refactoring/SKILL.md
timeline:
- timestamp: '2026-05-31T02:07:12Z'
  action: add
  contributor: unknown
  details: Added named skill langgenius/component-refactoring
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
---

## Installation

No additional setup required. This skill uses Dify's existing frontend toolchain.

### Prerequisites

- Access to Dify frontend codebase (`web/` directory)
- Node.js environment with `pnpm` package manager
- Basic understanding of React hooks and component architecture

### Quick Start

Navigate to the web directory and verify component metrics:

```bash
cd web
pnpm analyze-component <path>
pnpm analyze-component <path> --json
```

### How to Use

**Request refactoring analysis** when you have high-complexity components:

```bash
pnpm refactor-component <path>
pnpm refactor-component <path> --json
```

The `--json` flag outputs structured data for programmatic use.

### Complexity Thresholds

| Score | Status | Recommendation |
|-------|--------|-----------------|
| 0-25 | ✅ Simple | Ready to test |
| 26-50 | ⚠️ Medium | Minor refactoring optional |
| 51-75 | ⛔ Complex | Refactor before testing |
| 76-100 | ⛔ Critical | Must refactor |

**Apply refactoring when:**
- Complexity score exceeds 50 (on a 0-100 scale)
- Line count surpasses 300
- Users request code splitting or hook extraction
- Tools warn to refactor before testing
