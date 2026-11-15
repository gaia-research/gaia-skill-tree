# Upstream backlog campaign, November 2026 — control file

Recovery entry point. Update it on every material state change.

- **Status:** P0 correction round 1 is committed and pushed at `11405f2dacaa2f6501039dbce3936106e0fb9bee`; the first independent Terra review returned FINDINGS on `6674c8268703f6137f8e4c8067e0be7ca73bd378`, and the corrected builder-reported checks are recorded below. Await independent second review. P0 is not PASS/complete; P1 has not started. See [PREFLIGHT.md](PREFLIGHT.md).
- **Baseline:** `main` @ `9b4d9b98` (v9.5.0), snapshot 2026-11-15.
- **Plan:** [PLAN.md](PLAN.md). **Executor prompt:** [EXECUTOR_PROMPT.md](EXECUTOR_PROMPT.md).
- **Review surface:** the founder decision page, <https://claude.ai/artifact/Wru54QS4QXn4zBu9YPfixd> (private to the founder). This file is the record; the page is not.
- **Planning mission authority:** read-only. The planning session changed no issue, label, branch, variable or registry file. Its only write is this report directory.

## Founder rulings 2026-11-15

Six choices, saved by the founder on the decision page between 15:02:53Z and 15:04:33Z and also pasted into the planning session as the page's copy-as-JSON output. The saved documents and the pasted JSON agree. Recorded verbatim below before any action is taken on them. A choice approves only what its card states.

```json
{
  "page": "Upstream Backlog Plan",
  "snapshot": "2026-11-15",
  "choices": [
    {
      "id": "d1-sync-route",
      "decision": "1. How version syncs are approved and landed",
      "choice": "a",
      "optionLabel": "Umbrella approval route",
      "note": ""
    },
    {
      "id": "d2-gbrain",
      "decision": "2. GBrain family hold (C3)",
      "choice": "c",
      "optionLabel": "Lift for records and version-only sync",
      "note": ""
    },
    {
      "id": "d3-addy",
      "decision": "3. Addy Osmani family hold (C2)",
      "choice": "b",
      "optionLabel": "Records and version sync, migration still deferred",
      "note": ""
    },
    {
      "id": "d4-agentdb",
      "decision": "4. AgentDB source reconciliation (C1)",
      "choice": "a",
      "optionLabel": "Small CLI change, then relink AgentDB",
      "note": ""
    },
    {
      "id": "d5-closures",
      "decision": "5. Who closes stale records",
      "choice": "c",
      "optionLabel": "Hybrid",
      "note": ""
    },
    {
      "id": "d6-batching",
      "decision": "6. Weekly batching activation",
      "choice": "a",
      "optionLabel": "Activate before the first write",
      "note": ""
    }
  ]
}
```

The option text each choice selected, exactly as the card stated it:

| # | Choice | Card text |
|---|---|---|
| 1 | A. Umbrella approval route | You apply upstream:approved per refreshed umbrella. The workflow opens draft PRs, which are retargeted to one integration branch. Superpowers goes first as a canary. |
| 2 | C. Lift for records and version-only sync | As B, plus sync the version. New candidates and the breadth audit (#2276) remain held. (B: Close the children whose skill is in the registry, each with per-row proof and a receipt. No version sync, no new intake.) |
| 3 | B. Records and version sync, migration still deferred | Close the four children with proof, sync the version under the existing identifiers. |
| 4 | A. Small CLI change, then relink AgentDB | Add an explicit, timeline-logged way for sync-upstream to re-point a record to a new repository. Then set AgentDB's verified source and version. |
| 5 | C. Hybrid | Hand-close the free records now. Use Steward closure for the held children once they are released. |
| 6 | A. Activate before the first write | Run the documented bootstrap and set the three variables right after the repair, then monitor two weekly windows. |

Founder message approving the plan, 2026-11-15 (verbatim):

> Okay, push the plan as a PR and then send me the handoff prompt for the executor. I will still be the one sending the roster. Thank you. The plan is approved.

### What the rulings change, and what they do not

- **Rulings 2 and 3 amend two existing founder locks to the stated extent only.** C3 (`founder/steward/decisions/issue-question-q-bfd37238.json`, GBrain) and C2 (`issue-question-q-2568173e.json`, Addy) still read as full holds, and Steward issue hygiene consumes those records. The executor records today's rulings in the Steward decision records as its first registry-adjacent step, or Steward keeps treating both families as held. Those files were not edited by the planning session.
- **Still held after ruling 2:** new GBrain candidates, the GBrain breadth audit (#2276), `skip-child-gate` on GBrain, and any trust or rank change.
- **Still held after ruling 3:** the `addy-osmani` to `addyosmani` handle migration and every rename of a published identifier.
- **Ruling 4 authorizes a CLI change and the AgentDB relink.** It is not approval of any Ruflo or AgentDB release. Those need a fresh human `upstream:approved` like any other.
- **Ruling 5 does not by itself turn Steward closure writes on.** `issueHygiene.writesEnabled` stays `false` until the independent verification the 2026-11-06 ratification requires. Hand closures of the free records need no new authority.
- **Ruling 6 executes the activation the founder approved on 2026-11-08** (`steward-upstream-batch-activation-2283.json`), in the documented safe sequence. Repository variables are set by a person.
- **No ruling grants:** L4 approval of any candidate, calibration, Origin or evidence changes, approval labels applied by an agent, or a merge to `main`.

## Lanes

| Phase | Lane | State |
|---|---|---|
| P0 | Authorize and baseline | Preflight passed; integration branch created at verified main; scoped C2/C3 record/consumer amendment pending implementation and independent review |
| P1 | Repair the watcher (AgentDB, `links.github` fallback, #2278 dry run) | not started |
| P2 | Batch mode, then one dry-run census | not started |
| P3 | Record reconciliation (81 records) | not started |
| P4 | Version sync through the approval workflow | not started |
| P5 | Structural freezes and relinks | not started |
| P6 | New components, only if the census has any | not started |
| P7 | One regeneration, one PR to `main`, closeout | not started |

## Pending founder inputs

- Roster and execution authority received in the founder's execution instruction; concurrency maximum four. The founder confirmed no budget ceiling and an available execution window.
- Founder changed Opus to Antigravity and explicitly authorized resumption without fallbacks. No provider/model substitution is permitted. Details: [PREFLIGHT.md](PREFLIGHT.md).
- Still founder-only during execution: `upstream:approved` on each refreshed umbrella (Superpowers first), the three repository variables for batching, issue-hygiene write enablement after required independent verification, an L4 page if P6 has rows, and the merge of the integration PR.

## Execution log

### 2026-11-15 — P0 correction round 1 delivered; second independent review pending

- PR #2467: <https://github.com/gaia-research/gaia-skill-tree/pull/2467>, base `dev/upstream-backlog-2026-11`. Corrected builder commit `11405f2dacaa2f6501039dbce3936106e0fb9bee` is pushed; the dedicated campaign worktree is clean on `dev/upstream-backlog-authority-2026-11` at that exact SHA.
- The first independent Terra review of `6674c8268703f6137f8e4c8067e0be7ca73bd378` returned **FINDINGS**, not approval: one critical reparented/new GBrain hold escape; warning C1 `upstream:needs-info` bypass; warning rewritten Addy historical text; and a conditional P4 dependency on a version-approval workflow route. The summarized receipt and correction mapping are in [P0_HANDOFF.md](P0_HANDOFF.md).
- Builder reports correction round 1 at `11405f2dacaa2f6501039dbce3936106e0fb9bee`; reports 932 issuehygiene tests and 64 founder-record/desk tests passed, plus Steward coverage and `git diff --check`. These results are builder-reported, not independently certified.
- P0 is **awaiting independent second Terra review**; do not mark P0 PASS/complete or P1 started. PR #2467 remains draft. P2 census has not run.
- Usage checkpoint cutoff and sanitized estimates: see [COSTS.md](COSTS.md). The measured canonical snapshot includes the builder correction and first Terra review; current in-flight administration and further review are unavailable.

### 2026-11-15 — preflight and authorized resumption

- Loaded the approved control/plan commit `692b807e198d8940df58fef8b5aaef1dcc29bbac` from draft planning PR #2466, the watcher contract including F3a, and the specified Steward lock, decision and issue-hygiene policy records.
- Initial preflight stopped on Anthropic Opus authentication failure and an unintended inherited fallback. After the founder's provider change and resumption instruction, explicit empty fallback lists and zero retries were set on the four named campaign agents using supported agent definitions. Fresh Hydrogen and Antigravity Opus probes passed; actual child identity/effort records were verified. Luna and Terra probes passed independently. No harness code was changed.
- Verified remote main is unchanged at `9b4d9b98043140188f00b14d0ac8fa6bc02491b7`; created local `dev/upstream-backlog-2026-11` there. Isolated P0 feature branch `dev/upstream-backlog-authority-2026-11` carries the approved planning commit through a merge commit. The original dirty checkout is untouched.
- P0 inspection found that Steward's current lock consumer recognizes only the original full-hold resolutions. Updating prose alone would not implement the limited release. A bounded amendment must preserve historical rulings, keep new/absent GBrain candidates and Addy migration held, and retain all existing proof and write switches. No policy switch, approval label, issue closure, registry mutation or generated-artifact rebuild has occurred.

## Landed

Nothing merged to the integration branch or main yet.
