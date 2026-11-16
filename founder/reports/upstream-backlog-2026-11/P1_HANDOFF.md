# P1 Handoff — Watcher & CLI Technical Reconciliation

## 2026-11-17 current gate — STOPPED; Terra findings at round 2

At exact feature review HEAD `b614688657d34234472caaeef7069733647869df`, independent Terra (`openai-codex/gpt-6.1-terra`, high) returned **FINDINGS / issues_found, NOT PASS**. Warnings: comparisons must become UNKNOWN when required counts are unstable; all repository count reads must fail closed for missing/invalid/mismatching authoritative identity (named and numeric). Focused 122 passed, but no full required regression/parity at this SHA. Detailed receipt and chronology: [P1_COUNT_REPAIR.md](P1_COUNT_REPAIR.md). First metadata actual run 43927918189 failed unsafe-link; normal run 43896669237 failed 244/250; no second metadata run. Historical causes UNKNOWN.

**STOPPED — metadata2-round correction limit reached; await specific operator authorization.** Recommendation only: one targeted Sol-shared correction exactly covering these findings, independent Terra re-review, then full regression before any diagnostic dispatch. Not authorized yet. No third round, probe, normal run, permission increase, merge, or P2. PRs #2468/#2469 remain OPEN/DRAFT against `dev/upstream-backlog-2026-11`. Preserve history/worktrees; campaign-complete cost UNAVAILABLE, no bulk cost investigation or P0 partial-as-total.

> **STOPPED AT FOUNDER GATE — #2278 refusal reproduced; P1 blocked; NO MERGES.** Actual run 43896669237 failed (watcher step exit 3) at source `fa6ca42ab8c56ded58f340165388a69ae1957a7a`. See [P1_RUNNER_REPORT.md](P1_RUNNER_REPORT.md) and exact JSON. `EXECUTOR_PROMPT.md` mandates stop and return to founder. No investigation, repair, monitoring, rerun or P2–P7. Await explicit founder authorization for bounded #2278 repair before code/redispatch. Terra code PASS is not actual-runner PASS/P1 completion. PRs #2468/#2469 remain OPEN/DRAFT.

Builder reports below remain precisely attributed to `worker-sol-shared` (`openai-codex/gpt-6.1-sol`, medium). Independent Terra now PASSed with no actionable findings at the pinned source/schema pair; historical findings/cancellation remain history, not the current verdict. The authorized P1 runner invocation is validated and **NOT YET DISPATCHED**.

## Historical Terra receipt on pre-repair source `60120a1` (not the current candidate verdict)

- Tests at source `60120a1ec7b24a31e7e9e0a5d75c337963993442`: actual `1015` pytest passed; parity exit 0 with both staged-row equalities true; `git diff --check` passed. Isolated empty-name/root-crossfield/active `.gaia/registry` schema/missing-invalid schema/invalid Git refs/valid encoded `#` and `/` probes confirmed.
- Correct count/classification: baseline `9b4d9b98043140188f00b14d0ac8fa6bc02491b7` and integration had **10**, not 11, AgentDB raw-schema errors: permitted `trustMagnitudeInputHash`; `apexGateStatus` unexpected `crossOrgVerifier` and `systemWideCap` (one); five `migrate_trust_magnitude` timeline actions; one `recalibrate_trust_magnitude`; two `github-actions[bot]` contributor values. P1 `da255f0` added the **11th**, a `note` timeline event (`registry/named/ruvnet/agentdb.md:148`; writer `src/gaia_cli/commands/dev/named.py:175` emits note). Older lines 94/151 below that called all 11 pre-existing are incorrect and superseded; retained builder reports are historical, not the final verdict.
- `scripts/validate.py:535` checks named records. `scripts/check_trust_magnitude_consistency.py:83` documents schema drift and checks selected fields/evidence/timeline shape; it does **not** normalize/validate the whole raw record. Actual AgentDB named check passed, raw-schema errors remain.
- **Critical:** `src/gaia_cli/commands/dev/sync_upstream.py:457` whole raw-schema validation prevents safe sync: dry-run on actual AgentDB (record hash unchanged) is blocked, as is read-only scan of all **23** watcher-in-scope suites with invalid raw schemas; ordinary future approval-route sync is blocked. No real-runner dispatch. P1 incomplete; P2 onward not started.
- `gaia dev validate`: `scripts/validate.py` 11/11 passed, but overall command exit 1 because generated `registry/named-skills.json` is absent for redaction/timeline/TM consistency checks. Regeneration is deferred to P7/canonical gates; do not claim overall validate PASS or treat this known missing generated index as a new regression.
- No schema/CLI/writer/validator contract selected. Do not modify trust input hash/cache, evidence/trust schema/history, ranks, Origin, frozen records, or timelines except within the newly founder-authorized bounded Opus repair. No fallback, regeneration, runner dispatch, or phase advancement. The founder's latest instruction satisfies the previously pending authorization; execution now waits solely on the assigned Opus route or an explicit founder-approved route/effort adjustment. Terra reviews the repair; real-runner `apply=false` exit 0 with empty `unknownEvidence` remains a later gate.
- Cost: campaign-complete usage/cost unavailable; prior `$4.907920` is P0-only, partial. Original interrupted/resumed run inclusion not verified; actual billing unknown. Current bookkeeping excluded. See `COSTS.md`.

- **Historical status at round-2 delivery:** **READY FOR REVIEW** (superseded by Terra FINAL FINDINGS below; not P1 complete). Current status and authority are stated at the top of this handoff.
- **PR:** <https://github.com/gaia-research/gaia-skill-tree/pull/2468> (draft, base `dev/upstream-backlog-2026-11`, head `dev/upstream-backlog-watcher-2026-11`)
- **Base / Source Gate:** `7a86be4e757acc8d01c762b4fd924b7d37899ed2` (P0 merge `bfed2d777b76448f6ede5d40e1a834050dff07d0` + `P1_SOURCE_RECONNAISSANCE.md`)
- **Implementation Commits:**
  - `232238bac8fc493fec3f04f80a803deeb7cf58f6` — `feat(p1): add explicit --repo repoint to sync-upstream and upstream.repo fallback in watcher`
  - `da255f0ee136226be434fe486e1d07e3d547616b` — `chore(registry): reconcile ruvnet/agentdb source and v3.10.0 via canonical CLI`
  - Final docs/handoff commit on `dev/upstream-backlog-watcher-2026-11` (see `git log -1` / PR #2468 head)

## Prepared P1 real-runner dry run — exact command; dispatch once after final preflight (Terra PASS recorded)

Workflow: `.github/workflows/upstream-watcher.yml`, workflow name `Upstream Watcher`, `workflow_dispatch`, intended ref `dev/upstream-backlog-watcher-2026-11` (the P1 feature branch; not default/integration). Validated workflow inputs against the current definition with `gh workflow view upstream-watcher.yml --ref dev/upstream-backlog-watcher-2026-11`; no conflicting workflow run was listed at pre-dispatch check. Dispatch is the next authorized action; never retry after an uncertain response.

```bash
gh workflow run upstream-watcher.yml \
  --ref dev/upstream-backlog-watcher-2026-11 \
  -f apply=false \
  -f child_mode=batch \
  -f staging=off \
  -f staging_bootstrap=false \
  -f skill_id= \
  -f challenge_watch=false \
  -f challenge_input= \
  -f challenge_shadow=false \
  -f escalate_candidate=
```

These are the workflow's inputs/defaults except explicit `staging=off` to ensure this is a generic batch dry run, not staged P2/F3a. `apply=false` selects `--dry-run`; `child_mode=batch`; `staging_bootstrap=false`; all optional skill/challenge/escalation values are empty/false. Do not set/infer repository variables. **Not** the P2/F3a bootstrap (`child_mode=batch`, `staging=weekly`, `staging_bootstrap=true`, `apply=false`), which remains separate and gated by founder-set variables/authority.

Expected runner behavior: workflow step invokes `scripts/upstream_watcher/watcher.py --child-mode batch --dry-run --report generated-output/upstream-watcher-report.json`; workflow artifact name is `upstream-watcher-report`. After a future authorized run, require workflow conclusion `success` (exit 0), download/read that artifact and verify top-level `unknownEvidence` is exactly `[]`, and confirm dryRun true with zero issues created/updated; investigate and stop on any discrepancy. Artifact is uploaded with `if: always()`, so inspect it even for failed runs. This command has not been run; no live report exists. `apply=false` guards watcher issue creation/update; no registry mutation is part of this workflow. Do not use `apply=true` or challenge-watch.

## 1. Summary of Changes

1. **Explicit repository repoint in `gaia dev sync-upstream` (`--repo <owner>/<repo>`):**
   - Added `--repo` argument to `DevCommand.configure` in `src/gaia_cli/commands/dev/__init__.py` (minimal argparse wiring required to expose the canonical flag on `gaia dev sync-upstream`).
   - Updated `src/gaia_cli/commands/dev/sync_upstream.py`:
     - Validates `--repo` against canonical `^[a-zA-Z0-9][a-zA-Z0-9-]*/[a-zA-Z0-9._-]+$` (no whitespace).
     - Validates `--source-url` release tag matches `--tag` (URL-unquoted) and `--source-url` owner/repo matches `--repo` when `--repo` is provided.
     - Preserves existing no-flag behavior and prevents silent repo changes: when `--repo` is omitted and `upstream.repo` already exists, `--source-url` must match `upstream.repo` (cannot silently switch via `links.github`).
     - Allows syncing the same tag when `--repo` explicitly changes `upstream.repo`; still refuses same-tag + same-repo.
     - Preserves frozen-record protection (`preflightNamedSkillMutable`) and all pre-flight checks before any write; atomic single-write update.
     - Logs repoint provenance using existing `timeline.action: upstream_synced` schema fields (`previousValue: <old_repo>@<old_version>`, `newValue: <new_repo>@<new_version>`, and `details` capturing old+new repo, version, and source URLs). Preserves all prior timeline history verbatim.
   - Added unit and CLI argparse tests in `tests/test_dev_upstream_verbs.py` (`TestSyncUpstreamRepoint`).

2. **Watcher `links.github` empty/missing fallback to `upstream.repo`:**
   - Added `resolve_suite_source` in `scripts/upstream_watcher/finder.py` and wired it into `detect_mode` (`finder.py`) and `_poll_suite` (`scripts/upstream_watcher/watcher.py`).
   - Falls back to `upstream.repo` **only** when `links.github` is empty or missing, enabling `gsd-build/get-shit-done` to be polled.
   - Non-empty invalid `links.github`, invalid fallback `upstream.repo`, and contradictory `links.github` vs `upstream.repo` all fail closed (`UnknownEvidenceError`). C1 `LOCKED_SOURCES` (`validateReleaseSource`) remains enforced.
   - Added regression tests in `tests/upstream_watcher/test_identity_2283.py`.

3. **Technical reconciliation of `ruvnet/agentdb` via canonical CLI:**
   - Reconciled `registry/named/ruvnet/agentdb.md` to verified `ruvnet/agentdb` release `v3.10.0` (`2026-11-10T19:45:36Z`, commit `2a8115de9ddbc672df4d725069b77228b43af53d`).
   - Updated `links.github` on `ruvnet/agentdb` only to `https://github.com/ruvnet/agentdb/blob/2a8115de9ddbc672df4d725069b77228b43af53d/README.md` via `gaia dev update-named --github-link ... --no-build`.
   - Preserved `suiteRef: ruvnet/ruflo`, all 5 `suiteComponents`, `level: 3★`, `trustMagnitude: 81.0`, `overallTrustGrade: B`, `evidence`, and all prior `timeline` entries. Did not touch the 5 component records (which remain live in `ruvnet/ruflo` `v3.77.1`).
   - **No approval labels, markers, or umbrella edits were performed.** This technical reconciliation is not fresh release approval.

4. **Documentation:**
   - Updated `docs/agents/upstream-watcher.md` to document `--repo <owner>/<repo>` and `resolve_suite_source` fallback behavior.
   - Updated `founder/reports/upstream-backlog-2026-11/CAMPAIGN.md` with P1 builder checkpoint.

## 2. Canonical CLI Commands Executed (`ruvnet/agentdb`)

```bash
# 1. Dry-run verification of new canonical --repo flag
GAIA_OPERATOR_OVERRIDE=1 PYTHONPATH=src python3 -m gaia_cli.main dev sync-upstream ruvnet/agentdb \
  --repo ruvnet/agentdb \
  --tag v3.10.0 \
  --source-url https://github.com/ruvnet/agentdb/releases/tag/v3.10.0 \
  --released-at 2026-11-10T19:45:36Z \
  --mode components \
  --dry-run

# 2. Actual canonical repoint + version sync
GAIA_OPERATOR_OVERRIDE=1 PYTHONPATH=src python3 -m gaia_cli.main dev sync-upstream ruvnet/agentdb \
  --repo ruvnet/agentdb \
  --tag v3.10.0 \
  --source-url https://github.com/ruvnet/agentdb/releases/tag/v3.10.0 \
  --released-at 2026-11-10T19:45:36Z \
  --mode components

# 3. Actual canonical GitHub link update (--no-build; update-named has no --dry-run flag)
GAIA_OPERATOR_OVERRIDE=1 PYTHONPATH=src python3 -m gaia_cli.main dev update-named ruvnet/agentdb \
  --github-link https://github.com/ruvnet/agentdb/blob/2a8115de9ddbc672df4d725069b77228b43af53d/README.md \
  --notes "P1 technical reconciliation per C1/ruling 4: point links.github to verified ruvnet/agentdb v3.10.0 release" \
  --no-build
```

### Before / After Fields (`registry/named/ruvnet/agentdb.md`)

| Field | Before | After |
|---|---|---|
| `links.github` | `https://github.com/ruvnet/ruflo` | `https://github.com/ruvnet/agentdb/blob/2a8115de9ddbc672df4d725069b77228b43af53d/README.md` |
| `updatedAt` | `'2026-09-10'` | `'2026-11-16'` |
| `upstream.repo` | `ruvnet/ruflo` | `ruvnet/agentdb` |
| `upstream.version` | `v3.67.0` | `v3.10.0` |
| `upstream.releasedAt` | `'2026-10-31T22:06:47Z'` | `'2026-11-10T19:45:36Z'` |
| `upstream.sourceUrl` | `https://github.com/ruvnet/ruflo/releases/tag/v3.67.0` | `https://github.com/ruvnet/agentdb/releases/tag/v3.10.0` |
| `upstream.syncedAt` | `'2026-11-02T22:17:17Z'` | `'2026-11-15T18:09:39Z'` |
| `upstream.mode` | `components` | `components` |
| `suiteRef` / `suiteComponents` | `ruvnet/ruflo` / 5 `agentdb-*` components | Preserved unchanged |
| `timeline` (appended) | *(prior 15 entries preserved verbatim)* | `upstream_synced` (`ruvnet/ruflo@v3.67.0` → `ruvnet/agentdb@v3.10.0`) + `note` (`Updated GitHub link to ...`) |

## 3. Independent-Source Public Refs

- `ruvnet/agentdb` authoritative `releases/latest`: `v3.10.0` published `2026-11-10T19:45:36Z`, <https://github.com/ruvnet/agentdb/releases/tag/v3.10.0>, commit `2a8115de9ddbc672df4d725069b77228b43af53d`.
- `ruvnet/agentdb` `README.md` at `v3.10.0`: <https://github.com/ruvnet/agentdb/blob/2a8115de9ddbc672df4d725069b77228b43af53d/README.md>.
- `ruvnet/agentdb` `main` (`84081e21afa383f7f0849fed96c90b177ce27c8b`) mentions `3.10.1` with no GitHub Release; intentionally not targeted.
- `ruvnet/ruflo` `releases/latest`: `v3.77.1` (`3a1479883b55b7f786ef0bf3141478e4dfb9444f`), where all 5 `agentdb-*` component `SKILL.md` files also remain live.

## 4. Verification Results

- `python3 -m pytest tests/upstream_watcher tests/test_upstream_approve_workflow.py tests/test_dev_upstream_verbs.py -q`: **1015 passed** in 180.51s (after P1 correction round 2; includes full-record schema validation, active `registry_schema_dir` resolution, `git check-ref-format` tag validation, atomicity, URL parsing, and watcher link-validation regressions).
- `python3 tests/upstream_watcher/parity_2283.py`: **exit 0** (`stagedRowsEqualBatchRows: true`, `stagedRowsEqualDailyUnstagedRows: true`).
- `git diff --check`: **exit 0** (clean).
- Read-only **full-frontmatter** `namedSkill.schema.json` validation of `registry/named/ruvnet/agentdb.md` against `registry/schema/namedSkill.schema.json` (via `registry_schema_dir(".")` + `validator_for` + `_schema_format_checker()`): **11 pre-existing/legacy schema errors** (while `upstream` and `timeline[-2]` `upstream_synced` individually conform):
  - `<root>`: `Additional properties are not allowed ('trustMagnitudeInputHash' was unexpected)`
  - `apexGateStatus`: `Additional properties are not allowed ('crossOrgVerifier', 'systemWideCap' were unexpected)`
  - `timeline.1.action`, `timeline.2.action`, `timeline.5.action`, `timeline.6.action`, `timeline.7.action`: `'migrate_trust_magnitude'` not in `timelineEvent.action` enum
  - `timeline.11.action`: `'recalibrate_trust_magnitude'` not in `timelineEvent.action` enum
  - `timeline.18.action`: `'note'` not in `timelineEvent.action` enum (emitted by `gaia dev update-named`)
  - `timeline.9.contributor`, `timeline.14.contributor`: `'github-actions[bot]'` does not match `^[a-zA-Z0-9][a-zA-Z0-9-]*$`
  - `registry/named/ruvnet/agentdb.md` (`da255f0ee136226be434fe486e1d07e3d547616b`) is preserved unchanged; under strict whole-record validation, future `sync-upstream` runs on `ruvnet/agentdb` will fail closed until those legacy fields/history are resolved by an authorized decision.
- `GAIA_OPERATOR_OVERRIDE=1 PYTHONPATH=src python3 -m gaia_cli.main dev validate`: 11/11 graph, schema, reference, named-skill, and suite checks passed; exited 1 solely on `Trust Magnitude consistency` because `registry/named-skills.json` is not built in this worktree (`gaia dev docs` regeneration is intentionally deferred to P7).

## 5. Limitations & Pending Gates

- **Scope note:** `src/gaia_cli/commands/dev/__init__.py` received a 6-line `add_argument("--repo", ...)` addition in `DevCommand.configure` so the canonical CLI parser exposes `--repo`.
- **No Class S / docs regeneration:** `gaia dev docs` and `scripts/build_docs.py` were not run (deferred to P7).
- **Current pending gate:** worker-sol-shared live preflight, then its bounded repair under existing authorization. Terra independently reviews the resulting repair. Real-runner dry run is only a later gate after review; P1 remains incomplete. Opus is retired from this assignment; no retry/fallback to Opus or Hydrogen. No live Sol probe has occurred.
- **Historical run parameters (not authorized to dispatch now):** `.github/workflows/upstream-watcher.yml` real-runner dry run with `apply=false` would need to confirm exit 0, empty `unknownEvidence`, `gsd-build/get-shit-done` visibility, and whether `#2278` recurs:
  - `apply`: `false`
  - `child_mode`: `fanout`
  - `staging`: `inherit`
  - `staging_bootstrap`: `false`
  - `skill_id`: `""`
  - `challenge_watch`: `false`
  - `challenge_input`: `""`
  - `challenge_shadow`: `false`
  - `escalate_candidate`: `""`

## 6. P1 Correction Round 1 — Terra Findings & Correction Receipt (2026-11-16)

Independent Terra review of `98fd89e791dff1c4034e6dfc4dc68299abcb74a0` surfaced 4 findings (1 CRITICAL, 3 WARNING). All 4 were reproduced on isolated temporary fixtures before fixing and verified fixed after:

1. **CRITICAL (`src/gaia_cli/commands/dev/sync_upstream.py` non-atomic write):**
   - *Before:* `Path.write_text` truncated the target file on a simulated partial write after 20 bytes (`465` bytes → `20` bytes).
   - *Fix:* Replaced `write_text` with canonical `gaia_cli.canonicalTransaction._atomic` (same-directory temp file + `fchmod` preserving original mode + `flush` + `os.fsync` + `os.replace` + directory fsync + temp unlink on failure).
   - *After:* Injected partial temp write and failed `os.replace` both leave original bytes 100% unchanged with zero leftover temp files; original file mode (`0o640`) preserved.
2. **WARNING (`src/gaia_cli/commands/dev/sync_upstream.py` missing schema validation):**
   - *Before:* `--user invalid_name` and `--released-at not-a-timestamp` succeeded without error.
   - *Fix:* Added `_validate_proposed_named_record` using `namedSkill.schema.json` (repo `registry/schema/namedSkill.schema.json` with bundled `src/gaia_cli/data/registry/schema/namedSkill.schema.json` fallback), `jsonschema.Draft7Validator`, and explicit RFC 3339 `date-time` / `uri` `FormatChecker` checks on proposed `upstream`, `contributor`, `required` fields, and appended `timeline[-1]` (`timelineEvent`) inside `_run_dev_preflights` before dry-run/write.
   - *After:* `invalid_name`, `not-a-timestamp`, invalid `mode`, and missing required fields all exit 1 and leave original bytes unchanged.
3. **WARNING (`src/gaia_cli/commands/dev/sync_upstream.py` regex-only URL/tag parsing):**
   - *Before:* `--tag 'v2.0.0#bad' --source-url '.../v2.0.0#bad'` and `--repo neworg/..` succeeded.
   - *Fix:* Replaced regex URL matching with `urllib.parse.urlsplit` in `_parse_release_source_url` and `_parse_owner_repo_from_url`, plus `_is_valid_owner_repo` rejecting `.` / `..`, whitespace, userinfo, ports, literal `?` / `#`, and malformed host/scheme, while percent-decoding valid release tags (`%23`, `%2F`).
   - *After:* Literal `#bad`, `?foo=bar`, `neworg/..` exit 1 with original bytes unchanged; `v2.0.0%23hotfix` and `v2.0.0%2F1` succeed.
4. **WARNING (`scripts/upstream_watcher/finder.py` prefix-only `parse_owner_repo`):**
   - *Before:* `links.github = 'https://github.com/good/repo garbage'` with `upstream.repo = 'good/repo'` resolved to `('good', 'repo', ...)` instead of failing closed.
   - *Fix:* Added `_validate_complete_github_url` and `_is_valid_owner_repo` in `resolve_suite_source` to validate scheme, host, userinfo, port, query, fragment, whitespace, and dot/dotdot segments before repo extraction, without falling back to `upstream.repo` on non-empty invalid `links.github`.
   - *After:* Malformed `links.github` raises `UnknownEvidenceError` before any `fetch_json` poll; valid root/tree/blob/percent-encoded paths and empty/missing `links.github` fallback remain intact.

- **Pending:** Independent Terra re-review of PR #2468, then authorized real-runner `Upstream Watcher` dry run (`apply=false`, exit 0, empty `unknownEvidence`).

## 7. P1 Correction Round 2 (Final) — Terra Findings on `1a3e9b8` & Correction Receipt (2026-11-16)

Independent Terra review of `1a3e9b8e2aa277415960fe5f0c8b9ac59451ffb8` (which re-verified round 1: 994 passed, parity both true, diff check PASS, atomic failure/mode/no-leaks, and old 4 findings fixed) surfaced 3 remaining WARNING findings. All 3 were reproduced on isolated temporary fixtures before fixing and verified fixed after:

1. **WARNING (`src/gaia_cli/commands/dev/sync_upstream.py:393` — subset-only schema validation):**
   - *Before:* `_validate_proposed_named_record` only checked `required` key presence plus `upstream`, `contributor`, and `timeline[-1]` subschemas; an isolated fixture with `name: ""` (violating `minLength: 1`) synced and wrote.
   - *Fix:* Replaced subschema-only checks with full-record validation of the entire composed proposed frontmatter + timeline against `namedSkill.schema.json` using `jsonschema.validators.validator_for(schema, default=Draft7Validator)` and `_schema_format_checker()`. Updated test fixtures in `tests/test_dev_upstream_verbs.py` (`_SKILL_MD_2STAR`, `_SKILL_MD_WITH_UPSTREAM`, subprocess fixture) to be valid full records (removing non-schema `installable: true` while preserving `TestFreeze` coverage).
   - *After:* Empty `name: ""`, unexpected root keys (`additionalProperties: false`), short `description` (`minLength: 10`), and invalid `createdAt` date format all exit 1 and leave original bytes unchanged.
   - *Real-record diagnosis (`registry/named/ruvnet/agentdb.md`):* Read-only full-record validation against `registry/schema/namedSkill.schema.json` surfaces 11 pre-existing/legacy schema contradictions (`trustMagnitudeInputHash`, `apexGateStatus.crossOrgVerifier`/`systemWideCap`, `timeline` `migrate_trust_magnitude`/`recalibrate_trust_magnitude`/`note`/`github-actions[bot]`). Existing `ruvnet/agentdb` bytes (`da255f0ee136226be434fe486e1d07e3d547616b`) are preserved unchanged; no schema weakening or unauthorized grandfathering was added.
2. **WARNING (`src/gaia_cli/commands/dev/sync_upstream.py:325` — schema lookup bypassed `registry_schema_dir()` and fell back to bundled schema):**
   - *Before:* `_resolve_named_skill_schema` hardcoded `Path(registry_path) / "registry" / "schema" / "namedSkill.schema.json"` and silently fell back to bundled `data/registry/schema/namedSkill.schema.json`; an isolated `.gaia/registry` fixture with a custom `upstream.version` pattern (`^release-.*$`) succeeded with `v1.0.0`.
   - *Fix:* Resolved `Path(registry_schema_dir(registry_path)) / "namedSkill.schema.json"` from the same active canonical registry as `named_skills_dir(registry_path)`, removed the silent bundled fallback, and added `validator_for(..., default=Draft7Validator).check_schema(data)` so missing, unreadable, non-object, or invalid JSON Schema files fail closed.
   - *After:* `.gaia/registry` custom schema constraint is enforced; missing, invalid JSON, and invalid JSON Schema (`{"type": 123}`) all exit 1 with original bytes unchanged.
3. **WARNING (`src/gaia_cli/commands/dev/sync_upstream.py:154` — decoded tag not validated against Git ref rules):**
   - *Before:* `--tag v2.0.0..oops` and `--tag 'v2.0.0 bad'` (with `--source-url .../v2.0.0%20bad`) passed and wrote metadata.
   - *Fix:* Added `_validate_git_tag_ref` using `subprocess.run(["git", "check-ref-format", f"refs/tags/{tag}"], capture_output=True, stdin=subprocess.DEVNULL, timeout=10, check=False)` after rejecting empty/NUL/control-character strings, failing closed if `git` is unavailable (`OSError` / `TimeoutExpired`), and calling it on both `--tag` and the percent-decoded `--source-url` tag.
   - *After:* `v2.0.0..oops`, `v2.0.0 bad`, `~1`, `^1`, `:1`, `*1`, `@{1}`, `.lock`, trailing `.`, trailing `/`, NUL/control chars, and unavailable `git` all exit 1 with original bytes unchanged; valid percent-encoded tags (`v2.0.0%23hotfix` -> `v2.0.0#hotfix`, `v2.0.0%2F1` -> `v2.0.0/1`) continue to succeed.

- **Pending:** Final independent Terra re-review of PR #2468, then authorized real-runner `Upstream Watcher` dry run (`apply=false`, exit 0, empty `unknownEvidence`). P1 is **not complete** until both gates pass.


## 2026-11-18 corrected metadata-only probe authorization and dispatch checkpoint

Founder explicitly authorized exactly one additional targeted Sol-shared correction for the two Terra findings. That correction is complete at feature source `8cb977a6aa693412021c85277595e0642a61ae64`; independent Terra high-effort review passed with no actionable findings and 214 focused tests. Parent-run full regression passed 1180 tests in 237.67s at the same SHA, both parity booleans true, all missing arrays empty, transient retained, clean Git/index, and protected workflow/live.py/shared-helper/registry/skill-tree surfaces unchanged. Parent independently verified the historical original 605-byte JSON SHA-256 `11cec0992acd45591220737c5ffac4c1b546aff02c34f627aa73d464f080be87` and first metadata artifact SHA-256 `85fe68bf7bdd3808c7077d63bae431701276d14f14ad3cb6a1450ea5f046a03f`. Attribution is to the parent, not retroactively to Terra. Terra's historical artifact hashes were not rechecked locally. `gaia dev validate` remains non-green/unclaimed because the Class P index is missing. Costs remain complete UNAVAILABLE; `$4.907920` is P0 partial, not current campaign total.

Current decision/status: one reviewed metadata-only diagnostic is authorized; P1 remains BLOCKED pending that diagnostic. The additional code correction does not grant permissions, relax production guard, permit ordinary watcher writes, or authorize merge. Root cause #2278 remains UNKNOWN until diagnostic data exists. Preserve prior normal-run failure 43896669237 (head `fa6ca42...`, original 605-byte artifact) and first metadata-run failure 43927918189 (head `59ff427...`, receipt/hash above) as historical failures; neither is rewritten as fixed or rerun.

Preflight verified clean feature worktree `dev/upstream-backlog-watcher-2026-11`, exact HEAD `8cb977a6aa693412021c85277595e0642a61ae64`, and explicit remote feature ref at that same SHA. Integration remains `bfed2d777b76448f6ede5d40e1a834050dff07d0`; schema ref remains `6bed0edf324d49e42cd8953351deaccaa733d22f`. PRs #2468 and #2469 remain OPEN/DRAFT, targeting integration. No reset, discard, tracking repair, merge, normal run, permission change, label/variable/issue/registry mutation, or unrelated workflow dispatch.

Exact reviewed existing workflow inputs for the one experiment: `.github/workflows/upstream-watcher.yml` on feature ref; `metadata_probe=true`, `apply=false`, `child_mode=batch`, `staging=off`, `staging_bootstrap=false`, `skill_id=`, `challenge_watch=false`, `challenge_input=`, `challenge_shadow=false`, `escalate_candidate=`. All normal watcher steps must skip; challenge/upstream-poll dependents must remain skipped. Workflow permissions remain exactly `issues: write`, `contents: read` (implicit metadata read); no `pull-requests: read`, PAT, or permission changes. Expected artifact `DIAGNOSTIC-upstream-metadata-probe` / `generated-output/diagnostic-upstream-metadata.json`, explicitly diagnostic-only, acceptance-ineligible, P1-false. Combined inventory guard unchanged.

At this checkpoint there is no new dispatch result yet. After one dispatch, record the single returned run identity/status and freeze the feature branch. Do not poll, sleep, monitor, or collect artifacts in this job; background monitor owns that. If submission response is uncertain, perform one read-only lookup by exact head/time; never repeat POST. P1 remains blocked until the diagnostic is assessed.
