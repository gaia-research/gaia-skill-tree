---
id: mattpocock/handoff
name: Handoff
contributor: mattpocock
origin: false
genericSkillRef: agent-handoff
status: named
title: The Handoff Protocol
level: 4★
description: Compacts the current conversation into a summary for a fresh agent to
  continue the work.
createdAt: '2026-05-21'
updatedAt: '2026-06-04'
suiteRef: mattpocock/productivity
links:
  github: https://github.com/mattpocock/skills/blob/main/skills/productivity/handoff
evidence:
- class: B
  source: https://github.com/mattpocock/skills/blob/main/skills/productivity/handoff/SKILL.md
  evaluator: mbtiongson1
  date: '2026-05-22'
  notes: High-fidelity agent handoff and context compaction skill.
---

## Installation

This skill is included in the Matt Pocock skills suite:

```bash
npx skills@latest add mattpocock/skills
```

No additional setup required.

### Core Purpose

Enables seamless agent transitions by creating a summary document that allows a fresh agent to continue work without losing context.

### Key Setup Requirements

1. **Output Location** — Save handoff documents to the OS temporary directory, not the current workspace
2. **Content Optimization** — Avoid duplicating information already captured in artifacts (PRDs, plans, ADRs, issues, commits, diffs). Reference them instead.
3. **Security** — Redact sensitive data including API keys, passwords, and PII

### Document Structure

The handoff document includes:

- **Conversation Summary** — Key decisions, progress, and current status
- **Suggested Skills Section** — List tools/capabilities the next agent should invoke
- **References** — Links or paths to existing artifacts rather than redundant content
- **Focus Area** — If user-provided arguments exist, tailor the document around those priorities

### Usage Workflow

When initiating a handoff:

1. Provide context about what the next session will address (optional arguments)
2. The protocol automatically compacts the conversation into a portable summary
3. The document is saved to a temporary location accessible across sessions
4. The next agent uses this document to resume work efficiently

This approach maintains continuity while keeping documentation DRY and security-conscious.
