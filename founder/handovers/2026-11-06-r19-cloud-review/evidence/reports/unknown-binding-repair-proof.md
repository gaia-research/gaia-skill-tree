# Routine 19 attached-operation binding repair — builder proof, not acceptance

## Identity, disposition and scope

Frozen candidate `17ad597ad3478b7caae182b1581a965a8fcfa252`, tree `fa46a693d3ad3a26f19474851197e97c56f77769`, remains independently **REJECTED**, as recorded in `wiring-whole-independent-review-completion.md`. This repair appends, without altering that evidence:

- `a1b266acea756f2c1e7011b7b39b2a7e20592026` — bind and revalidate runner report attachment, with regression tests.
- `9d78106dcf95b146c1e5fd0b0b8687f9776e3463` — additional actual in-flight possibly-sent test. Final tree `3f75207d4c239dc13731c7931cc9f130b21cb60f`.

Only `src/gaia_cli/steward/fullrun.py` and `tests/steward/prmaintenance/test_runner.py` changed. No core, executor, policy, contract, registry, version, mirror or activation changes. Commit author/committer supplied per command as Marcus Rafael B. Tiongson <153011150+mbtiongson1@users.noreply.github.com>; signing disabled per command. Tracked worktree clean after commits.

Observed harness: `PI_PROVIDER=openai`, `PI_MODEL=gpt-6.1-terra`, `PI_REASONING_LEVEL=high`. This is runtime export evidence, not provider-side attestation. No nested agents or fallback.

## Fresh red and green

Before editing at exact frozen HEAD, copied the independent expected-invariant probe `test_unknown_required.py` into this worktree's ignored `.gaia/unknown-binding-probe/`. Explicit `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src:$PWD"` import printed `$HOME/.gaia-worktrees/steward-r19-shared-write-2283/src/gaia_cli/steward/fullrun.py`. Running `python -m pytest -q -s -p no:cacheprovider .gaia/unknown-binding-probe/test_unknown_required.py` yielded **1 failed in 6.33s**, assertion `done == pending`, with `RESULT local_status= done shared_state= unknown slot_held= True invocations= 1 effects= 1`. This was an expected-invariant failure, not a passing test or evidence of replay/refund. The original independent reject and its probe/control are unchanged. This fresh red was captured in the tool output, not a separate log file.

At exact final `9d78106dcf95b146c1e5fd0b0b8687f9776e3463`, same environment and command, module path again explicitly printed, the same probe gave **1 passed in 11.37s**, `local_status= pending shared_state= unknown slot_held= True invocations= 1 effects= 1`. Full command output including HEAD and path: `unknown-binding-green.log` next to this proof. The green does not convert the earlier failure into a pass.

## Mechanism and safety

The runner derives the shared ID from already attached action params when omitted; explicit different (including null) IDs are refused. It re-inspects and validates subject and shared truth outside the mutation. Possibly-sent, unknown and quarantined remain pending even for failed/refused/aborted reports; genuine terminal shared evidence remains required for success-shaped reports, and a never-attached local failure remains allowed. The original report payload remains unchanged, preserving its repeat semantics.

A deep-copied params snapshot is checked inside the pure prepared callback on **every** local CAS attempt. Attachment or subject changes after the read/inspection refuse and require a fresh report, rather than applying stale evidence. Neither shared inspection nor sender invocation occurs inside the retrying callback. Fixture tests force actual local CAS conflicts both when an attachment appears after an unbound initial read and when the inspected attachment changes; they assert pending local state and actual shared slot/charge/effect state. A real coordinator test invokes the report from inside the fixture sender callback while the durable shared state is actually `possibly-sent`, before the sole fake effect and lost response. Tests exercise all three failure shapes with bound/omitted IDs, mismatch refusal, unknown and quarantined holds, independent observed-terminal reconciliation, and never-attached local failure. Unknown senders are not aborted, settled or refunded to pass tests; observed-terminal recovery uses independently supplied matching fixture evidence, not a replay. No timer, quota, window, existing concurrency guard or test deadline was relaxed.

## Checks and logs

All logs below are in this proof's campaign directory; tests use disposable local remotes/fake forges, explicit worktree `PYTHONPATH`, no cache provider and no bytecode writes.

- Final exact HEAD: `python -m pytest -q -p no:cacheprovider tests/steward/prmaintenance/test_runner.py tests/steward/test_fullrun.py` — **74 passed in 133.18s**, `unknown-binding-final-fullrun.log`.
- Before the final test-only commit, identical runtime source: same two modules **73 passed in 115.68s**, `unknown-binding-fullrun.log`. The earlier runner-only group was **21 passed in 81.73s**, `unknown-binding-runner.log`.
- Before the final test-only commit, identical runtime and protected test bytes: `tests/steward/prmaintenance/test_coordination.py tests/steward/prmaintenance/test_coordination_boundaries.py tests/steward/prmaintenance/test_coordination_processes.py` — **78 passed in 273.85s**, `unknown-binding-coordination.log`.
- Before the final test-only commit, identical runtime and protected test bytes: `tests/steward/prmaintenance/test_executor.py tests/steward/prmaintenance/test_executor_processes.py tests/steward/prmaintenance/test_gate.py` — **86 passed in 376.00s**, `unknown-binding-executor.log`.
- Additional in-flight test before its commit: **1 passed in 9.26s**, `unknown-binding-possibly-sent.log`; included again in final 74.
- `git diff --check` passed before each commit. No full repository/archive pipeline was run. Original test safeguards were not modified; these checks do not independently certify the prior builder's entire 1,165-test union.

## Remaining independent and operational gates

No self-acceptance: the parent must resume **unfinished independent WHOLE-feature review**, including this diff, all previously unreviewed surfaces, and any independent adversarial probes. Passing this one regression is not whole-feature coverage or operational readiness. C1–C4/D and prior source/operational holds remain. No live canonical/coordination/legacy ledger access, GitHub mutation, namespace/config/provisioning, migration, settlement, writer retirement, push, activation, deployment or global change was performed. No real time service or server protection was verified; no exactly-once or guaranteed-liveness claim is made. Unknown operations may hold indefinitely. Parent owns publication and subsequent review.
