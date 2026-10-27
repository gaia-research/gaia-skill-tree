# Handover — Gaia Steward evolution, after Yggdrasil IV

**Status:** for a fresh orchestrator, **once the start conditions in §1 hold**. Until they hold, do nothing in this handover.

**Written:** 2026-10-27, against `main` `b0f6d9e` and the refs in §8.

**Architecture:** [`../STEWARD-EVOLUTION.md`](../STEWARD-EVOLUTION.md).
- That document is PROPOSED. Only the rulings the founder has ratified bind you.
- Where a ruling is unratified, take that ruling's "default until ratified" path (STEWARD-EVOLUTION §17).

**Authority you inherit:**
- your session's founder mission brief;
- `CLAUDE.md`, `STEWARD.md` and `steward/POLICY.yaml`;
- the Yggdrasil IV ratification and the Gaia Frontier ruling.

This handover grants nothing beyond them.

---

## 0. Read first, in this order

1. This handover, §§1–2.
2. `founder/STEWARD-EVOLUTION.md`: §0, §1, §5, §6, §12, §17.
3. The **post-Yggdrasil-IV** versions of:
   - `founder/STEWARD.md` §§6, 9–13;
   - `founder/STEWARD-OPERATING-MODEL.md` §§1, 4, 17.
4. The Yggdrasil IV merge PR and ratification as merged, and the Frontier ruling file on `main`.
5. `founder/steward/POLICY.yaml` and `founder/steward/decisions/`.

The v2 and v3 architecture reports are session artifacts. Their load-bearing facts are carried in STEWARD-EVOLUTION §16; do not hunt for the reports.

---

## 1. Start conditions — check each one and record the evidence

| # | Condition | How to check |
|---|---|---|
| 1 | Yggdrasil IV is on `main` | Read the state and merge commit of the Yggdrasil IV integration PR (#2151 at writing) with the GitHub tools, then run `git merge-base --is-ancestor <mergeCommit> origin/main` |
| 2 | `main` is verified | CI is green on the `main` head. `gaia steward full run --observe --ledger local --json` exits 0, or reports only honest unknowns. |
| 3 | No Yggdrasil IV work is in flight on Steward surfaces | `dev/yggdrasil-iv` is merged or deleted, and no open PR touches `src/gaia_cli/steward/`, `founder/steward/`, `.github/workflows/steward*` or `founder/STEWARD*.md` |
| 4 | You know which rulings are ratified | List which SE-n rulings are ratified, as decision records or a founder ruling document. Every unratified ruling takes its default path. |
| 5 | You know where #2175 stands | Required only before Stage 3. Record its state now. |

If condition 1, 2 or 3 fails, stop. Report which one failed and why. Do not start "just the docs part".

Yggdrasil IV's cleanup mandate (in the Frontier ruling) allows retiring superseded adapters and paths. Before you reuse anything named below, re-inventory these Steward surfaces on `main`:
- skills;
- workflows;
- `src/gaia_cli/steward/`.

---

## 2. Reconcile the then-current state (the first part of Stage 1)

### 2.1 Snapshot at writing — diff against this

| Item | State on 2026-10-27 |
|---|---|
| `refs/heads/steward/ledger` | `33af04c`, generation 72, `updatedAt` 2026-10-27T14:58:56Z |
| Runs | 3, all `abandoned`. The last one, `run-20261021T174049Z-36e4510c`, was abandoned by `operator:cli` with the reason quoted in STEWARD-EVOLUTION §16.2. |
| Work | 1 item `building`, kept on purpose for adoption by the next run: `trust_calibration_drift`, `addy-osmani-api-and-interface-design`. Its packet is lost. |
| Lane | 100 entries. 99 have been `queued` since 2026-10-21 (50 `trust_calibration_drift`, 49 `unused_import`); 1 is `dispatched`. |
| Lease record | Holder is the abandoned run; it expired at 2026-10-27T10:10:48Z |
| `dev/steward-integration` | `8ffdd66` |
| `.github/workflows/steward-full.yml` | Paused by the founder in `ecb6cfa`; the job runs only on `if: false` |
| `.github/workflows/steward.yml` | Daily at 07:10 UTC, `gaia steward full run --observe --trigger scheduled --ledger local` |
| Yggdrasil IV branch, at writing | Changes `src/gaia_cli/steward/ledger.py`: adds a ledger `operations` map and isolates remote refs |

### 2.2 Steps

1. **Read the ledger without writing to it:**

   ```bash
   git fetch origin refs/heads/steward/ledger:refs/remotes/origin/steward-ledger-readonly
   git show origin/steward-ledger-readonly:ledger.json
   ```

   Diff it against §2.1. List every run, lease, work item and lane entry, with its age.
2. **Name every invoker of the ledger since the snapshot:** commit times, `actor`, run ids. Find the host behind the CLI invocations of 2026-10-23 and 2026-10-27.

   **Add no schedule until this is known** (STEWARD-EVOLUTION §18, Q1).
3. **Confirm the post-IV ledger code and schema** on `main`: the `operations` map and ref isolation. Run `tests/steward/` there.
4. **Re-observe each queued debt** on post-IV `main`.
   - **Reproduced:** keep it.
   - **Not reproduced:** supersede it through the CLI, with a reason.
   - **The CLI cannot supersede it:** that is a CLI gap. File it under the CLI Pre-Flight Rule in `CLAUDE.md`, and never hand-edit the ledger.
5. **The `building` work item** follows the operator's disposition (adopt) only when both hold:
   - its debt is re-observed on post-IV `main`;
   - its route envelope, `trust-calibration-drift` in `POLICY.yaml`, is confirmed unchanged by Yggdrasil IV. That envelope prepares commands for human approval and writes nothing to the registry.

   Otherwise, put it on the desk.
6. **The stale lease record:** confirm the runtime treats an expired lease held by an abandoned run as free. Rehearsal scenario F covers adoption after the TTL. If the runtime does not, file a defect.
7. **The stuck escalation:** find out why the 24-hour escalation (`STUCKBUILDINGSECONDS`) left the item on `building` across the 2026-10-23 and 2026-10-27 resumes. It may be by design or a defect (STEWARD-EVOLUTION §18, Q9). If it is a defect, file it.
8. **Correct `founder/steward/decisions/LEDGER.md`** so its lifecycle columns match `main`:
   - decision 7 is implemented on `main` and paused;
   - check #2121, #2122 and #2123.
9. **Re-verify the findings in STEWARD-EVOLUTION §16.4**, and record which still hold.
10. **Write one reconciliation receipt** (template in §7). It is a founder document; commit it only if the founder wants it in the tree.

---

## 3. Stages

Every stage lists the same headings:
- objective, prerequisites and scope;
- what it reuses and what it produces;
- acceptance tests and failure criteria;
- definition of done, and the envelope it runs in (STEWARD-EVOLUTION §12).

A stage's acceptance must pass before the next stage begins.

### Stage 1 — Foundation (envelope E0)

- **Objective:** honest state and explicit records, before any new behaviour.
- **Prerequisites:** §1 conditions 1–4.
- **Scope, in:**
  - the reconciliation in §2;
  - schemas and validators for:
    - the domain policy file;
    - repository records (STEWARD-EVOLUTION §9.2);
    - the typed contract registry;
    - authorization records (§6.3);
    - classification records (§14.2);
    - watchdog configuration;
  - seed records for the cohort, at profile `observe`. This needs SE-2; without it, seed Tree-only records.
- **Scope, out:**
  - turning any new sensor on;
  - any schedule;
  - any write outside gaia-skill-tree;
  - any authorization record, because the founder writes those.
- **Reuse:**
  - the `steward-decision-v1` record format;
  - the loader patterns in `policy.py`;
  - `GitRefLedgerStore(ref=…)` from `ledger.py`, whose ref is already a constructor parameter, so a second domain needs a second ref, not a second mechanism;
  - the way `scripts/check_steward_coverage.py` refuses false claims.
- **Artifacts:**
  - the reconciliation receipt;
  - schemas, validators and tests;
  - observe-only seed records.
- **Acceptance:**
  - Validators reject:
    - unknown fields;
    - unknown contract relations;
    - a missing owner;
    - a private repository on a public host;
    - a `profile` above `observe` without a ratified record.
  - Every unknown is reported as unknown.
  - The receipt accounts for every ledger run, lease, work item and lane entry.
  - The remote ledger receives no write except CLI dispositions the founder approved.
- **Failure:**
  - any need to hand-edit the ledger;
  - any contradiction with post-IV canon;
  - any record that implies authority nobody ratified.
- **Definition of done:** the founder has reviewed the receipt and the records, and merged the PR.

### Stage 2 — Observation (envelope E1)

- **Objective:** Lane A observation that is zero-model and read-only, plus an independent watchdog.
- **Prerequisites:** Stage 1 done. Cross-repository scope needs SE-2; without it, observe the Tree only. The watchdog needs SE-7.
- **Scope, in:**
  - **An `automation-health` sensor.** It watches scheduled workflows for repeated failure, a failed trust ramp, and silence (no run within twice the cadence).
  - **A `contract-freshness` sensor.** It covers pinned snapshots, vendored code against the producer's `main`, path and branch existence, and version floors. Edges frozen by decision serve as quiet controls.
  - The domain's section of the desk.
  - The watchdog, on a separate host.
- **Scope, out:**
  - any model call;
  - any write outside the domain's own receipts, ledger ref and desk.
- **Reuse:**
  - The sensor contract (operating model §7) and `sensors_ci.py`. `scripts/steward_collect_ci_runs.py` already turns `gh run list` output into sensor input; run it once per repository.
  - The desk and digest.
  - Freshness signals the tools already publish.
  - Skill Heaven's live-parity check against gaia-research's `ledger.ts`, as the pattern for vendored code.
- **Artifacts:**
  - two sensor families, with fixtures;
  - contract-registry entries. Proposed edges stay `proposed` until ratified.
  - the watchdog workflow;
  - drill records.
- **Acceptance:**
  - Fixtures cover, per sensor:
    - one true catch;
    - one no-op;
    - unknown coverage;
    - a malformed contract, reported as unknown;
    - an edge frozen by decision, which stays quiet.
  - The first live run raises, unprompted, every §16.4 finding that still holds, and nothing for the healthy controls.
  - A re-run creates no duplicates.
  - The job makes zero model calls; no model credential is present in it.
  - The watchdog disable drill alerts within twice the cadence, and clears after recovery.
  - The private canary passes, or no private repository is in scope.
- **Failure:**
  - any false "healthy";
  - any model call;
  - desk noise above the weekly cap;
  - any public output that carries private metadata.
- **Definition of done:** four consecutive daily runs that are quiet or correct, and one founder review of the desk output.

### Stage 3 — Execution (envelope E2, attended)

- **Objective:** one governed Lane A outcome, end to end, in a repository other than gaia-skill-tree.
- **Prerequisites:**
  - Stage 2 done.
  - #2175 resolved, with its protections verified effective.
  - The SE-6 executor probe passed.
  - One standing authorization record. Candidate: the retrieval-index contract behind gaia-skill-heaven#216, if it is still breached.
- **Scope, in:**
  1. Admit, then lease.
  2. Build, with a builder that holds no write credential.
  3. Run the repository's checks, then an independent verifier.
  4. The driver opens a draft PR through the repository's adapter.
  5. The maintainer merges.
  6. Read back, then mark `resolved`.
- **Scope, out:**
  - merge, release or deploy;
  - workflow edits;
  - threshold or floor changes;
  - a second concurrent item.
- **Reuse:**
  - the runtime's lane, verification, landing and receipts;
  - the target repository's documented refresh procedure;
  - skill-cost.
- **Artifacts:**
  - the target repository's adapter, generated from its record;
  - one receipt chain.
- **Acceptance:**
  - The receipt carries:
    - tested SHAs and CI run ids;
    - the verifier's identity and verdict;
    - model and effort for each attempt;
    - skill-cost dollars;
    - founder minutes;
    - readback evidence.
  - Fault injection gives the right result in every case:

    | Injected fault | Required result |
    |---|---|
    | Crash mid-build | Resume without repeating recorded steps |
    | Duplicate tick | Exactly one winner |
    | Quota error | `deferred`, not failed |
    | Contract edited during the lease | The attempt is invalidated |
    | Authorization withdrawn | The run stops before any write |
    | Unknown landing rule | Refused |
  - The next item is chosen with a recorded reason.
- **Failure:**
  - any write outside a draft PR;
  - the verifier is the builder;
  - resolution without readback;
  - self-authorization.
- **Definition of done:** one verified, re-observed outcome, with every drill recorded.

### Stage 4 — Progress (envelope E3, attended)

- **Objective:** one forward item that is founder-authorized, anchored to ENDGAME and outside Yggdrasil IV, taken to a reviewed draft PR. Read it back once it is merged.
- **Prerequisites:**
  - Stage 3 done.
  - SE-4 and SE-10 ratified.
  - Classification evaluated on a founder-labelled sample: precision ≥ 0.9, and no `governance` item filed as `progress`.
- **Scope, in:**
  1. Read-only classification of a bounded sample.
  2. The founder authorizes one item.
  3. Dependency check, then admission with a budget.
  4. Execution and verification.
  5. A draft PR.
  6. Readback, or a recorded waiting status.
- **Scope, out:**
  - labels, comments or project-field writes by classification;
  - any item owned by Yggdrasil IV, Meta or Governance;
  - more than one item in flight.
- **Reuse:**
  - the Stage 3 chain;
  - Project #6's fields, read-only.
- **Artifacts:**
  - classification records;
  - one authorization record, written by the founder;
  - a receipt chain.
- **Acceptance:**
  - The classification can be reproduced from its recorded inputs.
  - The item's anchor quotes ENDGAME, and the verifier confirms its target behaviour.
  - Drills give the right result:

    | Drill | Required result |
    |---|---|
    | Issue body edited after authorization | Refused before any write |
    | Unmet dependency | `blocked` |
    | Item touches Yggdrasil IV | Classified `governance` |
  - The founder intervenes zero times between steps that were already permitted.
- **Failure:**
  - a fabricated anchor;
  - a `governance` item admitted;
  - any GitHub write by classification.
- **Definition of done:** one verified forward outcome, with the measures SE-2 needs for its comparison recorded.

### Stage 5 — Generalization (envelope E4)

- **Objective:** show the runtime is reusable. Onboard one new repository and offboard one, with no engine change. Stand up a private host only if a trigger in STEWARD-EVOLUTION §8.4 has fired.
- **Prerequisites:** Stage 4 done.
- **Scope, in:**
  - discovery, which yields candidates only;
  - onboarding through a record;
  - an offboarding drill;
  - a private host, if a trigger fired;
  - only now, the question of extracting runtime seams.
- **Acceptance:**
  - Onboarding changes zero lines of engine code: only configuration and records.
  - Offboarding keeps history and releases leases.
  - A rename keeps identity; a transfer offboards.
  - The private canary passes for any private scope.
- **Failure:**
  - an engine fork;
  - a leak.
- **Definition of done:** the acceptance above, plus a founder ruling on whether to extract seams.

### Stage 6 — Autonomy (envelope E5)

- **Objective:** scheduled, unattended operation of the E2–E4 envelopes, inside budgets, with automatic demotion.
- **Prerequisites:**
  - the SE-5 promotion window has passed;
  - the watchdog is live;
  - write credentials are confined (SE-3);
  - a founder ruling.
- **Scope, in:**
  - schedules for observation and admission;
  - budget enforcement;
  - a weekly retro, with at most one improvement PR a week (STEWARD-EVOLUTION §13).
- **Scope, out:**
  - merge, release or publication;
  - any expansion of authority.
- **Acceptance:**
  - The promotion-window measures hold for four unattended weeks.
  - Every demotion trigger has been tested once by drill.
- **Failure:** any boundary breach means automatic demotion to E1, and the founder is notified.
- **Definition of done:** four unattended weeks within the measures, then a founder review.

---

## 4. First mission — the smallest useful step after Yggdrasil IV

**Name:** *Make the Steward see its own silence.*

**Why this one:** the costliest failures found were invisible, not hard (STEWARD-EVOLUTION §11). This mission only adds detection.
- It needs no new charter: it stays inside the Tree domain, under routine 13, "CI Architecture and Efficiency Steward".
- It is valid whichever SE rulings land.

**Prerequisites:** §1 conditions 1–3.

**Steps:**

1. **Do §2 in full.** Land the decision-ledger correction as a founder-doc PR. Include the reconciliation receipt in it if the founder wants the receipt in the tree.
2. **Reuse before you build.** Read the latest daily `steward.yml` run's artifact or summary. Does the existing `ci_failure` sensor already raise debt for gaia-skill-tree's own red scheduled workflows, such as `verify-evidence` if it is still red?
   - **If it does**, the gap is a *consumer*, not detection: Class B debt with no executor and no route to the desk. Record that, and do not build a duplicate detector.
3. **Add only what is missing, as zero-model checks with fixtures and tests:**
   - **silence**: a scheduled workflow on `main` with no run within twice its cron cadence;
   - **Steward liveness**:
     - a run `awaiting-action`, or an item `building`, for longer than `STUCKBUILDINGSECONDS`;
     - a lease past expiry that is held by a finished run;
     - the age of the last observe receipt.

   Wire them into the existing daily observe in `steward.yml`, still with `--ledger local`. Add no new workflow and no new schedule.
4. **Let it run on `main`** for one scheduled tick, then trigger one manual re-run.

**Stopping point:** after that second run. Report:
- what it found;
- duplicates (expected: zero);
- model calls (expected: zero);
- anything it reported as unknown.

Then stop. Do not move on to any of the following until the founder rules on SE-2 and SE-7:
- cross-repository observation;
- contracts;
- the watchdog;
- executors;
- Lane B;
- any write outside gaia-skill-tree.

**Not in this mission:**
- ecosystem repositories;
- the independent watchdog;
- the contract registry;
- Lane B;
- executors;
- schedules;
- any private scope.

---

## 5. Standing rules for every stage

- **Branches and PRs follow `CLAUDE.md`.**
  - Never push to `main`; the founder merges.
  - Use merge commits.
  - Multi-PR work lands on a `dev/*` integration branch, and founder docs may be committed straight to it.
- **One stage per PR series.** Pass a stage's acceptance before you open the next stage.
- **Log token spend on every push**, per model and date, from canonical skill-cost, as a comment on the PR.
- **Leave Yggdrasil IV alone.**
  - Never touch `dev/yggdrasil-iv`, or any surface Yggdrasil IV owns.
  - Consume only Yggdrasil IV contracts that have been released.
- **Obey the Never list** in STEWARD-EVOLUTION §6.4, in every stage.
- **Report each stage** using the receipt template in §7.

## 6. Escalate to the founder immediately when

- canon after Yggdrasil IV contradicts STEWARD-EVOLUTION.md;
- a ledger operation would need a hand edit;
- anything would expand authority, budget or envelope;
- a public output would carry private metadata;
- the same stop condition fires twice for the same item.

## 7. Receipt template

```text
Stage or mission:
Start conditions:         each one, with its evidence
Ledger before → after:    ref, generation, runs, leases, work, lane
Changes:                  PRs, SHAs, files
Tests and drills:         command, result, exit code
Live runs:                run ids, findings, duplicates, model calls
Founder decisions needed: id, question, recommendation
Cost:                     skill-cost per model, with provenance
Founder minutes:          self-reported
Next:                     what, why, prerequisite
```

## 8. Reference snapshot (2026-10-27)

| Ref | SHA |
|---|---|
| `main` | `b0f6d9e502369aea2ebebe13eed8d961675094bd` |
| `steward/ledger` | `33af04c386c9063822eea75c91963acf4f0aa6cc` (generation 72) |
| `dev/steward-integration` | `8ffdd668775abf261b0dd581f6acf2e3672188cd` |
| `dev/yggdrasil-iv` | `bed78e716bc56d61cddc039c88ac95980be2ddf7` |
| Commit that paused the agentic driver | `ecb6cfa` |
| Commit that added agent-agnostic execution | `dbdf986` |
