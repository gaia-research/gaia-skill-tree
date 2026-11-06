> Public copy of the bounded independent worker-dsflash review. Local home paths normalized only; tests are reviewer executions unless explicitly marked carried. This is NOT whole-source acceptance.

# Routine 19 — bounded independent review of F1 / F2 / F3 (worker: DSFlash)

Scope of this verdict is **only** the bounded F1/F2/F3 repair review assigned in
`f1-f2-independent-review-assignment.md`. It is **not** a whole-source acceptance, does not lift the
cloud WHOLE-SOURCE REJECT of `314fdf655`, and does not aggregate anyone else's test counts.

## 0. Verdict

**REJECT** — bounded F1/F2/F3 scope.

| Area | Verdict | Basis |
|---|---|---|
| F1 (no-ID failure finishing a matching outstanding shared sender) | **PASS** | Independent old→new probes reproduce the defect on `314f` and its absence on `31a9`, with local/shared state, slot, usage and invocation/effect counts unchanged in every control. |
| F2 (post-effect refusal mislabelled as `refused/shared-route-unavailable`) | **FAIL** | The reported 502 path is fixed and correlated, **but** the same wrapping turns **5 pre-existing tests RED that pass at `314f`** and removes the caller-visible distinction for definite, deterministic refusals (capacity exhaustion, completion-evidence mismatch, untrusted-completion binding). The immutable candidate is therefore not green, and no test migration accompanied the contract change. |
| F3 (founder receipt ruling / authority clarification) | **PASS** (documentation only) | Verbatim decision exists as commit `41f79697a` (18:42:50) before the clarification commit `72aba6635` (18:45:05); the included blob is byte-identical; prior ratification is preserved verbatim; scope is comment **writes** only and is consistent with the unchanged runtime. |

No duplicate send, no refund, no synthetic completion/tombstone, no replay and no capacity overrun was
demonstrated on any path I exercised (old or new). The blocking issue is a **reporting-contract
regression plus an unmigrated red suite**, not a demonstrated duplicate effect.

No provider access refusal occurred in this session; no retry, model fallback, context stripping,
rephrasing or nested agent was used. Provider/model used: `PI_PROVIDER=deepseek`,
`PI_MODEL=deepseek-flash`, `PI_REASONING_LEVEL=high` (the user-selected worker). The disclosed
OpenAI-whole-review refusal and the independent cloud REJECT of `314f` are carried unchanged and are
not re-run here.

## 1. Exact source binding (verified from Git objects, not from the proof document)

Review worktree: `$HOME/.gaia-worktrees/steward-r19-f1f2-review-dsflash-2283`

| Object | Value |
|---|---|
| HEAD | `31a9a59b9c978db19fd9a451ca310844d1dc401e` |
| HEAD tree | `02ce5633db8c56d20110af15f658f1653f1f9088` |
| Rejected baseline | `314fdf655edb7a6cb9bd131461bc11952366979d` / tree `e53b5920571b1458a6b6d0bde1fe454f57c7b411` |
| Technical repair | `3fad32497990b5d620295afb9399262ed08c15c3` / tree `e969c65e99797fd25eca06af572921da893b8773`, parent `314f` |
| F3 authority commit | `72aba66351dd0395073220131fad8e80878643b2` / tree `e2a19269b411d793dbb93323d9e37f76dff15cc1`, parent `314f` |
| Composition merge | `31a9` = merge of `3fad32497` + `72aba6635` |
| `git diff 3fad..31a9 -- src scripts` | **empty** (runtime identical to the reviewed repair) |
| Tracked worktree state | clean (`git status --porcelain` → 0 lines) before and after this review |

SHA-256 of the exact files the review read (extracted with `git archive`, so the bytes are the
committed bytes):

| File | 314f | 31a9 |
|---|---|---|
| `src/gaia_cli/steward/fullrun.py` | `cb65e1cf…2329d05e` | `b671139f…1fae2f7d3` |
| `src/gaia_cli/steward/prmaintenance/coordination.py` | `5a199ec9…5f2ded92df4b` | `41e64e44…b6c57398990c6c7a` |
| `src/gaia_cli/steward/prmaintenance/executor.py` | `14ea5fea…9dae6120caf104d` | `641cc535…254e4f8ac599f7f` |
| `src/gaia_cli/steward/prmaintenance/cli.py` | `ad06ca9b…665e2b7b62c0` | **unchanged** |
| `scripts/steward_drive.py` | `f4024565…3af63eb8360dd191` | **unchanged** |
| `tests/steward/prmaintenance/test_runner.py` | (old) | `4e913e3d…21668fb4e11af64` |
| `tests/steward/prmaintenance/test_executor.py` | (old) | `dc587697…6106db3c7e59a2` |

These independently match the hashes in `cloud-f1-f2-repair-proof.md`; nothing here is taken from that
document on trust.

**FULL `314f..31a9` diff reviewed**: 7 files — 3 runtime (`fullrun.py`, `coordination.py`,
`executor.py`), 2 test files, 2 founder documents. Every added/changed assertion in both test files was
read line by line, plus the surrounding production call boundaries
(`FullRunner.record`/`_applyRecord`/`_mutateRun`, `PrWriteCoordinator.invoke`/`_transition`/`inspect`,
`Executor.execute`/`report`, `cli.main`, `Driver.handlePrWrite`).

## 2. Method (disposable scratch only, no candidate mutation)

* Two scratch trees built with `git archive <sha> | tar -x -C $TMPDIR/r19-dsflash-review/{old,new}`
  — read-only object access, no worktree/ref/replace-ref mutation of the shared store.
* A third overlay tree `old-newtests` = `314f` runtime + the candidate's new test files (for the
  old-RED direction of the candidate's own assertions).
* Two probe files written **only** inside the disposable scratch trees, never in the candidate:
  * `tests/steward/prmaintenance/test_probe_dsflash.py` — sha256 `2672ac8a6146f8e0c8620cb6e2353bc93ad8aeedc1eac7813fe5aea2b7fbb65f`
  * `tests/steward/prmaintenance/test_probe_dsflash_contract.py` — sha256 `caf2a3e1a07f44594258df612600cf3b6eecf8eb6ccb0895a6c01ef16818a14b`
* Environment: Python 3.14.6, pytest 9.1.1, `PYTHONPATH=src`, `PYTHONDONTWRITEBYTECODE=1`.
  **Normal plugin loading**; the repo's own `pyproject.toml` guards were untouched and in force
  (`timeout = 60`, `timeout_method = "thread"`, `addopts = "-ra --strict-markers"`). No `-p` changes,
  no skips, no timeout increase, no deselect.
* **No** long suite, **no** background process, **no** live forge/network, **no** production
  namespace/ledger/clock/policy/registry/config, **no** install/activation/migration, **no** commit,
  push or merge. Parent source worktree never used for probes.
* All coordination remotes, forges and clocks in the probes are disposable local fixtures
  (`FakeServices`, `GitRefLedgerStore` on a scratch bare repo, `Forge` fixture, `Clock` fixture).

Evidence directory (this review's own logs):
`$HOME/gaia-skill-tree/.gaia/steward/campaigns/2026-11-05/routine19-shared/f1-f2-dsflash-evidence/`

## 3. F1 — verified repaired (with honest remaining limits)

Fix location: `src/gaia_cli/steward/fullrun.py:1941-1962` (new pre-CAS shared snapshot for a
no-ID `failed`/`refused`/`aborted` report), plus `fullrun.py:1963` changing the attachment test from
truthiness to `operationId is not None` so an empty ID can no longer bypass inspection.

The mutation callback (`prepared`, `fullrun.py:1997-2005`) still performs **only** local document work
and state revalidation; no shared read happens inside the CAS retry loop (confirmed by code and by
`test_cas_retry_refuses_concurrent_attachment_without_replaying_shared_inspection`, which passes on
`31a9`, and by `test_inspected_attachment_changed_on_cas_is_refused`).

### 3.1 Independent old-vs-new probe matrix (my runs)

`PROBE` lines from `probe-old-tree-314f.log` / `probe-new-tree.log` (shared op = same run, matching
subject, `state=unknown`, active slot, usage `(1,1)`, 1 invocation/1 effect in the fixture):

| Probe | 314f (rejected baseline) | 31a9 (candidate) |
|---|---|---|
| no-ID `failed` + matching outstanding sender | **RECORDED**, local `done/done` | **REFUSED**, local `pending/awaiting`, shared `unknown`, slot held, `(1,1)`, 1/1 |
| no-ID `refused` (same fixture) | RECORDED, `done/done` | REFUSED, `pending/awaiting` |
| no-ID `aborted` (same fixture) | RECORDED, `done/done` | REFUSED, `pending/awaiting` |
| no-ID `failed`, **empty** shared store (never sent) | RECORDED, `done/done` | RECORDED, `done/done` (never-sent path preserved) |
| no-ID `aborted`, matching sender under a **foreign runId** | RECORDED | RECORDED (foreign run remains distinct) |
| no-ID `aborted`, matching sender only **prepared** (`intent`, never invoked) | RECORDED | **REFUSED** (conservative; 0 invocations/0 effects) |
| no-ID `failed`, **terminal** matching sender (`completed-effect`) | RECORDED | RECORDED; shared truth unchanged; 1/1 |
| no-ID `failed`, `inspect()` raises `Refused` (protocol/clock) | RECORDED | **REFUSED** (`RecordRefused`) |
| no-ID `failed`, shared **repository binding mismatch** | RECORDED | **REFUSED** |
| no-ID `failed` with `operationId: ""` | **RECORDED** (the bypass) | **REFUSED** (`no recorded shared …`) |
| no-ID `failed` with `operationId: "zz"` / 63-hex | REFUSED | REFUSED |
| close action, matching close sender (reason+replacement equal) | RECORDED | **REFUSED** |
| close action, sender reason differs | RECORDED | RECORDED (scope distinguishing control) |
| shared snapshot empty, sender appears afterwards | RECORDED | RECORDED (documented non-atomic limit, see 3.3) |

Assertions test **real object state and effects**, not mocked verdicts: local action/step status is read
back from the persisted run document (`runner._load()`), shared truth from `coordinator.inspect()`,
capacity from `core.usage(...)`, and effect counts from the fixture services/forge
(`len(services.invocations) == len(services.effects) == 1`). The primary new test feeds the **actual**
unattended-driver abort report (`scripts/steward_drive.py:599-610`, `Driver.handlePrWrite`) into
`runner.record`, so the production interlock is exercised, not a synthetic dict.

### 3.2 Old-RED / new-GREEN for the candidate's own assertions

`candidate-tests-on-old-runtime-314f.log` (31a9 tests on 314f runtime): **9 failed, 12 passed**
(F1 primary + close-matching + physical-ID + binding-mismatch + missing-binding/read-failure fail;
foreign-subject, terminal-matching, never-attached, pre-send refusal pass). On 31a9 the same nodes are
green (`16 passed` for the eight F1 nodes in my run; parent runner group `89` is carried evidence, not
my count).

### 3.3 Remaining limits — assessed as honest limits, **not** new safety regressions

1. **Cross-store snapshot, not a transaction.** The shared read happens before the separate local CAS;
   a sender reserved/claimed after that read is invisible. Probe `F1-snapshot-race`: local action
   `done/done` while the later sender is `unknown`, active, `(1,1)`, 1 invocation. The code comment says
   exactly this (`fullrun.py:1948-1951`); no atomicity or exactly-once claim is made in code or proof.
   This narrows, and does not close, the window; it is strictly better than `314f` (which never read).
2. **Prepared-only senders are conservatively blocked.** A shared `reserved`/`intent` sender (never
   invoked, 0 effects) also refuses the local failure report. Fail-closed, but it is a new operational
   requirement: the prepared-but-unsent shared operation must be canceled (`executor.abort`) or expire
   before the local report can be recorded. After two refused records the unattended driver stops the
   run and the action waits for lease-TTL supersession — no deadlock, but a visible stall.
3. **Terminal match is not attached.** A no-ID `failed` report while a matching sender is
   `completed-effect` is still recorded locally as `failed`/`done` with no `operationId`
   (`F1-matching-terminal`). No replay is possible for that step, but local truth then disagrees with
   shared truth (local "failed", shared "completed-effect"). Carried, not introduced.
4. **Physical identity is unavailable.** The local action carries no immutable PR/replacement IDs, so a
   same-number/different-physical-PR sender cannot be disproved: the matcher blocks instead of guessing
   (probe: `prId="different-physical-id"` → refused). Documented at `fullrun.py:1945-1947`.
5. **Subject-field equality is the only link.** Producer, head, base ref/SHA, action and (for close)
   reason/replacement must match exactly; any divergence is treated as *absence* (recorded), not as
   uncertainty. Same-run `unknown`/`possibly-sent`/`quarantined` differences are covered by the
   candidate's parametrized controls; I did not find a same-run case where divergence produces a
   duplicate effect, because the shared claim/slot guards still hold the single sender.

## 4. F2 — reported path fixed, but the repair breaks 5 pre-existing contracts

Fix locations: `coordination.py:76-77` (new `InvocationUncertain`), `coordination.py:706-724` (whole
post-adapter body wrapped; any exception → `InvocationUncertain("sole invocation outcome unavailable")`),
`executor.py:507-519` (`uncertain()` correlated outcome `{operationId, state: possibly-sent,
coordinationState: unavailable, repo, runId, number, headSha, action, reason}`, plus a guarded
post-invocation `inspect`).

### 4.1 The originally reported path is fixed (my reproduction, both runtimes)

| Probe | 314f | 31a9 |
|---|---|---|
| close PATCH effect applied, then synthetic **HTTP 502** (`F2-cli-close-502`, my probe + candidate test) | CLI exit 2, JSON `{refused: shared-route-unavailable}` **no** `operationId` (cloud P4 exactly) | CLI exit 2, JSON `operationId` + `state: possibly-sent` + `coordinationState: unavailable`, no `refused` |
| merge PUT effect applied, then 502 (`F2-merge-502`, my probe) | `executor.execute` raises `CoordinationError('response does not prove a completed effect or definite rejection')` | correlated `possibly-sent`/`unavailable`; shared `possibly-sent`, slot held, `(1,1)`, 1 invocation/1 effect; cold replay → `possibly-sent`, still 1 effect |
| completion returns evidence that fails `validateEvidence` (`F2-evidence-auth-failure`) | raises `CoordinationError('evidence does not bind the exact invocation')` | correlated `possibly-sent`/`unavailable`; 1/1; replay no new effect |
| settlement write fails (`_transition("complete")` refuses) | raises | correlated `possibly-sent`/`unavailable` (CLI exit 2, full JSON), 1/1 |
| recovery then +10 fixture days (`POST-EFFECT-MATRIX`) | n/a | `quarantined` → still `quarantined` after 10 days → replay `quarantined`; `(1,1)`; 1/1 |
| genuine pre-send kill-switch refusal | exit 2, `refused: kill-switch`, no `state`, state `intent`, 0/0 | **identical** (distinct refusal preserved) |
| refusal raised **inside** adapter entry after claim | `state: unknown` | `state: unknown` (unchanged pre-existing classification; not a "refused") |
| settlement succeeded, then **post-settlement inspect** fails (`POST-SETTLEMENT-INSPECT`, my probe) | not applicable (no such guard) | report `state: possibly-sent`, `coordinationState: unavailable` while shared truth is `completed-effect`, slot released, `(1,1)`, 1/1 |

No false *no-send* claim was found: every post-effect path reports uncertainty, never `refused` and
never a success it cannot prove. No synthetic completion, shared abort, tombstone or refund is issued
by the repair (code path only raises; verified by state inspection).

Two presentation notes (not blockers by themselves):

* In an uncertainty outcome the `state` field is a *knowledge* label (`possibly-sent`), not the observed
  store state; the observed state is only available via the pre-existing `reported()` (see the
  post-settlement inspect probe, where shared truth was `completed-effect`). The pair
  (`state`, `coordinationState: unavailable`) is truthful in direction, but the contract should say
  explicitly that `state` is a classification when `coordinationState` is `unavailable`.
* CLI exit `2` is returned for a genuinely completed operation when its settlement read fails; replay is
  blocked by terminal state, so no duplicate is possible, but an operator sees "not success".

### 4.2 The blocking finding — 5 pre-existing tests changed from GREEN to RED

My independent runs of the same node ids on both runtimes (logs in the evidence directory):

* `preexisting-contract-tests-old-314f.log` → **6 passed** (`314f`).
* `preexisting-contract-tests-new-31a9.log` → **5 failed, 1 passed** (`31a9`): the exact 5 the Parent
  reported.

| Failing test (31a9) | Old contract (314f) | New behaviour (31a9) |
|---|---|---|
| `test_post_effect_mismatch_cannot_invent_matching_merge_settlement[head]` (test_executor.py:539-553) | `pytest.raises(core.CoordinationError, match="^matching independently verified merge/parent proof unavailable$")` then quarantine/replay/usage/effect assertions | `executor.execute` returns `possibly-sent`; no exception |
| `…[base]`, `…[parents]` | same | same |
| `test_invalid_or_untrusted_completion_never_retires_or_refunds_sender` (test_coordination.py:479-497) | `pytest.raises(core.CoordinationError, match="exact invocation")` then `possibly-sent`/active/`(1,1)`/replay `ALREADY`/1 invocation | `InvocationUncertain("sole invocation outcome unavailable")` — type matches `CoordinationError`, message does not |
| `test_real_store_completion_generation_9_to_10_byte_boundary[one-byte-overflow]` (test_coordination_boundaries.py:176-221) | `except core.Refused` → asserts `"capacity"`, `result is None`, store bytes/generation unchanged, no double increment | `InvocationUncertain` is a *sibling* of `Refused`, so it is not caught → the test errors and **none** of its capacity assertions execute |

Classification — **contract/diagnostic regression with preserved safety controls, not a lost effect
control**. My own probes on `31a9` re-established every control the failing tests encode:

| Control | My probe evidence (31a9) |
|---|---|
| No invented merge settlement after a head/parents mismatch | `MISMATCH-head`: `InvocationUncertain` with `__cause__ = CoordinationError("matching independently verified merge/parent proof unavailab…")`; shared state never reaches `completed-effect`; recovery → `quarantined`; re-execute → `quarantined`; usage `(1,1)`; 1 invocation/1 effect. `MISMATCH-parents-cli`: exit 2, then recovery `quarantined`, `(1,1)`, 1 effect |
| No retire/refund/replay on an untrusted completion | `INVALID-COMPLETION`: cause = `CoordinationError("evidence does not bind the exact invocation")`; shared `possibly-sent`, active slot, charges `(1,1)`, replay status `already-applied`, 1 invocation/1 effect |
| Capacity refusal leaves the store untouched | `CAPACITY-REAL-BOUNDARY` (real 512 KiB persisted-byte fixture, one byte over): cause = `Refused("critical record capacity exhausted; settlement headroom reta…")`, generation 8→9 only for the claim, `storeUnchangedSinceCompletion=True`, shared `possibly-sent`, active slot, 1 invocation/1 effect |
| No refund / no replay after post-effect 502 | `POST-EFFECT-MATRIX`: `possibly-sent` → `quarantined` → held after +10 days → replay `quarantined`; `(1,1)`; 1/1 |

What is genuinely lost at the caller boundary (the reason this cannot be accepted as-is):

1. **Distinct definite refusals are collapsed into generic uncertainty.** `capacity exhausted` and
   `completion-evidence mismatch` are deterministic conditions the operator could previously
   distinguish; now the CLI prints one generic sentence and drops the cause. The cause survives only
   in-process (`__cause__`), which the CLI does not surface.
2. **The invariants are no longer asserted.** The 5 tests still exist and still fail, so the controls
   above are currently verified only by *my* probes — not by the suite. Deleting/loosening them would
   be weakening; migrating them strictly (assert `InvocationUncertain`, its `__cause__`, and every
   state/charge/no-replay/capacity assertion) is the acceptable path.
3. **The suite is internally contradictory.** The candidate's own new test
   `test_post_effect_errors_remain_correlated_even_when_shared_write_fails` encodes the new
   uncertainty contract, while the 5 pre-existing tests encode the old definite-refusal contract.
4. **Proof-gate completeness gap.** The candidate proof lists only the focused new nodes (12 / 29 / 14
   passed) and says "existing guard tests … were not removed or skipped", but never ran
   `test_coordination.py` / `test_coordination_boundaries.py` / the pre-existing executor guards, which
   the change breaks. The parent long groups are what surfaced it.

## 5. F3 — verified (documentation only)

* Verbatim founder reply recorded exactly as `"git is best effort, not preconditions"` in
  `founder/reports/steward-campaign-2026-11-05/R19_RECEIPT_FOUNDER_DECISION_20261106.json`, whose blob
  is `bdd6fe9a6b86ca66c9e8a0f9ca3a15349fb3a346` — identical in commit `41f79697a` (18:42:50, on
  `dev/steward-campaign-2026-11-05`) and in the candidate `31a9`.
* Ordering: `41f79697a` (18:42:50) precedes `72aba6635` (18:45:05); `72aba` is the clarification commit
  that introduces the same blob into this line. `41f79697a` is **not** an ancestor of `31a9` (it lives
  on the campaign branch); the identical bytes are composed into the candidate by the `31a9` merge. The
  assignment's "committed before" claim is therefore substantively true, with that branch nuance.
* `founder/steward/decisions/steward-pr-maintenance-authority.json:17-18` adds the clarification and
  the ordering record; `:20` and `:22` restate it in `recommended`/`unblocks`. All pre-existing lines
  (including "GitHub receipts" in the decision text, the verbatim founder directives, the activation
  conditions and the POLICY ceilings line) are preserved; the diff is additive.
* Scope of the clarification is explicitly **posted comment/receipt writes only**; it explicitly keeps
  durable independent verification, pre-close justification, authentic API/effect evidence, required
  hold/comment reads, fail-closed checks, and shared Git/CAS/history guarantees; it explicitly denies
  activation, migration, quota, CLI-output, CI-churn and merge/release/deployment permission. It does
  not broaden authority.
* Consistency with runtime (unchanged since `314f`): `gate.py:315` "requireTrail is compatibility-only;
  receipt publication is never authority"; `receipts.py` only renders/checks/records; no write path
  requires a posted receipt (`cli.py` `receipt check` exits 3 when absent but is not a precondition of
  `execute`). So the clarification documents the code's actual behaviour; the old "each with GitHub
  receipts" wording was the stale half.
* Sequencing note for later activation (not a defect): the authority file is one of
  `gate.AUTHORITY_FILES` and its text is part of the coordination `bindingProof` source bytes. Any
  hypothetically in-flight operation prepared before the clarification would carry the old authority
  text; with the route dormant (`live activation holds` unchanged) there is no live effect, but the
  lesson applies before activation.

## 6. Assertion / coverage matrix (candidate's added tests)

| Candidate test (31a9) | Asserts real state? | Evidence used | 31a9 | 314f overlay |
|---|---|---|---|---|
| `test_no_id_failure_does_not_finish_matching_outstanding_sender` (test_runner.py:412) | yes | persisted action/step status, `inspect` state/slot/usage, fixture invocation/effect counts, real `Driver.handlePrWrite` abort | pass | **fail** (RED reproduced) |
| `test_never_attached_local_failure_remains_terminal` (:446) | yes | empty store `operations == {}` then local terminal record | pass | pass |
| `test_no_id_failure_ignores_foreign_shared_subject` (:463, 7 params) | yes | per-field foreign subject + shared state + counts | pass | pass |
| `test_no_id_close_subject_includes_reason_and_replacement` (:483, 3 params) | yes | matching refused; reason/replacement differ → recorded | pass | **matching fails** |
| `test_foreign_repository_binding_cannot_prove_absence` (:512) | yes | binding mismatch refuses; sender intact | pass | fail |
| `test_unavailable_physical_pr_identity_cannot_prove_foreign_subject` (:527) | yes | `prId` differs → refuses (cannot disprove) | pass | fail |
| `test_missing_binding_and_shared_read_failure_do_not_imply_absence` (:542) | yes | no factory / `LedgerUnavailable` inspect → refuses; action still pending | pass | fail |
| `test_no_id_failure_after_matching_terminal_does_not_change_shared_truth` (:565) | yes | terminal sender unchanged, local done | pass | pass |
| `test_cli_close_502_reports_correlated_uncertainty` (test_executor.py:165) | yes | CLI exit/JSON, shared slot/usage, forge fact, 1/1, recovery +10 days | pass | **fail** (cloud P4 reproduced) |
| `test_post_effect_errors_remain_correlated_even_when_shared_write_fails` (:200, 3 params) | yes | outcome + shared state + slot/usage + 1/1 + cold replay | pass | fail (all 3) |
| `test_cli_presend_refusal_remains_distinct` (:229) | yes | genuine pre-send refusal distinct, no invocation, `intent` | pass | pass |

Gaps I closed with my own probes (no candidate test covers them): prepared-only sender, terminal
no-ID match, `operationId: ""`, malformed ID, binding mismatch, `inspect()` refusing with a
`CoordinationError`, snapshot-then-sender race, merge 502, evidence-auth failure, post-settlement
inspect failure, real 512 KiB capacity boundary.

My run counts (do not sum with parent/cloud numbers):

| My run | Node scope | Result |
|---|---|---|
| `probe-new-tree.log` | 20 independent probe cases on 31a9 | 20 passed (probe harness), all `PROBE` lines green |
| `probe-old-tree-314f.log` | same 20 cases on 314f | 19 passed + 1 failing (`LedgerUnavailable` escapes the old CLI on the synthetic settlement patch — itself part of the F2 defect) |
| `candidate-tests-on-old-runtime-314f.log` | 21 candidate nodes on 314f runtime | 9 failed, 12 passed |
| `preexisting-contract-tests-old-314f.log` | 6 nodes | 6 passed |
| `preexisting-contract-tests-new-31a9.log` | 6 nodes | **5 failed, 1 passed** |
| `probe-contract-classification-new.log` | 7 independent classification cases on 31a9 | 7 passed, all control assertions green |
| `f1-cas-and-attached-controls-new.log` | CAS-race + attached-report controls on 31a9 | 6 passed |
| focused candidate F1 nodes on 31a9 | 8 nodes / 16 params | 16 passed |
| focused candidate F2 nodes on 31a9 | 3 nodes / 5 params | 5 passed |

**Carried evidence, not my runs:** parent long groups (`executor` 58 pass / 3 fail, `coordination`
76 pass / 2 fail, plus proof-gate 58, runner 89, ledger/driver 177 passing) and the cloud counts
(2967 overlapping whole `tests/steward`, 58/58/74/78/149 group numbers). They are **not** aggregated
here; my `31a9` rerun of the 6 contract nodes reproduces the same 5 failures deterministically.

## 7. Limits of this review

* I did not run the long grouped suites; the Parent owns them. I reproduced only the 6 contract nodes
  and the focused/parametrized nodes listed above.
* No live GitHub, clock, namespace, protection, ledger provisioning, metric or deployment surface was
  touched; real-transport behaviour remains unverified (carried hold).
* F4 quota/epoch ratchet, prepared-lease semantics, 2048 detail cap, non-merge method refusal, CLI
  design/after-before docs, historical shared-Git transition, writer drain and activation holds are
  **out of scope** and unchanged.
* This review neither accepts nor re-rejects whole-source `31a9`; the cloud WHOLE REJECT of `314f`
  stands, and source gates/coverage gaps remain independently open.
* No source fix, assertion change, commit, push, merge, ledger/forge/config/install action was taken;
  the candidate worktree remained clean throughout.

## 8. What the bounded scope needs to become ACCEPT-able

1. **Resolve the 5 red tests with semantically strict migration** (preferred) *or* narrow the wrapping
   so definite conditions stay distinguishable. Migration must assert: `InvocationUncertain`
   (or whatever definite type is chosen), the `__cause__` message for capacity / evidence mismatch /
   binding mismatch, shared state `possibly-sent` (then `quarantined` via recovery), unchanged
   store generation/bytes for the capacity case, usage unchanged `(1,1)`, 1 invocation/1 effect, and
   no replay. Deleting the `pytest.raises` or accepting "any exception" would be weakening.
2. **Surface the settled-vs-uncertain contract explicitly**, e.g. a distinct settlement-refusal type
   whose cause is reported (or an explicit `observed: false` / `uncertainty: <cause>` field), so an
   operator can tell "capacity exhausted, cannot be settled" from "transport unknown" — without
   reintroducing a false `refused`/no-send claim.
3. **Add executor/CLI-level coverage** for capacity exhaustion, completion-evidence mismatch,
   untrusted-completion binding and post-settlement inspect failure (currently only my probes).
4. **Document the prepared-only operational consequence** (cancel/expire the shared preparation before
   a local no-ID failure can be recorded; run stalls up to the lease TTL otherwise).
5. Re-run the full Steward groups on the resulting immutable candidate and obtain independent
   verification; do not accept on focused nodes alone.
