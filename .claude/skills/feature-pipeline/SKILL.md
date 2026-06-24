---
name: feature-pipeline
description: >-
  Five-phase multi-agent exploration-to-ship pipeline. Use this skill to explore a CLI,
  flag, or module, test end-to-end, and run explore-then-ship workflows. Trigger for
  'explore X', 'test/ship X', 'run pipeline on X', or '/feature-pipeline'. Do not use
  for simple bug fixes or single-file edits. ORCHESTRATOR coordinates LIGHTER and HEAVIER
  sub-agents: LIGHTER stress-tests and files issues; HEAVIER plans (user approves first)
  and implements; LIGHTER watches CI and checks drift. Uses M1-M4 stop hooks. Supports
  Claude Code, Cursor, Codex, Windsurf, with handover fallbacks.
version: 2.0.0
argument-hint: "<feature-or-cli-to-explore>"
---

# feature-pipeline

Five-phase exploration-to-PR pipeline. ORCHESTRATOR — the currently active
agent, regardless of model or harness — coordinates lighter and heavier
sub-agents to explore a feature, file issues, plan and implement fixes, run
sandbox tests, watch CI, and deliver a clean summary.

```
Phase 1 ── LIGHTER explores → files GitHub issues           [STOP M1]
Phase 2 ── ORCHESTRATOR drafts PR + HEAVIER plans
           → user approves → ORCHESTRATOR commits           [STOP M2]
Phase 3 ── HEAVIER RED/GREEN sandbox review → PR comment    [STOP M3]
Phase 4 ── LIGHTER iterates on comment + watches CI         [STOP M4]
Phase 5 ── LIGHTER drift check → user summary
```

ORCHESTRATOR owns coordination only — it does not explore, plan, implement,
or review. Target: ORCHESTRATOR produces ≤50% of total pipeline output.
When sub-agent spawning is unavailable, write a **Handover** and pause.
Do not perform sub-agent work yourself.

---

## Terminology

| Label | Meaning |
|-------|---------|
| **ORCHESTRATOR** | The currently active agent running this skill. Coordinates, delegates, and holds state. Never does sub-agent work. |
| **LIGHTER** | One capability tier below ORCHESTRATOR: faster, cheaper, suited to exploration and CI watch. If ORCHESTRATOR is already at base tier, LIGHTER = ORCHESTRATOR tier. |
| **HEAVIER** | One capability tier above ORCHESTRATOR: deeper reasoning, suited to planning and adversarial review. If ORCHESTRATOR is already at apex, HEAVIER = ORCHESTRATOR tier. |

### Harness compatibility

| Harness | Spawn mechanism | Notes |
|---------|-----------------|-------|
| Claude Code | `Agent` tool (`subagent_type`, `model`) | Preferred |
| Cursor | Background agents / `@agent` | Pass brief as system prompt |
| Codex CLI | `codex run --agent` | Pass brief via `--instructions` |
| Windsurf Cascade | Cascade sub-tasks | Delegate via task handoff |
| Other / unknown | **Trigger Handover Protocol** | See below |

---

## Phase 1 — Feature Exploration (LIGHTER)

Spawn LIGHTER with this brief:

> You are a developer sandbox-testing `{{feature}}` for the first time. Invoke
> it in at least five distinct ways (happy path, edge cases, invalid inputs, flag
> combos, piped output). Note every footgun, unintuitive behaviour, unclear error,
> or doc gap. File one GitHub issue per distinct finding:
> - Title: `[{{feature}}] <short description>`
> - Labels: `exploration`, `needs-triage`
> - Body: steps to reproduce / expected / actual / severity (low | medium | high)
>
> End with a severity table of all issues filed.

**Handover if spawning fails** → write a [Handover](#handover-protocol) with
`role: LIGHTER`, `task: Phase 1 exploration`, `context: {{feature}}`.
Do not explore the feature yourself.

→ **[STOP HOOK M1](#stop-hooks)** after LIGHTER reports completion.

---

## Phase 2 — Plan & Draft PR (ORCHESTRATOR + HEAVIER)

ORCHESTRATOR does these steps directly (this is its core coordination work):

1. Read Phase 1 issues → write a one-paragraph **Problem Statement** (what is
   broken, why it matters, what a fix should achieve).
2. Create branch `fix/{{feature}}-findings-<slug>`.
3. Open a **draft** PR:
   - Title: `fix({{feature}}): address exploration findings`
   - Labels: `draft`, `needs-plan`
   - Body: Problem Statement + `Closes #N` links + `## Plan` placeholder.

Then spawn HEAVIER with: issue bodies, PR URL, relevant source file excerpts.

HEAVIER produces a **numbered implementation plan**:
```
1. <file/area>  —  <change>  —  <rationale>  [⚠ breaking | ⚠ test-only | ⚠ schema]
2. …
```

**Present plan to user. Do not commit a single line until the user explicitly
approves or edits the plan.** Accept corrections ("change step 3 to …",
"skip step 2"). Update PR body `## Plan` with the approved plan.

After approval, ORCHESTRATOR implements step by step:
- One atomic commit per plan step: `<type>(<scope>): <desc>`
- Update labels: remove `needs-plan`, add `in-progress`
- Push

**Handover if HEAVIER spawning fails** → write a [Handover](#handover-protocol)
with `role: HEAVIER`, `task: Phase 2c planning`. Pass issue bodies and source
excerpts. Do not plan yourself — hand off.

→ **[STOP HOOK M2](#stop-hooks)** after implementation commits are pushed.

---

## Phase 3 — Sandbox Review (HEAVIER)

Spawn a fresh HEAVIER in `isolation: worktree` with the PR branch checked out.

Brief:

> Read the full diff (`git diff origin/main...HEAD`). For each changed public
> surface or behaviour: write a RED test (must fail before the fix — verify by
> temporarily reverting, running, re-applying) and a GREEN test (must pass with
> fix). Run `gaia validate` for schema changes; `gaia docs build --check` for doc
> changes. Post this review comment to the PR:
>
> ```markdown
> ## Sandbox Review
>
> ### RED tests
> | Description | Result | Notes |
> |-------------|--------|-------|
>
> ### GREEN tests
> | Description | Result | Notes |
> |-------------|--------|-------|
>
> ### Issues found
> - [ ] <description> — `<file>:<line>`
>
> ### Verdict: APPROVE / REQUEST CHANGES
> ```

**Handover if spawning fails** → write a [Handover](#handover-protocol) with
`role: HEAVIER`, `task: Phase 3 sandbox review`, pass PR diff URL and branch.
Do not review yourself.

→ **[STOP HOOK M3](#stop-hooks)** after review comment is posted.

---

## Phase 4 — Iterate & Watch CI (LIGHTER)

Spawn LIGHTER (same agent as Phase 1 if context is intact, else fresh) with
the PR context and the Phase 3 review comment URL.

Brief:

> Read the review comment. For each `[ ] issue`: fix, commit
> (`fix(<scope>): <desc> (per review)`), push. Subscribe to CI events. On each
> failure: read logs, diagnose root cause, push targeted fix. Do not exit until
> all required checks pass. On CI green: remove `draft` status, swap
> `in-progress` → `ready-for-review`. If the same check fails 3× with no new
> diagnosis, escalate to ORCHESTRATOR with the exact log excerpt.

**Handover if spawning fails** → write a [Handover](#handover-protocol) with
`role: LIGHTER`, `task: Phase 4 CI watch`. Do not watch CI yourself.

→ **[STOP HOOK M4](#stop-hooks)** after CI is green and PR is marked ready.

---

## Phase 5 — Drift Check & Summary (LIGHTER)

Spawn LIGHTER for the final hygiene pass.

Brief:

> `git fetch origin main` → `gaia dev diff`. If unexpected drift: print a
> warning table (skill ID / field / main value / branch value) and pause — do
> NOT auto-fix. If clean: send the user the final summary (feature explored,
> issues filed with links, PR URL + title, CI status, commit list, what was
> fixed). All agents exit.

**Exception to no-self-work rule**: if spawning fails here, ORCHESTRATOR may
run the drift check and summary itself — Phase 5 is lightweight and final.

---

## Stop Hooks

Stop hooks are mandatory pauses after commit milestones. ORCHESTRATOR prints
the banner and waits for explicit user input before the next phase begins.
If the harness cannot block mid-turn, print the banner and **end the turn** —
resume when the user responds.

| Hook | Trigger point | What to review | User options |
|------|---------------|----------------|--------------|
| **M1** | LIGHTER files last issue and prints severity table | Issue list, severity | `continue` → Phase 2 · `stop` · `add: <notes>` |
| **M2** | ORCHESTRATOR pushes initial implementation commits | PR diff, commit list | `continue` → Phase 3 · `stop` · `amend: <notes>` |
| **M3** | HEAVIER posts review comment to PR | Verdict, `[ ]` items | `continue` → Phase 4 · `stop` · `override: <notes>` |
| **M4** | LIGHTER reports CI green and PR marked ready | Final PR state, checks | `continue` → Phase 5 · `stop` |

**Stop hook banner**:
```
╔══ STOP HOOK M<N> ════════════════════════════════════════════════════════════╗
║  <one-line summary of what just completed>                                   ║
║  Review above, then reply: continue · stop · <feedback>                      ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

ORCHESTRATOR does not auto-advance past a stop hook.

---

## Handover Protocol

When sub-agent spawning is unavailable (harness limitation, permission error,
quota), ORCHESTRATOR writes a handover document and pauses. It does **not**
do the sub-agent's work — handover is always preferred.

### Storage selection

| Environment | Storage | Path / Location |
|-------------|---------|-----------------|
| Local filesystem available | Disk file | `./feature-pipeline-handover-{{feature}}.md` |
| Cloud / no filesystem | Git comment | PR comment, or commit note on current branch |

### Handover document

```markdown
## 🔀 Feature Pipeline Handover — Phase <N>

**Feature**: {{feature}}
**Timestamp**: <ISO 8601>
**PR**: <URL or "not yet created">
**Branch**: <name or "not yet created">

### Role needed
LIGHTER | HEAVIER

### Task
<paste the exact Phase section brief from this skill — do not paraphrase>

### Context
<issues filed: #N, #M / plan approved: yes/no / review comment: <URL> /
 CI status: pending | green | failed | N/A>

### State snapshot
{
  "phase": <N>,
  "issueNumbers": [N, M],
  "prUrl": "...",
  "planApproved": true | false,
  "reviewCommentUrl": "..." | null,
  "ciStatus": "pending | green | failed | n/a"
}

### Resume
1. Read this document.
2. Complete the Task above as the specified role.
3. When done: update State snapshot, then either write a Phase <N+1> handover
   or post a completion note on the PR and notify ORCHESTRATOR.
```

After writing the handover, ORCHESTRATOR prints:
```
⚠  Sub-agent spawning unavailable.
   Handover written → <path or "PR comment">
   Assign task to a <LIGHTER | HEAVIER> agent, then reply 'continue'.
```

Then ends its turn. It does not proceed to the next phase.

---

## Constraints

| Rule | Detail |
|------|--------|
| **ORCHESTRATOR compact ratio** | ORCHESTRATOR produces ≤50% of total pipeline output. It coordinates, writes the PR skeleton, approves the plan, and holds state. Sub-agents do the work. |
| **Verbosity** | Medium. Print phase banners, stop-hook banners, and key decisions. Suppress step-by-step narration of sub-agent work — sub-agents handle their own output. |
| **Phase order** | Strict. Phase N+1 does not start until Phase N is complete and its stop hook is cleared. |
| **No self-work on handover** | When spawning fails, write a handover — do not perform sub-agent work. Exception: Phase 5 drift check (lightweight, final). |
| **Model-tier assignment** | Fixed relatively: LIGHTER for exploration and CI watch; HEAVIER for planning and sandbox review; ORCHESTRATOR for PR authoring, approval gating, and state. |
| **Plan approval** | Zero implementation code before explicit user approval of the HEAVIER plan. |
| **No force-pushes** | Commits append only. Rebase on explicit user request only. |
| **CI loop** | Phase 4 has no exit until all required checks pass, or a 3× failure escalation surfaces to ORCHESTRATOR. |
| **Programmatic-First** | Registry mutations via `gaia dev add` / `gaia dev merge` / `gaia dev split`. Never hand-edit `registry/nodes/`. |
| **Single PR** | One PR per `/feature-pipeline` run, covering all Phase 1 issues. |
| **Drift pause** | Phase 5 drift detected → warn and pause, never auto-fix. |

---

## Invocation

```
/feature-pipeline <feature>
```

If `<feature>` is omitted, ask: *"Which feature or CLI should I explore?"*

**Examples**: `gaia scan` · `packages/mcp` · `the --canon flag` · `gaia skills install`

---

## Phase banner

Sub-agents print at phase end:
```
── Phase <N> complete ─────────────────────────────────────────────────────────
```
ORCHESTRATOR prints stop-hook banners separately. Both must never be suppressed.
