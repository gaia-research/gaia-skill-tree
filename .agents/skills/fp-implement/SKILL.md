---
name: fp-implement
description: >-
  Phase 2d of the feature-pipeline suite. Reads the approved implementation
  plan from state and commits it step by step. Only runs when planApproved is
  true. Use after /fp-plan has received user approval and printed the M2-plan
  stop hook. Each commit is atomic; pushes after every step.
version: 3.0.0
---

# fp-implement  (Phase 2d — Implementation)

Commit the approved plan one step at a time. Bounded: finishes or hits an
obstacle, updates state, ends the turn.

## Setup

```bash
STATE=".agents/skills/feature-pipeline/scripts/state.sh"
```

Verify preconditions before touching any code:

```bash
approved=$($STATE get planApproved)   # must be "true"
branch=$($STATE get branch)
pr=$($STATE get prNumber)
```

If `planApproved != true`, print:
```
⚠ Plan not yet approved. Run /fp-plan first.
```
and end the turn.

Checkout the branch:

```bash
git checkout "$branch"
```

## Implementation loop

Read the plan from the PR body (`gh pr view "$pr" --json body`), or ask the
user to paste it.

For each numbered plan step:

1. Implement the change in the relevant file(s).
2. Commit atomically:
   ```bash
   git add -p   # stage only the relevant hunk
   git commit -m "<type>(<scope>): <description>"
   git push
   ```
3. Print one line: `  ✓ Step N committed: <commit hash short>`

If a step raises an unexpected obstacle (import error, schema conflict, etc.):
- Leave a `TODO` comment at the exact location.
- Commit the partial work: `wip(<scope>): partial step N — <obstacle summary>`.
- Update state:
  ```bash
  $STATE set ciStatus "blocked"
  ```
- Print what the obstacle is and end your turn. Do not attempt the next step.

## Phase completion (all steps done)

```bash
$STATE set phase 4   # jump to review-ready
```

Update PR labels via `mcp__github__update_pull_request`:
- Remove `needs-plan`
- Add `in-progress`

Print M2 stop hook and end your turn:

```
╔══ STOP HOOK M2 ══════════════════════════════════════════════════════════════╗
║  Implementation complete — <N> commits pushed to <branch>                    ║
║  Run /fp-review to start sandbox review.                                     ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

## Constraints

- One commit per plan step — no squashing.
- Never commit secrets, generated registry artifacts, or unrelated files.
- `gaia dev add`/`gaia dev merge`/`gaia dev split` for any registry mutations —
  never hand-edit `registry/nodes/`.
- No force-pushes.
