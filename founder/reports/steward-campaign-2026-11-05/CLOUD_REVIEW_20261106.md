> User-supplied independent cloud report. Public copy fingerprints the cloud session identifier only. Results below are the cloud reviewer's reported executions, not additional Parent runs. Original text is retained in session evidence.

# Routine 19 independent whole-feature review (cloud, 2026-11-06)

## 1. Verdict

**REJECT** for the whole frozen candidate `314fdf655edb7a6cb9bd131461bc11952366979d`, tree `e53b5920571b1458a6b6d0bde1fe454f57c7b411`.

The rejection rests on one demonstrated Medium defect (F1). It belongs to the same class as the 17ad rejection: local FullRun work finishes as a failure while a shared sender for the same PR subject stays outstanding and the effect really happened. F2 is the CLI half of the same problem. No duplicate invocation or effect, and no refund, was found anywhere I probed. Git interpretation, exact-tree materialization, the one-shot adapter, the clock and the transport all held under fresh negative probes with matching positive controls.

## 2. Identity, environment and bindings

- **Reviewer:** Claude Code agent in an Anthropic cloud session (`[cloud-session-sha256:d17b7ff9371a6a2a]`, environment kind `anthropic_cloud`). `get_session` reports configured model `claude-opus-5-5`, served model `claude-opus-5-5` and session effort `medium`. No provider refusal or access-control block occurred. No route change, fallback or nested reviewer agent was used.
- **Checkout:** a detached worktree at handoff HEAD `b69df2e55e9c74ff0702209c4f80a3aaa45a51de`. Git 2.43.0, Python 3.13.18.
- **Dependencies:** pytest 9.2.0 and pytest-timeout, installed in a scratch-only venv. Nothing global was changed. `pyproject.toml` keeps `timeout = 60` and `timeout_method = "thread"`. No plugin was disabled, no timeout raised, nothing skipped.
- **Baseline:** `3cd5504e…` has tree `9b29681b…`. Candidate `314fdf65…` has tree `e53b5920…`. Both were verified with `git rev-parse <c>^{tree}`.
- **Direct diff:** `git diff --name-status 3cd5504e 314fdf65` gives 36 paths, +4,947/−609, byte-identical to `SOURCE_DIFF.txt`.
- **Handoff delta:** `git diff --name-only 314fdf65 b69df2e5` touches only `founder/handovers/2026-11-06-r19-cloud-review/`, across 2 commits. Runtime and test bytes are unchanged.
- **Blob bindings at review HEAD:** these match the Parent binding file.
  - `proofs.py` 38592e83…
  - `test_exact_tree.py` b9c2f3e0…
  - `executor.py` d4ff046d…
  - `coordination.py` 3d98a3b3…
- **Worktree state:** clean after all runs.

## 3. Findings (most severe first)

### F1 — Medium (rejecting): a failure report without an operation ID finishes local work while the shared sender is outstanding

- **Where:** `src/gaia_cli/steward/fullrun.py:1932-1983` (`_recordPrWrite`).
- **Defect:** shared inspection runs only when the action already carries an `operationId` or the report supplies one. A `failed`, `refused` or `aborted` report with no ID marks the action and step `done`, even when the shared coordinator holds an outstanding sender for the identical subject (repo, PR, head, base, action, producer, run).
- **Demonstrated (fresh probe P3):** I used the repository's own `coordinated(lost=True)` fixture on PR 2270, `stable-run`, and recorded `{"state":"failed", … no operationId}`.
  - Local result: action `done`, outcome `failed`.
  - Shared state: `unknown`, 1 invocation, 1 effect.
  - The existing test `test_never_attached_local_failure_remains_terminal` covers only the case where no shared operation exists.
- **Reachable producers:**
  1. The unchanged unattended driver auto-settles every emitted `forge.merge_pr`/`forge.close_pr` as `aborted` and never attaches an ID (`scripts/steward_drive.py:599-610`).
  2. The CLI refusal output in F2 carries no ID.
- **Impact:** the local run, desk and report say "failed" or "aborted" for an effect that may have happened.
- **What still holds:** no duplicate send. The global slot and the logical-replay record keep refusing, and the hourly and run charges are retained.

### F2 — Medium/Low: `execute` reports `refused` after a real effect

- **Where:** `src/gaia_cli/steward/prmaintenance/cli.py:482-484` and `coordination.py:712`.
- **Defect:** when the sole invocation produced an effect but `completion` cannot authenticate it, `execute` prints `{"refused":"shared-route-unavailable"}` and exits 2. The output has no `operationId` and no state. In that case `completion` raises outside the adapter `try`, so the shared state is left `possibly-sent`.
- **Demonstrated (fresh probe P4):** the fake forge applies the close and then returns 502.
  - CLI: exit 2, `refused: shared-route-unavailable`.
  - Shared state: `possibly-sent`, 1 effect, PR `closed`.
  - P2: `recover` then quarantines the operation, and the slot stays pinned after +10 days. This is consistent with the documented "no TTL refund".
- **Impact:** a "refused" label on a possibly-sent invocation invites a driver to record a failure, which feeds F1.

### F3 — Governance, owner gate (not a code defect): receipts and the pre-close justification are no longer preconditions

- **Baseline:** the gates required the pickup and verification trail before a merge and the "closed" justification receipt before a close (`refusedClose(..., "justification-missing")`).
- **Candidate:** those assertions are inverted in `test_gate.py`:
  - `test_closure_without_adequate_evidence_is_refused`: `validateClose(...)["verdict"] == "pass"` with no justification.
  - `test_github_trail_is_best_effort_not_independent_verification`.
- **Why it needs a founder ruling:**
  - The campaign assignment and the routine doc state "best-effort WRITEs" as intended.
  - The unchanged ratified record `founder/steward/decisions/steward-pr-maintenance-authority.json` still reads "…merged… and … closed, each with GitHub receipts."
  - None of the 36 paths contains a founder ruling that changes it.

### F4 — Low, carried (not new): limits only ratchet down

- **Where:** `coordination.py:354`.
- **Behaviour:** `state["limits"] = min(history)`. One transient policy lowering, for example `hourlyWriteCap: 0`, permanently lowers that epoch's shared caps, so later policy can never restore them.
- **Status:** this is unchanged core behaviour that 6b9147 already accepted (the "competing-lowered-cap" probe). It fails safe but limits liveness.

### Observations (not demonstrated as defects)

- Preparation lease: the 120 s lease (`PREPARATION_SECONDS`) runs across separate `gate-*` and `execute` CLI processes, and `execute` re-authorizes, including fetches, before it claims. There is no takeover CLI; abort then re-prepare is permanently tombstoned for the same subject.
- Ambiguous reserve: if a reserve CAS acknowledgement is lost, the CLI prints no operation ID, and the prepared operation pins the global slot until someone derives its ID.
- `verification.detail` is capped at 2,048 bytes. A large verifier or builder record makes reserve refuse; this fails closed.
- `ProductionServices.authorize` hardcodes `method: "merge"`. A producer whose `mergeMethod` is not `merge` is refused; this fails closed.

## 4. Coverage matrix (36 paths plus core and callers)

Legend: R = read the full diff or file; P = fresh probe; T = fresh test run; S = skimmed (names, assertions, structure).

| # | Path | Coverage | Result |
|---|---|---|---|
| 1-4 | `.agents` and `.claude` skills: `gaia-steward-full`, `gaia-steward-pr-maintenance` | R; mirror `cmp` and `sync_agent_skill_mirror --check` = 0; `quick_validate_skill` = 0 ×2; `validate_skills` = 0 | Byte-identical mirrors; version 1.0.0 kept. Docs state "receipts best effort" (F3). |
| 5 | `docs/en/cli-reference.html` | R (diff) | Public copy changed; needs the founder before/after CLI gate (hold). |
| 6 | `founder/steward/README.md` | R | Consistent with source; no activation claimed. |
| 7 | `founder/steward/routine-coverage.json` | R (diff), JSON parse | OK |
| 8 | `founder/steward/routines/pr-maintenance.md` | R | Contract matches code; see F3. |
| 9 | `scripts/steward_drive.py` | R (diff and `handlePrWrite`) | Default ledger is `local`. PR writes are still refused, but auto-`aborted` without an ID feeds F1. |
| 10 | `src/gaia_cli/commands/steward.py` | R | `--ledger git` is refused before store access unless the action is `status`; no origin probe. |
| 11 | `src/gaia_cli/steward/desk.py` | R | `ordinary_local` suppresses the ledger-local warning. Visible desk change is under the CLI hold. |
| 12 | `src/gaia_cli/steward/fullrun.py` | R (diff); T (runner, fullrun); P3 | `_requireLocal` guards; shared binding of reports; **F1** |
| 13 | `src/gaia_cli/steward/ledger.py` | R; P (replace-ref and env probe via `plumb`) | `--no-replace-objects`, graft `/dev/null`, env scrub hold. |
| 14 | `prmaintenance/cli.py` | R; P4 | **F2**. Unconfigured route refuses before collection; `--auth` raw JSON refused. |
| 15 | `prmaintenance/collect.py` | R (diff and callers) | `prId`/`repositoryId` added. `ghApi` is still `gh` subprocess (read-only path). |
| 16 | `prmaintenance/coordination.py` (new) | R (all 735 lines); T; P1, P2 | CAS, chain, prefix cache, slot, fences, accounting, headroom and grants verified; F4 carried. |
| 17 | `prmaintenance/executor.py` (new) | R (all 569 lines); T; P1, P2, P4; clock and transport probes | One-shot entry burned before network; re-authorize after claim; credentials bound to origin. |
| 18 | `prmaintenance/gate.py` | R | Legacy bearer, reservation and finalize routes refuse or delegate; F3. |
| 19 | `prmaintenance/policy.py` | R | Strict binding: main only, GitHub-only URL form, clock contract bounds. |
| 20 | `prmaintenance/proofs.py` | R; T; P (env and attributes); P (bounds) | Exact raw blobs with SHA-1 re-verification; modes, symlinks, gitlinks and destination safety hold. |
| 21 | `prmaintenance/reconcile.py` | R | Hardened `git()` wrapper. |
| 22 | `prmaintenance/state.py` | R | Docstring-only change; legacy readers are diagnostics. |
| 23-36 | 14 test files (`coordination_helpers`, `test_coordination{,_boundaries,_processes}`, `test_exact_tree`, `test_executor{,_processes}`, `test_gate`, `test_resources`, `test_runner`, `test_fullrun_cli`, `test_fullrun_scenarios`, `test_local_full_state`, `test_steward_drive`) | T (all); S (names diffed vs baseline); R (key fixtures and the changed assertions) | Removed or renamed tests enumerated (§5). Timeout, barrier and join guards are present; no new skip, xfail or timeout increase found in the diff grep. |

Unchanged callers and readers checked:

- `gate.verificationFor` and `recordVerification` (host time is only checked against trusted bounds).
- `collect.liveSnapshot`, `mergeParents` and `listAll`.
- Other `steward/` Git callers (`fullrun._git`, `landing`, `repairs`, `primitives`, `challenge_receipts`). These are not R19 authority paths, and they are unchanged and unhardened by design.

**Not completed (disclosed):**

- I did not do a line-by-line read of every body in the 14 test files.
- I did not re-audit `docs/en/cli-reference.html` against every flag.
- Process-level fork, spawn and kill cases were covered only by the fresh test runs, not by independent probes.
- Real HTTPS, proxy and TLS behaviour of `HttpsTransport` was not exercised (no live network, by mandate).
- The 4 MiB listing cap and the 120 s shared deadline were not boundary-probed.

The REJECT stands on F1 regardless of these gaps. If F1 and F2 are repaired, these gaps must be closed before any ACCEPT.

## 5. Fresh commands, results and exits (mine)

Fresh runs from the review worktree at HEAD `b69df2e5`, with runtime and test blobs = 314f:

| Group | Command | Result | Exit | Start–end (UTC) |
|---|---|---|---|---|
| proof-gate | `python -m pytest -q -p no:cacheprovider tests/steward/prmaintenance/test_exact_tree.py tests/steward/prmaintenance/test_reconcile.py tests/steward/prmaintenance/test_gate.py` | 58 passed | 0 | 09:26:54–09:27:51 |
| executor | `python -m pytest -q -p no:cacheprovider tests/steward/prmaintenance/test_executor.py tests/steward/prmaintenance/test_executor_processes.py` | 58 passed | 0 | 09:26:54–09:27:59 |
| runner | `python -m pytest -q -p no:cacheprovider tests/steward/prmaintenance/test_runner.py tests/steward/test_fullrun.py` | 74 passed | 0 | 09:26:54–09:27:21 |
| coordination | `python -m pytest -q -p no:cacheprovider tests/steward/prmaintenance/test_coordination.py tests/steward/prmaintenance/test_coordination_boundaries.py tests/steward/prmaintenance/test_coordination_processes.py` | 78 passed | 0 | 09:26:54–09:27:42 |
| other changed | `python -m pytest -q -p no:cacheprovider tests/steward/prmaintenance/test_resources.py tests/steward/test_fullrun_cli.py tests/steward/test_fullrun_scenarios.py tests/steward/test_local_full_state.py tests/steward/test_steward_drive.py` | 149 passed | 0 | 09:27:59–09:28:48 |
| whole `tests/steward` | `python -m pytest -q -p no:cacheprovider tests/steward` | 2,967 passed (0 failed, 0 skipped reported) | 0 | 09:28:48–09:36:02 |

The four groups ran concurrently. Their counts match Parent's (58/58/74/78), but they are independent executions.

**Old red / new green (exact tree):** I copied the candidate's `test_exact_tree.py` into a worktree at rejected `e7f1933b`, with `PYTHONPATH` pointed at that worktree's `src` (import path verified). Result: **9 failed**, exit 1. These include `dropped_history_cannot_be_hidden_by_attributes[environment|info]`, `committed_attributes_do_not_hide_historical_index_rows`, symlink/missing paths and oversize/gitlink. On 314f the same file is green, inside the proof-gate group.

**Fresh probes:** these are scratch-only and not committed. All use disposable repositories and fake forges and clocks.

| Probe | What it does | Result |
|---|---|---|
| Git interpretation | `refs/replace` maps the real blob to `FAKE`. Positive control: plain `git cat-file` returns `FAKE`. Tried `GIT_CONFIG_COUNT`/`KEY`/`VALUE` `core.useReplaceRefs=true`, `GIT_CONFIG_PARAMETERS`, `GIT_NO_REPLACE_OBJECTS=0`, `GIT_REPLACE_REF_BASE`, and repo config `core.useReplaceRefs=true`, plus `export-ignore` and `export-subst` attributes. | `proofs.blob`, `proofs.git`, `exportBase` and `GitRefLedgerStore.plumb` all return `REAL`. `exportBase` keeps the export-ignored file and the unexpanded `$Format$`. |
| Bounds | 16,384 entries vs 16,385; 4×16 MiB (exactly 64 MiB) vs +1 byte. Real required roots at 314f are 52 regular blobs, 682,873 B (max 32,513 B). | Exact fit → True; +1 → False, in both cases. |
| P1 one-shot | After a merge: direct replay of the captured adapter call, a `copy.copy(services)` replay, `coordinator.invoke` with a different transition (Refused), the same transition (ALREADY), and a cold executor `execute`. | Invocations = effects = 1 throughout. |
| P2 | Close followed by a 502. | `possibly-sent` → `quarantined`; no change after +10 days; 1 effect. |
| P3 | Failure report without an ID (F1). | Local `done/failed`, shared `unknown`, 1 effect. |
| P4 | CLI `execute` against a close followed by a 502 (F2). | Exit 2, `refused`, no ID; shared `possibly-sent`; PR closed. |
| Clock | Each of: missing `no-store`, `Age: 3`, nonce mismatch, uncertainty 3 > 2, float seconds, extra field, status 203, RTT 2.5 s > 2, monotonic backwards, cross-sample regression, future jump. Control: `[998, 1003]`. | All 11 refused. |
| Transport | `http://`, userinfo and query origins; `//evil`, `..` and CRLF routes. Clock transport carries `token=None`; API transport is bound to `api.github.com`. | All refused. |

**Parent and carried evidence:** I did not re-run any of the following; they are carried, not counted as mine.

- `evidence/parent-314f/` (58/58/74/78, exit 0, 07:51:38Z) is consistent with my fresh counts.
- The builder's 17ad union of 1,165 tests and the packaging and resource claims predate later repairs. I did not re-verify them.
- The 6b9147 core boundary acceptance (including the lowered-cap and ack-loss probes) is carried for unchanged core lines only.

**Limits of this review:**

- No live clock, GitHub, namespace or proxy behaviour was exercised.
- Fake-forge tests do not prove server-side protections, real `mergeable` semantics or close/reopen races.
- No exactly-once, atomic-close or liveness claim is made.

## 6. Delivery and activation holds (unchanged, not waived)

- Namespace, ref, genesis and history pins, and server no-delete/no-reset protection must be provisioned independently. A trustworthy deployed clock endpoint is also missing.
- Explicit activation is required. Bypassing old writers must be retired or drained.
- The ongoing historical shared-Git campaign needs an owner-approved transition. The new default-local behaviour and the legacy `--ledger git` mutation refusal would otherwise strand it.
- A separate founder before/after gate is required for changed R19 CLI output, `docs/en/cli-reference.html` and the desk output. M1's warning approval does not cover them.
- F3 needs a founder ruling, because the receipt preconditions diverge from the ratified "each with GitHub receipts".
- Archive stays parked. C1–C4, D, L4 and data decisions, and `issueHygiene.writesEnabled: false`, are unchanged. No registry, version or authority files are among the 36 paths.
- This review grants no CI-churn file-edit permission and did no live mutation, push, PR or activation.
