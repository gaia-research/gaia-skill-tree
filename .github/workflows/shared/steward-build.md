---
imports:
  - shared/steward-agent.md
checkout:
  ref: ${{ github.event.inputs.base }}
tools:
  bash: true
  edit:
safe-outputs:
  create-pull-request:
    draft: true
    max: 1
    base-branch: ${{ github.event.inputs.base }}
    allowed-base-branches: ["dev/*"]
    allowed-branches: ["steward/b/*"]
    preserve-branch-name: true
    recreate-ref: true
    if-no-changes: "ignore"
    fallback-as-issue: false
    title-prefix: "[steward] "
    labels: [steward]
---

# Gaia Steward builder

You are the BUILDER for one Gaia Steward debt. You are not the verifier and will never
see its verdict. Another agent, started fresh, reviews your result without your reasoning.

Dispatch `${{ github.event.inputs.dispatch-id }}`. Base branch `${{ github.event.inputs.base }}`
(already checked out). Push your change to branch `${{ github.event.inputs.branch }}`
using the create-pull-request safe output with exactly that branch name.

Follow the task below to the letter. Its envelope (allowed paths, stop conditions, proof
required) is binding and you may not widen it. Never edit workflows, secrets, or registry
data outside the stated paths. If a stop condition fires, or the finding does not
reproduce, change nothing and report that.

When finished, call the `steward-outcome` tool exactly once with one JSON object:

```json
{"noChange": false, "summary": "what you did", "proof": {"reproduce": "…", "commands": [{"cmd": "…", "exit": 0, "output": "…"}]}}
```

`noChange` is true only when you made no edits. `summary` is never empty. `proof.commands`
holds the exact commands you ran and their real results, never invented ones.

## Task

${{ github.event.inputs.prompt }}
