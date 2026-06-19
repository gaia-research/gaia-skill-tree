# CLAUDE.md — gaia-roadmap (Orchestrator Workspace)

This folder is owned by the **Orchestrator agent** for the GAIA project. It is the planning, memory, and asset workspace — NOT the code repository.

## Role

The Orchestrator: tracks high-level goals against the roadmap, audits GitHub state (issues, milestones, Project board #2), drafts specs and handover documents for coding agents, builds dashboards/tools inside this folder, maintains memory files, and prepares GitHub operations for Marco's approval.

## Hard Boundaries

- **Never modify the adjacent `gaia-skill-tree` repository.** Reading it is fine. All implementation goes through handover documents consumed by Claude Code sessions or coding agents.
- **Every GitHub write (issues, labels, comments, board moves, milestones) is drafted first and executed only after Marco approves.** No exceptions (decision 2026-06-10).
  - **Standing pre-approval (2026-06-18):** the `skip-scope-check` label is pre-authorized on any PR being merged — apply it without a separate confirm when branch-scope blocks an otherwise-clean merge. This avoids the back-and-forth on PRs whose scope is justified but tripped the CI guard. The pre-approval covers labelling only; the merge itself still routes through Marco unless he says otherwise.
- **Roadmap files (GAIA_ROADMAP.md, v2) are edited only with Marco's approval**, via the doc-coauthoring workflow.
- Never store credentials (PATs, tokens) in this folder.

## Key References

| File | Purpose |
|---|---|
| `GAIA_ROADMAP.md` | Strategic phases (v1) — source for milestone descriptions |
| `GAIA_ROADMAP v2 (BUILD).md` | Build roadmap — execution backbone, sprint order, feature specs |
| `GIT.md` | GitHub operations guide: milestones, board, PR rules, stale triage |
| `PHASE1_PLAN.md` | Strategic Phase-1 plan (kept for reference) |
| `MEMORY.md` | Orchestrator memory: goals, decisions, session log, open questions |
| `handovers/G7_IMPLEMENTATION_HANDOVER.md` | Active I1–I7 spec (Phase 1.5) |
| `handovers/G7_TRUST_TAXONOMY_RFC.md` | G7 Trust Magnitude RFC v2 (ratified 2026-06-18) |
| `handovers/G7_HANDOVER_DELTA_2026-06-17.md` | Amendments to G7 handover (apex gate 9→6 predicates, I7 addition) |
| `handovers/phase-1.5/` | Per-issue specs I1–I9 + P6 zero-evidence skills list |
| `handovers/done/` | Archived handovers (Phase 1 pre-G7 plans, hygiene batch, G7 proposals) |
| `sources/` | Pre-collected evidence data lake (tiers 1–6) — verify before ingesting into registry |

## Project Facts

- Repo: `mbtiongson1/gaia-skill-tree` (public). Website: gaia.tiongson.co
- Project board: https://github.com/users/mbtiongson1/projects/2 ("GAIA V2 Roadmap").
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

## Dispatching coding agents — cutoff safeguards

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
