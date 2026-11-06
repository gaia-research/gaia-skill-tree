# Cloud F1/F2 repair proof

## Historical partial attempt (superseded by the candidate section below)

The prior 314 candidate and the independent cloud REJECT remain rejected. No self-acceptance. P3/P4 scratch sources were unavailable; the two probes below are independently reconstructed, not cloud scripts. No fix, green result, candidate commit or long-group results exist in this attempt.

## Identity and source

- Branch `dev/steward-r19-cloud-repair-2283`; HEAD `314fdf655edb7a6cb9bd131461bc11952366979d`, HEAD tree `e53b5920571b1458a6b6d0bde1fe454f57c7b411`.
- `PI_PROVIDER=openai`, `PI_MODEL=gpt-6.1-terra`, `PI_REASONING_LEVEL=high`. No nested agent.
- `PYTHONPATH=src` resolves the runner, coordinator, executor and CLI modules in `$HOME/.gaia-worktrees/steward-r19-cloud-repair-2283/src/gaia_cli/steward/` (the latter three under `prmaintenance/`). The focused run below explicitly used that path. A plain Python module-path check without `PYTHONPATH` failed with `ModuleNotFoundError`; it is not evidence of the test import path.
- SHA-256 working-tree source bytes (unchanged from HEAD):
  - `src/gaia_cli/steward/fullrun.py`: `cb65e1cf032de51e1c1420296d0c2fda043052ad74c4fed2391879ba2329d05e`
  - `src/gaia_cli/steward/prmaintenance/cli.py`: `ad06ca9b03b3d509f54d199b7ba26b46ce019718bc3477ae2af6965e2b7b62c0`
  - `src/gaia_cli/steward/prmaintenance/coordination.py`: `5a199ec9080486ef683d5078dd9fc3d2fc8ef469354f327ae6205f2ded92df4b`
  - `src/gaia_cli/steward/prmaintenance/executor.py`: `14ea5fea737142f9286b51016441497ed1038f68aee01f8639dae6120caf104d`
  - `scripts/steward_drive.py`: `f4024565fccf466888ff4c06ac41d264030854d7855a9e703af63eb8360dd191`
- Uncommitted reconstructed probe files (these hashes are NOT the HEAD tree): `tests/steward/prmaintenance/test_runner.py` SHA-256 `33dd0badd830779f2578c8a90299856f2cf4cb2e3d8805b224655829d8d70565`; `tests/steward/prmaintenance/test_executor.py` SHA-256 `70ce3b593005a686bbec24d706cd7a83f37443dd2c0ed1b1309d2e27a82ec869`. Tracked tree is dirty with these two test files only.

## Before: expected invariant RED

Command (exit 1, 2 failed, 16.34s):

```sh
PYTHONPATH=src python -m pytest -q -p no:cacheprovider \
  tests/steward/prmaintenance/test_runner.py::test_no_id_failure_does_not_finish_matching_outstanding_sender \
  tests/steward/prmaintenance/test_executor.py::test_cli_close_502_reports_correlated_uncertainty
```

- F1: real `coordinated(lost=True)` disposable shared coordinator fixture with PR 2270 and matching action subject and actual local run ID. Prior to the report, assertions proved shared `unknown`, its operation occupied the active slot, usage `(1,1)`, and one invocation/one effect. A no-ID failed report made local action `done` rather than the asserted `pending`. The following step and post-record shared assertions were not reached and thus are not claimed.
- F2: fixture-only production executor and CLI, close action PR 2270, actual close effect followed by synthetic HTTP 502. Exit 2; the shared operation was actually `possibly-sent`, its active slot held, usage `(1,1)`, fixture PR closed, one invocation and one effect. CLI JSON instead contained `refused: shared-route-unavailable` and no operation ID; the correlation assertion failed. Recovery/+10-day assertions are in the probe but were not reached and are not claimed.

All coordination remotes and forge effects in the probes were disposable local fixtures; no live forge, production ledger, namespace, clock or configuration was accessed or changed. Existing guard tests and plugin settings were not removed or skipped.

## Historical after / remaining work at the partial stop

At that point, no remediation was implemented. No GREEN, independent review, immutable candidate, clean tracked tree or commit exists. Reproduce the unattended driver auto-abort path and all requested foreign-subject, exact scope/run, no-operation, missing-binding, read-failure, CAS-race and terminal controls; then implement the smallest coherent repair and re-run both invariant probes. In particular, establish when never-sent can actually be proven and document the cross-store read/local-CAS race; do not assume a shared read and local update are atomic. Check pre-send refusal separately from post-invocation uncertainty, including failure to persist an uncertainty transition. Validate all requested no-replay/no-refund guards. Parent owns the long test groups after an immutable candidate; none were run here. F3 governance needs founder ruling; separate CLI/legacy transition and activation holds remain. F4 and all other excluded authority/cap/lease/policy surfaces remain untouched.

## Resumed candidate — 2026-11-06

- Immutable candidate `3fad32497990b5d620295afb9399262ed08c15c3`, tree `e969c65e99797fd25eca06af572921da893b8773`, parent `314fdf655edb7a6cb9bd131461bc11952366979d`. Branch `dev/steward-r19-cloud-repair-2283`; tracked worktree clean after commit. The original 314 and b69 handoff remain unchanged. Author and committer Marcus Rafael B. Tiongson; per-command identity and signing disabled, no global config changed.
- Runtime: `PI_PROVIDER=openai`, `PI_MODEL=gpt-6.1-terra`, `PI_REASONING_LEVEL=high`. The earlier two RED results above were retained; the original cloud P3/P4 sources were not available and were not run. This is not the refused whole-review request and is not independent acceptance.
- Import binding: with `PYTHONPATH=src`, modules `gaia_cli.steward.fullrun`, `gaia_cli.steward.prmaintenance.coordination`, `.executor`, `.cli` resolve respectively under `$HOME/.gaia-worktrees/steward-r19-cloud-repair-2283/src/gaia_cli/steward/` and its `prmaintenance/` subdirectory.
- SHA-256 final source: `src/gaia_cli/steward/fullrun.py` `b671139f2040b386e970d2cee2d1b6267f3d030f7232af6d8ccab481fae2f7d3`; `src/gaia_cli/steward/prmaintenance/coordination.py` `41e64e4426c2671de300c79a3e52aed9ca826b5c5a343868b6c57398990c6c7a`; `src/gaia_cli/steward/prmaintenance/executor.py` `641cc53510478df9d45084cd8836755b81c83a9526cdf0c31254e4f8ac599f7f`; unchanged `src/gaia_cli/steward/prmaintenance/cli.py` `ad06ca9b03b3d509f54d199b7ba26b46ce019718bc3477ae2af6965e2b7b62c0`; unchanged `scripts/steward_drive.py` `f4024565fccf466888ff4c06ac41d264030854d7855a9e703af63eb8360dd191`; `tests/steward/prmaintenance/test_runner.py` `4e913e3d6759b4da062f1ab6cf545124670cddfafde306aca21668fb4e11af64`; `tests/steward/prmaintenance/test_executor.py` `dc587697e278767956dd240c490c49890cac207e6d567adbc86106db3c7e59a2`.

### Repair and observed guards

F1 reads validated shared truth before the local CAS callback for no-ID failure/refusal/abort. A same-run possible subject match in preparation or outstanding sender state refuses the report, leaving action pending and step awaiting; no ID is guessed or attached. Missing binding, wrong repository binding and shared read failure also refuse instead of inferring absence. A validated empty shared snapshot allows the never-sent local failure; foreign run, number, head, base ref, base SHA, producer, action, and close reason/replacement controls remain distinct. Existing local CAS attachment races are refused. The actual `Driver.handlePrWrite` auto-abort output was fed to the runner in the matching sender fixture. Shared unknown state, active slot, run/hour charges `(1,1)`, one invocation and one effect remain intact; the control with a terminal shared effect leaves shared truth unchanged. An empty operation ID now fails validation rather than bypassing inspection.

The local action does **not** contain immutable physical PR or replacement identities: consequently the matcher cannot establish an exact physical match or disprove one when all available fields match. It conservatively blocks a possible match (including the physical-ID-different fixture) rather than guessing an ID. The namespace pins repository identity but a mismatched binding does not prove absence. These are snapshot guarantees: a different process may reserve or send after the shared read and before the separate local CAS. The stores have no cross-store transaction; local CAS rechecks local action changes, not a new shared event. No exactly-once or cross-store atomicity claim is made.

F2 distinguishes errors raised after adapter entry from pre-send refusal. Completion authentication, completion settlement or unknown-transition errors return an operation-correlated `possibly-sent` outcome with `coordinationState: unavailable`; this is uncertainty, not an assertion of the current shared state. The 502 fixture applied the sole close effect; CLI exit 2 retained the operation ID, actual shared `possibly-sent`, active slot and `(1,1)` charges, and one invocation/effect. Recovery quarantined it and it stayed held after ten fixture days without replay. Separate completion and transition failure tests and a cold-executor replay check held at one effect. A kill-switch pre-send refusal retained its distinct `kill-switch` result, left the operation in intent, and invoked nothing. No synthetic completion, shared abort, tombstone or refund was issued by the repair.

### Focused commands

The final-source run used normal plugin loading (no `-p` changes), existing 60-second/thread guards and no skips: **12 passed in 83.61s**, exit 0:

```sh
PYTHONPATH=src python -m pytest -q \
 tests/steward/prmaintenance/test_runner.py::test_no_id_failure_does_not_finish_matching_outstanding_sender \
 tests/steward/prmaintenance/test_runner.py::test_never_attached_local_failure_remains_terminal \
 tests/steward/prmaintenance/test_runner.py::test_no_id_close_subject_includes_reason_and_replacement \
 tests/steward/prmaintenance/test_runner.py::test_foreign_repository_binding_cannot_prove_absence \
 tests/steward/prmaintenance/test_runner.py::test_cas_retry_refuses_concurrent_attachment_without_replaying_shared_inspection \
 tests/steward/prmaintenance/test_executor.py::test_cli_close_502_reports_correlated_uncertainty \
 tests/steward/prmaintenance/test_executor.py::test_post_effect_errors_remain_correlated_even_when_shared_write_fails \
 tests/steward/prmaintenance/test_executor.py::test_cli_presend_refusal_remains_distinct
```

Earlier focused run before only a comment and an added foreign-repository test: **29 passed in 180.98s**, exit 0; it included the two reconstructed invariant tests, seven foreign-subject/run cases, physical-ID uncertainty, missing binding/read failure, no-operation, three close-scope controls, terminal, both local CAS tests, attached sender failures, 502, completion/settlement/unknown-transition errors, genuine pre-send refusal, concrete merge/close success and lost-response recovery. That command used `-p no:cacheprovider` as in the prior partial, not the final normal-plugin command. An intervening normal-plugin focused run of **14 passed in 84.37s** included physical-ID and shared-read failure controls. Earlier development run had two test-harness assertion mistakes (wrong `status` API and expected refusal code); they were corrected and are not reported as product passes. `pytest` 9.1.1 with `pytest_timeout` available; no timeout or thread guards were altered.

### Pending, holds and limits

Parent owns long test groups and independent verification against this immutable candidate; they were not run here. Cloud whole-source REJECT and other carried rejections remain; no self-acceptance. F3 receipt governance requires founder ruling. Separate CLI/design, legacy shared transition, provisioning, protection, drain and activation holds remain. No F4 caps/leases/detail/method, policy, schema, registry, global configuration, live GitHub, production coordination ledger/namespace/clock or external operational surfaces were modified; no push or merge.
