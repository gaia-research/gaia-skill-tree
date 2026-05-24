---
name: fp-drift
description: >-
  Phase 5 of the feature-pipeline suite. Runs gaia dev diff against main to
  check for unexpected skill drift on the PR branch, then delivers the final
  pipeline summary. Use after /fp-iterate has confirmed CI is green and printed
  the M4 stop hook. Also useful standalone to check skill drift on any branch.
version: 3.0.0
---

# fp-drift  (Phase 5 — Drift Check & Summary)

Fetch main, check for skill drift, deliver the final summary. Lightweight —
runs directly without spawning a sub-agent.

## Setup

```bash
STATE=".agents/skills/feature-pipeline/scripts/state.sh"
feature=$($STATE get feature)
branch=$($STATE get branch)
pr=$($STATE get prNumber)
prUrl=$($STATE get prUrl)
issues=$($STATE get issueNumbers)
```

If state is missing or `ciStatus != "green"`, print a warning and exit:
`⚠ CI is not confirmed green. Run /fp-iterate first.`

## Drift check

```bash
git fetch origin main
gaia dev diff 2>/dev/null || gaia validate
```

**If unexpected drift is detected** (skills changed that are unrelated to the
PR's stated purpose):

Print a warning table:

```
⚠ Skill drift detected:

| Skill ID | Field | Value on main | Value on branch |
|----------|-------|---------------|-----------------|
| …        | …     | …             | …               |
```

Do NOT auto-fix. End your turn — let the user decide whether the drift is
intentional.

**If no unexpected drift:**

Collect the commit list:

```bash
git log origin/main..HEAD --oneline
```

Print the final summary:

```
✅ Feature Pipeline Complete
════════════════════════════════════════════════════════

Feature explored : {{feature}}
Issues filed     : <count>  (links: <#N> <#M> …)
PR               : <prUrl>
CI               : All checks green ✅
Skill drift      : None detected ✅

Commits
───────
<sha7> <message>
…

What was fixed
──────────────
• <issue title>
…
```

End the pipeline:

```bash
$STATE set phase 7
$STATE set ciStatus "done"
```

Print:
```
── Pipeline complete ──────────────────────────────────────────────────────────
```
