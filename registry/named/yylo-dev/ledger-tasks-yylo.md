---
id: yylo-dev/ledger-tasks-yylo
name: Ledger Tasks (yylo)
contributor: yylo-dev
origin: true
genericSkillRef: project-management
status: awakened
level: 2★
description: Comprehensive guide for using YYLO Ledger task management — a Kanban
  board and task state stored as hash-chained Markdown inside the repository (no hosted
  tracker). Covers create/list/search/get/mark/update/archive, dependency management
  (deps/ready/order), history/receipts, cold archive, cross-project routing, and typed
  merge orchestration across agent worktrees. The underlying YYLO CLI orchestrates
  multiple coding-agent harnesses (Claude Code, Codex, Gemini CLI, Pi) over that same
  shared task state.
createdAt: '2026-09-11'
updatedAt: '2026-09-11'
evidence:
- source: https://github.com/yylo-dev/yylo-skills/blob/main/skills/ledger-tasks-yylo/SKILL.md
  evaluator: claude
  date: '2026-09-11'
  type: repo-own
  trustNumber: 50.0
  notes: 'MIT-licensed skill from the yylo-skills pack (7 SKILL.md skills, active
    since Sep 2026). Verified by direct clone 2026-09-11 (full history): 3 commits,
    1 contributor. File exists, content matches intake description.'
  commits: 3
  contributors: 1
  skillCountInRepo: 7
- source: https://github.com/yylo-dev/yylo
  evaluator: claude
  date: '2026-09-11'
  type: repo-own
  trustNumber: 50.0
  grade: B
  notes: 'The YYLO CLI (@yylo/cli on npm) that powers the ledger, MIT licensed (Copyright
    JUNO AI INC.). Verified by direct clone 2026-09-11 (full history): 1291 commits,
    7 contributors. Orchestrates coding agents (Claude Code, Codex, Gemini CLI, Pi)
    over the shared Kanban/task state the skill drives.'
  commits: 1291
  contributors: 7
installable: true
links:
  github: https://github.com/yylo-dev/yylo-skills/blob/main/skills/ledger-tasks-yylo/SKILL.md
verification:
  firstEvidenceAt: '2026-09-11T13:52:43Z'
timeline:
- timestamp: '2026-09-11T13:52:43Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/yylo-dev/yylo-skills/blob/main/skills/ledger-tasks-yylo/SKILL.md
    (type: repo-own)'
- timestamp: '2026-09-11T13:52:43Z'
  action: evidence_graded
  contributor: unknown
  details: 'Graded evidence from https://github.com/yylo-dev/yylo-skills/blob/main/skills/ledger-tasks-yylo/SKILL.md
    as B (trustNumber: 50.0)'
- timestamp: '2026-09-11T13:52:50Z'
  action: evidence_added
  contributor: unknown
  details: 'Added evidence from https://github.com/yylo-dev/yylo (type: repo-own)'
- timestamp: '2026-09-11T13:52:50Z'
  action: evidence_graded
  contributor: unknown
  details: 'Graded evidence from https://github.com/yylo-dev/yylo as B (trustNumber:
    50.0)'
- timestamp: '2026-09-11T13:54:46Z'
  action: evidence_graded
  contributor: unknown
  details: 'Updated evidence #0 from https://github.com/yylo-dev/yylo-skills/blob/main/skills/ledger-tasks-yylo/SKILL.md;
    changed commits, contributors, grade, notes, skillCountInRepo (grade: B → ungraded)'
- timestamp: '2026-09-11T13:54:55Z'
  action: evidence_graded
  contributor: unknown
  details: 'Updated evidence #1 metadata from https://github.com/yylo-dev/yylo; changed
    commits, contributors, notes'
---

## Implementation

### YYLO Ledger CLI Reference

Use `yy ledger` for all commands. YYLO 0.2.2 supports the exact `yylo-ledger 0.2.0` task CLI. `yy kanban` is a labelled compatibility alias for the same controller-routed task runtime.

#### Supported task contract

- The public Ledger 0.2.0 surface is task-oriented: create, get, update, mark, archive, list/search, dependencies, ordering, history, doctor, compatibility, conversion, rollback, and cold archive operations.
- Read current task state before mutation, preserve mutation receipts where offered, and never bypass controller routing or lifecycle state with direct file edits.
- Normal discovery is hot-only unless an explicit cold-archive command is used.

#### Core commands

```bash
yy ledger create "Task description here" --status backlog --tags feature,backend
yy ledger list --limit 5 --sort asc
yy ledger search --status todo --tag backend --limit 10
yy ledger get TASK_ID
yy ledger mark done --id TASK_ID --response "Completed: implemented X, tested Y" --commit abc123def
yy ledger update TASK_ID --status todo --tags backend,urgent
yy ledger archive TASK_ID
```

#### Dependency management

```bash
yy ledger deps TASK_ID
yy ledger deps add --id TASK_ID --blocked-by BLOCKER1 BLOCKER2
yy ledger ready
yy ledger order --scores
```

Cycle detection prevents circular dependencies automatically. `ready` returns tasks where status is backlog/todo/in_progress and all `blocked_by` tasks are done/archive; `order` produces a topological sort of open tasks respecting dependencies, for safe parallel execution planning.

#### Cold archive

Normal `list`/`search`/`ready`/`order` are hot-only by design. `get TASK_ID` transparently resolves a hot or archived task; `archive-search` gives bounded, projected discovery of cold tasks. Archive maintenance (`archive-pack plan|create|doctor`) requires explicit owner authorization, a clean repo/index, and durable report paths outside the repository — a stale plan or conflict fails closed rather than silently proceeding.

#### Cross-project routing and merge

Cross-project access is opt-in (`kanbanRegistry.enabled: true` plus an explicit allowlist). Scattered per-directory task stores can be consolidated with `yy ledger merge --dry-run --plan-file ...` followed by a separate, reviewed `--apply-plan` step that retains a receipt.

#### Controller routing

YYLO Ledger resolves its controller in order: explicit `JUNO_TASK_ROOT`, repository-local registration, then the current project root. Explicit/registered path or branch errors fail closed — YYLO Ledger never switches Git branches or falls back silently.

---

## Evidence

Evidence for the underlying `project-management` capability is inherited via `genericSkillRef: project-management`; rows specific to this implementation are added via `gaia dev evidence`.
