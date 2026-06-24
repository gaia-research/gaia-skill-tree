---
name: fp-review
description: >-
  Phase 3 of the feature-pipeline suite. Spawns HEAVIER in a worktree sandbox
  to run RED/GREEN tests on the PR diff and post a structured review comment.
  Reads branch and PR number from state. Use after /fp-implement has pushed all
  commits and printed the M2 stop hook.
version: 3.0.0
---

# fp-review  (Phase 3 — Sandbox Review)

Spawn HEAVIER in an isolated worktree, run tests, post a review comment.
One bounded turn.

## Setup

```bash
STATE=".agents/skills/feature-pipeline/scripts/state.sh"
branch=$($STATE get branch)
pr=$($STATE get prNumber)
```

Verify `phase == 4` (set by /fp-implement).

## HEAVIER brief

Spawn HEAVIER in `isolation: worktree` on `$branch`.

> You are reviewing PR #$pr on branch $branch.
>
> 1. Read the full diff: `git diff origin/main...HEAD`
> 2. For each changed public surface (function, CLI flag, schema field):
>    a. Write a RED test — it must FAIL before the fix. Verify by temporarily
>       reverting that change, running the test, then re-applying.
>    b. Write a GREEN test — it must PASS with the fix in place.
> 3. For schema-touching commits: run `gaia validate`
> 4. For doc-touching commits: run `gaia docs build --check`
> 5. Post this exact comment structure to the PR via `gh pr comment`:
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

After HEAVIER posts the comment, read the comment URL from its output.

## Phase completion

```bash
$STATE set reviewCommentUrl "<url>"
$STATE set phase 5
```

Print M3 stop hook and end your turn:

```
╔══ STOP HOOK M3 ══════════════════════════════════════════════════════════════╗
║  Sandbox review posted — PR #<N>                                             ║
║  Review the comment, then run /fp-iterate to address findings + watch CI.   ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

## Constraints

- If HEAVIER spawning fails: write `.fp-handover.md` with diff URL and branch
  name; end your turn. Do not review the PR yourself.
- Do not push any commits. This phase is read + comment only.
