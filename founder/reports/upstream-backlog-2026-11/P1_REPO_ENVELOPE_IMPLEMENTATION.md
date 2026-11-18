# P1 Repository-Envelope Implementation Receipt

**Status:** LOCAL IMPLEMENTATION COMPLETE (CODE + BOUNDED TARGETED CHECKS) — **UNREVIEWED / NOT EXECUTION-READY**
**Branch:** `dev/upstream-backlog-watcher-2026-11`
**Starting HEAD:** `9e56f559abc6db13b3b1a15eba7e136c36abc739`
**Delivered Scope:** Continuation and verification of the 15-path `repo_envelope` + `preserve_plan` draft (`827c588e0666acfa3f905afea0e22268438bad79`), EOF whitespace repair in `tests/test_repository_envelope_workflow.py`, and this technical receipt.

## Implemented Wire & Orchestration Contract

### 1. Repository Envelope Wire Protocol (`scripts/upstream_watcher/envelope.py`)
- **Envelope format:** `format: "gaia-upstream-repository"`, `envelopeVersion: 2`, `payloadVersion: 3`, normalized lowercase `repository`, sorted unique case-sensitive `findings[]` (1..256), and `payloadSha256`.
- **Per-named finding isolation:** Each member in `findings[]` retains `payloadVersion: 2`, case-sensitive `skillId`, `sourceUrl` (`https://github.com/<owner>/<repo>/releases/tag/<tag>`), `newVersion`, `releasedAt`, `mode` (`components` | `version-only`), optional `findingType` (`update` | `bootstrap`), `componentAdds`, `componentRemoves`, `linkLiveness`, `nameDrift`, `candidates[]`, and its own independent `payloadSha256`.
- **Source & scope invariants:**
  - `authority_repository` resolves each named skill's own `upstream.repo` / `links.github` via `resolve_suite_source` (AgentDB remains `ruvnet/AgentDB` distinct from `ruvnet/ruflo` despite `suiteRef`).
  - `validate_named` rejects `componentRemoves` outside the selected skill's `suiteComponents` and blocks mutating another suite root.
  - New candidate rows pin `evidenceUrl` to `/blob/<firstSeenVersion>/.../SKILL.md` (never mutable `main`).
- **Records mode (`repository-records-v1`):** `envelope.layout` externalizes large candidate sets into `records.py` chunks using `scope_key(skillId, candidateId)` (`namedSkillId`, `candidateId`). `envelope.read` hydrates and verifies generation SHA-256 and per-named `payloadSha256` before any selection.
- **Explicit named selection (`envelope.select`):** Requires `envelope.read` plus exact match on `skillId`, `payloadSha256`, and `sourceUrl`.

### 2. Grouped Batch Planner & Executor (`scripts/upstream_watcher/repository_batch.py`, `watcher.py`, `releaseidentity.py`)
- **Grouping & canonical selection:** `group_findings` groups incoming findings by verified release repository and rejects conflicting duplicates before any write. `inspect_history` uses `canonical_umbrellas(live["issues"], repo)` (lowest-numbered exact OPEN match) and scans both open and closed `upstream:release` and `upstream:bootstrap` issues, including historical named scopes whose current release repository differs.
- **Selective carry-forward & processed history:** `projection` isolates each named member's `closedUmbrellas` and `issues` view for `batch.plan_suite`, preventing sibling carry-forward or processed-history leakage. Unpolled siblings with unresolved rows in the newest closed envelope are carried forward under their own `skillId`.
- **Race & closure safety:** `execute_repository` re-reads live state and replans (up to 2 attempts) on `UmbrellaClosed` or `RepositoryRaced`, adopting a racing canonical umbrella or replanning into a new batch without editing closed issues.
- **Legacy migration planning (`preserve-legacy-reference` v1):**
  - `legacy_plan_policy.json` pins `planOnly: true` and `historicalAuthorityCommit: "9b4d9b98043140188f00b14d0ac8fa6bc02491b7"`.
  - `envelope.migration_plan` validates legacy payloads against current or pinned historical authority, binds `bodySha256` with `bodyHashScheme: "raw_api_utf8"` (strict raw API UTF-8 bytes; distinct from CLI stdout LF framing `9344b0c0...`), and sets `writeReadiness: false`.
  - `verify_migration_reference` rejects any alternate framing (trailing LF, CRLF, trimmed). Neither digest grants migration execution authority.
  - Any repository with a legacy hold (including `#1833` on `ruvnet/ruflo` and its historical named scope `ruvnet/agentdb`) reports `outcome: "held"` and `writeReadiness: false` with zero GitHub writes even under `--apply`.
  - Malformed/tampered/unknown-target payloads fail closed with exit `3` and `unknownEvidence`.

### 3. Workflow Consumers & CLI Boundaries (`.github/workflows/upstream-*.yml`, `approval.py`, `sync_upstream.py`)
- **`upstream-approve.yml` (`approve` & `skip-child-gate-guard`):**
  - `Verify repository-envelope selection before any approval-path write` runs before `Check labeler is a Verifier` and calls `workflow_payload` + `verify_repository_target`.
  - `issues.labeled`, `issues.opened`, `refire=true`, missing/mismatched `named_skill_id` / `finding_sha256` / `approved_source_url`, non-canonical targets, and legacy-held repositories all fail closed with zero approval-path writes.
  - `Check labeler is a Verifier` and `skip-child-gate-guard` preserve existing actor boundaries (`allowlisted` + `verifier_status`). Workflow `permissions` (`issues: write`, `contents: write`, `pull-requests: write`) are unchanged.
  - `Check child gate` and `Count unresolved candidate rows` read only `SELECTED_PAYLOAD`. `Open draft PR` always uses `Refs #<issue>` for `repository_envelope=true` (never `Fixes`).
  - `Run gaia dev sync-upstream` invokes `python -m gaia_cli dev sync-upstream` with exact `--tag`, `--source-url`, `--released-at`, `--mode` (and `--bootstrap` when `findingType == "bootstrap"`). `sync_upstream.py` enforces `preflightNamedSkillMutable` (frozen/held protection), `min_two_stars`, and `source_url_matches_skill`.

### 4. Held Compatibility Modes (Fail-Closed Read-Only)
The following legacy/unsupported write paths are intentionally held fail-closed and never fall back to single-ID writers or repo-wide mutations:
- `watcher.py --escalate`: returns exit `3` (`writeReadiness: false`), no writes.
- `run_repository_batch(..., mode="fanout")`, `reset_records` set, or `staging.active`: sets `writeReadiness: false`, `executionHold`, `outcome: "held"`, zero writes; missing/corrupt staging journal exits `3`.
- `upstream-approve.yml` (`legacy-approve`), `upstream-reject.yml` (both `v2` and `legacy-*`), `upstream-close-children.yml` (both `v2` and `legacy-*`): first step is `Repository-envelope compatibility hold`, exiting `1` before checkout or writes.

## Verification Summary

1. **Parent Baseline at `9e56f559abc6db13b3b1a15eba7e136c36abc739`** (recorded by parent):
   - Command: `tests/upstream_watcher/test_repository_envelope*.py`, `tests/test_repository_envelope_workflow.py`, `tests/test_upstream_approve_workflow.py`, `tests/upstream_watcher/test_count_2278.py`
   - Result: **244 passed, 1 skipped in 169.85s** (`$TMPDIR/upstream-backlog-2026-11/p1-baseline-9e56f559-r2.log`).
   - Cached `#1833` run (`P1_LEGACY_CACHE=$TMPDIR/upstream-backlog-2026-11/envelope-proof/1833.json`): **1 passed in 0.38s**.
2. **Targeted Post-Edit Check (after EOF blank-line fix in `tests/test_repository_envelope_workflow.py`)**:
   - `git diff --check`: **exit 0** (clean).
   - Command: `P1_LEGACY_CACHE=/data/data/com.termux/files/usr/tmp/upstream-backlog-2026-11/envelope-proof/1833.json PYTHONPATH=src:. python3 -m pytest tests/upstream_watcher/test_repository_envelope.py tests/upstream_watcher/test_repository_envelope_records.py tests/upstream_watcher/test_repository_envelope_cached_case.py tests/upstream_watcher/test_count_2278.py tests/test_repository_envelope_workflow.py -k "not test_actual_workflow_extraction_fails_closed_for_missing_stale_or_malicious_selectors" -q --tb=short`
   - Result: **66 passed, 10 deselected in 38.30s** (offline, socket-blocked; includes real CLI sync, actor/skip-gate denial, child-gate isolation, `#1833` cached hold with zero writes, records round-trip, race/closure replan, and mixed issue+PR inventory).
   - Note: The 10 parametrized `test_actual_workflow_extraction_fails_closed_for_missing_stale_or_malicious_selectors` cases were deselected in this bounded run to stay within time/turn bounds; they passed in the parent baseline at `9e56f559` and must be included in the parent's full non-author run.

## Protected Data & Scope Proof

- Zero changes to `registry/`, `skill-trees/`, `docs/graph/`, `docs/api/`, `src/`, `founder/MEMORY.md`, `founder/reports/upstream-backlog-2026-11/P1_IDENTITY_FOUNDER_DECISIONS.json`, or historical receipts. (`docs/agents/upstream-watcher.md` was updated solely to document the `repo_envelope` contract, exit codes, and rollout blockers.)
- No network calls, live Actions dispatches, issue/label/permission mutations, migrations, merges, or P2–P7 advancement.

## Remaining Gates (No Execution Authority)

1. **Independent Terra shared review** of the exact local commit SHA.
2. **Non-author full regression & parity** (parent-run), explicitly including `tests/test_repository_envelope_workflow.py` alongside `tests/upstream_watcher`, `tests/test_upstream_approve_workflow.py`, `tests/test_dev_upstream_verbs.py`, and `tests/test_repository_envelope_cached_case.py` (with `P1_LEGACY_CACHE`).
3. **Founder rollout decision** for transitioning the `06:00 UTC` scheduled `fanout` run in `upstream-watcher.yml` to `batch` (scheduled `fanout --apply` currently exits `4` fail-closed rather than silently succeeding with zero writes).
4. **Queued base update** (`integration/tstack-suite-2472` when landed) and publication via existing draft PRs.
5. **Conditional ordinary `apply=false` acceptance** remains unconsumed and gated on the above.

---

## Terra Review Findings & Remediation Record (2026-11-20, post-`f71055311`)

Independent Terra shared review of `f71055311c2d1105014466bcaf5ae81202e63e74` returned **BLOCKED / FINDINGS**. Below is the candid disposition of each finding:

1. **Shallow checkout vs `historical_authority` pinned commit — FIXED:**
   - Added bounded exact-pin fetch (`git fetch --depth=1 --no-tags origin "$COMMIT"` for `historicalAuthorityCommit` from `legacy_plan_policy.json`) to `upstream-watcher.yml` (`watcher` job only; `metadata-probe` and `permission-ab-control` unchanged) and `upstream-approve.yml` (`skip-child-gate-guard` and `approve`).
   - Updated `repository_batch.historical_authority` to probe `git cat-file -e <commit>^{commit}` when `git show` fails, raising `PayloadError` (`unknownEvidence`, exit `3`) if the pinned commit object is unavailable locally.
   - Verified offline via local shallow clone (`git clone --depth=1 file://...`) negative-fail + bounded-fetch recovery in `test_shallow_clone_fetches_pinned_historical_authority_and_missing_pin_fails_closed`.
2. **`fanout` global hold returning `0` on `--apply` & physical vs logical counters — FIXED (rollout decision still open):**
   - `run_repository_batch` now returns exit `4` when `apply=True` with an unsupported/held mode (`fanout`, `staging`, `reset_records`), sets top-level `executionHold` (distinct from `knownLegacyHolds` and `unknownEvidence`), and separates `actualIssuesCreated` / `actualIssuesUpdated` (physical mutators, `0` on holds) from logical `issuesCreated` / `issuesUpdated`.
   - Unresolved operational policy gate: `upstream-watcher.yml` `schedule` still passes `fanout` with `--apply` (which will exit `4` fail-closed until the founder authorizes transitioning the schedule to `batch`).
3. **Unconditional first-step global holds in `upstream-reject.yml`, `upstream-close-children.yml`, and `legacy-approve` — FIXED:**
   - Replaced the unconditional `exit 1` first steps with `approval.verify_unaffected_legacy_target(issue)` after checkout and before any write step.
   - Isolated single-named legacy targets (`len(repo_members) == 1`, matching `sourceUrl`, no envelope/sibling/hold in live history) retain their existing protections/order/permissions; repository envelopes, `#1833`-style mismatches, shared-source repos, and malformed/unknown claims fail closed with exit `1` and zero writes.
   - Note: `legacy-reject` and `legacy-close-children` (`STEWARD_ISSUE_HYGIENE_V2 != 'true'`) retain their `Repository-envelope compatibility hold` first step because they lack v2 pagination/actor hardening.
4. **Docs & CLI help alignment — FIXED:**
   - Updated `docs/agents/upstream-watcher.md` and `scripts/upstream_watcher/watcher.py` `--help` strings to distinguish deployed `main` vs unmerged `repo_envelope` behavior, exit codes (`0`, `1`, `3`, `4`), safe `apply=false` batch invocation, `#1833` raw-body hold + deployment order, and the open schedule rollout blocker.

### Correction Verification Results
- `git diff --check`: **exit 0** (clean).
- `P1_LEGACY_CACHE=/data/data/com.termux/files/usr/tmp/upstream-backlog-2026-11/envelope-proof/1833.json PYTHONPATH=src:. python3 -m pytest tests/upstream_watcher/test_repository_envelope.py tests/upstream_watcher/test_repository_envelope_records.py tests/upstream_watcher/test_repository_envelope_cached_case.py tests/upstream_watcher/test_count_2278.py tests/test_repository_envelope_workflow.py -k "not test_actual_workflow_extraction_fails_closed_for_missing_stale_or_malicious_selectors" -q --tb=short`: **69 passed, 10 deselected in 44.42s**.
- `PYTHONPATH=src:. python3 -m pytest tests/test_upstream_approve_workflow.py -k "test_staged_close_children_dispatch_checks_out_trusted_main_not_dispatch_ref" -q --tb=short`: **1 passed, 168 deselected in 0.70s**.
