---
id: langgenius/backend-code-review
name: Backend Code Review
contributor: langgenius
origin: false
genericSkillRef: code-review-pipeline
status: awakened
level: 2★
description: Review backend code for quality, security, maintainability, and best
  practices based on established checklist rules.
createdAt: '2026-05-31'
updatedAt: '2026-06-04'
links:
  github: https://github.com/langgenius/dify/blob/main/.agents/skills/backend-code-review/SKILL.md
timeline:
- timestamp: '2026-05-31T02:06:53Z'
  action: add
  contributor: unknown
  details: Added named skill langgenius/backend-code-review
- action: migrate_trust_magnitude
  timestamp: '2026-06-18T11:27:18Z'
  details: TM None -> 0.0, grade ungraded -> ungraded (direct edit -- CLI gap)
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
trustMagnitudeInputHash: f514e5e7a20fb28c0844b113818039a6a5e72981ee6c88ec53ac40dde218ed4e
---

## Installation

No additional setup required. This skill is built into the Dify agent framework.

### Prerequisites

- Access to backend code files in the `api/` directory
- Python files (`.py` extension) for review
- Optional: Git staging area for pending changes to review

### How to Use

**Request a code review** by asking the agent to analyze backend code:

```
"Review this Python function for security issues"
"Analyze api/app.py for best practices"
"Check my pending changes for quality concerns"
```

**Review Modes:**

1. **Pending-Change Review** — Agent inspects staged/working-tree files ready for commit
2. **Code Snippet Review** — Paste function, class, or module excerpts directly
3. **File-Focused Review** — Reference specific backend files (e.g., `api/models/user.py`)

### What Gets Checked

- Database schema design (`api/models/`, `api/migrations/`)
- Architecture patterns (layering, dependency flow)
- Repository abstraction (CRUD operations)
- SQLAlchemy patterns (sessions, transactions)
- General best practices if no specific checklist matches

### Output Format

Reviews are categorized as:
- 🔴 **Critical** (must fix)
- 🟡 **Suggestions** (should consider)
- 🟢 **Nits** (optional improvements)

Each finding includes file path, line numbers, explanation, and actionable code fix.
