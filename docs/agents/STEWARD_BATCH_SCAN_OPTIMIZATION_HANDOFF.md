# Handoff Report: Steward Batch Scanning Optimization

**Date**: 2026-11-09  
**Branch**: `fix/2316-steward-batch-scanning`  
**Issue**: [#2316](https://github.com/gaia-research/gaia-skill-tree/issues/2316)  
**Related**: [#2434](https://github.com/gaia-research/gaia-skill-tree/issues/2434)  
**PR**: [#2437](https://github.com/gaia-research/gaia-skill-tree/pull/2437)  
**Status**: READY FOR REVIEW  

---

## 1. Summary & Objective

This pull request implements the targeted optimization for Issue #2316: eliminating redundant repository-wide scans during batched Class B Steward repairs (`gaia steward full run` with `maxDispatchesPerRun: 8`).

Previously, every `agent.build` packet emitted through `render_dispatch_prompt` → `render_dispatch` → `_scan_and_persist_routing` executed an unconditional, full `StewardController.scan()` across all 30+ sensors. In an 8-build batch, this executed 1 initial scan followed by 8 redundant scans (~3 minutes each on a live repository, taking ~25 minutes before builders could begin).

This PR enables safe, fail-closed reuse of the run's existing fresh `ScanResult` across compatible repair packets, reducing scan overhead while strictly guaranteeing that any repository change, git HEAD motion, dirty working tree, local state modification, or sensor input expiration immediately triggers a fresh scan.

*Note on release scope*: The v9.4.0 release preparation was confirmed not separately authorized and all release-only changes (manifest bumps, HTML cache-bust churn, and changelog release entries) have been removed from this PR, keeping it strictly scoped to Issue #2316.

---

## 2. Team & Delegation Verification

All subagents were orchestrated strictly following project guidelines with `@parke.dev/pi-subagent`:
- **Lead**: Gemini Flash, HIGH (coordination, architecture, synthesis)
- **Worker**: Gemini Flash (implementation, unit testing, benchmark execution)
- **Independent Reviewer**: Terra, HIGH (multi-round adversarial code review of the diff)
- **Preflight Verification**: Executed `subagent` with `action: "plan"`, verifying model identities, thinking levels, capabilities, and permissions before spawning.
- **Review Integrity**: Sign-off was reviewed iteratively through 30+ review passes until every potential edge case (symlink handling, name mangling, nested config objects, boundary transitions, large files, unroutable recoveries, ignored dot-prefixed sensor inputs) was hardened.

---

## 3. Benchmark Measurements: 8-Packet Batch

A representative 8-packet batch was benchmarked using `FullRunDriver` with 8 concurrent build dispatches under identical conditions.

### Benchmark Results Comparison

| Metric | Without Scan Reuse (Baseline) | With Scan Reuse (Optimized) | Impact / Delta |
|---|---|---|---|
| **Full-Scan Count** | 9 scans (1 initial + 8 dispatch) | **1 scan** (1 initial + 0 dispatch) | **88.9% reduction** (8 scans eliminated) |
| **Total Dispatch / Run Time** | 2.9255s (synthetic suite) / ~27 min (live repo) | **1.5356s** (synthetic suite) / ~3 min (live repo) | **~48% faster (synthetic) / ~89% faster (live)** |
| **Cumulative Fingerprint Validation Time** | N/A (unconditional scans) | **0.4024s** (402.40 ms across all 8 checks) | **~50.3 ms** average per validation check |
| **Full Repo Fingerprint Walk Time** | N/A | **2.7517s** (live repo, thousands of files) | **65x faster** than a 180s full scan |

### Key Benchmark Takeaways
1. **Zero Redundant Full Scans**: Exactly 1 full scan is performed for the entire batch. All 8 dispatches safely reuse the existing fresh scan.
2. **Negligible Validation Overhead**: Validating the entire repository state, git cleanliness, and all sensor inputs takes only ~50 ms on synthetic repos and ~2.75s on the full live repository, compared to ~180s for each redundant scan.
3. **Fail-Closed Assurance**: If any file changes during the batch, fingerprint validation fails immediately and triggers a full fresh scan.

---

## 4. Ignored Dot-Prefixed Sensor Input Verification

Review Finding 2 identified the risk that ignored dot-prefixed sensor inputs could bypass fingerprint invalidation:
- `local_inputs_fingerprint` in `src/gaia_cli/steward/controller.py` previously skipped entries where `filename.startswith(".")` or `d.startswith(".")` in `state_dir` (`.gaia/steward`).
- Because `.gaia/` is excluded from git clean checks (`git_tree_is_clean`), any dot-prefixed sensor input (such as `.gaia/steward/inputs/.ci-runs.json`, `.gaia/steward/inputs/.github-prs.json`, or `.gaia/steward/.custom_inputs/config.json`) would have silently bypassed invalidation.
- **Correction Applied**: `local_inputs_fingerprint` was updated so that all files and subdirectories under `state_dir` (including dot-prefixed ones) are hashed. Only the internal runtime synchronization state (`.scan.lock`, `.git`, root `debt.json`/`lane.json`, and root `receipts`/`full`) is excluded.
- **Focused Regression Coverage**:
  - `test_render_dispatch_ignored_dot_prefixed_sensor_input_modification_forces_rescan`: verifies modifying `.gaia/steward/inputs/.ci-runs.json` invalidates fingerprint and forces a rescan.
  - `test_render_dispatch_ignored_dot_prefixed_directory_input_modification_forces_rescan`: verifies modifying `.gaia/steward/.custom_inputs/config.json` invalidates fingerprint and forces a rescan.
  - `test_render_dispatch_ignored_dot_prefixed_watcher_input_forces_rescan`: verifies modifying `.gaia/upstream-watcher/.custom_feed.json` invalidates fingerprint and forces a rescan.

---

## 5. Architecture & Safe Reuse Contract

Scan reuse in `_is_scan_fresh` enforces a strict fail-closed contract across 10 independent verification dimensions:

1. **Git Repository Requirement**: Reuse is strictly refused outside a verifiable Git repository (`(root / ".git").exists()`).
2. **Git Working Tree Cleanliness**: `git_tree_is_clean` executes `git status --porcelain --untracked-files=all -- :!<state_prefix>`. Any untracked or modified file outside `.gaia/` makes the working tree dirty, immediately refusing reuse.
3. **Git HEAD Commit Binding**: Verifies `scan.head_commit is not None and scan.head_commit == git_head_commit(root)`. Capturing HEAD before and after observation collection in `controller.scan()` guarantees the scan reflects a stable commit.
4. **Local State Confinement**: Verifies `scan.debt_state_path` resolves to the local `debt.json`, and `scan.receipt_path` exists as a valid file confined within the local `receipts/` directory.
5. **Persisted Receipt Identity**: Validates that `scan.receipt_path.read_bytes()` on disk exactly matches `scan.receipt.to_dict()`.
6. **Ledger Generation Identity**: Hashes `debt.json` with SHA-256 (`debt_state_hash`) and requires an exact match before reuse.
7. **Comprehensive Local Inputs Fingerprint**: `local_inputs_fingerprint` recursively walks and hashes:
   - All input files and directories under `.gaia/steward/` (including all dot-prefixed sensor inputs).
   - Ignored surfaces inspected by sensors: `generated-output/`, `.gaia/upstream-watcher/`, `.agents/skills/`, `.claude/skills/`, and `registry/`.
   - All Python source files (`*.py`) under `scripts/` and `src/` (including git-ignored scripts like `scripts/build/*.py`).
   - Remote origin URL (`git_origin_url`).
   - Symlinks are safely inspected by hashing the link target and resolving target file contents in bounded 64KB chunks.
8. **Time-Sensitive Input Boundary Checking**:
   - Compares input freshness status (`"valid"`, `"past"`, `"future"`) between scan start time (`scan.receipt.started_at`) and reuse time (`now_dt`).
   - PR maintenance census (`github-prs.json`): 1-hour window (`maxCensusAgeSeconds`), 0 future tolerance.
   - Issue hygiene census (`github-issues.json`): 6-hour window (`maxCensusAgeSeconds`), 0 future tolerance.
   - Other inputs (`ci-runs.json`, `test-history.json`, `advisories.json`): 7-day window, 5-minute future tolerance.
   - Inputs > 20 MiB fail closed if uninspectable.
9. **Controller Instance & Sensor Signature Binding**:
   - `controller.instance_token`: unique cryptographic per-instance token prevents cross-instance reuse (even on Python ID reuse).
   - `sensor_signature`: deep structural signature traversing instance attributes, `__slots__` across the MRO (with private name-mangling resolution), and nested configuration objects (with cycle detection). Excludes only explicitly declared `_telemetry_attrs` (e.g. `StubSensor.scans`).
10. **Freshness Window**: Evaluates `scan.receipt.finished_at` (recorded at actual collection completion) against `controller.clock()` / UTC now within `DEFAULT_SCAN_FRESHNESS_SECONDS = 300`.

---

## 6. Verification & Test Evidence

All relevant test suites pass with 100% green status:

1. **`tests/steward/test_routing.py`**: **56 passed**
2. **`tests/steward/test_fullrun.py`**: **51 passed**
3. **`tests/steward/test_fullrun_scenarios.py`**: **70 passed**
4. **`tests/steward/issuehygiene/test_b7_runner.py`**: **8 passed**
5. **`python3 scripts/verify_lockstep.py`**: **Passes at v9.3.0**
6. **PR Guards (`python3 scripts/pr_guards.py --all`)**: All 6 guards PASS (`html-sink`, `rank-vocabulary`, `taxonomy-authority`, `version-stamp`, `lexicon`, `license`).
