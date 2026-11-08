# F7: gh-aw source fix and recompile, C4 audit and compile receipt (2026-11-08)

**Founder ruling F7 (verbatim):** "Fix the gh-aw source and recompile the lock files". The founder's go-ahead to install and compile (verbatim): "F7 yes." (recorded in PR #2389).

This is the compiled-source synchronization receipt that `founder/steward/FOUNDER_LOCK_2283.md` C4 requires. **Activation is not part of this change.** C4 step 4 still requires separate founder authorization to activate, and every lock remains paused.

## Environment and command

| Item | Value |
|---|---|
| Compiler | `gh aw version` = **v0.92.6**, installed with `gh extension install github/gh-aw --pin v0.92.6` (founder-approved global change). This is the release build that compiled all 8 previous locks. |
| Actions | `--action-mode action --action-tag v0.92.6`. `github/gh-aw-actions/setup` is pinned to `8b9c5e98dfe3472ac4e3f13e0a2441cd078a2ca7`, verified via the API: annotated tag `v0.92.6` (tag object `6479b854…`) points to that commit. The compiler recorded the pin in `.github/aw/actions-lock.json`. |
| Sources | `scripts/gen_steward_agent_workflows.py` generates the wrappers `.github/workflows/steward-{build,verify}-{claude,codex,copilot,pi}.md`, which import `.github/workflows/shared/steward-{agent,build,verify}.md`. `gen_steward_agent_workflows.py --check` passes. |
| Command | `gh aw compile steward-build-claude steward-build-codex steward-build-copilot steward-build-pi steward-verify-claude steward-verify-codex steward-verify-copilot steward-verify-pi --action-mode action --action-tag v0.92.6`: 8 succeeded, 0 warnings |

## Source changes (the only hand edits)

1. **The founder pause now lives in the source.** `FOUNDERPAUSE` in the generator adds a top-level `if: ${{ false }}` (with a comment) to every wrapper. gh-aw v0.92.6 compiles a top-level `if:` onto the generated `activation` job, and every other job needs activation, so the pause survives any recompile. It replaces the manual post-compile lock edit that a plain recompile would have dropped.
2. **`shared/steward-agent.md`:** the `steward-outcome` upload step moves from `actions/upload-artifact@v4` to `@v7.0.2`. The previous locks already ran v7.0.2 at SHA `cf430e03…`, so without this change a recompile would have downgraded the step to v4.

No lock file was hand-edited.

## Timeouts: a gh-aw v0.92.6 limitation, so the 8 findings stay open

The workflow_hygiene findings on the 8 locks are `activation`, `conclusion` and `steward_outcome` without `timeout-minutes` (24 jobs). v0.92.6 offers no source setting for any of them:

- **`activation` / `conclusion`:** the compiler refuses `jobs.activation.timeout-minutes` with "jobs.activation.timeout-minutes is supported only for the generated agent and detection jobs".
- **`steward_outcome`:** this is a custom `safe-outputs.jobs` job. The compiler refuses `timeout-minutes` there with "Unknown property: timeout-minutes. 'timeout-minutes' belongs under 'the root level', 'safe-outputs' or 'tools/repo-memory/validation'". The `safe-outputs.timeout-minutes` key bounds the built-in `safe_outputs` job only, which already has 45.

So **0 of 24** job timeouts can be added from source. The Steward sensor on the recompiled tree reports the same 8 debt ids with the same 3 findings each, and no new id. These findings stay open as a gh-aw limitation, never as hand edits.

A variant using `on.report-blocked-version: false` (to avoid the activation permission below) was rejected: it makes the compiler add a new `pre_activation` job with no timeout, which is new debt.

## Lock diff, every changed line classified (8 locks)

Every `+`/`-` line of `git diff -U0` across the 8 locks matched exactly one class. **Unclassified: 0.**

| Class | + | − | What it is |
|---|---|---|---|
| founder-pause | 8 | 8 | `if: ${{ false }} # Founder pause…` (manual) becomes `if: false` (compiled from source). **Pause preserved.** |
| c4-detection-hardening | 64 | 40 | `GH_AW_DETECTION_CONTINUE_ON_ERROR` `"true"` becomes `"false"`; `continue-on-error: true` removed from the threat-detect install and the detection conclusion; the outcome-persistence step's four clearance checks. This is the C4 source hardening, synced as C4 intended. |
| version-check-step | 112 | 0 | A new activation step, "Check compile-agentic version" (the strict-mode version check; `check-for-updates: false` is refused in strict mode) |
| activation-issues-write | 8 | 0 | `issues: write` on `activation`. The version-check step's blocked-version notification needs it. **Permission expansion on a job that never runs while paused.** |
| action-pin-sha | 48 | 48 | `github/gh-aw-actions/setup@v0.92.6` becomes `@8b9c5e98… # v0.92.6` (SHA pin), plus the matching manifest-comment lines |
| version-string | 38 | 22 | `GH_AW_VERSION`/`GH_AW_COMPILED_VERSION` `dev` becomes `v0.92.6`; `GH_AW_INFO_CLI_VERSION` added |
| metadata-header | 24 | 24 | `gh-aw-metadata`/`gh-aw-manifest` hashes and the generated-by banner |

**Semantic per-job diff** (parsed YAML, every lock): the only job-level differences are on `activation`:
- `if`: `${{ false }}` becomes `false`;
- `permissions` gains `issues: write`;
- the version-check step is added.

`on`, `concurrency`, job sets, `needs`, `runs-on`, every job's `timeout-minutes`, and every other job's permissions are unchanged. actionlint reports 40 lines before and 40 after.

## Checks

- `tests/steward/test_founder_workflow_lock_2283.py`: the pause is asserted on every compiled lock as `if: false`, and in every source wrapper. New tests assert strict detection in every lock.
- `tests/steward/test_gen_agent_workflows.py`: release build, SHA-pinned setup, no `GH_AW_VERSION: dev`.
- `test_sensors_ci.py` and `test_steward_workflow.py` pass: 89 passed (`-n 2`).

## Lock sha256 after compile

| Lock | sha256 |
|---|---|
| `.github/workflows/steward-build-claude.lock.yml` | `e0a031e4e2f5732dfc5bc6809de6d1125668232d609a8cf716895bc84a3accde` |
| `.github/workflows/steward-build-codex.lock.yml` | `1efe131e0a755d226630fcf4cd765ee76299cba837362a3000eb75464ad87e85` |
| `.github/workflows/steward-build-copilot.lock.yml` | `84a06cc39d934a1a501a21a661c69c711da63987d44ca78c0683c335d955a7f2` |
| `.github/workflows/steward-build-pi.lock.yml` | `0aa35bcb436b26922a1182813a9e21afbc76d79b9ef20f1f9de93c2bfe718a1d` |
| `.github/workflows/steward-verify-claude.lock.yml` | `e918039cf4ad2bbc2c751cf96f583523dde027ecf8739b585af3ac58704ff2d1` |
| `.github/workflows/steward-verify-codex.lock.yml` | `61759b3bc3cc1e39431ea05afc869c4a075b5123cabe915466a077653e17f66f` |
| `.github/workflows/steward-verify-copilot.lock.yml` | `06d02ddb50c9e305aa3ffe7e1c1df14a4dc1b85b96aa1ec88c01bb15db92514b` |
| `.github/workflows/steward-verify-pi.lock.yml` | `26bf66f83b6ac813a5c8da7491afe255121577e8731d8f1688f3aaf99218efbc` |
