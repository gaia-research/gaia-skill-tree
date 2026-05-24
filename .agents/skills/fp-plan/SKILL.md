---
name: fp-plan
description: >-
  Phase 2 of the feature-pipeline suite. Reads issues from state, creates a
  feature branch and draft PR, spawns HEAVIER to produce a numbered
  implementation plan, presents the plan for user approval, then writes the
  approved plan to state. Does NOT implement — that is /fp-implement. Use after
  /fp-explore has filed at least one issue and printed the M1 stop hook.
version: 3.0.0
---

# fp-plan  (Phase 2 — Plan & Draft PR)

Read issues, create branch + draft PR, get a HEAVIER plan, wait for approval.
One bounded turn. Implementation is a separate skill (/fp-implement).

## Setup

```bash
STATE=".agents/skills/feature-pipeline/scripts/state.sh"
feature=$($STATE get feature)
issues=$($STATE get issueNumbers)   # JSON array e.g. [12,13,14]
```

Verify `phase == 2` and `issueNumbers` is non-empty before proceeding.

## Step 1 — Problem Statement

Read each issue body via:

```bash
gh issue view <N> --json title,body
```

Write a single paragraph Problem Statement: what is broken, why it matters,
what a correct fix should achieve.

## Step 2 — Create branch and draft PR

```bash
# Slugify the feature name
slug=$(echo "$feature" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | cut -c1-40)
branch="fix/${slug}-findings"

git checkout -b "$branch"
git push -u origin "$branch"

$STATE set branch "$branch"
```

Open draft PR using GitHub MCP (`mcp__github__create_pull_request`):
- **title**: `fix({{feature}}): address exploration findings`
- **labels**: `draft`, `needs-plan`
- **draft**: true
- **body**:

```markdown
## Problem Statement
<from Step 1>

## Related issues
- Closes #N
- Closes #M

## Plan
_To be filled after approval._
```

Write PR info to state:

```bash
$STATE set prNumber <N>
$STATE set prUrl    "<url>"
```

## Step 3 — HEAVIER plan

Spawn HEAVIER with:
- The issue titles and bodies
- The PR URL
- Excerpts from the source files relevant to `{{feature}}`

HEAVIER brief:

> Produce a numbered implementation plan for the issues listed.
> Format each step as:
> `N. <file/area>  —  <change>  —  <rationale>  [⚠ breaking | ⚠ test-only | ⚠ schema]`
> Keep the plan to 3–8 steps. Be specific about file paths and function names.

**Present the plan to the user verbatim. Do not proceed until the user
explicitly types 'approve', 'continue', or provides edits.**

Accept corrections inline. After approval:

1. Update the PR body `## Plan` section with the final plan text.
2. Write the approved plan to state:
   ```bash
   $STATE set planApproved true
   $STATE set phase 3
   ```
   (Phase advances to 3 to indicate "ready for implement", but /fp-implement
   reads `planApproved == true` and `phase == 3`.)

Then print M2-plan stop hook and end your turn:

```
╔══ STOP HOOK M2-plan ═════════════════════════════════════════════════════════╗
║  Plan approved — branch: <branch>  PR: #<N>                                 ║
║  Run /fp-implement to commit the plan.                                       ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

## Constraints

- Do not implement any code. /fp-implement does that.
- Do not advance past plan approval without explicit user sign-off.
- If HEAVIER spawning fails: write a Handover to `.fp-handover.md` with the
  issue bodies and source excerpts; end your turn. Do not plan yourself.
