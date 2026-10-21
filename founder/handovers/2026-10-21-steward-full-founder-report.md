# Gaia Steward Full: founder report

**Date:** 2026-10-21
**Integration branch:** `dev/gaia-steward-full`
**PR:** #2119 (draft, dev → main). It is not merged; that decision is yours.
**Head:** see the PR (the final SHA and its CI state are in the PR body).

## 1. Delivery status

Everything the mission asked for is built and tested, and it was rehearsed against real git remotes with real agents.

- **Runner.** `gaia steward full` runs deterministically and makes zero model calls. Its ledger is durable and resumable: a git ref with compare-and-swap and leases.
- **Coverage and skills.** There is a 17-routine sensor registry with a checker that refuses false coverage claims. The skill family is the thin root `/gaia-steward-full` plus six atomic skills.
- **Authority loops.**
  - Class A lands on an integration branch and never on `main`.
  - Class B dispatches one bounded change through a real builder and an independent verifier.
  - Class C goes to a founder desk that stays quiet when nothing needs you.
- **Not done:** no live landing on this repository's real remote. That waits on decision 1 below, by design.

The rehearsal found **five real defects** (§6). All were fixed on dev with regression tests before this report.

## 2. Coverage: 17 routines

The source of truth is `founder/steward/routine-coverage.json` (v2), checked by `scripts/check_steward_coverage.py --check`. That check also proves the checker still rejects six known false catalogs.

- **Status.** Every routine is **partially covered**. None claims full coverage, and the checker refuses that claim.
- **Live state.** Each detector is classified from a real receipt: observed, unknown, not evaluated or partially covered. An unexecuted detector is never healthy.
- **Unknown.** The live scan on this repository reports 0 unknown and 0 partially covered.
- **Not evaluated.** Three driver-input detectors are not evaluated locally because no driver supplied them; the scheduled workflow supplies CI runs.

| # | Routine | Detectors | Main remaining gap |
|---|---|---|---|
| 1 | Dead-Code Gardener | 1 | Deletion still needs usage evidence a static scan cannot see |
| 2 | Architecture and Abstraction Doctor | 1 | Abstraction quality and ownership remain judgment work |
| 3 | Error, Diagnostics and Incident Learner | 1 | Incident learning has no detector |
| 4 | Test Portfolio Gardener | 1 | Weak assertions and redundancy are not measured |
| 5 | Flake and Isolation Hunter | 2 | Flake history needs a driver-supplied input |
| 6 | CLI and Runtime Contract Steward | 1 | Runtime contracts (exit codes, output formats) are not observed |
| 7 | Mutation, Authorization and Abuse-Boundary Examiner | 3 | Abuse paths that need runtime exercise remain manual |
| 8 | Schema Evolution Steward | 2 | Breaking-change detection across versions |
| 9 | Evidence and Trust Reconciler | 4 | Hooks 1922, 1445 and 2063 are unknown until independent verification |
| 10 | Timeline Causality Keeper | 2 | Corrections are human-gated |
| 11 | Registry Structure and Installability Examiner | 3 | No live-upstream probing (no network) |
| 12 | Artifact, Branch and Repository Hygiene Sentinel | 3 | Stale remote branches and artifact growth |
| 13 | CI Architecture and Efficiency Steward | 2 | Needs a driver-supplied CI run history |
| 14 | Release and Supply-Chain Examiner | 4 | Advisories need a driver-supplied pip-audit run |
| 15 | Frontend Quality and Resilience Steward | 2 | Rendered behaviour is not observed; fixes are human-gated |
| 16 | Browser, Privacy and External Trust Auditor | 2 | Third-party script review is manual |
| 17 | Knowledge, Nomenclature and Agent-Surface Editor | 3 | Vocabulary checks live in their own CI gates |

## 3. Sensors

There are 30 detectors with 46 routine bindings. By authority binding they split into 2 Class A, 33 Class B and 3 Class C.

Every detector declares inputs, source of truth, evidence, freshness, dedupe key, resolution scope, owning skill, proof and failure behaviour. Correctness rules enforced in code and tests:

- **Missing inputs.** A missing or empty required input makes the sensor *unavailable*. That means coverage unknown, exit 3, and no Class A. It never means "healthy". Six legacy sensors used to return clean on an empty tree; they are fixed.
- **Skipped subjects.** A skipped subject (unreadable, oversize or unparseable) is reported, never silent. The sensor is listed under `partialCoverage`, and that run sweeps none of its debt. A sensor that skips everything is unavailable.
- **Driver inputs.** Optional driver inputs older than 7 days, future-dated, or from a different repository are *not evaluated*. Unaudited third-party packages block the advisory sweep.
- **Redaction.** Credentials never reach debt, receipts or stdout. Schema and timestamp echoes are replaced by type, length and hash. Tests plant a key and grep every output for it.
- **False positives removed.** Workflow-permission false positives (8 to 0), test-isolation chdir false positives (12 to 0), and the unreachable-legacy mutating-commands finding.

## 4. Skills

The canonical skills live in `.agents/skills/` and are mirrored byte-for-byte to `.claude/skills/`.

- **Root:** `gaia-steward-full`, under 120 lines. It routes every mode (`--observe`, `--triage`, `--routine N`, `--debt ID`, `--verify`, `--retro`, `--status`, `--resume RUN`, `--afk`) and every action type.
- **Atomic skills**, each with the same nine contract sections:
  - `gaia-steward-observe`
  - `gaia-steward-triage`
  - `gaia-steward-land`
  - `gaia-steward-verify`
  - `gaia-steward-retro`
  - `gaia-steward-desk`
- **Reused, not copied:** `gaia-steward-lane`, `gaia-tm-inspect`, `gaia-trace-timeline`, `gaia-docs-sync`, `ci-churn`, `gaia-triage`, `gaia-issue-resolver`, `feature-pipeline`.
- `tests/steward/test_steward_skills.py` parses every documented command with the live CLI parser. It also checks that referenced paths exist and that no model identifier appears.

## 5. Runtime proof: live rehearsal with real receipts

Receipts are in `founder/steward/rehearsal/2026-10-20/`. Each scenario ran against its own bare git remote, whose default branch is `main`.

| | Scenario | Result | Evidence |
|---|---|---|---|
| A | Clean run is quiet | **PASS** after a fix | It prints exactly `Gaia Steward: nothing needs you.` and `status` carries the quiet desk. The first run was partial (defect 1). |
| B | Class A lands on dev | **PASS** | It created a `steward/a/…` branch with one commit on the integration head; the repaired file is identical to canonical. `--integration-branch main` is refused, and the `main` SHA is unchanged. |
| C | Real Class B builder plus independent verifier | **PASS** on attempt 3 | The builder ran on Haiku at medium effort; the verifier ran on Sonnet at high effort and never saw the builder's reasoning. The work went `queued → building → verified → landed → resolved`, with `condition_recovered`. Attempts 1 and 2 were correctly rejected by mechanical verification (defects 2 and 3). |
| D | Class C stops at the desk | **PASS** | 22 `trust_stamp_stale` debts went only to the desk, with 0 actions. 6 decisions carry all 7 fields, and operations are listed separately. |
| E | Broken sensor reports UNKNOWN | **PASS** | Removing `registry/named` gives exit 3, blocked, with 5 sensors unknown and Class A refused. Invalid `meta.json` gives exit 3 as well. |
| F | Crash and resume | **PASS** | After `kill -9` mid-run, resume does not repeat recorded steps. After the lease TTL, the run is adopted: its old actions are superseded and the same idempotency key is re-offered. |
| G | Concurrent invocation | **PASS** | 5 races and 10 invocations gave exactly one winner per race (exit 0 ×5, exit 4 ×5) and no stray lease. |
| H | #2114 on live data | **PASS** | `hikari9/auto-office` is not flagged (TM 88.97, grade B, matching the inspector). All 51 flagged skills match `inspectTrustMagnitude.py` on TM and grade. |

Negative probes in C were refused with exit 2. One was the builder's own id, case-shifted and with a zero-width character inserted, offered as the verifier; the other was the wrong verifier model. Agent effort `default` or `inherit` is also refused.

## 6. Defects the rehearsal found (all fixed on dev)

1. **A clean run was never quiet.** An optional driver input nobody supplied counted as a desk operation, and the human CLI printed its own string instead of the desk line. Fixed in 482a3ba90.
2. **The builder packet never stated the proof-transcript shape or the output paths.** A correct one-line fix was rejected and cost an attempt. Fixed in 8ec3267d7 and dca7dba16.
3. **Every policy route lists "obtain independent review" as a proof item, which no builder can evidence.** Reproductions also had no exit-0 convention. The verifier step now discharges that one item; a machine verdict still never accepts. The lane skill states how to evidence a reproduction (`! cmd`) and a statement. Fixed in 842ac7d54.
4. **A Class A `no_change` was held forever**, ignoring an integration base that later gained the drift. Fixed in 482a3ba90, with a test that fails without the fix.
5. **Unknown-coverage causes were invisible** outside a local file. The run summary and the desk now name the cause. Fixed in 482a3ba90.

Also: ledger growth is bounded (older runs keep headlines only), CI fixtures are portable (explicit git identity, interpreter-reported JSON positions), and the stale CLAUDE.md claim that the pre-commit hook enforces version lockstep is corrected (CI does).

**Kept by design, and documented:**
- An `awaiting-action` run holds the lease until its TTL, so a second invocation meanwhile exits 4.
- `--afk` is driver-side; the runner never prompts.

## 7. Regressions and issues

- **#2114:** fixed and verified on live data (scenario H).
- **#1642:** detected, not decided. 22 `trust_stamp_stale` debts sit on the desk as one Class C decision. No stamp was touched, and no calibration was executed.
- **Test results:**
  - The steward suite passes in full (about 1430 tests).
  - The full repository suite passes locally except five tests that need gitignored Class P files, which CI generates.
  - CI on the PR head is reported in #2119.

## 8. Class C queue: your decisions

| # | Decision | Recommended | Unblocks |
|---|---|---|---|
| 1 | **Landing target** (`steward-landing-target`) | Set `STEWARD_INTEGRATION_BRANCH` to a long-lived steward integration branch and `STEWARD_LANDING_ENABLED=true`; leave `steward/ledger` and `steward/a/*` unprotected | Live Class A landing, Class B dispatch, verification and integration |
| 2 | **Trust-stamp refresh policy** (#1642, 22 debts) | Choose one refresh mechanism, e.g. a gated `gaia dev` restamp inside a reviewed PR | Clearing the 22 stale stamps |
| 3 | **Class B route for `unused_import`** | Approve a one-file route with a routine guide | The first live Class B route on dead-code debt (49 findings) |
| 4 | **Lane throughput** | Raise `maxInFlight` to 2 after ten runs with zero verifier overturns | Two concurrent bounded repairs |
| 5 | **Dev-mutation gates** | Gate `provenance` and `evidence-seed`; keep `assess`/`prefill` advisory | Closing 4 `ungated_mutation` findings |
| 6 | **#1699 timeline order** | Authorize a CLI re-sort on a `review/meta` branch | 3 timeline-causality findings |

No credential findings are open.

## 9. Cost

There are two sources, and they are kept separate:

- **Claude Code `/usage` at the context checkpoint:** $59.61 total. Haiku $0.76, Opus $24.06, Sonnet $34.79.
- **Since then:** subagent work totalled about 2.1M tokens. That is the reported totals for the sweep-safety, precision, runner-fix and rehearsal workers, plus three builders and one verifier. The `/usage` figure above does not include it.

The authoritative per-model total is the session's final `/usage`; the token-spend comment on #2119 gives the figures available at that point.

## 10. Decision requested

1. **Review and merge #2119** when CI is green on its head. It is founder-gated, and Steward never merges into `main`.
2. **Decide item 1 in §8 (landing target)** so the scheduled workflow can land Class A repairs live. The other five items can follow at your pace; until you decide them, the desk keeps them queued.
