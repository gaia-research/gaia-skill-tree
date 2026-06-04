---
id: mattpocock/setup-matt-pocock-skills
name: Setup Matt Pocock Skills
contributor: mattpocock
origin: false
genericSkillRef: agent-environment-setup
status: named
title: The Environment Scaffolder
level: 3★
description: Scaffolds per-repo configuration for other engineering skills (like triage,
  tdd, diagnose).
createdAt: '2026-05-21'
updatedAt: '2026-06-04'
suiteRef: mattpocock/engineering
links:
  github: https://github.com/mattpocock/skills/blob/main/skills/engineering/setup-matt-pocock-skills
evidence:
- class: B
  source: https://github.com/mattpocock/skills/blob/main/skills/engineering/setup-matt-pocock-skills/SKILL.md
  evaluator: mbtiongson1
  date: '2026-05-22'
  notes: Scaffolding skill for Matt Pocock's engineering workspace.
---

## Installation

This skill is automatically available after installing the Matt Pocock skills suite:

```bash
npx skills@latest add mattpocock/skills
```

### Setup Process

Run this skill in your agent to configure foundational documents:

```
Invoke: /setup-matt-pocock-skills
```

### What This Skill Does

**Step 1 — Explore:** Reads your repository state via:
- `git remote -v` and `.git/config` (GitHub/GitLab detection)
- `AGENTS.md` and `CLAUDE.md` (existing config)
- `CONTEXT.md`, `CONTEXT-MAP.md`, and `docs/adr/` (domain docs)
- `docs/agents/` (prior output)
- `.scratch/` (local-markdown indicator)

**Step 2 — Present & Decide (one at a time):**
- **Issue Tracker** — GitHub Issues, GitLab Issues, local markdown, or other
- **Triage Labels** — Map five roles to your label vocabulary
- **Domain Docs** — Confirm single-context or multi-context layout

**Step 3 — Review & Edit:** Approve or modify draft output

**Step 4 — Write:** Updates or creates:
- `## Agent skills` block in `CLAUDE.md` or `AGENTS.md`
- `docs/agents/issue-tracker.md`, `docs/agents/triage-labels.md`, `docs/agents/domain.md`

**Step 5 — Complete:** Done. Later manual edits to `docs/agents/*.md` don't require re-running.

### When to Run

- Before first use of downstream engineering skills
- If those skills lack context about your issue tracker, triage labels, or domain docs
- When switching issue trackers or restarting configuration
