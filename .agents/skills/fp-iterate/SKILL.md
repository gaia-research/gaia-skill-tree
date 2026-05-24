---
name: fp-iterate
description: >-
  Phase 4 of the feature-pipeline suite. Addresses outstanding review items
  from the Phase 3 comment, then runs a bounded CI poll (max 10 rounds,
  30s apart). If CI is still pending after the poll, exits cleanly — re-invoke
  to retry. If CI fails, prints the failing check and exits. Use after /fp-review
  has posted the sandbox review comment and printed the M3 stop hook.
version: 3.0.0
---

# fp-iterate  (Phase 4 — Address Review & Watch CI)

Address `[ ] issues` from the review comment, push fixes, poll CI. Bounded:
always exits — either green, still-pending (retry), or failed (diagnose).

## Setup

```bash
STATE=".agents/skills/feature-pipeline/scripts/state.sh"
branch=$($STATE get branch)
pr=$($STATE get prNumber)
reviewUrl=$($STATE get reviewCommentUrl)
ciRound=$($STATE get ciRound)
```

Checkout the branch:

```bash
git checkout "$branch"
```

## Step 1 — Address review items

Read the review comment:

```bash
gh api "$reviewUrl" --jq '.body'
```

For each `- [ ] <description>` item in "Issues found":
1. Fix the issue.
2. Commit: `fix(<scope>): <description> (per review)`
3. Push.
4. Print: `  ✓ Fixed: <description>`

If a review item is ambiguous or requires architectural input, leave it as
`[ ]` and add a note. Do not guess — surface it in the stop hook message.

## Step 2 — Bounded CI poll

```bash
.agents/skills/fp-iterate/scripts/ci-poll.sh "$pr" --max 10 --interval 30
poll_exit=$?
```

Update round counter:

```bash
$STATE set ciRound $(( ciRound + 1 ))
```

**Exit code 0 — CI green:**

```bash
$STATE set ciStatus "green"
$STATE set phase 6
```

Remove `in-progress` label, add `ready-for-review` via
`mcp__github__update_pull_request`. Remove draft status.

Print M4 stop hook and end your turn:

```
╔══ STOP HOOK M4 ══════════════════════════════════════════════════════════════╗
║  CI green ✅  PR #<N> ready for review                                       ║
║  Run /fp-drift for the final drift check and summary.                        ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

**Exit code 1 — still pending after 10 rounds:**

```bash
$STATE set ciStatus "pending"
```

Print and end your turn (do NOT loop):

```
⏱ CI still pending after round <ciRound>. Re-run /fp-iterate to check again.
```

**Exit code 2 — CI failed:**

```bash
$STATE set ciStatus "failed"
```

Read the failing check name from ci-poll output, fetch its logs:

```bash
gh run view --log-failed 2>/dev/null | head -60
```

Print the diagnosis (root cause, file, line if identifiable) and end your turn.
Do not push a blind fix — wait for the user to confirm the approach.

## Constraints

- `ci-poll.sh` is the only CI mechanism. Do not write a manual sleep loop.
- Re-invoking `/fp-iterate` is the intended retry path for exit code 1.
- If the same check fails 3× across consecutive `/fp-iterate` runs
  (`ciRound >= 3` and `ciStatus == "failed"`), escalate to the user with
  the full log excerpt before attempting any fix.
- No force-pushes.
