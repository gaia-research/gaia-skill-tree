# Upstream backlog campaign, November 2026 — control file

Recovery entry point. Update it on every material state change.

- **Status:** Code and decision records at `11405f2dacaa2f6501039dbce3936106e0fb9bee` are independently verified by Terra (all 3 prior code/record findings fixed; 932 `issuehygiene` + 64 founder/desk tests PASS; coverage/diff check PASS; 71 synthetic baseline children yielded A1 proposals — not live closure proof). Terra's review of `4778b2a04de62f60df48f7a0a7df5c9aa943da22` confirmed all other doc/snapshot checks and returned `FINDINGS` solely for the `BASELINE_UPSTREAM_METADATA.json` / prose `0 frozen` claim (raw frontmatter flag vs canonical `gaia_cli.frozen.frozenIds`). Two routine correction rounds are exhausted; this narrow deterministic reporting-artifact correction updates only derived report data/prose using `gaia_cli.frozen.frozenIds` over baseline `9b4d9b98` Git objects (canonical count: **24**). **Final Terra narrow check is PENDING. P0 is not complete; P1 has not started.** See [PREFLIGHT.md](PREFLIGHT.md).
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
| P0 | Authorize and baseline | Code/records at `11405f2` independently verified; narrow reporting-artifact correction (`frozen: 24`) delivered; final Terra narrow check pending |
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

### 2026-11-15 — Terra review of `4778b2a` (FINDINGS) and narrow reporting-artifact correction

- **Independent Terra review on `4778b2a04de62f60df48f7a0a7df5c9aa943da22`:** confirmed doc-only delta (no code/test/decision/POLICY/workflow/registry changes), 81 snapshot IDs match `PLAN.md` and canonical census with valid digests, all 472 metadata Git paths/blobs/source fields match baseline `9b4d9b98`, historical date fix is correct, and cost privacy is clean. **Sole finding:** `BASELINE_UPSTREAM_METADATA.json` line 9 reported `0` frozen and all 472 entries `frozen: false` (inferred from absence of a frontmatter `frozen` flag, contradicting canonical `gaia_cli.frozen.frozenIds`), plus unqualified `0 frozen` in `CAMPAIGN.md` line 119 and `P0_HANDOFF.md` line 85.
- **Routine correction limit:** the two routine correction rounds are exhausted. No code, policy, authority, workflow, or registry repair or scope expansion was performed; `11405f2` code and decision records remain untouched.
- **Narrow reporting-artifact correction:** applied canonical `gaia_cli.frozen.frozenIds` (`src/gaia_cli/frozen.py`, including suite inheritance) to the 472 `registry/named/**/*.md` records parsed directly from baseline `9b4d9b98043140188f00b14d0ac8fa6bc02491b7` Git objects. Canonical count is **24** (all 24 self-frozen via `timeline:upstream_deprecated` with `installable: false`, including `garrytan/investigate` and `mattpocock/personal` whose 2 `suiteComponents` are also self-frozen; active capstones `mattpocock/productivity` and `mattpocock/skills` remain unfrozen). Updated `BASELINE_UPSTREAM_METADATA.json` (`counts.frozen: 24`, per-record `frozen` flags, `frozenDefinition: "gaia_cli.frozen.frozenIds (src/gaia_cli/frozen.py)"`, `entriesDigestSha256: 997c80e0b5d8df626817e43f26fbbb94ac3d1b854c3f93f5e1ac07185e75e324`). `BASELINE_UPSTREAM_RECORDS.json` (81 issues) is unchanged.
- **Gate:** Final Terra narrow check is **PENDING**. PR #2467 remains draft (`dev/upstream-backlog-authority-2026-11` -> `dev/upstream-backlog-2026-11`). **P0 is not complete; P1 has not started.**
- **Usage checkpoint:** see [COSTS.md](COSTS.md) (measured mixed-method cutoff **$4.417187**; in-flight narrow correction and pending Terra check excluded).

### 2026-11-15 — second Terra verification, baseline snapshots, and doc-only correction 2

- **Independent Terra verification on `11405f2dacaa2f6501039dbce3936106e0fb9bee`:** all 3 prior code/record findings are fixed; 932 `issuehygiene` tests and 64 founder-record/desk tests PASS; `scripts/check_steward_coverage.py --check` PASS; `git diff --check` PASS. An independent synthetic probe of 71 baseline children using actual registry URLs yielded `A1` proposals (explicitly **not** live closure proof). C1 (`q-08ecd62d`), C4 (`q-6720aecf`), and `founder/steward/POLICY.yaml` (`issueHygiene.writesEnabled: false`) remain unchanged. The P4 `upstream-approve.yml:469` version-only workflow gap remains a recorded prerequisite, not permission to apply GBrain `skip-child-gate`.
- **Remaining Terra verdict on `11405f2`:** `FINDINGS` solely for the stale doc date (`previous resolution (2026-11-04)`) in `P0_HANDOFF.md` initial summary lines 11–12.
- **Doc-only correction 2 & initial P0 baseline snapshots:**
  - Corrected `P0_HANDOFF.md` lines 11–12 to match the `#2283` baseline records without inventing historical dates, and recorded the second Terra receipt. No code, workflow, or decision-record files were modified.
  - Produced `BASELINE_UPSTREAM_RECORDS.json` for the exact **81** `PLAN.md` issues (6 umbrellas, 3 bootstraps, 72 appendix children) from the saved canonical `scripts/steward_issue_census.py` output (`249` open + `325` recentlyClosed; first closed baseline seeded at `728` because none was retrievable): **81 found** (`open` in `issues`), **0 missing**. Initial P0 evidence only — **not** a P2 watcher census and grants no closure proof.
  - Produced `BASELINE_UPSTREAM_METADATA.json` from `registry/named/**/*.md` at approved `main` `9b4d9b98043140188f00b14d0ac8fa6bc02491b7`: **472** named files, **17** with `upstream` block, **0** frozen *(superseded: raw frontmatter flag check; canonical `gaia_cli.frozen.frozenIds` count is **24**)*, **15** `installable: true`, **30** `installable: false`, **427** `installable` unset, **445** with `links.github`.
- **Gate:** Final independent Terra doc-only review is **PENDING**. PR #2467 remains draft (`dev/upstream-backlog-authority-2026-11` -> `dev/upstream-backlog-2026-11`). **P0 is not complete; P1 has not started.**
- **Usage checkpoint:** see [COSTS.md](COSTS.md) (measured mixed-method cutoff **$3.821332**; in-flight administration and Terra reviews excluded).

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
