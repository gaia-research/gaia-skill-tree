---
id: mattpocock/prototype
name: Prototype
contributor: mattpocock
origin: false
genericSkillRef: prototype
status: named
title: The Prototyping Engine
level: 3★
description: Build throwaway prototypes to answer specific design or logic questions
  before committing to production code.
createdAt: '2026-05-21'
updatedAt: '2026-06-04'
suiteRef: mattpocock/engineering
links:
  github: https://github.com/mattpocock/skills/blob/main/skills/engineering/prototype
evidence:
- class: B
  source: https://github.com/mattpocock/skills/blob/main/skills/engineering/prototype/SKILL.md
  evaluator: mbtiongson1
  date: '2026-05-22'
  notes: Production interactive prototyping skill.
---

## Installation

This skill is included in the Matt Pocock skills suite:

```bash
npx skills@latest add mattpocock/skills
```

No additional setup required.

### How to Use

**Step 1 — Identify your question**

Determine whether you're validating logic/state or exploring UI design.

**Step 2 — Choose your branch:**

- Logic questions → Build a terminal app testing the state machine
- UI questions → Create multiple design variations on one route

**Step 3 — Run with one command**

Use your project's existing task runner (e.g., `pnpm`, `python`, `bun`).

**Step 4 — Location matters**

Place prototype code near the actual module or page it tests, with a clear "prototype" label in the filename.

### During Prototyping

- Keep state in memory (no persistence unless testing a database specifically)
- Skip polish — no tests or error handling beyond what's needed to run
- Display full state after each action so changes are visible

### When Finished

- Capture the answer in a durable location
- Document what question was answered
- Delete the prototype or integrate validated decisions into production code
- Don't leave prototype code rotting in the repository

**Key principle:** The goal is learning fast, then deletion — not building production-ready code.
