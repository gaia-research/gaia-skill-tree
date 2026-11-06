# #2283 canonical fanout cache + accepted security composition

## Status / exact checkpoints

**Authorized implementation and offline evidence completed. Fresh independent combined-source review remains REQUIRED before parent publication/integration. Builder evidence is not independent acceptance, and standalone #2292 ACCEPT does not accept these watcher bytes.**

Dedicated branch/worktree: `dev/steward-founder-lock-2283`, `$HOME/.gaia-worktrees/steward-founder-lock-2283`.

| Checkpoint | Exact SHA |
|---|---|
| Input founder candidate | `42322964ae5899712df5b492e98f37600e04bd89` |
| Cache repair | `25de4ebd7e47d8cef95bcac354e6697123368542` |
| Independently accepted standalone security | `8298c459a2fc2dd8a5e7d36e9e6e16a910454d6d` |
| Explicitly authorized dependency (already campaign-merged) | `dc5781a3199922d51ddabbbb0ab42f0fb2e39fbe` |
| Dependency tree | `ec673a0571cc24e0d5c091143db33d774367d10a` |
| Actual feature-only dependency merge | `e624328721f8e86bc54adf7d8c1cd080e341217d` |
| **Source + matrix checkpoint** | **`afe8644bd841473ef3ad5711bed5cc0cd1343667`** |
| Source checkpoint tree | `7706581a705c0f874e20fd4f317e4dfe41289190` |
| **Final feature HEAD (proof-only last commit)** | **`5cbe7e80af20589da4c125289b263c70d869ea55`** |
| Final tree | `0fb861268760517d6706a9b71b0d3b246a06c0d4` |

The merge was ordinary `git merge --no-ff` into this feature branch only, conflict-free. Its parents are exactly the cache repair and authorized dependency above. All prior history is retained; no reset/rebase/cherry-pick, project remote operation, push, main or campaign integration ref write occurred. Author/committer on all four new feature commits: Marcus Rafael B. Tiongson <153011150+mbtiongson1@users.noreply.github.com>, via per-command git flags, not global configuration.

Runtime verified `PI_PROVIDER=openai-codex`, `PI_MODEL=gpt-6.1-sol`, `PI_REASONING_LEVEL=high`. No nested agents, model fallback, or imposed task time/turn caps. Root/founder CLAUDE, graft skill, strict repair proof/rejection and mandatory security aggregate review were read. Native graft was relevant; no available Skill Heaven surface was installed or falsely claimed validated.

## Cache defect: actual BEFORE / AFTER

The independent rejection correctly identified a pre-existing, in-scope defect: preflight/snapshot/identity validation used case-insensitive GitHub owner/repo identity, but the same-run cache used case-sensitive `(label, prefix)`. A newly created issue was absent from the fixed initial snapshot. Mixed `ruvnet/ruflo` / `RuvNet/Ruflo` findings could therefore create two umbrellas; existing snapshots could be updated unnecessarily.

Added **18 release regression cases** before changing production source: both casing directions × empty/older/current snapshot × same/new/case-distinct tag. On exact input production source the selected regression command produced **14 failed / 4 passed / 63 deselected in 0.64s**. At the repaired/combined source all 18 pass. The full identity module, including six new bootstrap cases, a source-suffix preservation case and mixed-case conflicting-skill preflight variants, passes **90 tests**.

An additional exact-Git-revision offline replay loaded `issuer.py` at 42322964 and the source checkpoint into in-memory modules; all creates/updates/resets/body edits were mocked. Each case submits lower-case `v2`, mixed-case next finding, then an exact repeat:

| Snapshot / next version | Before creates / updates | After creates / updates |
|---|---:|---:|
| Empty / `v2` | 2 / 0 | 1 / 0 |
| Older `v1` / `v2` | 0 / 2 | 0 / 1 |
| Current `v2` / `v2` | 0 / 1 | 0 / 0 |
| Empty / `v3` or `V2` | 2 / 0 | 1 / 1 |
| Older `v1` / `v3` or `V2` | 0 / 2 | 0 / 2 |
| Current `v2` / `v3` or `V2` | 0 / 2 | 0 / 1 |

Every after-case selects ONE issue across all three findings; the last repeat skips. Legitimate new versions still update, including case-distinct `V2`. Existing same-source/different-skill refusal remains before any mocked writes, now also with mixed source casing.

### Routing / case-sensitive boundaries

- Cache lookup and every release/bootstrap suite cache insertion lower-case only the **suite-bearing title prefix**, consistent with existing snapshot matching. The prefix excludes the version/tag.
- Same-version checks compare the suffix after that matched prefix **exactly**; `v2 != V2`. Previous-version comments slice the matched prefix rather than applying case-sensitive `removeprefix` to a differently cased title.
- Skip caches preserve the actual existing title. No identity-only change rewrites title/body/provenance, resets approval or performs an unnecessary update.
- No source URL, whole title/body, branch, tag, candidate path or version is blindly lower-cased. A rendered `https://github.com/RuvNet/Ruflo/releases/tag/Release/V2` / `Release/V2` control preserves exact source suffix and caller casing. Inputs and original snapshot objects remain unmodified.
- Generated release bodies remain strictly validated with `generated=True` before create/update/approval reset and before every generated-cache skip/update. Original historical snapshot recovery remains explicit `False`. Malformed generated bodies retain zero-write refusal, and historical headless repair remains supported. No strictness was relaxed to solve routing.

The bounded repair changes only `scripts/upstream_watcher/issuer.py` and `tests/upstream_watcher/test_identity_2283.py`: 91 insertions / 13 deletions at its own commit. Shared prefix use requires the bootstrap controls; child identity, batch emission policy and registry authority were not expanded.

## Dependency composition integrity

Read-only Git/blob/matrix assertions establish:

- All four required checkpoints are ancestors of final HEAD; feature merge parents are exact.
- **24/28 accepted security paths are byte-identical** to independently accepted standalone source. The four intentional differences are current matrix/proof/documentation bindings only: `2283-dispositions.json`, `2283-scanner-proof.json`, `2283-reconciliation.md`, `2283-finish-proof.md`. One new composition-proof document is added.
- Accepted `.github/workflows/branch-scope.yml` and `tests/steward/test_landing.py` are byte-identical to the accepted dependency. Its canonical Class B scope/fork protection is retained, not reconstructed or discarded.
- Overlapping `issuehygiene/reconcile.py` equals the founder version with **only the accepted unused `Path` import removed**. Both parents' substantive work survives.
- All **22 other founder paths** touched since the shared baseline remain byte-identical to the input founder candidate, including original lock records/marker/workflow source and watcher count/source safeguards.
- **39/39 matrix-bound current sources** equal the committed source checkpoint; **38/39** also equal standalone security source. The sole source difference is the expected founder `live.py`; it equals the input founder file exactly. Neither the dependency merge nor the cache fix changes it again.
- The sole matrix field changed against accepted security is `scripts/upstream_watcher/live.py.reviewedSourceSha256`. All IDs, original source hashes, line/pattern/fingerprint history, multiplicities, statuses, original authorities, ledger dispositions and other 38 rows remain exact.

## Required changed-watcher semantic/source refresh

- Path: `scripts/upstream_watcher/live.py`
- Original ID: `debt:credential_leak:scripts-upstream-watcher-live-py:2393fe51171e5834`
- Original reviewed/source SHA-256 preserved: `6bc60cf787a1a18b5b31629f1bb6c368d03422fff94ee644bdade8c466edf5ad`
- **Current source SHA-256:** `ed81ff83b6ea246aada1dee23bbbdbe053f50f506b171c5c816b9e97174a8d12`
- **Current matrix SHA-256:** `ef616f78c39ea79eb12a499db7c2777cb1c3553efcc8c6b14229fc1c5381dda5`
- **Current machine proof SHA-256:** `a4344057e0cb98d4f1158c0bb56c06567021de6431ee5091a3820523b7653420`
- Original fingerprint `39be36177943`, original matrix line 465, current detected line **511**, one occurrence.

This is **not hash-only clearance**. The original lexical match remains the unchanged `mentions_suite` whole-token docstring example, not an embedded credential. `canonical_umbrellas` uses the escaped/lookaround title predicate only to identify ambiguous suite titles, which fail closed; the exact identity parser is separate.

The new bytes since standalone source are operationally meaningful: `LiveGh.list_issues("open")` calls `_verified_open`, consumed by fanout `_open_snapshot` and batch `read_live`. Metadata-count acceptance now requires before/after agreement. On discrepancy, `_open_totals` uses non-search GraphQL typed issue/PR connection counts, supplied as explicit `gh api graphql -f` query/owner/name arguments. Missing/error/partial responses, booleans/nonintegers/negative counts and invalid repository identity refuse. Counts bracket a second complete REST walk; both typed row counts, totals and ordered identities must agree. `_walk` rejects malformed/nonpositive/boolean/duplicate issue numbers. There is no offset tolerance, search-based absence, literal authentication value, scanner bypass or new authority in these additions. Existing mutation methods were not modified by this delta.

Full count/pagination/source/identity regressions pass under mocks. This does **not** prove historical #2278 runner/token context, a transactional GitHub snapshot guarantee, runtime credential handling, correctness of external live counts, or safety of operating the whole watcher. Original S28 semantic classification is of one docstring occurrence only, not the entire new file. Fresh independent combined review must inspect these changes and their callers; the prior 8298 ACCEPT cannot be reused for them.

## Actual OFFLINE scanner replay

Inspected the supplied `finish_scanner_proof.py` first, then copied it into ignored local scratch and corrected stale defaults. The replay binds **actual committed** source/matrix bytes to `afe8644bd841473ef3ad5711bed5cc0cd1343667` and its tree, not the old hard-coded helper HEAD. The final commit is proof-only and is not mislabelled as the source checkpoint. Each current finding's sanitized line/pattern/fingerprint is recorded in the machine proof separately from preserved original locations.

Baseline scanner loaded in memory from `d694986b865e158e21c613683021a9b7822f945c` scanned baseline bytes; current sensor scanned committed reviewed bytes. Only the **39 selected paths**, not the fleet/canonical scanner, were invoked:

| Group | Paths | Original / baseline detected / current detected |
|---|---:|---:|
| D1 | 16 | 30 / 30 / 30 |
| D2 | 14 | 24 / 24 / 24 |
| D3 | 9 | 17 / 17 / 17 |
| Total | 39 | 71 / 71 / 71 |

Exact `(pattern, fingerprint)` multisets match, including repeated line/mirror occurrences. **Zero newly visible matches**; none suppressed. Original source hashes, current reviewed hashes and current committed blobs were asserted for all 39 paths. The previous 72-result/prose-match history and accepted standalone 71-replay remain explicitly historical in the machine proof/documents.

**23 controls actually passed:** eight generated credential families × `src/` and `tests/` paths (16 detected/sanitized positives); five unrelated same-line marker/neighbor cases (old false-negative vs new detection); two inherited in-match placeholder cases. Generated values never leave memory or appear in proof output. Baseline-equal policy, redactor/pattern source and public scanner were separately asserted; no policy/allowlist/redactor weakening occurred. Matrix/checker success does not authenticate original inventory identity or scanner authority; independent historical inventory review remains separately attributed.

**224 supported files per mirror**: exact path/content equality; zero missing/changed/mirror-only files; manifest SHA-256 `8d2debc9dd3b57fb40822744e1bb5df95835dee3ce277c50805dadc25cb8b6dc`. Five cached pinned official test originals retain accepted hashes; local copies adapt only import prefixes to this checkout. No new network/provenance fetch occurred.

## Actual tests / checks

At the exact source checkpoint (only proof/docs changed afterward):

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q -p no:cacheprovider \
  tests/steward/issuehygiene tests/steward/test_founder_workflow_lock_2283.py \
  tests/upstream_watcher scripts/upstream_watcher/tests/test_upstream_watcher.py
# 1427 passed in 239.66s

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q -p no:cacheprovider \
  tests/steward/test_security_reconciliation.py tests/steward/test_sensors_security.py \
  tests/steward/issuehygiene/test_b7_scrub.py tests/steward/issuehygiene/test_b8_census.py \
  tests/test_security_scanner.py tests/test_installability.py::test_diagnostics_are_bounded_and_redacted \
  tests/steward/test_landing.py
# 292 passed in 149.93s

node --test generated-output/security-reconciliation/upstream/local-*.test.mjs
# 42 passed, 0 failed/skipped
node --test tests/steward/impeccable_compatibility.test.mjs
# 6 passed, 0 failed/skipped
```

After current proof regeneration, focused security reconciliation / watcher identity / founder-lock modules: **123 passed in 5.26s**. Repeated at exact final HEAD `5cbe7e80af20589da4c125289b263c70d869ea55`: **123 passed in 7.15s**; final matrix/proof/current-source binding checks and cumulative baseline-to-HEAD `git diff --check` passed, tracked worktree clean. Suite counts overlap and are not summed as unique tests. `check_security_dispositions.py`, mirror `--check`, exact composition assertions and `git diff --check` passed. Tests use disposable local remotes/fixtures or mocked operations only; no real project remote was contacted. The old worker 1400-pass result is not represented as new-fix evidence. No full repository, Linux/Windows or Node-18 run is claimed; standalone platform evidence is not promoted to a new combined-source CI receipt.

## Protected holds / saved-census replay

Re-ran the real offline reconciliation renderer on the saved **218-issue** census, SHA-256 `ce11107af1030b42ac74887d89fb61ce785c614fb8ff5cb20747a7075e274d24`, with fixed time `2026-11-04T20:45:00Z`. Compared to saved `reconcile-before.json`: **218/218 original and snapshot objects unchanged**, **67/67 GBrain children held/none**. #1833 stays technical-only B; #1835/#2002/#2126/#2127 remain held/none. A=0, B=5, C=0, none=213; zero closure plans; resulting manifest hash `4ab6e52e7f3af33d51972e450736b8ce6a9109511b21d3ad0b2ef489bf51d3c3`.

The broad suite retains marker + all four finalized canonical records as separate prerequisites, missing/renamed/non-file marker and incomplete/open/malformed/mismapped-record refusal, unrelated fresh-checkout compatibility, generated strictness and legacy headless recovery. This is saved-input replay, not fresh census verification, ledger settlement or recovery of supposedly lost holds. `writesEnabled=false` and open closure authority remain unchanged.

## Deliverables / local reproducibility

Tracked evidence: `docs/agents/security/2283-founder-composition-proof.md`, refreshed `2283-scanner-proof.json`, and current-binding pointers in the two historical security documents. Only the one authorized current matrix hash field changed. Main cache/test changes are in the dedicated cache commit.

Ignored local receipts under feature worktree:

- `generated-output/founder-cache-composition/`: before/after test logs, combined tests, final focused log, `mixed_case_probe.py` + exact results, `composition_integrity.py` + result, saved reconciliation and hold summary, Node receipts.
- `generated-output/security-reconciliation/composition_scanner_proof.py`: inspected/adapted replay helper, no stale HEAD default; `combined-scanner-proof.json`; cached official test originals and import-only local adaptations.

These scratch files are not canonical state/receipts or hidden authority. Parent may inspect them and the committed documentation for the new independent combined review.

## Remaining gates / explicit no-operations boundary

1. Parent publication and **fresh independent combined-source engineering review** of final HEAD and source checkpoint/proof bindings. No self-approval, and no reused standalone acceptance for new watcher bytes.
2. C1 AgentDB canonical metadata/baseline reconciliation needs separate authorization/review. No registry/topology/trust/rank/evidence/intake/schema-authority decision here.
3. Historical #2278 root cause remains unproven. Source count safeguards/tests are not a historical diagnosis or live operational certificate.
4. C2 migration and C3 founder curation remain deferred with family/descendant holds intact.
5. C4 compiled sync/release compiler, threat engine, pause preservation, credentials/external state and any explicitly authorized future activation remain separate gates. No activation/compilation or #2126/#2127 closure.
6. Normal repository protection, applicable CI and human main-merge gates remain; no current combined-source remote CI all-green claim.

No canonical ledger/origin/scan/run/record/migrate/rollback/lease, real GH/forge write, project push/remote operation, main/campaign integration merge, package/global configuration change, deployment/release, credential probe, rotation or historical state rewrite was performed. The sole actual merge was the explicitly authorized accepted dependency into this feature branch. All bounded work is locally committed and tracked status is clean; no full-campaign/all-clear declaration is made.
