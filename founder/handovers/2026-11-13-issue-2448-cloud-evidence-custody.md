# Issue #2448 — durable evidence custody for ephemeral cloud Steward runs

Handoff for founder review. Branch `infra/steward-cloud-receipt-preflight-2448`, PR #2449
(extended; see "PR structure"). Nothing here is merged, deployed or released.
Operational contract for agents: `.agents/skills/gaia-steward-full/cloud-custody.md`.
Scheduler handoff: `founder/steward/CLOUD_DAILY_BRIEF.md` (**not installed**).

## 1. What was wrong

Daily Steward maintenance runs on short-lived cloud agents. `gaia steward scan|dispatch`
write the scan receipt, the content-addressed dispatch receipt and the verifier's
receipt under checkout-local, gitignored `.gaia/steward/receipts/`; the builder's diff
and `steward-proof-transcript-v1` were files in the same container. `refs/heads/steward/ledger`
holds full-run state only. When the container died, a later host had nothing to verify
against, and `gaia steward verify` correctly refused (#2445).

A second, worse hole sat in `fullrun.py::_verifyOne`: on `no dispatch receipt` it called
`render_dispatch` and verified the old patch against the **new** receipt. On a fresh host
that mints a new envelope under today's policy and judges yesterday's patch by it. It is
removed.

## 2. Audit: what the daily job actually is

* The daily cloud job is the external scheduled task `Gaia Steward Daily`
  (`trig_01NLfT4PzgwkWh8utSzRRopE`, `CRON_TZ=Asia/Manila 45 10 * * *`, `claude-sonnet-5-5`,
  fresh session per fire; last fired 2026-11-13T02:50Z, succeeded). Its prompt is prose and
  **names no gaia command**, so `full` versus standalone `scan`/`dispatch`/`lane next` is
  chosen by the agent each day. Both paths are therefore covered.
* `.github/workflows/steward.yml` (cron `10 7 * * *`) is the separate Class A pulse.
  `.github/workflows/steward-full.yml` has no schedule ("until explicitly reauthorized").
  Neither is the cloud-subagent job and neither was changed.
* A separate scheduled task, `Gaia Steward Heartbeat - basic`, is disabled.

## 3. Architecture and durability decisions

| Decision | Why |
|---|---|
| New append-only Git ref `steward/evidence`, not the hot ledger | Every run reads and rewrites `ledger.json` (8 MiB bound). Diffs and proof transcripts would bloat every load. The ledger instead **indexes**: full-run work items carry `evidence: {dispatchBundle, buildBundle, evidenceCommit}`. |
| Reuse the ledger's CAS | `GitRefLedgerStore.publishTree` is the old `compare_and_swap` tail, extracted unchanged (no force, no lease option; a root commit cannot replace an existing ref; refuses to resurrect a deleted ref). `GitEvidenceStore` subclasses it. No database, paid service or second framework. |
| Content-addressed objects + one manifest per bundle | `objects/<sha256>` holds raw bytes; `bundles/<debt key>/<bundle id>.json` lists them. `bundleId` = sha256 of the canonical identity; anything altered after publication stops matching its name. Existing paths are never replaced. |
| Chain `dispatch -> build -> verdict`, each bundle names its parent | The verifier gets the exact receipt that authorized the work, never "the newest receipt for that debt". Ambiguity (several builds or chains) is refused until `--bundle` names one. |
| Byte-exact restore, original authority | Receipts are restored without re-rendering; a restored dispatch must still hash to its own id, its scan must be the scan it names, and a **newer** local dispatch for the debt makes `verify` refuse. `gaia steward verify` itself is unchanged. |
| Write is not success until read-back | Every publish re-fetches the remote ref and re-verifies every object. A push that landed but could not be read back raises; retrying finds the bundle durable, re-verifies it and does not duplicate it. |
| Publish-time validation | A build needs a non-empty diff with hunks and a proof that parses as `steward-proof-transcript-v1` within the packet's proof contract. `/dev/null`, empty, malformed or out-of-contract proofs are refused before anything is stored. |
| Explicit mode | `--evidence git` or `GAIA_STEWARD_EVIDENCE=git`. An unknown value is an error, never a silent downgrade, and is checked before any work is dispatched. |

Not changed: Class B authority, models, budgets, lane limits, Class C, Star Bar, CI gates,
`require_operator()`. Only the Lead writes shared coordination state.

## 4. Fail-closed boundaries (changed execution path)

| # | Boundary | Code | On failure |
|---|---|---|---|
| 1 | Dispatch issued | `custody_ops.publishDispatch`; called from `dispatch`/`lane next` (`commands/steward.py::_custodyDispatch`) and `fullrun._dispatchCandidate` | Nothing printed on stdout (no prompt), exit 4; full run: phase `blocked`, no builder action, no lane move |
| 2 | Builder accepts | `evidence accept` | builder stops |
| 3 | Patch + proof stored | `publishBuild`; `fullrun._recordBuild` (outside the ledger CAS closure) | outcome refused, step stays pending, re-record after repair |
| 4 | Verifier retrieves | `verifyFromCustody`; `fullrun._verifyFromCustody` | work deferred (existing `awaiting-action`), never re-dispatched |
| 5 | Outcome recorded | `publishVerdict` | deferred |
| 6 | Before READY / PR | `evidence ready` re-reads the whole chain; requires dispatch -> build -> verdict with a mechanical verdict of `pending` | not ready, exit 4 |

`BLOCKED: provenance unavailable` is exit 4 everywhere. Without custody, `full run --verify`
now defers (with that banner) instead of re-dispatching. A mechanical verdict is never
acceptance; `ready` says `independentVerifierRequired: true`.

## 5. Tests

See section 7 for results. New files: `tests/steward/test_custody.py` (library, real git,
separate clones, "cloud A disappears" = `rmtree`), `test_custody_fullrun.py` (full runner
across two checkouts), `test_custody_cli.py`.

| Required scenario | Test |
|---|---|
| Cloud A dispatches, B verifies after A is gone | `test_cloud_a_dispatches_terminates_and_cloud_b_verifies_the_original`, `test_full_run_cloud_a_dispatches_and_builds_cloud_b_verifies_after_a_disappears` |
| Original authority, not today's policy | `test_restored_receipt_is_the_original_authority_not_todays_policy` |
| Missing / altered receipt | `test_altered_receipt_bytes_are_refused`, `test_missing_receipt_object_is_refused`, `test_altered_manifest_no_longer_matches_its_bundle_id`, `test_a_dispatch_edited_before_publication_is_refused` |
| Missing / wrong original scan | `test_missing_original_scan_is_refused_at_dispatch_time`, `test_a_scan_that_is_not_the_one_behind_the_dispatch_is_refused` |
| Wrong baseline, stale proof | `test_wrong_baseline_is_refused_on_restore`, `test_a_newer_local_dispatch_cannot_stand_in_for_the_original`, `test_a_proof_for_another_contract_is_stale_and_refused` |
| Missing / empty / malformed proof | `test_missing_empty_or_malformed_proof_is_refused` (5 cases), `test_an_empty_or_hunkless_diff_is_refused` |
| Interrupted persistence | `test_interrupted_push_leaves_nothing_visible_and_is_recoverable`, `test_push_that_lands_but_cannot_be_read_back_is_never_success_and_retry_is_idempotent`, `test_record_is_refused_while_custody_is_down_and_succeeds_once_repaired` |
| Concurrent writers | `test_concurrent_writers_preserve_every_bundle` (4 threads on 4 clones, one linear history) |
| Resume never duplicates | `test_resumed_run_does_not_duplicate_the_dispatch`, `test_resumed_full_run_does_not_publish_or_dispatch_twice` |
| No re-dispatch to legitimize a patch | `test_without_custody_a_missing_original_receipt_defers_and_never_redispatches` |
| Quiet day / blocked day | `test_quiet_day_is_a_genuine_noop`, `test_quiet_day_with_custody_enabled_is_a_clean_noop`, `test_full_run_blocks_when_dispatch_cannot_be_made_durable` |

These are **tests and simulations** (separate directories and clones on one machine). They
are distinguished from the real cross-environment run in section 6.

## 6. Real cross-environment handoff (not a test, not a simulation)

Executed 2026-11-13 against the real GitHub remote, using a clearly named **rehearsal ref**
`steward/evidence-rehearsal-2448` (selected with `GAIA_STEWARD_EVIDENCE_REF`; production
`steward/evidence` was **not** created). Identical code path to production; only the ref name differs.

| Step | Where | What happened |
|---|---|---|
| Live scan | cloud A (this session's container, PR head `0af8850d`) | `gaia steward scan`: 264 open debt, authority B=183, C=81, coverage unknown 0. Not a quiet day. |
| Dispatch | cloud A | `gaia steward dispatch debt:unused_import:scripts-archive-add-hermes-batch-py:d44c8312efe0535a --prompt --evidence git`. Real dispatch `dispatch-460979a6df78fdd0d323`, receipt `steward-20261113T064623Z-9b229a3774fcf358`, baseline `0af8850d988e32f0cd184ce643f5da298cec158f`. The prompt reached stdout only after custody printed "dispatch bundle fc09a9b1fe7d published, read back from 163fea52d0a3". |
| Build | cloud A, in a scratch worktree | `evidence accept` passed. A real two-line fix (remove `import os`, `from datetime import datetime`); finding reproduced by a real `gaia steward scan`; `compileall` and `pytest tests/steward/test_sensors_code.py` (155 passed) recorded in a valid proof transcript. `evidence publish-build` (model `sonnet-5-5`, effort `high`) stored diff + proof, read back from `eb523435`. |
| Handoff | **cloud B: a separate cloud session** (`session_018A6ag3sbPkcGdR5dneojRE`, Haiku 5.5 medium, host `vm`, fresh clone of the branch at `0af8850d`, no access to A's filesystem) | `evidence status` saw dispatch + build; `evidence verify` retrieved and authenticated the originals, ran the canonical mechanical verifier and published the verdict (read back from `14c9ad68`): **verdict `pending`**, exit 0; `evidence ready` exit 0. |
| Independent re-check | a third fresh clone of the real remote, by the lead | `evidence ready` exit 0, same bundle ids and hashes. |

Hash comparison (A's originals vs the bytes cloud B restored): dispatch receipt `2c7d9be4…96d0b`,
scan receipt `3f778a89…fa20`, diff `3b81aafb…1d0d`, proof `e2ffd934…aa0c` are identical on both hosts.
Bundle ids: dispatch `fc09a9b1…a7a`, build `5fb627c6…20af`, verdict `cfa0dea5…63a0`.
Verification receipt `steward-20261113T065439Z-cae03cf1b818c29d` (sha256 `c628b996…b41e`).

Limits of this evidence, stated plainly:

* The lead (this session) acted as dispatcher **and** builder, so no independent Steward
  builder/verifier pair ran. Cloud B produced only the **mechanical** verdict, which is `pending`
  (it can never be `accept`). No independent Sonnet 5.5 Medium verdict was obtained and none is claimed.
* The patch was never landed, the debt is still open, and no lane or ledger state was written.
  It is a rehearsal artifact, not repair work. #2445 was not touched.
* B's own report is another session's output; the hash comparison and third-clone `ready` above were
  re-run by the lead rather than taken from it.
* Cloud B's `.gaia/` already held an empty-looking `steward/` directory before its first step
  (created at session start); its step-7 listing shows only restored originals plus its own verify
  outputs.
* The full runner's cross-checkout path (ledger pointers) is covered by tests only, not run live.
  Nothing used the production `steward/ledger`.

Leftovers on the shared remote: ref `steward/evidence-rehearsal-2448` (3 bundles). Remove with
`git push origin --delete steward/evidence-rehearsal-2448` once reviewed; it affects nothing else.

## 7. Verification results

* `tests/steward/test_custody*.py`: 42 passed (library 32, CLI 4, full-run 6).
* Whole `tests/steward` directory: 4274 passed, **47 failed**, all in `tests/steward/prmaintenance/`
  (`test_executor`, `test_gate`, `test_r19_review_regressions`, `test_exact_tree`,
  `test_executor_processes`). The identical 47 fail on a clean `origin/main` worktree in this sandbox
  (jinja2/SSL/git-environment dependent), so none come from this change. (jinja2 was installed
  mid-session; failures remained.)
* Regression runs before/after the refactor: `test_ledger`, `test_cli`, `test_cli_contract`, `test_fullrun*`,
  `test_ordinary_shared_ledger` all pass.
* `scripts/quick_validate_skill.py` on the three edited skills, `scripts/validate_skills.py`
  (passed, warnings pre-existing), `scripts/sync_agent_skill_mirror.py --check`: pass.
* Finding in the base PR: `tests/steward/test_steward_skills.py` was red on #2449's original head
  (root skill 192 > 160 lines; `gaia steward full abandon` did not parse). #2449's own CI did not run it.
  Fixed here by moving the contract into `cloud-custody.md` beside the skill (root skill back to 160 lines).
* GitHub CI on the final head: see the PR (recorded in the handoff comment, section 9).

## 8. Risks and open items

1. **Trust anchor.** Anyone who can push to `steward/evidence` can write a dispatch bundle that is
   internally consistent (self-hashing receipts are not signatures). In full runs the ledger pointer
   (written only by the lease holder) is the authority anchor; standalone `evidence verify` does not
   cross-check the ledger. Recommend restricting pushes to `steward/*` to the Steward identity.
2. **Production ref not yet created.** The first real daily run with custody creates `steward/evidence`.
3. **Scheduler not changed.** `CLOUD_DAILY_BRIEF.md` is exact replacement text; until installed, daily
   agents will not use custody. The task's prompt does not name a gaia command, so adoption depends on the agent.
4. **Independence.** Custody enforces durability and authenticity, not agent independence. Builder != verifier
   remains enforced only by the full runner (`forbiddenAgentIds`) and the brief.
5. **Branch scope.** This PR is `infra/` but now touches `src/` and `tests/`; `branch-scope` will reject it
   unless a maintainer applies `skip-scope-check` (pre-authorized for labelling per `founder/CLAUDE.md`) or
   the work is re-homed on a `cli/` branch. I did not label or rename.
6. **Retention.** `steward/evidence` grows without bound (append-only by design); archival/compaction is a
   later, founder-gated decision. Per-object bound 8 MiB.
7. `lane next --evidence git` and `full run --evidence git` live runs were not performed; both are covered
   by unit/integration tests and share the code exercised live.

## 9. PR structure

#2449 is **extended**, not split. Its documentation-only guard and this implementation describe the same
six boundaries; a separate implementation PR would leave #2449 asserting "not implemented" and duplicate
policy text. The interim block was replaced (not duplicated) by `cloud-custody.md`. Trade-off: a larger
diff and the scope-check item above; mitigated by this document and a per-file map:
`src/gaia_cli/steward/custody.py` (store + bundles), `custody_ops.py` (boundaries), `fullrun.py`
(dispatch/record/verify hooks), `commands/steward.py` (CLI), `ledger.py` (CAS tail extracted), tests,
skills + mirrors, and `founder/steward/CLOUD_DAILY_BRIEF.md`.

## 10. Rollback

* Runtime: custody is opt-in. Unset `GAIA_STEWARD_EVIDENCE` / omit `--evidence git`; behavior is the
  pre-change path except that `full run --verify` no longer re-dispatches a missing receipt (that was a defect).
* Code: revert the PR's commits on the branch (or `git revert -m` the merge). `publishTree` is a pure
  extraction; `compare_and_swap` behavior is unchanged and covered by `test_ledger.py`.
* Scheduler: remove the appended section from the `Gaia Steward Daily` prompt (nothing was installed).
* Remote: `steward/evidence*` refs are append-only and unused by anything else; delete a ref with
  `git push origin --delete <ref>` (founder action).
