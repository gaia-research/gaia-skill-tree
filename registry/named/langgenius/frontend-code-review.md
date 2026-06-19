---
id: langgenius/frontend-code-review
name: Frontend Code Review
contributor: langgenius
origin: false
genericSkillRef: code-review-pipeline
status: awakened
level: 2★
description: Trigger when the user requests a review of frontend files.
createdAt: '2026-05-31'
updatedAt: '2026-06-04'
links:
  github: https://github.com/langgenius/dify/blob/main/.agents/skills/frontend-code-review/SKILL.md
timeline:
- timestamp: '2026-05-31T02:06:56Z'
  action: add
  contributor: unknown
  details: Added named skill langgenius/frontend-code-review
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
trustMagnitudeInputHash: c1db6428eb8f75e1dfb4073907dac971a31ee4d03991411f645ac12efeac3af5
---

## Installation

No additional setup required. This skill integrates with Dify's review framework.

### Prerequisites

- Access to frontend source files (`.tsx`, `.ts`, `.js`)
- Reference documentation at `references/code-quality.md`, `references/performance.md`, and `references/business-logic.md`
- A code editor or repository with staged/working changes visible

### How to Use

**Request a frontend code review:**

```
"Review my frontend code"
"Check this .tsx file for issues"
"Review my pending changes"
```

### Review Modes

1. **Pending-change review** — Analyze staged or working-tree files ready for commit
2. **File-targeted review** — Review specific files you name

### What Gets Checked

The agent examines:
- Component/module structure and class names
- React hooks and prop memoization
- Styling consistency and organization
- Cross-referenced against three categories:
  - **Code Quality** — best practices, readability
  - **Performance** — bundle size, rendering efficiency
  - **Business Logic** — requirements compliance

### Output Format

Issues are organized by:
1. **Urgency** (critical, suggestions, nits)
2. **Category** (quality, performance, business logic)
3. **Details** (code snippets and fix suggestions)

Maximum 10 findings per category; excess results summarize as "10+"
