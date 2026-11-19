# P1 resumption — roster preflight and base rehearsal

**Status: BLOCKED for acceptance; review and regression in progress.** This is a continuation of [the pushed checkpoint](P1_STATUS_2026-11-20.md), not a new campaign or approval record.

## Source and PRs

- [#2468](https://github.com/gaia-research/gaia-skill-tree/pull/2468): OPEN/DRAFT. Local and remote `dev/upstream-backlog-watcher-2026-11` checked at `e1451f7fc5db2cb149e6bce30eb023c020c6cd8c`; tracked worktree clean before this receipt. No source diff versus repair `3fdd6d7573ce3cec922babba8b3c82eaf952dbd2` (campaign reports are the only subsequent changes).
- [#2469](https://github.com/gaia-research/gaia-skill-tree/pull/2469): OPEN/DRAFT at `6bed0edf324d49e42cd8953351deaccaa733d22f`. Both drafts still target `dev/upstream-backlog-2026-11` at `bfed2d777b76448f6ede5d40e1a834050dff07d0`. No PR, branch, label, variable, workflow, or registry mutation in preflight.

## Founder-authorized revised roster and live preflight

This roster supersedes all historical P1 rosters, but no other founder gate. Pi lead runtime reported `openai/gpt-6.2-sol`, `high`. The installed `@parke.dev/pi-subagent` dry-resolved all four plans; workers probed sequentially in fresh sessions with no tool use, 120-second hard limits, `fallback_models: []`, and `max_retries: 0`. Engineering calls must pin these no-fallback/no-retry overrides (the installed profile defaults otherwise permit retry/fallback). Configured per-session max is four; campaign concurrency across surfaces must also stay at or below four. Worker timeout ceiling remains 7,200,000 ms. No provider settings were changed.

| Role | Resolved route and effort | Verified permissions / live evidence |
|---|---|---|
| L1 Luna, `worker-luna` | `openai/gpt-6-luna`, medium | General, bounded read/bash/edit/write per plan; returned `LUNA_P1_ROUTE_READY` |
| L2 Terra, existing `campaign-terra-pinned` | `openai/gpt-6.1-terra`, high | General, bounded read/bash/edit/write per plan; returned `TERRA_P1_WORKER_ROUTE_READY`. The general `worker-terra` persona maps to the shared provider here, so it is not the L2 route. |
| L3 Sol, `worker-sol` | `openai/gpt-6.2-sol`, medium | General, bounded read/bash/edit/write per plan; returned `SOL_P1_WORKER_ROUTE_READY` |
| Independent Terra, `reviewer-shared` | `openai-codex/gpt-6.1-terra`, high | Central `pi-reviewer` route only, with read/grep/find/ls, no extensions or inherited conversation, 90-second probe. Returned `TERRA_P1_REVIEW_ROUTE_READY` after reading a known heading. Same model family as L2, never the author or implementation session. |

The three worker identities and efforts were observed in their Pi execution events. Only the centralized reviewer was routed via the shared `openai-codex` configuration. No Hydrogen/Opus assignments or model/provider switches. The reviewer wrapper starts one pinned Pi process per invocation and does not select alternate models. Central probe success is confirmation of invocation and a live read; it is not a code verdict.

### Token usage for dispatch probes only

UTC timestamps from the execution records are on **2026-11-19**; table is not a session or campaign total. Counts are measured provider usage fields in the child event streams, not estimates.

| Route | Input | Output | Total |
|---|---:|---:|---:|
| `openai/gpt-6-luna` | 1,822 | 10 | 1,832 |
| `openai/gpt-6.1-terra` | 1,800 | 12 | 1,812 |
| `openai/gpt-6.2-sol` (worker probe only) | 1,822 | 11 | 1,833 |
| `openai-codex/gpt-6.1-terra` (central probe) | not retained | not retained | not retained |

The central wrapper runs Pi with `--no-session`; its receipt does not expose token counts. No reviewer estimate or token/cost extrapolation is supplied.

## Pinned main reconciliation rehearsal (no merge)

- Main `80fb535bb7d77840fe9a52be558e6127e03f3850` includes `81fa6f1def98a0300afe513fc3addba17a4da208` (local `integration/tstack-suite-2472` tip, second parent of pinned main). Its remote branch ref was not advertised. The PR base `bfed2d777b76448f6ede5d40e1a834050dff07d0` is **not** in this main tip. Feature and main share merge base `9b4d9b98043140188f00b14d0ac8fa6bc02491b7`.
- `git merge-tree --write-tree --name-only --messages <feature> <main>` in a separate detached worktree exited 0. Preview tree `867521d557a495cfdc574f294d3b0675db4ecc47`. No actual merge, ref change, branch rewrite, index change, or push. Tree metadata comparison found all 67 feature-only and 220 main-only path/mode/object changes preserved exactly, with zero one-sided preservation mismatches.
- Four paths changed on both sides: `src/gaia_cli/commands/dev/__init__.py` (both evidence CLI and upstream sync flag retained) and the three `namedSkill.schema.json` mirrors in `docs/schema/`, `registry/schema/`, and `src/gaia_cli/data/registry/schema/` (same blob `956dfac5ffaad1bce3c3cddf4f0daa4ebac71faf` in the preview; inspected diff preserves both sets of prior changes). This is a rehearsal of inherited changes, not new trust/schema authority. No claim of semantic validation, reconciled runtime, or final reviewer PASS yet.

## Running gates and resumption

Local evidence directory: `$TMPDIR/upstream-backlog-2026-11/p1-resume-e1451f7fc/` (not published; cached issue data stays separate and is not included). Both running gates read the unchanged source at `e1451f7fc` in separate detached worktrees.

- `bd42bee0c`: central Terra focused re-review of the four findings at source-equivalent repair `3fdd6d757`, with `review-result.json` and terminal receipt. This is not the final reconciled-source review.
- `b04efdcf0`: non-author `pytest` on `tests/upstream_watcher`, `tests/test_upstream_approve_workflow.py`, `tests/test_repository_envelope_workflow.py`, `tests/test_dev_upstream_verbs.py`, `tests/test_named_persistence_contract.py`, `tests/test_upstream_persistence_contract.py`, with the offline #1833 fixture enabled via `P1_LEGACY_CACHE`; separate `tests/upstream_watcher/parity_2283.py` and PR-base `git diff --check`. Require the terminal `P1_NON_AUTHOR_COMPLETE` marker and actual outcomes. No result claimed yet.

Collect review, regression and parity receipts before assigning any repair (honor no more than two routine fix rounds per PR). Verify the final source including reconciliation with an independent central Terra verdict and rerun applicable tests before the one conditional ordinary `apply=false` invocation. It remains unconsumed. Separate founder-only schedule/write activation, #1833 migration and all held/frozen data, P2–P7 and merge gates remain unchanged.
