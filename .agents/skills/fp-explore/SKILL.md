---
name: fp-explore
description: >-
  Phase 1 of the feature-pipeline suite. Use this to explore a CLI or feature
  as a developer stress-testing it for the first time, then file GitHub issues
  for every distinct finding. Reads the target feature from .fp-state.json (or
  the argument if provided). Bounded: completes in one agent turn. Use after
  /feature-pipeline init, or invoke standalone with /fp-explore <feature>.
version: 3.0.0
argument-hint: "[<feature>]"
---

# fp-explore  (Phase 1 — Feature Exploration)

Explore `{{feature}}`, file GitHub issues, write issue numbers into state,
print the M1 stop hook. Done in a single bounded turn.

## Setup

Read the target feature:

```bash
# If no argument given, read from state:
feature=$(.agents/skills/feature-pipeline/scripts/state.sh get feature)
# If state missing, ask the user which feature to explore.
```

If `.fp-state.json` doesn't exist yet:

```bash
.agents/skills/feature-pipeline/scripts/state.sh init "<feature>"
```

## Exploration steps

1. **Orient** — read `--help` output, README sections, and any `CONTEXT.md`
   entries for `{{feature}}`. Note the expected behaviour.

2. **Explore** — invoke `{{feature}}` in **five or more** distinct ways:
   - Happy path (normal use)
   - Edge case (empty input, missing file, zero results)
   - Invalid input (bad flag, wrong type)
   - Flag combination (two or more flags together)
   - Piped or composed output (`| jq`, `| head`, etc.)

3. **Scratchpad** — for each issue found, capture:
   - One-line title
   - Exact reproduction commands
   - Expected vs actual behaviour
   - Severity: `low` | `medium` | `high`

4. **Cap at 8 findings** — if you find more, pick the highest-severity ones.
   Quality over quantity.

## Filing issues

For each finding, run:

```bash
gh issue create \
  --title "[{{feature}}] <short description>" \
  --label "exploration,needs-triage" \
  --body "## Steps to reproduce
<commands>

## Expected
<what should happen>

## Actual
<what happens>

## Severity
<low | medium | high>"
```

After each issue is created, append its number to state:

```bash
.agents/skills/feature-pipeline/scripts/state.sh push issueNumbers <N>
```

## Phase completion

Print the severity table:

```
| Issue # | Title | Severity |
|---------|-------|----------|
| #N      | …     | high     |
```

Advance state to Phase 2:

```bash
.agents/skills/feature-pipeline/scripts/state.sh set phase 2
```

Then print the M1 stop hook and end your turn:

```
╔══ STOP HOOK M1 ══════════════════════════════════════════════════════════════╗
║  Phase 1 complete — <N> issues filed for {{feature}}                         ║
║  Review above, then run /fp-plan to continue.                                ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

## Constraints

- File issues via `gh` — do not use GitHub MCP tools here (script is faster).
- Cap at 8 issues. Do not keep exploring after the cap.
- Push issueNumbers to state after **each** issue (not in batch at the end).
- End the turn after the stop hook. Do not start Phase 2 yourself.
