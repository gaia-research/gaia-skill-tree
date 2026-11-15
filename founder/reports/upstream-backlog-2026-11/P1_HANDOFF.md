# P1 Handoff — Watcher & CLI Technical Reconciliation

- **Status:** **READY FOR REVIEW** (P1 correction round 1 complete; **NOT P1 complete** — awaiting independent Terra re-review, then authorized real-runner `Upstream Watcher` dry run `apply=false` exit 0 with empty `unknownEvidence`)
- **PR:** <https://github.com/gaia-research/gaia-skill-tree/pull/2468> (draft, base `dev/upstream-backlog-2026-11`, head `dev/upstream-backlog-watcher-2026-11`)
- **Base / Source Gate:** `7a86be4e757acc8d01c762b4fd924b7d37899ed2` (P0 merge `bfed2d777b76448f6ede5d40e1a834050dff07d0` + `P1_SOURCE_RECONNAISSANCE.md`)
- **Implementation Commits:**
  - `232238bac8fc493fec3f04f80a803deeb7cf58f6` — `feat(p1): add explicit --repo repoint to sync-upstream and upstream.repo fallback in watcher`
  - `da255f0ee136226be434fe486e1d07e3d547616b` — `chore(registry): reconcile ruvnet/agentdb source and v3.10.0 via canonical CLI`
  - Final docs/handoff commit on `dev/upstream-backlog-watcher-2026-11` (see `git log -1` / PR #2468 head)

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

- `python3 -m pytest tests/upstream_watcher tests/test_upstream_approve_workflow.py tests/test_dev_upstream_verbs.py -q`: **994 passed** in 201.54s (after P1 correction round 1; includes new atomicity, schema validation, parsed URL/repo, and watcher link-validation regressions).
- `python3 tests/upstream_watcher/parity_2283.py`: **exit 0** (`stagedRowsEqualBatchRows: true`, `stagedRowsEqualDailyUnstagedRows: true`).
- `git diff --check`: **exit 0** (clean).
- Read-only `namedSkill.schema.json` validation of `registry/named/ruvnet/agentdb.md` (`upstream` block and `timeline[-2]` `upstream_synced` event): **0 errors**; `suiteRef: ruvnet/ruflo`, 5 `suiteComponents`, `level: 3★`, `trustMagnitude: 81.0` preserved.
- `GAIA_OPERATOR_OVERRIDE=1 PYTHONPATH=src python3 -m gaia_cli.main dev validate`: 11/11 graph, schema, reference, named-skill, and suite checks passed; exited 1 solely on `Trust Magnitude consistency` because `registry/named-skills.json` is not built in this worktree (`gaia dev docs` regeneration is intentionally deferred to P7).

## 5. Limitations & Pending Gates

- **Scope note:** `src/gaia_cli/commands/dev/__init__.py` received a 6-line `add_argument("--repo", ...)` addition in `DevCommand.configure` so the canonical CLI parser exposes `--repo`.
- **No Class S / docs regeneration:** `gaia dev docs` and `scripts/build_docs.py` were not run (deferred to P7).
- **Pending Gate 1:** Independent Terra review of PR #2468 on `dev/upstream-backlog-watcher-2026-11`.
- **Pending Gate 2 (after Terra PASS):** Dispatch `.github/workflows/upstream-watcher.yml` on the real runner with `apply=false` to confirm exit 0, empty `unknownEvidence`, `gsd-build/get-shit-done` visibility, and whether `#2278` recurs:
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
