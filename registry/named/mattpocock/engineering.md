---
id: mattpocock/engineering
name: Engineering
contributor: mattpocock
origin: true
title: The Matt Pocock Engineering Discipline
genericSkillRef: engineering-discipline
status: named
level: 5★
description: Engineering category suite for Matt Pocock's skills.
createdAt: '2026-05-21'
updatedAt: '2026-06-04'
suiteRef: mattpocock/skills
suiteComponents:
- mattpocock/diagnose
- mattpocock/grill-with-docs
- mattpocock/improve-codebase-architecture
- mattpocock/prototype
- mattpocock/setup-matt-pocock-skills
- mattpocock/to-issues
- mattpocock/to-prd
- mattpocock/triage
- mattpocock/ubiquitous-language
- mattpocock/zoom-out
---

## Installation

Install the full Matt Pocock skills suite with:

```bash
npx skills@latest add mattpocock/skills
```

### Setup Required

Before using engineering skills (`to-issues`, `to-prd`, `triage`, `diagnose`), you must run the setup skill in your agent:

```
Run: /setup-matt-pocock-skills
```

This interactive setup configures three foundational documents:

1. **Issue Tracker** — Choose GitHub Issues, GitLab Issues, or local markdown
2. **Triage Labels** — Map your label vocabulary (`needs-triage`, `ready-for-agent`, etc.)
3. **Domain Docs** — Confirm your documentation layout (single-context or multi-context)

The setup updates or creates:
- `## Agent skills` block in `CLAUDE.md` or `AGENTS.md`
- `docs/agents/issue-tracker.md`, `docs/agents/triage-labels.md`, `docs/agents/domain.md`

### What's Included

Ten engineering skills for code-focused work:
- **Core Practices**: TDD, bug diagnosis, architecture improvement
- **Planning & Documentation**: Convert plans to GitHub issues, create PRDs, grill sessions
- **Team Coordination**: Issue triage through state machine workflows
- **Supporting Tools**: Prototype creation, zooming out for context
