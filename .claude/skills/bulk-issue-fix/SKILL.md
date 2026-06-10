---
name: bulk-issue-fix
description: >-
  Dynamic-workflow harness that takes a triaged GitHub issue list (priority + category +
  one-liner per issue) and lands every mechanical fix in a single PR while leaving RFC /
  feature-request issues with thoughtful trade-off comments deferred to the next batch.
  Use when the user pastes a triage report and says "bulk fix them in one PR", "/loop until
  finished with issues", "land everything that's mechanical", "work through the open issues",
  or otherwise asks to clear a queue of triaged issues end-to-end. Composes its own run plan
  per batch (which issues are mechanical, which are already-fixed, which are RFCs), fans out
  investigation subagents in parallel, applies fixes sequentially in the working tree, posts
  RFC comments via `gh`, and produces a deferred-batch summary file. Not for one-off bug
  fixes — route those to direct work. Not for un-triaged issue lists — ask for triage first
  or route to a triage skill.
version: 1.0.0
argument-hint: "<triage-report-or-paste>"
---

# bulk-issue-fix

A **dynamic workflow** for clearing a triaged GitHub-issue queue in one PR. Modeled on the
same shape as `/gaia-curate-dynamic` (runtime-composed plan, parallel sub-agent fan-out,
sequential application, single human gate) but specialised for issue triage → bulk fix.

> The orchestrator reads the triage report, *splits* the issues into mechanical / already-
> fixed / RFC buckets, dispatches investigation subagents in parallel for the mechanical
> ones, applies the resulting diffs sequentially in a single working tree, posts thoughtful
> deferral comments on the RFCs, and ships one PR. RFCs are *not* fixed in this batch —
> they're surfaced for the user to triage next week.

This skill replaces the ad-hoc improvisation that happens when a `/loop` task is "fix all
the issues". It encodes the moves that work and refuses the ones that don't (parallel
edits to overlapping files, worktree isolation when generated artifacts collide, one giant
commit, silent skipping of issues).

## When to invoke

Trigger on any of:

- A triage report paste (numbered issue list with priority/category/title) followed by
  "fix them" / "bulk-fix" / "land them in one PR".
- `/loop until finished with issues` plus a triage report in the same turn.
- "Work through these issues" / "clear the queue" / "close the mechanical ones".
- Explicit `/bulk-issue-fix`.

Do **not** trigger for:
- A single bug fix request → just fix it directly.
- An untriaged "look at the open issues" request → run a triage skill first, or ask the
  user to paste their triage.
- Issues that need product decisions the agent can't make → defer + comment, never guess.

## Inputs

Read from the user message (or ask, exactly once, for whatever's missing):

| Input | Description | Default |
|---|---|---|
| `triage` | The triage report — issues with #, priority, category, title | required |
| `branch` | Branch to commit on. For cross-cutting bulk fixes (schema + CLI + docs + frontend together), use `dev/<slug>` — scoped prefixes like `cli/`, `schema/`, `review/meta/` are blocked by `branch-scope.yml` when a single PR crosses scopes. Only use a scoped prefix if the whole batch fits one scope. | current branch if not `main`/`master` and matches the scope rule above; else ask |
| `repo` | `owner/repo` for `gh` calls | infer from `git remote get-url origin` |
| `mode` | `safe` (investigate first, ask before destructive moves) or `auto` (proceed through every gate that the orchestrator's confidence is ≥0.85) | `safe` |

Never ask more than once. If the user said "go ahead and apply fixes manually" or similar
in their kickoff, treat that as standing authorisation for `mode: auto` and don't gate
on individual fix application — only on the final commit/push/PR-open.

## Core principles

1. **Bucket first, fan out second.** Before any subagent dispatch, partition every issue
   into one of four buckets. The bucket determines the subagent shape; getting this wrong
   wastes the most context.

   | Bucket | Trigger | What happens |
   |---|---|---|
   | **mechanical** | Bug, schema cleanup, missing data, doc drift, CI flag, evidence/body backfill | Investigation subagent → diff → orchestrator applies |
   | **already-fixed** | The fix is on `main` (or the working tree); issue just needs closing | Verify on disk, then `gh issue close` with a comment pointing at the commit/PR |
   | **rfc** | "RFC", "exploration", "needs-triage", multiple-valid-approaches, badge architecture, default-flipping, naming debates | One-shot comment subagent that writes a thoughtful trade-off / "better way" comment; orchestrator posts via `gh issue comment`; issue stays open and lands in the deferred-batch summary |
   | **out-of-scope** | The triage rated it Low and the issue is genuinely speculative or duplicates a Medium/High in the same batch | Add to deferred-batch summary, no comment needed |

   Print the bucket assignment up-front as a markdown table. The user can correct it in
   one message before fan-out begins.

2. **Parallel for investigation, sequential for application.** Investigation subagents
   read independently and can run concurrently — fan them out in a single turn, one per
   mechanical issue. **Application is single-threaded in the orchestrator's working tree**
   so generated artifacts (`gaia.json`, `gaia.gexf`, regenerated docs, schema mirrors)
   don't collide and so a follow-up fix can read the file the previous fix just wrote.
   Worktree isolation is wrong for this skill — the issues share a registry.

3. **Subagents return diffs, not edits.** Investigation subagents are read-only (use
   `Explore`-shaped agents). They report exact file paths, line numbers, root cause, and
   the literal old → new code for each change. The orchestrator applies them. This keeps
   the diff visible in one context and prevents two subagents from rewriting the same
   file in parallel.

4. **Programmatic-First for registry mutations.** Per `CLAUDE.md`, every meta shift
   (skills added/merged/split, evidence appended, timeline events) goes through
   `gaia dev <verb>`, gated by `GAIA_OPERATOR_OVERRIDE=1` for non-Verifier sessions.
   Direct JSON edits to `registry/nodes/` are forbidden. The exception is **bulk
   migrations** (e.g. stripping a deprecated field across 290 files) — those go via a
   one-off Python script that `json.loads`-verifies every file it touches and is
   committed alongside the change for audit.

5. **One PR, logical commits.** All changes land on the active branch as 2–4 logically
   grouped commits (e.g. `[meta] strip rarity axis (#356)`, `[design] fix flowchart
   plaque flicker (#346)`, `[meta] backfill evidence + bodies (#600 #554)`,
   `[infra] note OIDC requirement (#467)`). The PR body lists every closed issue with
   `Fixes #N`, the migration script used (if any), CLI gaps that forced direct edits,
   and links to the deferred-batch summary.

6. **Verify before pushing.** After all fixes apply, run the full local CI parity:
   `gaia validate`, `pytest`, `gaia docs build --check`, `gaia docs build` if drift,
   and the project's specific guard greps. Zero hits is the bar. If any fail, surface
   the failure and stop — never push red.

7. **RFC comments earn the deferral.** A one-line "deferred to next batch" is a waste
   of the RFC author's time. Each RFC comment must include: (a) the trade-offs as the
   agent sees them, (b) at least one concrete repercussion of the obvious approach,
   (c) a "better way" sketch *if one exists* — otherwise an explicit "I don't see a
   cleaner alternative; deferring is right". Sign with a `<!-- bulk-issue-fix:rfc -->`
   marker so re-runs don't double-comment.

## Stage 0 — Plan synthesis (orchestrator, runtime-composed)

The orchestrator does this itself, before any subagent dispatch:

1. Parse the triage report into `{number, priority, category, title}` per issue.
2. Read each issue's body via `gh issue view <n>` (or the GitHub MCP) for any issue
   the orchestrator can't bucket from the triage line alone. Cap at the issues actually
   needed — don't pull all 28 if 6 are obvious mechanical bugs and 16 are obvious RFCs.
3. **Verify already-fixed claims**: for any issue suspected to be on main (e.g. a
   triage line says "investigate CI bypass" but the linked PR is merged), check the
   filesystem (`ls`/`grep`) before bucketing. The transcript that birthed this skill
   had #499 and #506 both in this state.
4. Write the bucket table and print it. Stop and ask once if `mode: safe`. If the user
   stays silent, proceed.
5. Estimate fan-out: one investigation subagent per mechanical issue; one comment
   subagent per RFC. If >12 of either, batch in groups of 6–8 to keep orchestrator
   context manageable.

Pin a tiny ledger to `generated-output/bulk-issue-fix-ledger.json` (gitignored) so a
long sweep can resume after `/clear`. Ledger fields: `bucket`, `findings[]`,
`applied[]`, `commented[]`, `deferred[]`, `prUrl`. Atomic writes after each stage.

## Stage 1 — Parallel investigation (mechanical bucket)

Dispatch one investigation subagent per mechanical issue **in a single turn**. Each
subagent uses the `Explore` agent type (read-only) and gets:

> In repo `{{repo_path}}`, investigate issue #{{n}}: `{{title}}`.
> Issue body: `{{body}}`.
>
> Report concrete findings: file paths with line numbers, root cause, and the literal
> diff (old code → new code) for each proposed change. Do NOT make any edits.
>
> If the fix is "delete a field across the registry data", just identify the patterns
> and counts — the orchestrator will do the bulk migration via a one-off Python script.
>
> If the issue is already fixed on disk, say so and quote the relevant lines.

For schema/data sweeps (e.g. "remove deprecated axis"), the investigation subagent
should also produce: a CI guard regex (to prevent regression) and a checklist of
generated mirrors that need rebuilding.

Subagents write their findings into `findings[<issue_n>]` in the ledger.

## Stage 2 — Sequential application (orchestrator)

Apply findings in **dependency order**, not issue-number order:

1. **Schema/data first.** A field removal must precede any code change that reads it,
   or `gaia validate` will fail mid-sequence.
2. **Bulk migrations via committable Python script.** For sweeps touching 50+ files,
   write the migration to `/tmp/<task>.py` (or `scripts/migrations/<dated>.py` if the
   user wants it kept), run it, and verify with the script's own re-grep before moving
   on. The script is committed in the same commit as the data change so reviewers can
   reason about what ran.
3. **Code edits second.** CLI/scripts/frontend/MCP package — order doesn't matter
   among these but each needs the schema migration done.
4. **Generated mirrors third.** Run `gaia docs build` (and any project-specific
   regenerator) so the gexf/json mirrors clear out the deprecated field.
5. **Backfills last.** Per-row mutations (evidence, bodies) come after the structural
   changes so they land against a clean tree. Use `gaia dev evidence` (programmatic)
   for evidence; direct markdown edits for bodies (no CLI verb exists yet — note this
   gap in the PR body per `CLAUDE.md`'s CLI-gap policy).

After each fix:
- Append `{issue, files_touched, summary}` to `applied[]` in the ledger.
- If `gaia validate` lives in the repo, run it; stop on red and surface the error.

## Stage 3 — Parallel RFC comments

Dispatch one comment subagent per RFC issue in a single turn. Brief (Sonnet-class —
these need judgment, not pattern-matching):

> Read issue #{{n}} fully. Compose a GitHub comment that:
> 1. Acknowledges the proposal in one sentence — no preamble.
> 2. Names the trade-offs as you see them (concrete, not vague).
> 3. Names at least one repercussion of the obvious approach.
> 4. Sketches a "better way" if you see one, OR explicitly says you don't and explains
>    why deferring is right.
> 5. Ends with "Deferring to next batch — see triage summary [link will be added]."
>
> End the comment with `<!-- bulk-issue-fix:rfc -->`. Return ONLY the comment body.

Orchestrator posts each comment via `gh issue comment <n> --body-file <tmp>`. Skip
posting if the marker already exists in a prior comment (idempotent re-runs).

## Stage 4 — Already-fixed closures

For each issue in the already-fixed bucket:
1. Verify the fix one more time on disk.
2. Comment with the closing commit SHA and PR number.
3. `gh issue close <n>` (only if `mode: auto` or the user said "close them").

## Stage 5 — Deferred-batch summary

Write `feature-pipeline-deferred-<YYYY-MM-DD>.md` (or whatever the project's pipeline
file convention is — check for `feature-pipeline-*.md` in the repo root) with:

- One section per RFC, one paragraph each: the proposal, the trade-off snapshot from
  the comment, and a one-line "fix path" the next batch should consider.
- One section listing the closed issues and the commit that closed them.
- One section listing the mechanical fixes shipped in this PR with `Fixes #N` lines
  ready to copy into the PR body.

This file is the handoff for the user's next triage session. It is committed in the PR.

## Stage 6 — Local verification

Run, in order, halting on first failure:

```bash
.venv/bin/gaia validate            # zero warnings (not just zero errors)
.venv/bin/pytest                   # green
cd packages/mcp && npx tsc --noEmit && npm test && cd ../..   # if MCP touched
.venv/bin/gaia docs build --check  # no drift
# project-specific guard greps (e.g. Guard B from docs-cohesion.yml)
```

Surface every failure with the exact command and the last 30 lines of output. Do not
push past a red light.

## Stage 7 — Commit, push, PR

1. Stage and commit in 2–4 logical groups (one commit message per group, conventional
   commit prefix matching the project's style — `[meta]`, `[cli]`, `[design]`, `[infra]`
   for Gaia; check `git log --oneline -20` to confirm).
2. `git push -u origin <branch>`. Retry on transient network errors with 2s/4s/8s/16s
   backoff (this is the same pattern `gaia-curate-dynamic` uses).
3. `gh pr create` with title `Bulk fix: <one-line scope>` and body:
   - `Fixes #N` line per closed issue (mechanical + already-fixed).
   - "Deferred to next batch: #N, #N, …" with link to the summary file.
   - Migration script command + verification output.
   - "CLI gaps" section listing any direct edits forced by missing `gaia` verbs.
   - "Verification" section with the exact local-CI command outputs.
4. Run `gh pr checks` once and surface the result. Do not block on green CI — that's
   the user's call.

## Stage 8 — Loop continuation

If invoked under `/loop`:
- After the PR opens, schedule a wakeup with `ScheduleWakeup` for ~20 min to check CI
  status (`gh pr checks`).
- On wakeup, if CI is green and there are no review comments, end the loop with a
  final summary message.
- If CI is red, investigate (failing job logs via `gh run view <id> --log-failed`)
  and apply a fix-up commit. Cap at 3 fix-up rounds before stopping and asking.
- If new issues have been triaged into the queue mid-sweep, do NOT pick them up —
  they belong to the next batch. Surface them in the final report.

## Failure modes to refuse

| Anti-pattern | Why it bites | Right move |
|---|---|---|
| Worktree isolation per fix | Generated artifacts (gaia.json, schema mirrors) collide on merge; `gaia validate` fails | Single working tree, sequential application |
| Parallel writes to the same file | Two subagents rewriting `styles.css` lose half the diff | Investigation in parallel, application sequential |
| Treating the Edit tool as available without Read | The harness requires Read first; bulk edits via inline Python `read_text/write_text` only after a script verifies parseability | Either Read each file, or use a verified bulk script |
| Closing RFCs as "deferred" with no comment | Wastes the proposer's time; they reopen | Substantive trade-off comment per Stage 3 |
| Skipping issues silently | The user will discover them next week and lose trust | Bucket explicitly, surface every issue in the bucket table and the summary file |
| Bumping the version automatically | Schema changes need a coordinated release; the user owns timing | Note "needs release" in the PR body, leave manifests untouched |
| Pushing red | "I'll fix it in CI" never happens | Local verify clean before push |
| Re-running and double-commenting on RFCs | Subsequent invocations spam the issue tracker | The `<!-- bulk-issue-fix:rfc -->` marker; skip if present |

## Resume protocol

On every invocation: if `generated-output/bulk-issue-fix-ledger.json` exists and its
`stage` is not `pr-opened`, print a one-line resume summary and continue from the
earliest unfinished stage. Re-run only the subagents whose ledger entries are missing
or marked failed.

## Constraints (strict)

| Rule | Detail |
|---|---|
| **Bucket every issue** | Every issue in the input triage gets exactly one bucket assignment, surfaced before fan-out. |
| **Investigation read-only** | Subagents in Stage 1 must use the `Explore` agent type and emit diffs only. |
| **Sequential application** | All file mutations happen in the orchestrator's turn, in dependency order. |
| **Programmatic-First** | Registry mutations through `gaia dev <verb>`. Bulk migrations via a committed Python script that validates each file. |
| **One PR** | The whole sweep lands as a single review PR with logical commits. |
| **RFC comments substantive** | Every deferred RFC gets a trade-off comment with the marker; never a one-liner. |
| **Local verify clean** | `gaia validate` warnings count as failures for this skill. Push only on green. |
| **Resumable** | Ledger writes after every stage; re-invocation resumes where it stopped. |
| **No version bumps** | The skill never edits `pyproject.toml` / package manifests. It notes the need in the PR body and stops. |

## Invocation

```
/bulk-issue-fix <triage-report>
```

If the triage report is omitted, ask once: "Paste the triage report (issue # +
priority + category + title per row), or point me at a triage skill output file."
Never invent triage — bucketing on guessed metadata is the failure mode this skill
exists to avoid.
