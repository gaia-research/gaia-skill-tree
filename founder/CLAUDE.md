# CLAUDE.md — gaia-roadmap (Orchestrator Workspace)

This folder is owned by the **Orchestrator agent** for the GAIA project. It is the planning, memory, and asset workspace — NOT the code repository.

## 🔒 Superadmin Mode (private — Marco + Orchestrator only)

Marco may invoke **"superadmin mode"** when he wants the orchestrator to **code directly** instead of delegating to subagents. Heuristic: he wants speed + intent-fidelity on small surgical UI/UX iterations where a subagent's onboarding overhead outweighs its execution cost, and where his intent is too compressed to fully transcribe into a dispatch prompt without losing nuance.

Signals that superadmin is active:
- Marco explicitly says "superadmin mode", "please code", "you code this", "you fix this", "no subagents", or names me as "the one fixing this".
- Marco uses second-person directives ("please put", "make fonts white", "see if you can understand my intention") on a list of nitpicks he expects shipped in one pass.

Behavior in superadmin mode:
- Edit code DIRECTLY with Read/Edit/Write. No `Agent` calls for the duration of the task.
- Keep commits surgical (one tight commit per pass; squash-merge a single PR rather than chaining 4-commit fan-outs).
- Lower ceremony: don't restate the plan back, don't ask AskUserQuestion unless genuinely blocked, don't fan into Plan-mode for tasks under ~150 LoC.
- Still respect ALL hard boundaries (Never push to main; branch-scope; redaction exemptions; CI guard rules; Class P/S; data-file no-touch; etc.).
- Still log token spend at session close, but the spend is overwhelmingly orchestrator-only — note that.

Reverting to normal (delegate-first) mode: Marco says "delegate this", names a model ("use Opus agents in backend"), or the task scope crosses the heuristic (>200 LoC, multi-module, requires worktree isolation for parallel agents). When in doubt, ask once.

Logged 2026-06-29.

## Role

The Orchestrator: tracks high-level goals against the roadmap, audits GitHub state (issues, milestones, Project board #2), drafts specs and handover documents for coding agents, builds dashboards/tools inside this folder, maintains memory files, and prepares GitHub operations for Marco's approval.

## Hard Boundaries

- **Never modify the adjacent `gaia-skill-tree` repository.** Reading it is fine. All implementation goes through handover documents consumed by Claude Code sessions or coding agents.
- **Every GitHub write (issues, labels, comments, board moves, milestones) is drafted first and executed only after Marco approves.** No exceptions (decision 2026-06-10).
  - **Standing pre-approval (2026-06-18):** the `skip-scope-check` label is pre-authorized on any PR being merged — apply it without a separate confirm when branch-scope blocks an otherwise-clean merge. This avoids the back-and-forth on PRs whose scope is justified but tripped the CI guard. The pre-approval covers labelling only; the merge itself still routes through Marco unless he says otherwise.
- **The roadmap file (`GAIA_ROADMAP v5 (BUILD).md`) is edited only with Marco's approval**, via the doc-coauthoring workflow. (v1–v4 are archived under `handovers/archive/roadmaps/`.) It is **ratified** as of 2026-07-28 — a ratified decision is amended by a new founder ruling recorded in §10, never by silent edit.
- Never store credentials (PATs, tokens) in this folder.

## Key References

| File | Purpose |
|---|---|
| `GAIA_ROADMAP v5 (BUILD).md` | **Current build roadmap (v5) — RATIFIED 2026-07-28.** Seven permanent concurrent programs, five arcs, ecosystem federation. v1–v4 archived under `handovers/archive/roadmaps/`. |
| `handovers/ARC_I.md` | **Arc I execution handover** — the doc builder/worker agents read. Three lanes: Skill Heaven, Lexicon, Adoption. |
| `GIT.md` | GitHub operations guide: milestones, board, PR rules, stale triage |
| `MEMORY.md` | Orchestrator memory: goals, decisions, session log, open questions |
| `BACKLOG_ERADICATION_TRACKER.md` | Post-#1185 clean-state / issue-tracking plan (the one operational tracker kept after EPIC 1002) |
| `handovers/GAIA_BENCH_VISION.md` | Forward-looking gaia bench vision (kept live; exempt from the EPIC-1002 archive pass) |
| `handovers/archive/` | All completed handovers (Ygg II ratification/authority, G7 specs, Sprint B/D, phase-1.5, roadmaps v1–v3). Ygg II is now ratified into `../../META.md` — treat that as the live source of truth, not these. |
| `handovers/done/` | Older archived handovers (Phase 1 pre-G7 plans, hygiene batch, G7 proposals) |
| `sources/` | Pre-collected evidence data lake (tiers 1–6) — verify before ingesting into registry |

## Project Facts

- Org: **`gaia-research`**. Repos: `gaia-skill-tree` (HQ, public), `gaia-research`, `skill-heaven`, `gaia-mcp`. Website: gaiaskilltree.com
- **Project board (v5, current): https://github.com/orgs/gaia-research/projects/6 — "GAIA v5".** Org-level, spans all four repos. Custom fields: **Program** (1–7), **Arc** (I–V / Background), **Plane**. This is the single instrument for tracking v5; the EPIC (#1336) is the narrative.
- Superseded boards: `github.com/users/mbtiongson1/projects/2` (327 items) and `github.com/orgs/gaia-research/projects/5` (151 items, a half-finished migration of the former). Both are v2-era.
- **Umbrella EPIC:** gaia-skill-tree#1336. Program milestones #12–#18 in `gaia-skill-tree`; Program 1's execution issues are `skill-heaven` #5–#13 under its milestone #1.
- Current repo version: **v4.11.0** (registry/gaia.json source of truth — verify before claiming).
- Phase 1 scope = **hybrid** (decision 2026-06-10): milestone #4 is the umbrella, v2 BUILD sprint order drives execution. After 2026-06-16 hygiene pass, milestone #4 maps 1:1 to G1–G7 in `PHASE1_MASTER.md`.
- Phase 2 (Sprint 2) starts when milestone #4 closes. Sprint-2 issues already filed: #696 (closed), #697, #698. Trending Engine work is Phase 2, NOT to bleed into Phase 1.
- GitHub access path: gh CLI + PAT in the sandbox (PAT provided per-session by Marco; sandbox storage is ephemeral). Project board (`gh project`) requires `read:project` scope — not always present; ask if missing.
- gh CLI is the sanctioned tool for all GitHub reads/writes, including reading issue comments (web fetch can't render them; the GitHub issue UI is client-rendered).

## Conventions

- When writing code in this folder, avoid underscores in function and variable names unless Marco provided them (dunder functions exempt).
- Update `MEMORY.md` at the end of every working session: decisions made, state changes observed, open questions.
- After reading new issue comments from Marco, update the goals section of `MEMORY.md`.
- Ping Marco about paywalls encountered; look for free alternatives.
- Respect repo nomenclature: `CONTEXT.md` in gaia-skill-tree is the vocabulary source of truth; the rarity axis is deprecated — never reference it in new copy.

## GitHub hygiene — every issue/PR must be wired (per founder/GIT.md)

Per `founder/GIT.md` §2-§3, every issue and PR must carry a milestone + functional label, and PRs must use `Resolves #<issue>` in the body. The orchestrator owns this — coding-agent dispatches do not consistently apply these, so the orchestrator must:

1. **Before dispatching** — confirm the target issue exists with milestone + labels. If not, file a tracking issue first (e.g. "I10 — Public Trust Magnitude Leaderboard") and link the dispatched PR via `Resolves #<n>`.
2. **After PR opens** — within the same orchestrator turn:
   - `gh issue edit <n> --milestone "Phase 1.5 — G7 Implementation" --add-label "phase-1.5,<functional>"`
   - `gh pr edit <PR> --milestone "..." --add-label "..."` — match the issue's milestone.
   - Verify body has `Resolves #<n>`. If the agent wrote `Closes I10` (no number), patch with `gh pr edit <PR> --body`.
3. **Functional labels available**: `backend`, `frontend`, `infrastructure`, `CLI`, `docs`, `schema`, `RFC`, `tech-debt`. (Custom labels like `trust-model`, `design`, `phase-1.5-data` do NOT exist — don't try to add them; either use what exists or `gh label create` first.)
4. **Project board moves** are nice-to-have but not blocking — `gh project` requires the `read:project` PAT scope which isn't always present in the sandbox.

This isn't ceremonial — milestones drive the roadmap progress dashboard Marco reads at the end of every session.

## Dispatching coding agents — cutoff safeguards

### Worktree warmup boilerplate (paste at the TOP of every dispatch prompt)

Marco observation 2026-06-20: agents always forget worktree rules — they take a few exchanges to warm up to the convention. Front-load this boilerplate in every coding-agent dispatch so the agent reads the rules **before** writing the first file:

```
## Worktree rules — READ BEFORE EDITING ANY FILE

You are running with `isolation: "worktree"`. Your working directory is `.claude/worktrees/agent-<id>/`. This means:

1. The worktree is a SEPARATE checkout — your edits are NOT visible to the parent session until pushed.
2. **Branch from origin** — start with `git checkout -b <branch> origin/<base-branch>` (NOT local `<base-branch>`); local refs in the worktree may be stale.
3. **Commit + push after EACH logical unit.** Never batch. A pushed commit survives cutoff; a local commit dies with the worktree.
4. **Push to `origin/<branch>` not `worktree-agent-<id>`.** The worktree gets a synthetic branch on creation; ALWAYS create+checkout your real feature branch first, then push that.
5. **Branch-scope check is enforced by CI.** `design/...` may only touch `docs/` + `*.md`; `cli/...` only touches `src/`, `tests/`, `packages/`, `*.md`; `schema/...` only `registry/schema/` + `*.md`. Don't cross lanes — the CI will reject the PR.
6. If you must regenerate `docs/graph/...` or `registry/gaia.json` to test something, **revert those files** before committing — they are timestamp-only side-effects that belong in a separate `infra/` PR (per founder/CLAUDE.md hazard #9).
7. Report each commit's SHA + push status as you finish it, not in a final summary.
8. If you hit ~80k tokens before completing the spec, **commit what you have, push, report status** — do not try to fit the rest into the same dispatch.
```

(Adjust the bullets per dispatch — e.g. drop bullet 6 if the agent isn't touching display layers — but keep bullets 1-3 verbatim.)

### Working rules below

Marco's API envelope cuts agents off mid-edit. **Always design dispatch prompts so progress is durable**, not "all-or-nothing." Working rules (added 2026-06-18 after Opus 4.8 #728 agent died at ~105k tokens with 151 lines of uncommitted `trustMagnitude.py` edits — recoverable from the worktree, but should not have happened):

1. **Mandate intermediate commits.** Every dispatch prompt that touches multiple modules or adds 100+ lines must specify split commits at natural breakpoints: e.g. "commit + push regression fix BEFORE adding new verb"; "commit + push schema BEFORE wiring validator." The worktree should always be a useful resume point on cutoff.
2. **Push early, push often.** Phrase as: "after each commit, run `git push origin <branch>` immediately. Do not batch pushes." A pushed commit survives cutoff; a local commit dies with the worktree.
3. **Don't gate the commit on the test run.** Commit + push first, then run tests. If tests fail, the next commit fixes them. The committed broken state is recoverable; the lost work is not.
4. **Worktree isolation: `isolation: "worktree"`.** Even on cutoff, the worktree persists with uncommitted edits visible — recoverable. Without isolation, the parent session's working tree gets mid-edit garbage and you have to reset.
5. **Token budget hint in the prompt.** For Opus dispatches expecting >80k subagent tokens, tell the agent: "if you hit 80k tokens before the verb is complete, commit what you have, push, and report progress — do not try to finish in one shot." Sonnet's lower per-token cost makes the same explicit budget less urgent but the discipline still applies.
6. **Report SHA + state at every milestone.** Dispatch prompts should require: "Report each commit's SHA + push status as you go, not just at the end." Then if the agent dies, the orchestrator knows EXACTLY what's on the remote vs the worktree.
7. **Re-dispatch path on cutoff.** When an agent dies mid-edit:
    - Check `git worktree list` for the agent's worktree (path matches `agent-<id>`).
    - `cd` into it, `git status` + `git diff --stat` — uncommitted work is salvageable.
    - Re-dispatch a continuation agent with `cwd` pinned to that worktree (or use `EnterWorktree path:` to take it over) and prompt "the previous agent died at <task>; the worktree has these uncommitted edits — finish, commit, push." Avoid restarting from scratch when 80% is done in the worktree.

When in doubt, prefer **2 small PRs** over 1 large dispatched PR. Each merged PR is a permanent lock-in; each dispatched megaprompt is a single point of failure.

### Additional hazards observed (2026-06-18, I3 agent)

8. **`sys.path` for imports from `src/`.** `src/gaia_cli/` modules import each other without the `src.` prefix (e.g. `from gaia_cli.evidence import ...`). Any script in `scripts/` that imports from `src/gaia_cli/` must do `sys.path.insert(0, str(Path(__file__).parent.parent / "src"))` — inserting `REPO_ROOT/src`, not `REPO_ROOT`. Pre-bake this in every dispatch prompt that writes a `scripts/` file.

9. **`generateNamedIndex.py` side-effect artifacts.** Running `generateNamedIndex.py` regenerates `docs/css/tokens.css`, `docs/graph/gaia.json`, `docs/graph/named/index.json`, and `registry/gaia.json` with timestamp-only diffs. Revert these from the staging area (`git restore docs/css/tokens.css docs/graph/gaia.json registry/gaia.json`) BEFORE committing the migration output — only `registry/named-skills.json` and `docs/graph/named/index.json` belong in the migration commit scope. **`docs/graph/named/index.json` IS required** (CI checks it); the others are revert noise.

10. **`git stash` during test runs on large working trees.** Stashing 200+ file changes and popping may silently restore only a subset on first pop (observed: 235 named-skill changes → 3 files restored). Always verify `git stash list` and run `git status` after pop. If the working tree is incomplete, run `git stash pop` again or `git checkout -- .` to restore. Better alternative: run tests on a separate worktree checkout (or use `--dry-run` flag) instead of stashing mid-work.

11. **Stale local branches.** A prior session may have left a local branch at `main` HEAD that CI will correctly accept as a no-op base. Safe to reuse, but check `git log --oneline -3` vs `main` first to ensure the branch isn't carrying stale commits.

### Timeline events — NEVER fabricate by hand

**Do NOT write timeline entries via direct frontmatter edit, ever.** This applies even when there is a known CLI gap, even for a "big bang" migration, even with a `(direct edit — CLI gap)` marker. A fabricated entry with a hardcoded timestamp is a lie in the audit log.

**Correct action when `gaia dev timeline` cannot write to a named skill file:**
1. Leave the timeline entry out of the PR entirely.
2. Note the CLI gap explicitly in the PR description.
3. Open a follow-up issue for the CLI fix.

A missing entry is auditable. A synthetic entry is not. **Do NOT include "fallback: direct frontmatter edit" language in any dispatch prompt for timeline operations.**

### EPIC branching model (default for all multi-issue sprints)

Big EPICs (like #855 Sprint B) use a **long-lived integration branch** (`dev/<sprint-name>`) that collects all feature work before merging to `main` at sprint end. This is the default for any EPIC with 3+ sub-issues.

```
main
└── dev/<sprint-name>               ← integration branch (PR → main at sprint close)
    ├── feat/<sprint>/<topic-1>     ← small PR → dev/<sprint-name>
    ├── feat/<sprint>/<topic-2>     ← small PR → dev/<sprint-name>
    └── feat/<sprint>/<topic-N>     ← small PR → dev/<sprint-name>
```

**Rules:**
1. Create `dev/<sprint-name>` off `main` HEAD at sprint start.
2. Each workstream opens a feature branch off the integration branch.
3. Feature branches open PRs targeting the integration branch (never `main` directly).
4. After all workstreams merge + reviewer sign-off, the integration branch opens a single PR → `main`.
5. The integration branch PR carries the EPIC issue number in its body (`Resolves #<epic>`).
6. CI runs on both layers: feature PRs validate their scope; the integration PR validates the aggregate.
7. **Never squash an EPIC integration PR.** Squash merges destroy the child PR commit topology and make post-hoc audits/reverts much harder. EPIC integration PRs must use a merge commit (or, if explicitly requested by Marcus, a rebase that preserves every child commit). Squash commits are absolutely banned for `dev/*` → `main` merges.

This prevents half-shipped features from landing on `main` and keeps the sprint atomic while preserving full audit history.

### Backlog Eradication sprint model (`dev/issue-backlog`)

The issue-backlog eradication sprint is an integration-branch campaign, not a sequence of direct-to-main fixes.

**Branching and ownership:**
1. The orchestrator owns `dev/issue-backlog` and its integration PR to `main`.
2. Every implementable issue gets one feature PR with base `dev/issue-backlog`; keep the feature diff as narrow as possible to minimize conflicts.
3. Founder-owned files (`founder/**`, plus root governance markdown when appropriate) may be committed directly by the orchestrator on `dev/issue-backlog` and pushed immediately.
4. The orchestrator assists merges after human gates and owns merge-strategy judgement: feature PRs can be squash-merged for revertability; the final `dev/*` → `main` integration merge must preserve topology unless Marco explicitly says otherwise.

**Agent routing:**
1. Use `scout` + `planner` on ambiguous, under-specified, stale, cross-cutting, or source-of-truth-conflicted issues before dispatching implementation.
2. Use worker tiers by difficulty: `worker` for light/surgical work, `worker-terra` for medium work, `worker-sol` for heavy backend/CLI/refactor work, and `worker-opus`/`worker-sonnet` for design work.
3. Nested agent use is allowed and encouraged: workers may spawn extra scouts/reviewers when the issue needs local exploration, provided they still push after meaningful progress.
4. Prefer chains for scout → planner → worker → reviewer on risky issues; use parallel scouts for independent evidence/curation questions.

**Human Gates:**
1. Use batch-level Human Gates for normal backlog work, not one founder approval per issue.
2. Design work is the exception: it is strictly human-gated, uses `/design-iteration` for approval-gated fix recovery, and should be batched last unless urgent.
3. CLI visual/output changes are also human-gated: anything that changes visible terminal output, cards, prompts, formatting, colors, symbols, truncation, or command copy must be batched for founder review with before/after CLI output. Pure scanner/parser/test/docs behavior that does not alter rendered CLI output can proceed on normal HG-2 review.
4. Any required regeneration commit (docs graph/API/profile/badge artifacts, generated registry projections, or other Class S outputs) requires an explicit human gate before landing.
5. Prepend a memory snapshot to `founder/MEMORY.md` at every Human Gate and whenever Marco invokes memory snapshot; these snapshot commits land directly on the active `dev/*` integration branch.

**Scope and CI posture:**
1. Skip issues already covered by EPIC #1336 unless Marco explicitly pulls them into this sprint.
2. Skip `docs/en/**` updates for this sprint except unavoidable nav/entrypoint/cache-bust changes needed by another accepted change.
3. Branch-scope failures are usually read as signal, not an automatic blocker, during this sprint; reviewers should use them to identify missed or leaked files. Apply/route scope exceptions deliberately rather than reshaping the whole sprint around the guard.
4. All CLI invocations in dispatches should use the checkout's Python entrypoint/module form (for example `PYTHONPATH=src python -m gaia_cli ...` where applicable) rather than a globally installed/pip `gaia`, so agents test the code under review.

**Pause-and-ask triggers:**
Pause and ask Marco before implementation when an issue has no obvious solution, conflicts with source-of-truth docs, needs product/design judgement, changes visible CLI output, affects evidence/rank calibration, requires destructive git/history operations, touches adjacent repos, or would auto-ingest/auto-publish without a human curation step.

### Release runbook — bundled registry snapshot

`src/gaia_cli/data/registry/gaia.json` and `named-skills.json` are gitignored. The PyPI wheel is built by `.github/workflows/publish-pypi.yml`, which has a "Bundle fresh registry snapshot" step that runs before `python -m build`:

- **Runs on `vX.Y.0` (minor/major):** downloads `gaia-artifacts.tar.gz` from the matching GitHub Release and copies the files into `src/gaia_cli/data/registry/`.
- **Skips on `vX.Y.Z` (patch):** the wheel inherits the snapshot from the previous minor/major.

When dispatching a release agent, remind it:
- `registry/gaia.json` is gitignored — do NOT commit it manually; CI handles it.
- `gaia pull` is the user-facing "get the latest registry" command; it downloads the same `gaia-artifacts.tar.gz` asset.
- If the "Bundle fresh registry snapshot" step fails, the wheel will be built without the bundled data files. Verify by checking the wheel contents (`unzip -l dist/*.whl | grep data/registry`) before publishing.

