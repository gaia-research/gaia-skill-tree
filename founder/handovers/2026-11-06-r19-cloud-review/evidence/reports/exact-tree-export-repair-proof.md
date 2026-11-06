# Exact base-tree materialization — source candidate, long regression tests pending

## Status and identity

**SOURCE CANDIDATE ONLY; LONG AFFECTED REGRESSION TESTS PENDING PARENT.** This is not acceptance, operational readiness, or a complete independent WHOLE audit. The independent rejection of `e7f1933b5f931d93196fd0146f47f3aecf248b2d` in `wiring-whole-git-hardened-independent-review.md` remains in force; no historical report, original unsafe-acceptance probe, or failure has been changed.

- Starting HEAD: `e7f1933b5f931d93196fd0146f47f3aecf248b2d`.
- Appended candidate: `314fdf655edb7a6cb9bd131461bc11952366979d`; tree `e53b5920571b1458a6b6d0bde1fe454f57c7b411`.
- Committed and working source Git blob `38592e8341c2daa1f0f46a75f94138c8567802c6` for `src/gaia_cli/steward/prmaintenance/proofs.py`.
- Committed and working test Git blob `b9c2f3e07cf9e7370334e9af621796a9be468816` for `tests/steward/prmaintenance/test_exact_tree.py`.
- Commit author and committer: Marcus Rafael B. Tiongson <153011150+mbtiongson1@users.noreply.github.com>, supplied per command with `commit.gpgsign=false`.
- Tracked tree clean. Untracked `.pi/tasks/` contains preserved harness task artifacts; intentionally not removed or committed. No version, policy, ledger, schema, CLI, coordinator or runner changes.
- Actual runtime exports: `PI_PROVIDER=openai`, `PI_MODEL=gpt-6.1-terra`, `PI_REASONING_LEVEL=high`; these are harness evidence, not independent provider attestation.

## Defect and exact-tree mechanism

`exportBase`, called only by `contentEngineProofs` for the base generator/templates and historical reports, previously invoked `git archive`. Archive attributes could omit committed history or rewrite bytes before index reconstruction. This change lists selected committed paths via `git --no-replace-objects --literal-pathspecs ls-tree -r -l -z` and obtains each regular-file blob by object ID via `cat-file blob`; no archive, checkout, smudge, text conversion or attribute processing occurs. Each blob's size and Git SHA-1 object ID are checked before writing. The existing scoped Git environment and no-replace/graft defenses remain in use.

NUL-delimited output is bounded and parsed as strict UTF-8; paths must be relative, nonempty, contain no dot/dot-dot/empty/backslash components, and belong to a requested subtree. Missing paths, duplicate entries, unsupported Git modes (including symlinks and gitlinks), malformed data, oversized output or objects, failures/timeouts, symlinked output ancestry, pre-existing output paths and I/O failures refuse materialization. Regular `100644` / executable `100755` modes are reproduced. Files are exclusively created in the fresh proof scratch tree. The check is not a claim of protection against arbitrary concurrent hostile filesystem rewrites.

Materialization explicitly bounds ls-tree output to 4 MiB, individual blob to 16 MiB, aggregate blobs to 64 MiB, and entries to 16,384. Each export shares the original 120-second archive deadline across its subprocess reads. Exceeding any bound fails closed as `base export failed` / UNKNOWN, never as a proof pass. These are newly explicit finite proof-materialization limits, not quota, ledger, retention, coordination, or write budget changes; large otherwise-valid base trees may now be refused and need separate review if encountered.

## Fresh red and brief final-source checks

- Original independently authored `.gaia/whole-review-probes/test_attrs_omits_history.py` deliberately asserted UNSAFE acceptance and remains unchanged in the separate review checkout. A copied expected-refusal variant is `.gaia/exact-tree-probe/test_refusal.py` in this worktree (ignored).
- At clean old HEAD `e7f1933b`, explicit `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src:$PWD" python -m pytest -q -s -p no:cacheprovider .gaia/exact-tree-probe/test_refusal.py` imported this worktree's `proofs.py` and produced **1 failed in 5.69s**: before override `index-rebuild` refused the bad head; after `GIT_CONFIG_COUNT`/`core.attributesFile` override, expected refusal **DID NOT RAISE**. Raw preserved `exact-tree-red.log` in this campaign directory. This expected-invariant RED does not assert a fake effect; the independent original report separately documents its intentionally unsafe passing 1-invocation/1-effect demonstration.
- At exact committed `314fdf655`, the same expected-refusal probe plus the complete new focused test module ran with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src:$PWD" python -m pytest -q -s -p no:cacheprovider .gaia/exact-tree-probe/test_refusal.py tests/steward/prmaintenance/test_exact_tree.py`: **10 passed in 25.69s**, exit 0. Raw log `exact-tree-brief-314f.log` prints HEAD, tree, committed/worktree matching blob IDs, and imported module path. The expected-refusal probe prints before/after `index-rebuild` refusal and **0 invocations / 0 effects** after the override.
- Focused tests cover inherited config-selected attributes, local `.git/info/attributes`, and committed `.gitattributes`; a literal `$Format:%H$` file independently marked `export-subst`, another marked `export-ignore`, exact history manifest, executable and non-executable modes; dropped history in both generated indexes, a genuine clean-history execution control, invalid/missing paths, source symlink, destination symlink and symlinked output ancestor, oversize blob and gitlink. Committed-attribute history tests use real base/head Git objects. Inherited/global/system/committed attribute mechanisms cannot affect raw ls-tree/cat-file bytes; no test claims inspection of a real system configuration.
- Earlier brief `exact-tree-raw-resume.log` (4 passed) and `exact-tree-limits-resume.log` (1 passed) were before the final source commit and are not represented as final-SHA runs. The earlier preliminary 10-pass log also predates the final symlink-path hardening. `git diff --check` passed.

## Interrupted logs — not results

The previous context's `exact-tree-focused.log`, `exact-tree-runner.log`, `exact-tree-focused-resume.log`, `exact-tree-runner-resume.log`, and `exact-tree-executor-resume.log` contain progress only, no terminal pytest summary or recorded shell exit. Parent reported corresponding child processes gone. Treat them as **interrupted/incomplete**, neither passing nor failing; retain them. No long suite or background job was started by this continuation.

## Required parent-run regression groups on immutable candidate

Parent will run these as durable managed jobs against exact commit/tree and record **distinct raw logs and explicit pipeline exit-code files**, without increasing/changing pytest's existing timeout=60/thread, waits, joins, concurrency assertions, or skipping cases:

1. `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src:$PWD" python -m pytest -q -p no:cacheprovider tests/steward/prmaintenance/test_exact_tree.py tests/steward/prmaintenance/test_reconcile.py tests/steward/prmaintenance/test_gate.py`
2. Same environment: `python -m pytest -q -p no:cacheprovider tests/steward/prmaintenance/test_executor.py tests/steward/prmaintenance/test_executor_processes.py` (including previous replace/graft-related controls).
3. Same environment: `python -m pytest -q -p no:cacheprovider tests/steward/prmaintenance/test_runner.py tests/steward/test_fullrun.py` (attached unknown / pure-CAS safeguards).
4. Same environment: `python -m pytest -q -p no:cacheprovider tests/steward/prmaintenance/test_coordination.py tests/steward/prmaintenance/test_coordination_boundaries.py tests/steward/prmaintenance/test_coordination_processes.py` (protected shared holds/charges and CAS).

Suggested wrapper per group: `set -o pipefail; <command> 2>&1 | tee <unique-log>; rc=${PIPESTATUS[0]}; printf '%s\n' "$rc" > <unique-exit-file>; exit "$rc"`. Parent must verify HEAD, tree, source/test blob binding and actual exit files, diagnose any failures without hiding them, and record fresh versus carried evidence. Existing prior e7 tests are carried only as prior-source evidence, not new tests of 314f.

Independent WHOLE review must resume after the parent-run checks, including all prior unreviewed surfaces and this new diff. No real GitHub/coordination/legacy ledger, namespace, clock, server protection, activation, writer drain, migration, global Git/environment configuration, install, push or merge was performed by this continuation.
