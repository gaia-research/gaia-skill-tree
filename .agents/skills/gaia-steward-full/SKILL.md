---
name: gaia-steward-full
description: >-
  Run Gaia Steward end to end: observe every routine's detectors, triage debt by
  authority, land Class A repairs on the integration branch, drive a bounded batch of
  Class B dispatches through independent verifiers, re-observe, and leave a
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

`--routine` takes 1 to 19. Routine 18 is GitHub issue hygiene (`issue-hygiene`); routine 19 is routine pull-request maintenance (`pr-maintenance`, skill `gaia-steward-pr-maintenance`).
Issue-write authority is founder-ratified policy (ruling #10, A1-A5) but not rolled out:
`issueHygiene.writesEnabled` is false, so no closure actions are emitted, and there is no live closure
dry run, pilot or burn-down. Closures need ratification AND write opt-in AND an attributable Steward
owner and worker on every receipt; changing the kill switch alone grants no authority.

## Step 0: refresh the censuses

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

Routine 19 reads its own census the same way: `python scripts/steward_pr_census.py` (read-only GETs; exit 3 means incomplete, so the sensor reports coverage unknown).

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
| `forge.merge_pr`, `forge.close_pr` | `gaia-steward-pr-maintenance` (shared preparation, then explicit `execute --operation-id`; unattended driver refuses) |
   | `lead.integrate` | the orchestrator, merging into the integration branch only |

3. Record each outcome: `gaia steward full record RUN STEP --input outcome.json`.
4. Resume: `gaia steward full run --resume RUN --json`. Repeat until the run is
   `completed` or `blocked`.
5. Render the desk (`gaia-steward-desk`) and stop.

The runner tracks every step in a durable ledger (`refs/heads/steward/ledger`, or a
local file when no remote answers). Resuming never repeats a recorded step, and a
second concurrent invocation loses the lease and refuses cleanly. Only the Lead
writes the shared ledger; `--ledger git` is unchanged and is never replaced by local
state to get a green run.

Cloud agents are ephemeral and `steward/ledger` does not keep their receipts or proof: run Class B with `--evidence git`
and follow [cloud-custody.md](cloud-custody.md). Persistence fails closed (`BLOCKED: provenance unavailable`); never re-dispatch.

Only Routine 19 critical operation identity, immutable proof, global slot/accounting
and outcomes use its separately provisioned canonical coordination ref; ordinary run
state never moves there. Local run
expiry/action supersession cannot refund or cancel that shared sender. Every
success-shaped PR report (including already-*) binds shared head/evidence; unknown
stays recoverable. Missing coordination/current authority/clock config refuses
execution. Full-run completion does not settle an outstanding critical operation.

## Agents, models and effort

- Builders: `params.allowedModels` (Haiku or Sonnet). Verifier: Sonnet only, and
  never an agent listed in `params.forbiddenAgentIds`. Routine 19 dispatches are different: the active environment's roster
  profile (`python scripts/steward_pr.py roster …`) chooses agents by capability; no model name is canon, and the lane's
  `maxInFlight` and `maxDispatchesPerRun` still cap them.
- Every agent invocation names an explicit thinking effort. `default` and
  `inherit` are refused by `record`.
- Parallel `agent.build` actions from one run may be handed to builder subagents in one batch (founder decision `steward-class-b-throughput-2026-11-06`). Each builder gets only its own `params.promptPath`; any other fan-out needs the orchestrator's approval.
- No other models are authorized.

## Hard limits (enforced in code, repeated here)

- Never merge into `main`, push to `main`, force-push, tag, release or publish. The one exception is the ratified, narrowly scoped route `forge.merge_pr` (routine 19): a registered producer's pull request, one exact head SHA, an independent verification, GitHub's own branch protection, a merge commit, never a squash. It is never a general permission and is revoked by the kill switch.
- Class B: maxInFlight 8 (the policy value; the code accepts 1 to 8), maxDispatchesPerRun 8 (1 up to maxInFlight; one run emits up to the lesser of it and the free lane slots, as parallel `agent.build` actions over distinct debts), maxAttempts 2, cooldown 3600 s. Founder decision `steward-class-b-throughput-2026-11-06`.
- Closures (`forge.close_issue`) need `GH_TOKEN` or `GITHUB_TOKEN`. Without one they are reported under the driver's
  `unperformed` list with the reason, and nothing is written. A closure the executor refuses (exit 2) is recorded as a
  `refused` outcome with its reason code (B8 H-3a): the step settles, the pair is emitted again against a later census,
  and a pair refused three times becomes one founder question. It is never re-sent within the same pass.
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
| `routine_pr_*` (routine 19) | `gaia-steward-pr-maintenance`; Class C items go to `gaia-steward-desk` |
| escalated work too large for one dispatch | `gaia-triage`, then `gaia-issue-resolver` or `feature-pipeline` on its own PR |

## Stop conditions

Stop and report when the run is `completed` or `blocked`, a lease is lost, a forge closure comes back `blocked` (the driver halts; no further
closures this run), or an action asks for anything outside the table above.

## Where the rest lives

- Architecture contract: `founder/handovers/2026-10-20-steward-full-architecture.md`;
  issue hygiene: `founder/handovers/2026-10-21-steward-issue-hygiene-architecture.md`
- Coverage catalog and checker: `founder/steward/routine-coverage.json`,
  `scripts/check_steward_coverage.py`; routine 18 guide: `founder/steward/routines/issue-hygiene.md`
- Policy: `founder/steward/POLICY.yaml`; decisions: `founder/steward/decisions/`
