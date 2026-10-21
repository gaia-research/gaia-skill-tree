---
name: gaia-steward-full
description: >-
  Run Gaia Steward end to end: observe every routine's detectors, triage debt by
  authority, land Class A repairs on the integration branch, drive one bounded
  Class B dispatch through an independent verifier, re-observe, and leave a
  quiet founder desk or a precise list of decisions. Use for "/gaia-steward-full",
  "run the steward", "full maintenance pass", "what does the repo need",
  "resume the steward run", or a scheduled maintenance wake. Thin entrypoint:
  each phase is an atomic gaia-steward-* skill.
version: 1.0.0
---

# gaia-steward-full

The root of Gaia Steward Full. It owns no logic of its own: the deterministic
runner (`gaia steward full`) decides every state transition, and the atomic
skills below each do one job. This file maps a mode to a command and an action
to a skill, and states the rules that hold across all of them.

## Modes

| Invocation | Command | Skill |
|---|---|---|
| `/gaia-steward-full` | `gaia steward full run --json` | this loop |
| `--observe` | `gaia steward full run --observe --json` | `gaia-steward-observe` |
| `--triage` | `gaia steward full run --triage --json` | `gaia-steward-triage` |
| `--routine N` | `gaia steward full run --triage --routine N --json` | `gaia-steward-triage` |
| `--debt ID` | `gaia steward full run --triage --debt ID --json` | `gaia-steward-triage` |
| `--verify` | `gaia steward full run --verify --json` | `gaia-steward-verify` |
| `--retro` | `gaia steward full run --retro --json` | `gaia-steward-retro` |
| `--status` | `gaia steward full status --json` | `gaia-steward-desk` |
| `--resume RUN` | `gaia steward full run --resume RUN --json` | this loop |
| `--afk` | add `--afk` to any `run` | this loop |

The runner itself never prompts in any mode; `--afk` is recorded on the run for audit and
tells the driver to queue founder decisions instead of asking. An `awaiting-action` run keeps
the run lease until its TTL, so a second invocation meanwhile exits 4 (observing-existing).

Scheduled runs add `--trigger scheduled`. Class A landing additionally needs
`--integration-branch dev/<name> --push` (or `GAIA_STEWARD_INTEGRATION_BRANCH`);
the runner refuses `main`, `master` and the remote default branch.

`--routine` takes 1 to 18. Routine 18 is GitHub issue hygiene (`issue-hygiene`).

## Step 0: refresh the issue census

Before the first `run` of any mode that observes or triages, refresh the GitHub issue
census that routine 18 reads:

```bash
python scripts/steward_issue_census.py --repo gaia-research/gaia-skill-tree --out .gaia/steward/inputs/github-issues.json
```

Exit 0 is complete. Exit 3 is incomplete: the file is written with its completeness
flags false, and routine 18 reports not evaluated. Any other exit: delete the file, so
the sensor reports its input missing. The unattended driver `python scripts/steward_drive.py`
runs this step itself; `--no-census` skips it. A census older than the policy's
`maxCensusAgeSeconds` is never used.

## The driver loop

The runner makes zero model calls. Whatever needs a model or a forge comes back
as a pending action. Drive it like this, and nothing else:

1. Run the mode's command. Read `status`, `nextAction` and `actions`.
2. For each pending action, hand it to exactly one owner:

   | Action type | Owner |
   |---|---|
   | `agent.build` | a fresh builder agent following `gaia-steward-lane`, given only `params.promptPath` |
   | `agent.verify` | a different, fresh agent following `gaia-steward-verify` |
   | `forge.open_pr` | `gaia-steward-land` (draft PR to the integration branch) |
   | `forge.close_issue` | `gaia-steward-issue-hygiene` (one proven closure, performed by `scripts/steward_issue_close.py`) |
   | `lead.integrate` | the orchestrator, merging into the integration branch only |

3. Record each outcome: `gaia steward full record RUN STEP --input outcome.json`.
4. Resume: `gaia steward full run --resume RUN --json`. Repeat until the run is
   `completed` or `blocked`.
5. Render the desk (`gaia-steward-desk`) and stop.

The runner tracks every step in a durable ledger (`refs/heads/steward/ledger`, or a
local file when no remote answers). Resuming never repeats a recorded step, and a
second concurrent invocation loses the lease and refuses cleanly.

## Agents, models and effort

- Builders: `params.allowedModels` (Haiku or Sonnet). Verifier: Sonnet only, and
  never an agent listed in `params.forbiddenAgentIds`.
- Every agent invocation names an explicit thinking effort. `default` and
  `inherit` are refused by `record`.
- Subagents do not fan out without the orchestrator's approval.
- No other models are authorized.

## Hard limits (enforced in code, repeated here)

- Never merge into `main`, push to `main`, force-push, tag, release or publish.
- Class B: maxInFlight 1, maxAttempts 2, cooldown 3600 s, one dispatch per run.
  Need more throughput? File a founder-reviewable amendment
  (`founder/steward/decisions/`); never loop the CLI to get around the cap.
- Unknown coverage blocks Class A for the run. A not-evaluated sensor is never
  healthy.
- Class C goes to the desk. Founder availability is not permission, and `--afk`
  only queues decisions while A/B work continues.
- The builder never verifies its own work; the machine can reject or escalate
  but never accept.

## Reused skills

Steward finds and bounds the work; existing skills do the specialised parts.

| Debt or situation | Skill |
|---|---|
| any Class B dispatch | `gaia-steward-lane` (the builder's contract) |
| `trust_calibration_drift`, `trust_stamp_stale` | `gaia-tm-inspect` first: verify the effective-evidence context before any calibration |
| `timeline_causality_drift` | `gaia-trace-timeline` to reconstruct the order; the fix stays human-gated |
| `issue_closure_ready`, `issue_suite_review`, `issue_founder_decision` (routine 18) | `gaia-steward-issue-hygiene` (A closures), `gaia-steward-lane` (B suite review), `gaia-steward-desk` (C questions) |
| `generated_projection_drift` | `gaia-docs-sync` |
| `ci_failure`, CI churn | `ci-churn` |
| escalated work too large for one dispatch | `gaia-triage`, then `gaia-issue-resolver` or `feature-pipeline` on its own PR |

## Stop conditions

Stop and report when the run is `completed` or `blocked`, a step is refused twice,
a lease is lost, a forge closure comes back `blocked` (the driver halts; no further
closures this run), or an action asks for anything outside the table above.

## Where the rest lives

- Architecture contract: `founder/handovers/2026-10-20-steward-full-architecture.md`;
  issue hygiene: `founder/handovers/2026-10-21-steward-issue-hygiene-architecture.md`
- Coverage catalog and checker: `founder/steward/routine-coverage.json`,
  `scripts/check_steward_coverage.py`; routine 18 guide: `founder/steward/routines/issue-hygiene.md`
- Policy: `founder/steward/POLICY.yaml`; decisions: `founder/steward/decisions/`
