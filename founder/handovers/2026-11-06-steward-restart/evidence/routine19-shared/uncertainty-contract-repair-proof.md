# F1/F2 uncertainty-contract repair — bounded completion report

Status: candidate committed for Parent-owned long groups and independent verification.
This document is a builder report. It is **not** acceptance, not source approval, and not an
activation grant. The independent review `f1-f2-dsflash-independent-review.md` (run
`8f321497`) is the reviewer's own record; its REJECT of `31a9` stands for that subject. This
repair is a new immutable candidate, not a self-review of it.

## 1. Identity and binding

- Worktree: `$HOME/.gaia-worktrees/steward-r19-uncertainty-contract-2283`
- Branch: `dev/steward-r19-uncertainty-contract-2283`
- Base / prior candidate (unchanged): `31a9a59b9c978db19fd9a451ca310844d1dc401e`, tree `02ce5633db8c56d20110af15f658f1653f1f9088`
- Rejected source (unchanged): `314fdf655edb7a6cb9bd131461bc11952366979d`
- Handoff `b69df2e55e9c74ff0702209c4f80a3aaa45a51de` (unchanged, not touched)
- New candidate: `3bf9093b994fa0fa7700bbd0d4642fa26b7bc87a`, tree `070cd00ffb515dd7626cb1f08cbefe8b612d322d`, parent `31a9a59b9…`
- Commit author/committer: Marcus Rafael B. Tiongson `<153011150+mbtiongson1@users.noreply.github.com>`; commit made with per-command identity and `--no-gpg-sign`. No global configuration was read or changed. No push, merge, PR, release, activation or live operation was performed.
- Tracked worktree clean after the commit; only the five intended paths are in the commit.

Changed paths (source, then directly needed focused tests):

| Path | SHA-256 at `31a9` | SHA-256 at `3bf9093b9` |
|---|---|---|
| `src/gaia_cli/steward/prmaintenance/coordination.py` | `41e64e4426c2671de300c79a3e52aed9ca826b5c5a343868b6c57398990c6c7a` | `131a2a25f4fa7cce03213a94380fe2b113dbf3bd555a0817183107a488fa458c` |
| `src/gaia_cli/steward/prmaintenance/executor.py` | `641cc53510478df9d45084cd8836755b81c83a9526cdf0c31254e4f8ac599f7f` | `6184ffa9876eb0eed8f2f13a55f0d85995f8692f78f5b3630b67fe95b924e432` |
| `tests/steward/prmaintenance/test_coordination.py` | `47b996660cf8e49dc5b49607470a0089e99cf52529a489e9906281dcc8c962b7` | `d565ccb61323479a51f5fee0fb69409a176f1577ad2c983dab33c92b03f04f66` |
| `tests/steward/prmaintenance/test_coordination_boundaries.py` | `5972fa564565b0517697982f80b18dd77519d9d4f7fdd741b81f8b609ffc5be7` | `374c69a7410be270996d54ae47f7a2953447f7b81dab63f6e2cd0b46863fce1f` |
| `tests/steward/prmaintenance/test_executor.py` | `dc587697e278767956dd240c490c49890cac207e6d567adbc86106db3c7e59a2` | `6d4f2ec17222d89794aa023b0d50d8b2962d839323a727ee03d68db1c8dab7a9` |

Unchanged in this repair (identical to `31a9`; no F1 widening, no CLI change, no authority/policy/docs change):

- `src/gaia_cli/steward/fullrun.py` `b671139f2040b386e970d2cee2d1b6267f3d030f7232af6d8ccab481fae2f7d3`
- `src/gaia_cli/steward/prmaintenance/cli.py` `ad06ca9b03b3d509f54d199b7ba26b46ce019718bc3477ae2af6965e2b7b62c0`
- `scripts/steward_drive.py` `f4024565fccf466888ff4c06ac41d264030854d7855a9e703af63eb8360dd191`
- `founder/steward/**` authority records, `POLICY.yaml`, registry, docs, `docs/en/cli-reference.html`, schema, caps/leases/history, producers and all live/deployment surfaces.

Evidence root (logs are new and local; nothing there is committed):
`$HOME/gaia-skill-tree/.gaia/steward/campaigns/2026-11-05/routine19-shared/uncertainty-contract-logs/`

## 2. Why this repair exists

The independent DSFlash review (`8f321497`, report in this directory) verified F1 and F3, and
verified that the originally reported F2 path (real effect, then HTTP 502) was fixed, but
found five pre-existing contract/diagnostic regressions on `31a9`: post-entry failures had been
collapsed into one generic `InvocationUncertain("sole invocation outcome unavailable")`, so
(a) definite capacity refusal, (b) invalid completion binding/proof and (c) unknown transport
outcome were no longer distinguishable at the caller, and the suite contradicted itself while
the safety controls were only verified by the reviewer's probes.

Its §8 remediation items, and what this repair does:

1. strict migration of the five red tests, asserting the typed marker/cause plus every original
   state/store-byte/generation/slot/charge/no-replay/invocation/effect control — **done**;
2. a typed/sanitized cause visible to the caller, distinct for capacity vs invalid completion
   binding/proof vs transport unknown, without raw exception text or a false no-send claim —
   **done** via `InvocationUncertain.cause` and the executor's `uncertaintyCause` (bounded enum);
3. executor/CLI coverage for capacity, completion-evidence mismatch, untrusted completion
   binding and post-settlement inspect failure — **done** (four new focused tests);
4. document the prepared-only match operational consequence — **documented in §8 below**;
5. re-run full Steward groups and obtain independent verification — **parent-owned, not done here**.

No F1 matching logic, F3 authority/policy, F4 caps/limits, leases, history schema, proxy,
detail-cap or merge-method behaviour was changed. The CLI output change (uncertainty instead of
a false refusal, plus the new bounded cause field) remains under the founder before/after gate.

## 3. Baseline RED on the untouched base (`31a9`)

Run before any edit, in this worktree, tracked tree clean, normal plugin autoload, `PYTHONPATH=src`,
`PYTHONDONTWRITEBYTECODE=1`, unchanged `pyproject.toml` guards (`timeout = 60`,
`timeout_method = "thread"`), no `-p` plugin flags, no skips, no timeout increase, fixture-only
remotes/forges/clocks.

| Group | Node(s) | Command log / junit / exit | Result |
|---|---|---|---|
| executor | `test_post_effect_mismatch_cannot_invent_matching_merge_settlement` | `oldred-executor.log` / `.junit.xml` / `.exit` = 1 | **3 failed** in 27.79s (`DID NOT RAISE CoordinationError` for head/base/parents) |
| coordination | `test_invalid_or_untrusted_completion_never_retires_or_refunds_sender` | `oldred-coordination.log` / … | **1 failed** in 2.69s (expected `exact invocation`, got `sole invocation outcome unavailable`) |
| coordination boundary | `test_real_store_completion_generation_9_to_10_byte_boundary` | `oldred-boundary.log` / … | **1 failed, 1 passed** in 11.94s (`InvocationUncertain` escaped instead of `Refused`; exact-fit passed) |

Command shape (one node group at a time):

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q \
  --junitxml=<logdir>/oldred-<group>.junit.xml <node...>
```

These reproduce the Parent's five failures exactly; the Parent's `parent-31a9-*` artifacts were
read for context and are not counted as this worker's runs.

## 4. Classification of the five failures

All five are **necessary contract migrations** of an intentionally changed output contract, not
lost effect controls. F1 is untouched. The safety controls the tests encode were re-established
below with real fixtures. A "generic any-exception" catch was not used; removing the old
assertions would have been weakening, so each was replaced by stricter typed assertions.

### 4.1 The repaired post-entry contract

- `coordination.CapacityRefused(Refused)` — the persisted-record capacity check now raises a
  typed subclass (still an `isinstance(..., Refused)`); definite capacity exhaustion is
  distinguishable from other refusals without string matching.
- `coordination.CompletionInvalid(CoordinationError)` — the sole response or its evidence did not
  match the exact invocation/proof (unauthentic response object, merge/parent/close proof
  mismatch). Raised only by `ProductionServices.completion`; messages unchanged.
- `coordination.CompletionUnavailable(CoordinationError)` — the response cannot authenticate any
  definite outcome (non-200/opaque body, e.g. the 502 fixture): transport unknown.
- `coordination.InvocationUncertain(CoordinationError)` now carries a **bounded, sanitized**
  `cause` ∈ `capacity | completion-failed | persistence | transport`. It is raised only after the
  sole adapter was entered. The authentic underlying exception is kept in-process as
  `__cause__` and is never published.
- `executor.execute` reports `{operationId, state: "possibly-sent", coordinationState:
  "unavailable", uncertaintyCause: <cause|inspection>, evidenceSha256: null, …}`. `inspection` is
  executor-local: the shared report could not be read after a possible effect. No raw exception
  or raw evidence is serialized.

Classification map (post-entry only; pre-entry refusals still propagate as `Refused` and stay
distinct — see `test_cli_presend_refusal_remains_distinct`):

| Failing step | `__cause__` type | CLI `uncertaintyCause` |
|---|---|---|
| record the `unknown` transition after a lost adapter response | `CapacityRefused` / other | `capacity` / `persistence` |
| completion could not authenticate the sole response | `CompletionUnavailable` | `transport` |
| completion/proof mismatch, unauthentic completion, evidence validation | `CompletionInvalid` / `CoordinationError` | `completion-failed` |
| persist the `complete` transition | `CapacityRefused` / other | `capacity` / `persistence` |
| read the shared report after settlement | `ledger.LedgerUnavailable` | `inspection` |

`state` semantics (explicit): when `coordinationState` is `unavailable`, `state` is a
**knowledge classification** (possibly-sent), not an observed store state. Observed store state
is only reported by `reported()` after a successful shared read. The post-settlement-inspect test
shows the honest split: shared truth is `completed-effect` and the slot is released, while the
caller receives `possibly-sent / unavailable / inspection` because the report read failed. This
is truthful uncertainty, never a no-send claim; replay remains blocked by the terminal shared
state.

### 4.2 One-for-one assertion migration

**(A) `test_executor.py::test_post_effect_mismatch_cannot_invent_matching_merge_settlement[head|base|parents]`**

- Removed: `pytest.raises(core.CoordinationError, match="^matching independently verified merge/parent proof unavailable$")`.
  Rationale: `executor.execute` now returns correlated uncertainty for an intentional post-entry
  failure (F2 contract introduced in `31a9`), so the executor boundary no longer raises. The
  diagnostic is now typed at the coordinator boundary (`CompletionInvalid`) and sanitized to
  `completion-failed` at the executor boundary.
- Added (strict, observable): `result["operationId"] == operationId`, `state == "possibly-sent"`,
  `coordinationState == "unavailable"`, `uncertaintyCause == "completion-failed"`,
  `evidenceSha256 is None`, and `mergeCommitSha`/`observedState` absent — i.e. no invented
  settlement can be read from the report.
- Retained unchanged: shared `state == "possibly-sent"` and `evidence is None` (added for this
  test), active slot pinned, `usage(...,"merge") == (1,1)`, `recover → quarantined`,
  re-`execute → quarantined`, `invocations == effects == 1`.
- Net effect: stronger than before — it now asserts both the report and the shared truth, not
  just that raising happened.

**(B) `test_coordination.py::test_invalid_or_untrusted_completion_never_retires_or_refunds_sender`**

- Removed: `pytest.raises(core.CoordinationError, match="exact invocation")`.
  Rationale: post-entry failures are marked by `InvocationUncertain`; a regex search on the
  generic marker would no longer prove the authentic cause.
- Added: `pytest.raises(core.InvocationUncertain)`; `cause == "completion-failed"`;
  `__cause__` is `core.CoordinationError`; exact message equality
  `"evidence does not bind the exact invocation"` (equality is stricter than the old regex).
- Retained unchanged: `invocations == effects == 1`, shared `possibly-sent`, active slot,
  `usage == (1,1)`, replay returns `ALREADY`, and replay adds no invocation.

**(C) `test_coordination_boundaries.py::test_real_store_completion_generation_9_to_10_byte_boundary[exact-fit|one-byte-overflow]`**

- Removed: `except core.Refused` (the marker is a sibling of `Refused`).
  Rationale: settlement refusal after entry is uncertainty, not a no-send refusal.
- Added: catch `core.InvocationUncertain` only; assert exactly one of {returned result,
  uncertainty}; `cause == "capacity"`; `__cause__` is `core.CapacityRefused` and also a
  `core.Refused`; exact capacity message equality. The original
  `assert refusal is not None and "capacity" in str(refusal)` is retained verbatim.
- Retained unchanged: overflow returns no result (`result is None`); exact-fit completes
  (`status NEW`, `state completed-effect`); `calls == [8]` vs `[8, 9]` (no double increment);
  persisted tip/bytes unchanged from the captured pre-completion snapshot for overflow
  (generation 9); exact-fit generation 10 and exactly 524,288 bytes; both clients read the same
  tip; overflow keeps `activeOperationId` and `state possibly-sent` with `usage (1,1)`; replay
  returns `ALREADY` with one invocation; `invocations == effects == 1`. No threshold/profile/
  schema change.

**(D) `test_executor.py::test_post_effect_errors_remain_correlated_even_when_shared_write_fails`** (was green; strengthened)

- Added one line: `result["uncertaintyCause"] == {"completion": "completion-failed",
  "settlement": "persistence", "unknown-transition": "persistence"}[failure]`.
- All original correlation/state/slot/charge/no-replay assertions unchanged.

**(E) `test_executor.py::test_cli_close_502_reports_correlated_uncertainty`** (was green; strengthened)

- Added: the CLI JSON carries `uncertaintyCause == "transport"` for the 502 fixture.
- All original CLI exit/JSON/shared-state/recovery/+10-day/no-replay assertions unchanged.

### 4.3 New focused coverage (reviewer §8 item 3)

All fixture-only, disposable remotes/forges/clocks, no live surface:

- `test_cli_capacity_settlement_refusal_stays_sanitized_uncertainty` — CLI exits 2 with
  `operationId`, `possibly-sent`, `unavailable`, `uncertaintyCause "capacity"`, no `refused`,
  no raw `"critical record"` text, PR actually closed, shared slot/`(1,1)`, one invocation/effect,
  cold replay returns `possibly-sent` with still one effect (no replay).
- `test_completion_evidence_mismatch_is_sanitized_uncertainty` — evidence failing exact binding
  yields `completion-failed`; the rejected evidence bytes are not echoed; shared `possibly-sent`,
  slot, `(1,1)`, one invocation/effect, no cold replay effect.
- `test_untrusted_completion_binding_is_sanitized_uncertainty` — an untrusted completion
  (authenticity check) yields `completion-failed`; same state/slot/charge/no-replay controls.
- `test_post_settlement_inspect_failure_is_correlated_uncertainty` — a failed post-settlement
  report read yields `inspection` while the actual shared truth is `completed-effect`, slot
  released, `(1,1)`; cold replay is a terminal report (`closed`) with no new effect.

## 5. GREEN at the committed candidate

Same environment and guards as the baseline. Final runs at `3bf9093b9` / tree `070cd00ff`:

| Group | Command log / junit / exit | Result |
|---|---|---|
| focused executor regression + F2 + new coverage | `green2-executor.log` / … / `.exit` = 0 | **12 passed** in 127.68s |
| coordination diagnostics (invalid completion + 9→10 boundary) | `green2-coordination.log` / … = 0 | **3 passed** in 15.25s |
| executor completion/terminal surface (binding, success, lost response, rejection, close race, post-merge read) | `green2-executor-completion-surface.log` / … = 0 | **8 passed** in 84.34s |
| F1/F2 attachment regressions (same-run/foreign subject, close reason+replacement, missing binding/read failure, CAS race, physical-ID uncertainty, terminal no-op, attached unknown failures) | `green2-f1-attachment.log` / … = 0 | **30 passed** in 134.87s |
| positive controls (real current-source proof round trip, max source escaping exact outcome/generation headroom, worst bounded transitions, lowered caps, lost-response negative observations) | `green2-boundary-positives.log` / … = 0 | **8 passed** in 42.41s |

Total across these non-overlapping focused runs: 61 passed, 0 failed, 0 skipped, all exit 0.
Intermediate `newgreen-*` logs from an earlier WIP iteration (single-stage design) are preserved
but superseded and are not counted.

Observed boundary facts (from the boundary test's own prints, `green2-coordination.log`):

```
completion-probe overflow=0 returned-state=completed-effect refused=False cause=None persisted-bytes=524288 generation=10 invocations=1
completion-probe overflow=1 returned-state=None refused=True cause=capacity persisted-bytes=522994 generation=9 invocations=1
```

The overflow case leaves the store at the captured pre-completion generation/tip with the slot
held and one invocation/one effect; the exact-fit case settles at exactly 524,288 bytes.

## 6. Guards preserved

- `pyproject.toml` untouched: `timeout = 60`, `timeout_method = "thread"`, `-ra --strict-markers`
  unchanged; no new skips/xfails, no timeout increase, no config edit, no plugin disabling,
  no `-p no:cacheprovider` in the reported runs.
- `PYTHONPATH=src`, `PYTHONDONTWRITEBYTECODE=1`; module resolution from this worktree only.
- Existing 60 s per-test timeout, thread method, plugin autoload, multiprocessing barrier/join and
  cold-client controls are unchanged and exercised (F1 CAS/replay runs, boundary processes not run).
- Fixture-only effect counts; no production namespace, forge, clock, ledger provisioning,
  protection, install, push, merge, activation, drain or migration.
- No imports or runtime paths from the evidence root; the evidence directory holds only logs.
- No nested agents and no provider substitution. Prior provider-access history is disclosed in
  the assignment; no refused whole-review request was re-run, and no fallback was used.

## 7. Honest limits

- **Long groups are parent-owned and were not run here**: full `test_executor.py`,
  `test_runner.py` + `test_fullrun.py`, the full coordination trio
  (`test_coordination.py`/`_boundaries`/`_processes`), proof-gate and ledger/driver groups, and
  the whole `tests/steward` suite. The parent must run those on this immutable candidate; the
  focused coverage above is not a substitute.
- No live GitHub/forge, clock endpoint, namespace, protection, ledger provisioning, HTTPS/proxy/TLS
  or packaging/raw-failure/JUnit binding was exercised. Fake transports prove fixture behavior
  only.
- The capacity cause is proven by a real 512 KiB persisted-byte boundary at the coordinator; the
  executor/CLI capacity test injects the typed refusal to prove the caller mapping. No end-to-end
  real-remote capacity executor run was attempted.
- The post-settlement-inspect case deliberately reports uncertainty while the shared store holds
  a completed effect; that is the truthful direction but an operator sees exit 2 for a genuinely
  completed operation. Replay is blocked by terminal state, so no duplicate is possible.
- No cross-store atomicity or exactly-once claim is made (see §8).
- The CLI output surface now carries `uncertaintyCause` and uncertainty instead of a false
  refusal; this remains under the existing founder before/after gate for R19 CLI output.

## 8. Carried F1 limits and the prepared-only operational consequence

Unchanged by this repair; restated so it is not lost:

- The F1 shared read is a **snapshot taken before** the local run CAS callback. A different
  process may reserve or send for the same subject after that read and before the local CAS. The
  two stores have no transaction; local CAS rechecks local action changes, not a new shared
  event. No exactly-once or cross-store atomicity is claimed.
- Local actions do not carry immutable physical PR/replacement identities. The matcher therefore
  blocks a *possible* same-run subject match (repo, number, head SHA, base ref, base SHA,
  producer, action, and close reason/replacement) rather than guessing an operation ID; a
  mismatched repository binding does not prove absence, and missing binding/read failure fails
  closed.
- **Prepared-only consequence:** a shared sender in `reserved`/`intent` also matches. A local
  no-ID `failed`/`refused`/`aborted` report is refused while such a preparation exists, leaving
  the local action pending and the step awaiting. Operators must cancel/abort (or let it expire)
  the shared preparation before recording the local failure. Until then the run can stall up to
  the preparation lease TTL (`PREPARATION_SECONDS = 120`), and there is no takeover CLI; abort
  followed by re-prepare is permanently tombstoned for the same subject. This is an operational
  consequence of failing closed, not a safety regression, and F1 matching was not widened.
- A matching shared terminal sender (`completed-effect`, ..., or `canceled-unsent`) does not block
  the local record after the report's own validated shared truth is unchanged
  (`test_no_id_failure_after_matching_terminal_does_not_change_shared_truth`).

## 9. Holds and non-claims

- This is **not** acceptance of `31a9`, `314f`, `3bf9093b9` or any whole source. The cloud
  WHOLE REJECT of `314f` stands; the reviewer's bounded REJECT of `31a9` stands for that subject.
- F3 founder receipt ruling, authority records and policy are untouched; the ruling remains as
  ratified in `72aba6635` (composed in `31a9`); no receipt semantics were reinterpreted.
- F4 quota/epoch ratchet, preparation lease semantics, 2048-byte detail cap, non-merge method
  refusal and all other excluded surfaces are unchanged.
- CLI/desk before/after, historical shared-Git transition, namespace/protection/clock/writer
  drain/activation and CI-churn edit permission holds all remain. No CI-churn permission is
  claimed by this work.
- No push, PR, merge, deployment, release, install or migration was performed, and no global
  configuration changed.
