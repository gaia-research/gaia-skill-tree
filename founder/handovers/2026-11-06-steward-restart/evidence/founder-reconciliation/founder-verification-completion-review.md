# Independent verification completion — combined source PR #2283

## Findings and final combined gate

**COMPLETE — combined SOURCE-PR ACCEPT at exact `5cbe7e80af20589da4c125289b263c70d869ea55`.** No remaining actionable source defect or missing assigned independent check was established. This is the whole bounded founder/watcher/security source-PR gate, not merely acceptance of these new probes. It combines the prior independent engineering/security coverage with the four completed checks below.

The mixed-case duplicate independently rejected at `42322964ae5899712df5b492e98f37600e04bd89` is now independently reproduced before, and verified repaired after. The four evidence gaps in Terra's `founder-composition-independent-review.md` are closed by actual new verification, not by treating builder assertions as independent evidence. That historical BLOCKED report is preserved unchanged. The mandatory changed-watcher source/caller composition gate from the standalone security ACCEPT is satisfied for these exact bytes. Older documents' pending-review phrases describe their historical checkpoints; they are not newly outstanding requirements.

**No operational, activation, closure, credential-clearance, main-merge or full-mission approval is granted. Current `5cbe` CI is not verified green by this review.**

## Identity, runtime and method

Independent reviewer-shared; never implementation author. Observed runtime: `PI_PROVIDER=openai-codex`, `PI_MODEL=gpt-6.1-sol`, `PI_REASONING_LEVEL=high`; Python **3.14.6**, Git **2.56.0**, local Termux environment. No nested model/agent or fallback route was used.

Assigned detached checkout:
`$HOME/.gaia-worktrees/steward-founder-lock-2283-review`

`pwd`, `git rev-parse HEAD`, and `git status --short` confirmed the requested checkout, exact candidate, and clean status. Root/founder CLAUDE and graft skill were loaded; Terra's report was read first. Graft supplied the sensor, predicate and caller locations before source inspection. No tracked/source/configuration file was changed. Fresh checks were inline `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python - <<'PY'` programs, Git/blob comparisons and read-only source inspection. They did not invoke a worker probe/helper. Only this assigned report is durable authored output; allowed unreferenced merge-tree Git objects and ignored retrieval cache are the other local side effects.

## 1. Fresh exact-revision fanout reproduction — PASS

Loaded **both exact Git versions** of `issuer.py` and `releaseidentity.py` into in-memory modules:

- Before: `42322964ae5899712df5b492e98f37600e04bd89`.
- After: `5cbe7e80af20589da4c125289b263c70d869ea55`.

The independent fixture constructed three findings: first source/skill casing, second opposite casing, then an exact repeat of the second. Source URLs used the corresponding GitHub repository spelling and `/releases/tag/<tag>`. Both directions of `ruvnet/ruflo` ↔ `RuvNet/Ruflo`, three initial snapshots (empty, `v1`, `v2`), and three next tags (`v2`, `v3`, `V2`) were exercised: **18 cases per revision, 36 total**.

`_open_snapshot`, creates, updates, body edits and approval resets were mocked. `LiveGh` construction, subprocess execution and socket construction were forbidden during each invocation, so an unmocked external escape would fail. The real rendering, payload parsing, preflight, identity validation and routing/cache code ran. `releaseidentity.py` is byte-identical across the two revisions. Findings and snapshots were deep-compared afterward and remained unchanged.

Counts below are **creates / updates**, identical in both casing directions:

| Initial snapshot | Next tag | Before | Final |
|---|---|---:|---:|
| Empty | `v2` | 2 / 0 | **1 / 0** |
| Empty | `v3` | 2 / 0 | **1 / 1** |
| Empty | `V2` | 2 / 0 | **1 / 1** |
| Older `v1` | `v2` | 0 / 2 | **0 / 1** |
| Older `v1` | `v3` | 0 / 2 | **0 / 2** |
| Older `v1` | `V2` | 0 / 2 | **0 / 2** |
| Current `v2` | `v2` | 0 / 1 | **0 / 0** |
| Current `v2` | `v3` | 0 / 2 | **0 / 1** |
| Current `v2` | `V2` | 0 / 2 | **0 / 1** |

Every final case selected **one issue across all three findings**, and the last repeat skipped. Approval-reset counts equaled required update counts. A current/same-version case had **zero creates, updates, edits and resets**. Every final mocked write's title and payload source URL retained the finding's owner/repository and tag spelling; version suffixes were not lower-cased. This is fresh evidence of both duplicate repair and retention of genuine/case-distinct version updates, not a rerun of the builder's script or a claim of live GH behavior.

## 2. Fresh 39-path scanner/matrix/proof replay and 23 controls — PASS

Loaded the historical sensor directly from Git at `d694986b865e158e21c613683021a9b7822f945c` and the current sensor at final `5cbe`, each in its own in-memory module. Invoked only `SecretScanSensor._findings` on the **39 selected baseline/current Git blobs**; no fleet/canonical scan ran. The imported credential-pattern/redactor source was independently verified byte-equal to baseline.

For every row, independently asserted:

1. Baseline Git blob SHA-256 equals `originalSourceSha256`; final Git blob SHA-256 equals `reviewedSourceSha256`.
2. Baseline `(line, pattern, fingerprint)` multiplicities equal the original matrix findings.
3. Baseline and final **`(path, pattern, fingerprint)` MULTISETS** equal the original multiset, preserving repeated occurrences and mirror multiplicities.
4. Final exact finding dictionaries, including current lines, equal the corresponding machine-proof `currentFindings`; row counts, hashes, group and preservation flags agree.
5. All 39 final bound sources and the matrix equal source checkpoint `afe8644bd841473ef3ad5711bed5cc0cd1343667`.

| Group | Paths | Original / baseline / final occurrences |
|---|---:|---:|
| D1 | 16 | 30 / 30 / 30 |
| D2 | 14 | 24 / 24 / 24 |
| D3 | 9 | 17 / 17 / 17 |
| **Total** | **39** | **71 / 71 / 71** |

**Zero new selected matches; zero original matches lost.** Pattern totals remain **63 credential-assignment, 6 bearer-token, 2 JWT**. Compared the complete matrix JSON against accepted `8298c459a2fc2dd8a5e7d36e9e6e16a910454d6d`: replacing **only** `live.py.reviewedSourceSha256` makes the objects exactly equal, including top-level historical inventory references and every original ID/source/history/classification field.

Recomputed and asserted:

| Binding | SHA-256 |
|---|---|
| Current `scripts/upstream_watcher/live.py` | `ed81ff83b6ea246aada1dee23bbbdbe053f50f506b171c5c816b9e97174a8d12` |
| Current matrix | `ef616f78c39ea79eb12a499db7c2777cb1c3553efcc8c6b14229fc1c5381dda5` |
| Current machine proof | `a4344057e0cb98d4f1158c0bb56c06567021de6431ee5091a3820523b7653420` |

Proof scanner hash, matrix hash, source-checkpoint commit/tree and 39 row bindings all agree with actual Git bytes. Policy, redactor/pattern source and public scanner equal baseline and their recorded hashes. The proof's historical replay is unchanged; its new `priorStandaloneReplay` accurately wraps the accepted proof's source commit, matrix hash and 71-result count.

### Independently reconstructed controls

Constructed fresh deterministic values entirely in memory using SHAKE-256-derived character selections with an independent seed, appropriate family prefixes/lengths, and no actual credential input. No generated value was printed or saved. These were not the worker's generated bytes. Checked exact detector family, count, value-free finding JSON, finding-field shape and scrubbed raw-value absence.

| Cases | Paths | Baseline / final | Result |
|---|---|---:|---|
| AWS access-key ID, GitHub classic, GitHub fine-grained, Anthropic, OpenAI, Slack, private-key header, Google API key | Each in `src/control.py` and `tests/control.py` — **16 cases** | 1 / 1 each | PASS |
| Unrelated same-line `dummy`, `placeholder`, `not-real`, `canary` comments | `tests/control.py` — **4 cases** | 0 / 1 each | PASS |
| Unrelated neighboring value containing a marker | `tests/control.py` — **1 case** | 0 / 1 | PASS |
| Marker inside the matched specimen | `tests/control.py` | 0 / 0 | PASS |
| Same in-match specimen | `src/control.py` | 1 / 1 | PASS |

**23/23 passed**, independently matching all recorded proof outcomes. The retained in-match exemption is not a new whole-directory bypass or proof of arbitrary-token detection/nonissuance.

### Mirror/official-test carry-forward, actually byte-verified

Both complete tracked skill trees equal the independently audited `166e85514e3cd35d1c4e9cba506b1bb0560661f4` trees. Reconstructed the full supported path/content manifest from final Git blobs with the documented exclusions: **224 / 224**, zero missing/extra/changed supported files, digest **`8d2debc9dd3b57fb40822744e1bb5df95835dee3ce277c50805dadc25cb8b6dc`**.

Sensor, redactor, public scanner, authority policy, checker and operative compatibility/reconciliation/sensor-test files also equal that independent-audit checkpoint. Official five-test provenance/hash records and the 42-test count are unchanged from accepted `8298`. Thus the control audit's independently fetched official provenance and **42 passing adapted official tests** carry forward by actual source identity and verified report provenance; they were **not rerun or refetched here**. No new platform/browser certification is inferred.

## 3. Complete Git composition assertions — PASS

Read actual composition/proof claims, enumerated changed paths using `git diff --name-only`, and compared actual blobs, rather than trusting stated path counts.

- Feature merge **`e624328721f8e86bc54adf7d8c1cd080e341217d`** has exactly parents **`25de4ebd7e47d8cef95bcac354e6697123368542`** and **`dc5781a3199922d51ddabbbb0ab42f0fb2e39fbe`**.
- Baseline, founder input, cache fix, accepted standalone security, accepted root, feature merge and source checkpoint are all ancestors of final HEAD (seven explicit `git merge-base --is-ancestor` assertions).
- Baseline-to-standalone-security enumerates **28 paths**. **24 equal final byte-for-byte**. The exact four differences are `docs/agents/security/2283-dispositions.json`, `2283-scanner-proof.json`, `2283-reconciliation.md`, `2283-finish-proof.md`. Their changes are the authorized current matrix/proof/documentation bindings. The new `2283-founder-composition-proof.md` is additional, not miscounted among the 28. The two historical Markdown files only gain the inspected current-binding notices.
- Baseline-to-founder-input enumerates **25 paths**. **22 equal final byte-for-byte**. The only three differing founder paths are the cache source, its identity test, and `src/gaia_cli/steward/issuehygiene/reconcile.py`. The latter is exactly founder input **minus the single `from pathlib import Path` line**, with no other byte change.
- Accepted `.github/workflows/branch-scope.yml` and `tests/steward/test_landing.py` equal `dc5781` byte-for-byte. Accepted CI branch/fork scope behavior was not reconstructed or discarded.
- Cache commit `423..25de` changes exactly `issuer.py` and `test_identity_2283.py`. Merge-to-source-checkpoint changes exactly the matrix. The complete `423..final` changed-path set equals the asserted union of accepted security paths, these three founder exceptions, accepted workflow/landing tests, and the new composition document: **no unexpected path**.
- The **22 preserved founder paths** include the real founder-lock marker, decisions README and all four question decision records; workflow source; reconciliation CLI; watcher batch/finder/live/releaseidentity/watcher source; issue-hygiene executor/questions/sensor; workflow/founder-lock/count/pagination tests and the original watcher tests. This directly preserves the lock/hold/count surfaces supporting prior independent tests and saved-census evidence.
- **39/39** bound sources equal the source checkpoint; **38/39** equal accepted standalone security. The sole exception is the expected `live.py`, exactly equal to founder input `423`, with current hash above.
- Source-checkpoint tree: **`7706581a705c0f874e20fd4f317e4dfe41289190`**. Its final delta is exactly four proof/documentation paths: finish proof, new composition proof, reconciliation note, scanner proof. No source or matrix changes occur after it.

Executed:

```sh
git merge-tree --write-tree dc5781a3199922d51ddabbbb0ab42f0fb2e39fbe 5cbe7e80af20589da4c125289b263c70d869ea55
# exit 0; 0fb861268760517d6706a9b71b0d3b246a06c0d4

git diff --check d694986b865e158e21c613683021a9b7822f945c HEAD
# exit 0
```

The merge-tree result equals the actual final tree **`0fb861268760517d6706a9b71b0d3b246a06c0d4`**. No actual merge, commit, checkout change or ref write was performed.

## 4. Changed-live source semantic and caller gate — PASS

Read the actual `8298..final` live-source diff and the current producers/consumers, not merely the occurrence excerpt. AST comparisons additionally establish:

- `mentions_suite`, `canonical_umbrellas`, `suite_key`, `umbrella_suite` and `read_live` are unchanged from baseline apart from locations.
- Original finding **`39be36177943`**, ID `debt:credential_leak:scripts-upstream-watcher-live-py:2393fe51171e5834`, remains the same docstring occurrence: original **465**, current **511**, one occurrence.
- The only altered pre-existing `LiveGh` methods are `list_issues`, `_verified_open`, `_walk`, `_open_count`; `_open_totals` is the sole added method. All other method ASTs, including command execution and mutation methods, are unchanged.

`mentions_suite` (`live.py:510-512`) escapes the normalized suite key and applies whole-token lookarounds to a title. `canonical_umbrellas` (`:515-538`) uses it only when exact identity parsing fails. `batch.plan_suite` (`batch.py:619-646`) turns ambiguous titles into an inert `blocked-identity` plan, and `process_suite` (`:898-953`) does not write that plan. This is title-identity refusal, not credential parsing or authorization data.

The changed read path is operationally meaningful and was reviewed as such:

- `LiveGh.list_issues("open")` takes `_verified_open` before local label/since filtering. Ordinary acceptance requires equal metadata counts before/after a complete walk.
- On disagreement, `_open_totals` obtains **non-search** typed GraphQL issue/PR connection counts. Those counts bracket a second complete REST walk. Acceptance requires identical before/after typed totals, exact issue/PR counts in the confirmed rows, and identical **ordered issue numbers** across both walks. This is not a per-row body equality or transactional GitHub snapshot guarantee.
- `_walk` retains real census pagination/probe checks and rejects non-dict/missing, boolean, noninteger, nonpositive and duplicate issue identities. Unknown/malformed counts and incomplete walks fail closed after bounded source-defined retries; no offset tolerance or search absence shortcut was introduced.
- Query, owner and name are separate `gh api graphql -f` argv values through the unchanged runner, not shell interpolation or an embedded auth literal. Missing owner/name refuses; malformed/error/partial/noninteger/boolean/negative count responses refuse. The delta introduces no credential value, authentication-authority change, scanner exception or mutation permission.
- Fanout `_open_snapshot` (`issuer.py:365-384`) reads the verified open lists and complete closed-bootstrap history, translates list failures to `IdempotencyLookupError`, and is called before the first write (`:710`).
- Batch `read_live` (`live.py:457-481`) consumes the verified open list, removes PRs and combines required closed histories. `run_batch` (`batch.py:1027-1032`) returns unknown-evidence exit 3 on initial read failure; `process_suite` re-reads before a create/race re-plan. Source inspection confirms these interactions retain their fail-closed boundaries. This is not a claim that unrelated optional watcher operations cannot precede those reads.

### Additional fresh caller verification

Built an independent fake `gh` runner, not the repository/worker runner fixture. It served three synthetic REST rows (two issues, one PR), real include headers, empty terminal pagination probes and generated count responses. The actual final `listAll`/`LiveGh`/caller code ran, with subprocess and socket escapes forbidden. **22 fresh controls passed**:

- Stable metadata fast path; stale-metadata typed fallback; verified-list label filtering.
- Exact query/owner/name argv; fallback event order: metadata → REST walk/probe → typed count → REST walk/probe → typed count.
- Refusal of swapped issue/PR totals, changing totals, reordered identities, missing/error payloads, boolean/negative/float counts (eight invalid-evidence variants).
- Six malformed-identity variants: boolean, zero, string, missing, non-dict, duplicate.
- Actual fanout `_open_snapshot` label/history consumption and actual batch `read_live` PR removal.
- Invalid-count fanout invocation: zero mocked create/update/edit/reset calls; invalid-count batch invocation: exit **3**, `github-list` unknown evidence, zero issue creates/updates.
- Actual ambiguous-title `process_suite(..., apply=True)` remains `blocked-identity` with no runner calls; suffix-distinct title does not match the suite predicate.

This closes the new source/caller gate without claiming whole-file runtime credential security or live operational count correctness.

## Prior independent evidence combined, not relabeled as new runs

Terra independently ran the exact-final five-module focused command in `founder-composition-independent-review.md`: **169 passed**, covering strict generated zero-write behavior, mixed casing/case-sensitive suffixes/bootstrap/prefix boundaries/legacy headless recovery, conflicting distinct-skill refusal, marker + four decisions and holds, and count/pagination refusal. Its additional **119-test** run overlaps. Its checker, mirror check and **6 Node compatibility tests** also passed. These results are carried forward at the same exact SHA and clean source tree; none is falsely represented as a rerun here or summed as unique tests.

The independently authenticated inventory, all-39/all-71 semantic assessment, comment-only repair review, 23-control/upstream-provenance audit and standalone aggregate ACCEPT remain bounded inputs. Actual byte comparisons above preserve their operative sources, except the explicitly refreshed and newly reviewed `live.py`. Four underlying inventory/semantic/control/comment report SHA-256 values were independently checked against the accepted aggregate's digest table.

Inventory caveat is unchanged: the saved published comment authenticates the 39 ID/path mapping and reports canonical final debt digest `c7ea88b223ece4f10084dded2219ce03ba55d1c92b49d4cd7d4f9af1cdb3a222`; the separately supplied metadata snapshot digest is `5729f76d9bb265cf06541acaf797eea6c1c129b3c378da7138ba4ee5eda23972`. They are different snapshots; historical final debt bytes were not independently supplied/hashed. Checker success does not authenticate identity or scanner authority.

Prior independent saved **218-object** census replay preserved **218/218** original/snapshot objects and **67/67** GBrain child holds, #1833 technical-only B, #1835/#2002/#2126/#2127 held/none, A=0/B=5/C=0/none=213. It was not the later 221 census. This review carries that prior evidence with the actual preserved locks/questions/source comparisons and sole accepted unused-import deletion; it does **not** invent a new saved replay. The builder's final saved replay and 1427/292/123-test receipts remain builder evidence, not fresh independent runs.

Evidence snapshot SHA-256 identifiers:

| Report | SHA-256 |
|---|---|
| Historical Terra composition review | `176bab3bcf99a65e80f56b15dc14afc81d8bc4dd3fe8d70098f88443551c482d` |
| Prior strict founder/watcher review | `515f348274de35a05834752582d8d2128a7a092090046cea8a6194615debf2ae` |
| Accepted standalone security aggregate | `f75babdf5319272911b3c88ea9b8825169d13def73653b77c53195d9ec47394f` |
| Builder cache/composition proof (claims/reference only) | `0c723ffcba41b8413e7e71327502ba53da659fb64758ff8bdfc8657c22e962cc` |

Local probe-development errors were not concealed as successful checks: the first control/proof comparison assumed every control had a `path` field; the first fake runner mistakenly re-served page one to the terminal probe and was correctly refused as `unlinked-continuation`; a proof comparison initially assumed the older proof already had `priorStandaloneReplay`. Corrected only these in-memory fixture/schema assumptions and reran the affected checks successfully. None was a candidate defect or source edit.

## Operational exclusions remain binding

C1 registry metadata/provenance authority remains separate; C2 migration and C3 curation remain deferred. Historical #2278 external/runner/token cause is unproven. C4 compiled synchronization/compiler, threat engine, pause preservation, external credential state and future activation were not completed or approved. `writesEnabled=false` and open closure authority remain unchanged. Founder A retains the **8 MiB whole-settled-run** boundary; actual archive-data DoD remains **OPEN**, with no partial-archive or new wire authority.

No live ledger/origin/scan/run/record/migrate/rollback/lease, actual GH/network/credential probe, issuer contact, rotation, registry/trust/rank/evidence/intake mutation, compile, activation, configuration/package installation, push, actual merge, release or deployment occurred. No global nonissuance, complete runtime credential-security, historical external-cause, Node-18/Windows/full-browser or new combined Linux-platform certificate is claimed. Existing Linux receipts remain their original-checkpoint evidence. No current remote CI receipt was fetched or inferred; applicable CI, GitHub protection and explicit human main-merge gates remain in force.

**Final combined source gate: ACCEPT — `5cbe7e80af20589da4c125289b263c70d869ea55`, exact tree `0fb861268760517d6706a9b71b0d3b246a06c0d4`.** This completion does not overwrite the historical reports or authorize operating the system.
