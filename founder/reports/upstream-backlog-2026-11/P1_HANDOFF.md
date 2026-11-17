# Current handoff — ordinary P1 acceptance pending

The founder-authorized ordinary-only permission preparation is ready to publish; exactly ONE normal `apply=false` acceptance run is authorized after publication. Repeated authorization/continue replies mean one grant/run. P1 BLOCKED until actual report passes. Current expected local branch/head: `dev/upstream-backlog-watcher-2026-11` / `d176e98c8116c19efed40efeed9ef829b81f505e`, clean; prior remote feature ref `ef05149256f6091429f4f618bccaade3c3da7ee1` is ancestor. Tracking to integration/ahead is intentional. Terra corrected test PASS (238 focused); parent exact-head full regression 1204 passed in 196.33s, exit 0; parity true, missing arrays empty, transient retained. Offline normal-path dry-run passed with unknownEvidence empty and zero issue writes; not hosted acceptance. Full validate not green (Class P index missing); actionlint unavailable. Protected digest unchanged.

Publish 3cc+d176 and report checkpoint; update existing #2468/#2469 bodies preserving DRAFT/OPEN/no-merge. Then one dispatch only on feature ref after no-conflict check with `apply=false`, `metadata_probe=false`, `permission_ab=false`, `child_mode=batch`, `staging=off`, `staging_bootstrap=false`, `challenge_watch=false`, `challenge_shadow=false`, and empty skill/challenge/escalation inputs. No variables/labels/issue writes/P2/merges/extra probes. On uncertain submit do not repeat; one bounded read or UNKNOWN. Record run ID/URL/ref/full head/UTC/inputs/individual initial statuses; only report skips actually observed. Stop immediately for background monitor, no poll/artifacts/post-dispatch commit. Acceptance requires exit 0, artifact `upstream-watcher-report`, unknownEvidence empty, issue creates/updates zero. P1 remains BLOCKED until then.

---

## Historical handoff (preserved; superseded where conflicting)

# P1 Handoff — Watcher & CLI Technical Reconciliation

## Latest observed outcome — run 43950071316; stop at decision gate

Run `43950071316` failed at expected feature HEAD `a7cdb51158ef1b0383269478d2bb92d262f1f465`; diagnostic read exit 3, upload succeeded, ordinary jobs skipped. Artifact `14265604550`, file SHA-256 `fca80159c836ec44d1270268e2a3319963a16ef6aabba320a89731286b7567e0`, archive SHA-256 `88501e2aaf175928c2d66a1a629313812697e541be87f485d903c1ff439f2e05`. REST completed at 247 issues / 0 PRs; complete before GraphQL had 247 issues / 7 PRs. Issues matched; PRs and aggregate disagreed. Counts stable at sampled endpoints, but after GraphQL was partial; identity stability unknown. No 403/permission denial observed. API visibility discrepancy observed; cause unproven. P1 remains BLOCKED; diagnostic cannot qualify as acceptance. Full receipt: [P1_METADATA_PROBE_43950071316.md](P1_METADATA_PROBE_43950071316.md). **STOPPED AT PERMISSION DECISION — observed REST/GraphQL visibility gap; P1 BLOCKED.** Proposed next gate only: request specific founder approval for ONE controlled metadata-only permission A/B (details in `P1_COUNT_REPAIR.md`). Not authorized by prior 'proceed'; no implementation or dispatch.

## Current checkpoint — authorized metadata-only diagnostic dispatch

Founder authorized the canonical-reuse proposal. Source `9b6c65ec58288a6d28e1c1e7b08093e58ed4a84b` independently passed Terra high review with no findings (229 focused tests, 3.39s); separate non-author parent regression passed 1195 tests in 211.20s; parity both true, missing arrays empty, transient retained, clean Git/index/status, protected surfaces unchanged. Local historical JSON hashes checked against available files match; remote PR-ref/archive hashes were not independently rechecked. `gaia dev validate` remains non-green/unclaimed due missing Class P index. Inputs are metadata_probe=true, apply=false, child_mode=batch, staging=off, staging_bootstrap=false, remaining filters empty and challenge flags false. P1 remains BLOCKED pending diagnostic; original #2278 causality UNKNOWN. Integration/schema pinned at `bfed2d777b76448f6ede5d40e1a834050dff07d0` / `6bed0edf324d49e42cd8953351deaccaa733d22f`; PRs #2468/#2469 OPEN/DRAFT, no merge. See append-only dispatch receipt.

## Current next action — await canonical-reuse scope authorization

Lead read-only proposal only (not granted authority): consider ONE bounded metadata-probe refactor reusing existing canonical read-only pagination/transport and removing independent query reconstruction; see [P1_COUNT_REPAIR.md](P1_COUNT_REPAIR.md). Exact rejected query and cause remain UNKNOWN; run 43941667985 failed and P1 remains BLOCKED. Await explicit founder authorization of this specific scope. No implementation, probe, permission change, normal run, or merge. PRs #2468/#2469 remain OPEN/DRAFT; feature HEAD `d42c6c2f3c02b0ed239cb9176f6b84141ddf6897` clean, integration `bfed2d777b76448f6ede5d40e1a834050dff07d0` and schema `6bed0edf324d49e42cd8953351deaccaa733d22f` unchanged.

## Current gate — second actual metadata probe failed; STOP for Lead decision

Run `43941667985` failed at exact feature HEAD `fcde5d9324812276ea09029ae225089bdfbe3952`: diagnostic-only job executed, metadata step exit 3, artifact uploaded; ordinary watcher, challenge-watch, and upstream-poll jobs skipped. REST collected one 100-row issue-typed page and then rejected the continuation as `unsafe-link-query` after HTTP 200. Before GraphQL typed walks completed (245 issues, 7 PRs); after values are samples only. Aggregate count 252 before/after. The first REST page's 100 identities match the complete before GraphQL issue set; this is not a full comparison. REST typed counts, REST PR visibility and identity stability are unknown. No 403/permission error occurred. Sanitized report and artifact hashes are in [P1_METADATA_PROBE_43941667985.md](P1_METADATA_PROBE_43941667985.md).

The diagnostic is nonhealthy, acceptance-ineligible and does not establish original #2278 cause. One authorized extra correction and one probe have been used. **No further code correction, permission grant, retry/dispatch, normal watcher run, or merge is authorized.** No permission increase is justified from an HTTP-200 validator rejection alone. Next safe action is a Lead/founder decision whether to authorize bounded read-only review of continuation-query validation. Preserve prior normal run 43896669237 and first metadata run 43927918189 receipts unchanged. P1 remains BLOCKED; PRs #2468/#2469 remain OPEN/DRAFT; integration `bfed2d777b76448f6ede5d40e1a834050dff07d0` and schema `6bed0edf324d49e42cd8953351deaccaa733d22f` unchanged; NO MERGES.

## Superseded gate — 2026-11-17 STOPPED; Terra findings at round 2

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

Historical dispatch-time checkpoint; superseded by current actual outcome in the gate at the top of this file and [P1_METADATA_PROBE_43941667985.md](P1_METADATA_PROBE_43941667985.md). The diagnostic failed. Do not redispatch or monitor/poll further; P1 remains blocked pending Lead/founder decision.


## 2026-11-18 — paired diagnostic publication and dispatch handoff

Founder latest **`proceed`** explicitly authorizes publication of reviewed A/B workflow and exactly ONE paired diagnostic. It is not authority for a normal watcher run or P1 acceptance. Terra independently PASSed implementation (235 focused tests). Non-author parent regression at feature HEAD `bb94411d9ea831c06a46b004eed9d28394c06d21`: 1201 passed / 222.15s, parity both true, missing arrays empty, transient retained and clean Git. Full `gaia dev validate` remains not green/claimed because Class P index is missing; actionlint unavailable.

Exact required dispatch: existing `.github/workflows/upstream-watcher.yml`, feature branch `dev/upstream-backlog-watcher-2026-11`; `permission_ab=true`, `metadata_probe=false`, `apply=false`, `challenge_watch=false`, `challenge_shadow=false`, `staging_bootstrap=false`, `child_mode=fanout`, `staging=off`, empty `skill_id`, `challenge_input`, `escalate_candidate`. A/B true must force every ordinary path to skip. CONTROL and TREATMENT are independent and always upload separate artifact names `DIAGNOSTIC-upstream-metadata-permission-ab-CONTROL` and `DIAGNOSTIC-upstream-metadata-permission-ab-TREATMENT`; each contains `diagnostic-upstream-metadata.json`. Only treatment adds `pull-requests: read`; no permissions/normal paths change.

Before publish, local feature HEAD clean at `bb94411d9ea831c06a46b004eed9d28394c06d21`; remote feature ancestor `1a57a915fe02d45157da9e717fa7149a9f9e35d1`. Integration `bfed2d777b76448f6ede5d40e1a834050dff07d0`, schema `6bed0edf324d49e42cd8953351deaccaa733d22f`. Approved author identity `Marcus Rafael B. Tiongson <153011150+mbtiongson1@users.noreply.github.com>`. Push only the local feature and report checkpoint to explicit feature ref. Existing #2468/#2469 bodies may be updated; keep both OPEN/DRAFT, base integration; no merges. Following exactly one dispatch, perform one read-only run lookup only if needed to identify the run. Return promptly, do not monitor/poll/sleep, collect artifacts, or interpret pair; background lead owns monitoring. Freeze branch after dispatch. P1 remains BLOCKED; permission causality UNKNOWN. Complete costs UNAVAILABLE; `$4.907920` P0 partial, not total.


## 2026-11-19 — paired diagnostic result (run 43966535296)

The paired metadata-only diagnostic completed. Actual run head was `f6939f9ace0f672c76297eb749b2b314d262b7c7`. CONTROL job `133647365969` failed its metadata step (exit 3) with observed contents:read, issues:write, metadata:read; TREATMENT job `133647366335` succeeded with the same plus pull-requests:read. Normal visibility, upstream polling, and challenge-watch jobs were skipped. Parent failure is the CONTROL diagnostic's expected nonhealthy signal, not the experiment verdict.

Both unmodified artifacts, bounded metrics, exact identity hashes, artifact IDs/hashes, and limits are recorded in [P1_PERMISSION_AB_RUN_43966535296.md](P1_PERMISSION_AB_RUN_43966535296.md). In brief: complete REST showed CONTROL 247 issues / 0 PRs versus TREATMENT 247 issues / 8 PRs; complete GraphQL-before sets matched across arms. After GraphQL was an incomplete one-node sample in each arm. Runner image versions differed. This is empirical context-specific support for association of the treatment grant with PR visibility, not universal API causality or P1 acceptance. Both artifacts mark diagnosticOnly=true, acceptanceEligible=false, p1Pass=false; causality is not established. P1 remains BLOCKED; ordinary permissions unchanged. No new run or merge authorized.
