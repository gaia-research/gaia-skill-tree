# Routine 19 Git object boundary repair — builder proof, not acceptance

## Identity, disposition and scope

Frozen candidate `9d78106dcf95b146c1e5fd0b0b8687f9776e3463`, tree `3f75207d4c239dc13731c7931cc9f130b21cb60f`, remains independently **REJECTED**, as recorded in `wiring-whole-repaired-independent-review.md`. This repair appends, without altering prior reject or repair records:

- `44b796dae0bfe1ad75e72af368ec3d465596a663` — enforce `--no-replace-objects` and sanitize git environment across object readers.
- `e7f1933b5f931d93196fd0146f47f3aecf248b2d` — regression coverage for git replace refs, environment overrides, coordination history, and canonical source authority. Final tree `d4309487fef8046dd901b94b8151e0c4d5f7a109`.

Author and committer for both commits: `Marcus Rafael B. Tiongson <153011150+mbtiongson1@users.noreply.github.com>`, supplied with per-command `git -c` identity and `commit.gpgsign=false`. No version bump. Tracked worktree is clean.

Observed harness runtime: `PI_PROVIDER=openai`, `PI_MODEL=gpt-6.1-terra`, `PI_REASONING_LEVEL=high`. Runtime evidence only, not provider-side attestation. No nested agents or fallback.

## Fresh red and green

The independent reviewer's probe `test_replace_object_boundary.py` deliberately asserted the defect / unsafe acceptance (`assert result['state'] == 'merged'`). To measure the genuine invariant, an expected-invariant refusal regression was authored in the checkout's ignored `.gaia/git-boundary-probe/test_refusal.py`. It asserts that `gate.validateWrite` raises `gate.GateRefused` both before AND after local `refs/replace/` mapping from the bad head to a clean commit, and asserts zero forge invocations and effects.

- **Old RED:** At clean `9d78106dcf95b146c1e5fd0b0b8687f9776e3463`, running `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src:$PWD" python -m pytest -q -s -p no:cacheprovider .gaia/git-boundary-probe/test_refusal.py` printed imported module `$HOME/.gaia-worktrees/steward-r19-shared-write-2283/src/gaia_cli/steward/prmaintenance/proofs.py`. Result: **1 failed in 3.59s**, `Failed: DID NOT RAISE GateRefused`. The unhardened git reader honored the replacement ref and treated the tampered head as clean. Log: `git-object-boundary-red.log`.
- **New GREEN:** At exact final commit `e7f1933b5f931d93196fd0146f47f3aecf248b2d`, same command and imported module path: **1 passed in 4.96s**. `GateRefused` was raised on the bad head before replacement, and STILL raised after replacement ref creation. Forge invocations and effects remained 0. Log: `git-object-boundary-green.log`.

## Reader inventory and threat model limits

### Readers modified

1. **Proof object readers (`src/gaia_cli/steward/prmaintenance/proofs.py`):**
   - `git()` now passes `--no-replace-objects` and `-c core.useReplaceRefs=false`.
   - `safeGitEnv()` builds a scoped subprocess environment stripping `GIT_DIR`, `GIT_WORK_TREE`, `GIT_INDEX_FILE`, `GIT_OBJECT_DIRECTORY`, `GIT_ALTERNATE_OBJECT_DIRECTORIES`, `GIT_REPLACE_REF_BASE`, `GIT_GRAFT_FILE`, and `GIT_COMMON_DIR`.
   - Forces `GIT_NO_REPLACE_OBJECTS="1"` and `GIT_GRAFT_FILE=os.devnull` (disabling legacy `.git/info/grafts`).
   - Protects `hasCommit(root, sha)` (`cat-file -e`), `blob(root, sha, path)` (`cat-file blob`), `exportBase` (`git archive`), and through them `stampProof`, `reportJsonProof`, and `contentEngineProofs`.
2. **Reconciliation worktree & history reader (`src/gaia_cli/steward/prmaintenance/reconcile.py`):**
   - `git()` now passes `--no-replace-objects`, `-c core.useReplaceRefs=false`, and uses `proofs.safeGitEnv()`.
   - Protects worktree creation, payload extraction from original head, merge, commit, and diff generation.
3. **Service authority boundary (`src/gaia_cli/steward/prmaintenance/executor.py`):**
   - `ProductionServices.__init__` expands its pre-flight check to fail closed (`core.CoordinationError`) on inherited `GIT_REPLACE_REF_BASE`, `GIT_GRAFT_FILE`, and `GIT_COMMON_DIR` in addition to object/worktree overrides.
   - `remoteGit()` reuses the coordinator's sanitized store transport.
4. **Driver CLI helpers (`src/gaia_cli/steward/prmaintenance/cli.py`):**
   - `snapshotFor.fetch` and `doReconcileRetired` now delegate to `proofs.git()`.
5. **Coordination store & transport boundary (`src/gaia_cli/steward/ledger.py`):**
   - `GitRefLedgerStore.git()` now passes `--no-replace-objects`, `-c core.useReplaceRefs=false`, strips all override variables from `sub_env`, and sets `GIT_NO_REPLACE_OBJECTS="1"`, `GIT_GRAFT_FILE=os.devnull`.
   - Demonstrably necessary because `coordinator` relies on `GitRefLedgerStore` for critical single-slot coordination; without this, `cat-file -p` during `store.load()` could return a replaced/tampered ledger commit or blob.

### Threat model and limits

- **Threat addressed:** Defends against Git object substitution (via `refs/replace/*` or custom `GIT_REPLACE_REF_BASE`), graft parent forgery (via `GIT_GRAFT_FILE` or `.git/info/grafts`), and repository layout overrides (via `GIT_OBJECT_DIRECTORY`, `GIT_ALTERNATE_OBJECT_DIRECTORIES`, `GIT_DIR`, `GIT_WORK_TREE`, `GIT_INDEX_FILE`, `GIT_COMMON_DIR`) during proof generation, authority verification, and coordination history reads.
- **Model limits:** This does NOT claim defense against an arbitrary hostile local filesystem where an unprivileged attacker can rewrite arbitrary local repository files or corrupt the Python process memory. It enforces strict fail-closed isolation at the Git subprocess execution boundary without mutating global/ambient environment (`os.environ` or git configuration).
- **Generic ledger compatibility:** Schema (`steward-pr-writes-v1`, `steward-ledger-v1`), JSON serialization bytes, CAS fast-forward commit parentage, and recovery remain 100% compatible. Only unsafe object/environment overrides are blocked. Proved by 136 passing tests in `test_ledger.py` and `test_local_full_state.py`.

## Verification checks and logs

All tests run with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src:$PWD"`, no bytecode, no cache provider. Logs located in this campaign directory:

- `git-object-boundary-red.log`: old RED on `9d78106d` — **1 failed in 3.59s**.
- `git-object-boundary-green.log`: new GREEN on `e7f1933b` — **1 passed in 4.96s**.
- `git-object-boundary-test-executor-final.log`: `tests/steward/prmaintenance/test_executor.py` — **56 passed in 242.49s**, including new tests:
  - `test_git_replace_ref_cannot_turn_tampered_report_into_accepted_send`: before and after replacement ref checks, 0 forge invocations/effects.
  - `test_clean_head_succeeds_even_when_replacement_refs_exist`: clean head positive control succeeds normally (merged, 1 invocation / 1 effect) when replacement refs are present.
  - `test_inherited_git_overrides_refuse_at_service_boundary`: 8 override variables fail closed at `ProductionServices` boundary.
  - `test_env_selected_replacement_namespace_cannot_bypass_object_reads`: `GIT_REPLACE_REF_BASE=refs/custom/` fails closed at service boundary and is stripped/ignored by `proofs.git`, refusing the bad head.
  - `test_coordination_store_and_history_immune_to_replacement_refs`: `GitRefLedgerStore.load()` ignores replacement refs on ledger commits/blobs, loading authentic state.
  - `test_canonical_source_authority_immune_to_replacement_refs`: `ProductionServices.sourceTexts()` reads authentic authority blobs at `fx.base`, ignoring replaced commit.
- `git-object-boundary-test-runner-fullrun-final.log`: `tests/steward/prmaintenance/test_runner.py` + `tests/steward/test_fullrun.py` — **74 passed in 129.76s** (attached unknown, CAS retry, in-flight reports preserved).
- `git-object-boundary-test-coordination-final.log`: coordination suites (`test_coordination.py`, `test_coordination_boundaries.py`, `test_coordination_processes.py`) — **78 passed in 305.62s**.
- `git-object-boundary-test-ledger-final.log`: `test_ledger.py` + `test_local_full_state.py` — **136 passed in 65.29s**.
- `git diff --check` passed cleanly across both commits.

## Remaining independent and operational gates

- Frozen candidate `9d78106dcf95b146c1e5fd0b0b8687f9776e3463` remains independently **REJECTED**. This repair is implementation proof, **not self-acceptance** or whole-feature certification.
- Parent must resume independent WHOLE-feature review, including this diff, previously unreviewed surfaces, and any fresh independent probes.
- All operational holds (canonical namespace provisioning, server branch protection, trusted nonce-bound clock endpoint, writer draining, migration planning for historical shared campaigns, C1–C4/D holds) remain in effect. No real GitHub mutations or global configuration changes were made.
