# #2283 — actual-data archival action plan and authority decision brief

**Advisory plan only. Archival mission NOT complete; no implementation or live-operation authorization is created here.**

## 1. Recommendation / next safe action

1. Preserve checkpoint **`9aa9db35f85da35636130eaf2cad6f4b0311b615`**, its predecessors, draft/rejection history and Lane A acceptance. Do not reset, rebase, silently replace history, or merge based on this plan.
2. Parent should confirm the cached-generation evidence below against its next authorized read-only snapshot. This planner did not contact origin. If origin has advanced, supply exact `ledger.json` bytes, commit/ancestry and checksum for offline re-evaluation; do not assume either continued zero eligibility or newly settled work.
3. **Do not run a production migration on the evidence presently available.** Unchanged whole-run eligibility selects nothing, including the newly completed canonical run. Bundling artifacts, relaxing historical sensor predicates, or recognizing the unused-import resolution cannot remove its other blockers.
4. Put the precise unit-of-archival/schema question in §5 before the founder, within this sprint/#2283. **Recommended default: retain the existing whole-settled-run boundary and report the accepted 8 MiB fallback honestly while the archival requirement remains open.** The small reference-free metric opportunity does not justify pretending the pending-data problem is solved. If the founder nevertheless wants that narrow real-data archival slice, §6 is the bounded implementation plan, conditional on explicit approval and independent review.

This is not a request to adjudicate Class C so that an archive can pass. No new tracker, broad identity migration, GBrain work, trust settlement, retention expiry or unilateral permission expansion is proposed.

## 2. Identity, sources and evidence limits

- Actual session environment: **`PI_PROVIDER=openai-codex`, `PI_MODEL=gpt-6.1-sol`, `PI_REASONING_LEVEL=xhigh`**; session `01a1a912-c5ab-7578-b235-096751512fe5`. No fallback/provider/model substitution or nested agents. These are runtime environment observations, not an independent backend attestation of effort implementation; no unsupported-effort error was observed.
- Dedicated checkout HEAD is exactly **`9aa9db35f85da35636130eaf2cad6f4b0311b615`**. Initial and pre-report tracked status were clean; diff-check passed. Source, policy, configuration and live metadata were not edited. The assigned report is the only file written by this planner.
- Read root/founder `CLAUDE.md`; repository-required graft skill and existing graft index/cards first. The local checkout has no graph, and the adjacent existing graph lacks archive/ledger/fullrun coverage and has an older CLI card. No graph rebuild/refresh or telemetry mutation was performed. Missing graph coverage required exact-checkout source/AST inspection; no claimed graft token saving.
- Read all of `unbounded-b-worker.md`, `lane-b-independent-final-review.md`, `lane-b-shared-complete-proof.md`, and the related recovery assignments. Read the recorded founder authorization and complete founder-reconciliation issue capture, including the 8 MiB/non-destructive scope and C1–C4/D1–D3 locks. Also inspected `FOUNDER_LOCK_2283.md` from local commit `42322964ae5899712df5b492e98f37600e04bd89`; that other lane is context, not this checkout's acceptance.
- Parsed the complete `cycle-02-resumed.json`, `cycle-02-status-after.json`, merge and resolution receipts. The canonical run is `run-20261104T191141Z-c3a4df1e`; PR #2289 merged at **`cc2522c293d15d9e01606dcee741f5e9b04136d9`**. The resumed receipt reports completed/done. Status reports no active runs/holder and work counts blocked=1, escalated=4, no_change=1, resolved=1.
- Read-only local Git-object inspection found **`refs/steward/remote-ledger-5e28c1b0a09e` → `6cb42c90bbc40ce000e67fcbfac895eda2c5af63`**, newer than both previously reviewed snapshots. It agrees with the resumed/status receipts: generation 392, updated `2026-11-04T23:55:22.653027Z`, eight completed/six abandoned runs, no leases, unused-import work resolved. Both old snapshots are ancestors (local `merge-base --is-ancestor`, exit 0); all 13 baseline run objects are still exactly equal.
- This cache is **not a fresh origin observation**. No real-origin fetch, archive/show/history/status command, scan, run, record, lease, migration or rollback was executed. No external proof files, flagged credential lines or credential values were inspected. No forge/config/package/activation/release/deployment operations occurred.

Receipt SHA-256 anchors:

- `cycle-02-resumed.json`: `60bae7859badc84809b1077d0d7367d3853cfa362f37e275134655f45e4fd9b7`.
- `cycle-02-status-after.json`: `2e40975aec1524770ecbf9d1be24be40ff9eadf6b9446d76c382ecabb1b93851`.
- Cached generation-392 raw ledger: **`cecda4873e5cd1bb90712a376f39940aecbd62b4f86fc313dc13abb233cb6838`**; Git blob `d05bb090d52d1d577e297df08b51bb843fccd627`.

## 3. Can anything qualify under the current rules, unchanged?

**No whole-run transfer qualifies in the newest available local bytes. There is no current subdetail migration API.** This conclusion is newly measured, not extrapolated from the old zero-eligibility reports.

Offline procedure: `git show <immutable-commit>:ledger.json`, JSON validation, then direct calls to the checkout's pure `archive.eligible(document, run)` and `phase_hold`; no store/load/transport methods and no predicate monkeypatching.

| Immutable ledger commit | Exact bytes | Terminal / total runs | Eligible terminal | 8 MiB headroom |
|---|---:|---:|---:|---:|
| `9b3e58abd5117cd7b8c607859ac8cb68525ba999` | 1,005,272 | 13 / 13 | 0 | 7,383,336 |
| `74d338e498afcc547a089b3379e1398a7ad78085` | 1,124,502 | 13 / 14 | 0 | 7,264,106 |
| **`6cb42c90bbc40ce000e67fcbfac895eda2c5af63`** | **1,204,756** | **14 / 14** | **0** | **7,183,852** |

Load-bearing source at checkpoint 9aa9:

- `src/gaia_cli/steward/archive.py:306–389`: complete-tree typed phase schemas; unknown/reference-bearing/nonportable fields remain hot. Historical uncertainty is not a work verdict.
- `archive.py:392–429`: `eligible` requires completed/abandoned/failed, phases and finish time; no current lease reference; recognized settled action/step/decision statuses; no unresolved/deferred run work; authoritative settlement of historical open debt snapshots and every matching current work reference; valid times.
- `archive.py:509–529`: `projected` removes **all** phases, and `hydrate` verifies that exact whole-run projection. It cannot selectively externalize a sensor collection.
- `fullrun.py:2574–2619`: completed means the runner has no further pending/deferred execution or coverage block at report time. It does **not** mean every observed debt, founder question or associated work is settled.

For the newly completed canonical run specifically:

- All three actions and all 13 steps are done; top-level unresolvedWork/deferred are empty; there is no current lease. Those facts are useful but insufficient.
- Its reference set still intersects **all six** non-resolved work records. Observe and reobserve each contain five historical open debt-status entries whose current work is not resolved. The newly resolved unused-import record does not settle these other records.
- Its one decision is a canonical historical `type: integrate` event **without a `status` field**. The unchanged eligibility predicate refuses that unknown settlement status. Do not rewrite it to `closed`, infer a founder ruling, or manufacture work-history changes.
- Complete phase validation also holds it. Among observed producer/schema mismatches: `class_a.issueClosures` is undeclared; configured `reconcile.integrationBranch` is non-null; optional-input reason text contains filenames rejected by `phaseText`. These may be conservative historical-schema holds, but correcting them alone would not settle the other references/decision guard.

Proof needed before an unchanged-rule transfer: pin a new canonical generation; validate the entire selected run; establish explicit authoritative resolution for every required hot work reference, recognized decision/action/step statuses and absence of leases/deferred/unresolved work; validate portable phases; calculate positive **net** serialized saving; then recompute all eligibility on every CAS retry. Missing work, an expired-but-present lease, verified/landed/no_change work, old observations or a terminal label are not settlement.

## 4. Where real bytes are, and the narrow detail-only opportunity

Generation 392 occupies **14.36%** of 8 MiB. Compact runs contribute 926,409 bytes; compact phase JSON totals 683,476 bytes. Contributor encodings are not additive physical file accounting.

**The dominant phase bytes are protected references:** the present observe/reobserve `freshOpenDebt` + `openDebtIds`, plus triage `reportOnly`/`classB`/`classC`, total **620,663 compact bytes**—about 91% of compact phase bytes. They include pending and Class C references. Do not externalize/deduplicate these lists or replace their original objects with identifier summaries to obtain savings.

Only three runs have modern retro sensor/routine arrays (Nov 1, Nov 2 and the new canonical run). Removing *all* those collections in memory would save **46,444 physical serialized bytes gross**, before pointers/index/schema overhead. That is an **inadmissible upper bound**, not a safe migration: the arrays contain sensor/routine references, Class C-related entries and uncertainty detail that must stay hot. Older runs also have scalar/count retro shapes, which cannot be expanded into invented observations.

The producer is `fullrun.py:2507–2570` (`_phaseRetro`), which copies numeric per-sensor counts into immutable retro summaries alongside identity/coverage data. A genuinely narrower possible profile is historical **numeric metric leaves**, not whole sensor or source phases:

| May move only after explicit §5 approval and source/dependency review | Must stay hot verbatim |
|---|---|
| Enumerated `phases.retro.sensors[i].observations` objects containing exactly nonnegative integer `drift`/`healthy`, for specifically reviewed non-C, non-pending-related producers in a terminal immutable run. No free-form paths or user-selected JSON pointers. | Every original sensor ID, routine ID list, detector/reference object, array order, state/registered/executed/unknown/notEvaluated flags, reason, partial/coverage summary; entire C-related or pending-related sensor entries. |
| A future separately reviewed reference-free historical leaf profile, only if its producer/consumer contract and actual dependency independence are demonstrated. | All observe/reobserve debt maps/lists, scan-receipt references, resolution/notes objects, triage, reconcile, verify/results, class-A/B outcomes, unknown shapes and all other phase data by default. |
| Copies of exact original ledger/run bytes in immutable archives for provenance. Copying does not remove hot authority. | Entire `work` and history, lane/dedup/tombstones, current and recorded leases, decisions/desks, actions/outcomes/steps/idempotency, receipts/proofArtifacts/CI/branches/PR references, run lifecycle/options/source references, replay data and pending summaries. No representation weakening of these objects. |

Keep even empty/false/unknown protected fields unchanged. A zero-drift metric alone is not proof that a producer has no pending dependency; the candidate list needs affirmative source/authority review. Sensor identity is not evidence bytes. If a sensor entry itself is a protected reference object or has a live reconciliation dependency, retain the **entire entry**, not just its identity fields.

**Headroom reality:** deleting all 96 modern sensor `observations` leaves, even including protected sources, yields only **7,319 gross bytes** before overhead. A deliberately optimistic in-memory sizing profile selected 13 zero-drift producer IDs per modern run (39 leaves), kept all other values and references, and used one illustrative bounded segment/profile/index-list manifest per run plus an index head. Gross omission was 988 bytes/run; illustrative net total was **1,469 bytes**. This was serialization arithmetic with placeholder hashes—not a validated new format, safety acceptance, implementation, fixture migration or production transfer. The sizing-only IDs were bundled-schema-mirror, agent-skill-mirror, registry-integrity, cli-contract, taxonomy-script-drift, knowledge-contradiction, generated-projections, repository-hygiene, test-portfolio, test-isolation, supply-chain, schema-validity and timeline-causality. This list is not a ratified allowlist. Narrower reviewed selection may save less or nothing.

Thus there is a potential **small** reference-free historical-detail mechanism, but no demonstrated meaningful capacity relief at the current protected boundary. Most real headroom would require moving protected reference-bearing objects, which this assignment forbids. Safe artifact bundling does not alter that arithmetic or settle work. Do not widen the mask just to produce a larger migration receipt.

## 5. True authority boundary and exact founder question

Existing recorded authorization covers an initial bounded 8 MiB hot ledger, non-destructive indefinitely retained archival of settled terminal detail/fully settled history, shared portability, migration verification and rollback. It explicitly excludes active/decision-pending archival, history deletion and authority elevation. The independent review and repaired checkpoint expressly reserve finer-grained eligibility for separate authorization/review.

**Distinction:** designing immutable detail storage is already aligned with the authorized architecture. But changing the eligibility unit from a fully settled terminal run to selected leaves of a run linked to pending work, and introducing a partial-phase wire schema, are not permissions supplied by this plan or by green tests. No Class C adjudication is necessary to *design* that split; neither is it authorized to implement/apply the expanded split merely by calling pending detail historical.

Parent should present this one unselected decision, using the repository-required founder review surface; this report is not that approval record:

> **Do you ratify a narrow extension allowing explicitly reviewed, reference-free immutable numeric retro metric leaves of terminal runs to be archived while their parent run remains linked to unresolved work/decisions, with every protected object/reference and coverage state remaining hot unchanged?** It requires a new fail-closed ledger compatibility version, exact hydration and portable source-byte proof. The current cache offers at most 7,319 gross metric bytes, and an illustrative narrower profile saves only 1,469 net bytes. Approval would cover the bounded engineering/review scope only, not live migration, Class C action, broader reference archival or mission acceptance.
>
> **A — Retain current boundary (recommended default):** preserve 8 MiB fallback and all hot data; keep actual archival completion explicitly open in this sprint. Re-evaluate only genuine future settlement/new snapshots, without manufacturing history.
>
> **B — Approve the narrow detail-only design/test scope:** ratify the exact protected-field mask, reviewed producer/path profile and new compatibility boundary first; then execute §6 and the independent/live gates. Accept the small gain honestly, not as broad archival completion.
>
> **C — Require a different archival benefit/target before engineering:** specify the desired bounded byte target and review a concrete alternative mask. No implicit permission to move pending/reference data; if that would be necessary, return to the founder with exact affected objects rather than implement it.

No option is selected by this document. C1–C4/D1–D3 rulings are not generic memory or settlement permission. If A is chosen, this sprint has an accepted capacity fallback and an explicitly held archival requirement—not a completed archival mission or a vague follow-up issue.

## 6. Minimal file-aware implementation plan — ONLY if B is approved

### Format, provenance, projection and readers

1. **`src/gaia_cli/steward/archive.py`**: retain current `eligible`/whole-run projection. Add a separate reviewed detail-profile selector and paired projection/hydration; never bypass `phase_hold` or reuse `projected` to clear a pending run's phases. Selection must bind exact run ID, original sensor position **and identity**, source generation, profile version and retained hot spine. Reject unknown producer fields, duplicate/overlapping selections, array reordering, wrong scalar types, unexplained dependencies and nonpositive net savings. Unknown lifecycle/coverage stays unknown; it is not evaluated as healthy.
2. Reuse the exact-source snapshot and **commit-specific provenance anchor** protocol (`archive.py:498–558, 661–740`) and complete original-run envelope where suitable. Partial hydration restores only approved omissions and compares every retained value against the archived source; it cannot replace a changed protected spine. Source snapshot bytes/hash and source commit ancestry must be independently retrievable through archive refs, including equal bytes from different source commits. Do not reconstruct material pruned before this feature.
3. **`ledger.py:194–276, 593–623`**: introduce a distinct ratified ledger schema for partial projections. Current V2 requires phases `{}` for `_stewardArchive`; merely adding another optional pointer to V1/V2 is unsafe. Old V1 **and current V2** clients must reject the new schema even below 1 MiB. New code reads V1/V2/new version; rollback never downgrades it. Define explicit omission/profile metadata in the new wire schema—no unexplained missing fields, `{}` placeholders masquerading as normal summaries, or scalar coercions. Add transition validation for appended history, exact restoration and protected-state equality. Unchanged pointers/hot-only writes should not require archive transport availability.
4. Use versioned partial-archive/rollback index events; preserve the existing index chain and its bounded run/debt/routine/time search. Bind selected paths/profile to each event and source envelope. Do not describe a sensor metric or search hit as proof that a debt is resolved. Keep bounded pages/cursors (current 32 events, 256 KiB, at most ten pages/read); no unbounded index walk or per-leaf hot index explosion.
5. **`fullrun.py`**: audit `_verifiedRun/_loadRun` (508–518), terminal resume (620–655), record/replay (966–1022), `_view/_observationOf` (1343–1360, 889–898) and every direct phase consumer. Ordinary summary reads must hydrate exactly or refuse before output/CAS; no empty/healthy fallback. Status can remain hot-only where it reads no removed detail; decisions/desks remain exact. A partially archived terminal run is immutable until verified detail rollback; unrelated work can continue under unchanged CAS/lease rules. No decision settling or action re-execution.
6. **`commands/steward.py:574–608`**: smallest explicitly selected preview/apply/retrieve/rollback extension, shared Git only. No auto/local fallback, campaign execution or silent background migration. New visible CLI output requires its existing founder gate. **`founder/steward/MEMORY.md`** documents the approved profile, new-reader requirement, guarantee limits and repair procedure; policy/decision records are not edited as an engineering shortcut.

### Transfer, artifact and recovery contract

- Retain source hot bytes → publish immutable snapshot/commit anchor/run detail → fetch/read back and verify size, hash, schema, run/profile/identity, ancestry and exact hydration → publish/verify index → **forward hot CAS last**. On conflict reload and reselect from the newest authoritative document, including new leases/work/dependencies; never reuse a stale projection. No saving means no hot write.
- Numeric-leaf scope opens **no artifact files**. Original proof/receipt/path/reference objects remain hot, and exact JSON strings/hashes are not portable evidence-file bytes. Any later artifact-bearing profile requires separately approved explicit rooted manifests, bounded file/count/total sizes, traversal/symlink/race refusal, source/receipt identity binding, exact-byte hashes and independent fresh-clone blob retrieval. Missing or unsafe bytes hold the record; never collect arbitrary `.gaia` trees or secrets, rewrite evidence, or publish unreviewed private files. Bundling alone still cannot satisfy work settlement.
- Before CAS, interruption leaves hot source untouched and at most durable orphan archives. After ambiguous publication/CAS success, re-read canonical state and verify exact existing pointers/events before retry; no duplicate history or actions. Identical concurrent publication is accepted only after readback; a corrupt/colliding existing ref refuses without overwrite, deletion or force.
- Detail rollback fetches/verifies the original and appends an event, restores only the selected leaves into the **latest** unchanged run spine, and forward-CASes without overwriting intervening work, leases, actions or other runs. Keep new schema/index/archives indefinitely. Refuse if restoration exceeds the configured byte limit or the spine changed; never reset the whole ledger.
- Missing/corrupt segment/snapshot/anchor refuses hydration/rollback; bad index refuses history extension. Recover only exact independently verified bytes from surviving backups, preserving provenance parents. A colliding/corrupt extant ref requires separately authorized repair engineering, never automatic replacement. Original source/history remains preserved.

### Tests and acceptance sequence

- Extend `tests/steward/test_archive_phase_schema.py`, `test_archive_contracts.py`, `test_archive_readers.py`, `test_archive_safety.py`, `test_archive.py`, `test_archive_cli.py`, and `test_ledger.py`; add partial-profile fixtures without weakening old counterexamples. Test protected canonical-subtree byte equality, complete hydrated phase/run equality, uncertainty/notEvaluated/partial preservation, legacy scalar retro refusal, array identity/order, false/null/unknown fields, missing objects, wrong hashes/source commits/profile paths and index cursors.
- Disposable Git remotes only for engineering: cross-clone retrieval, >2 MiB supported payload regression, equal ledger bytes/different source commits with archive-only fresh fetch, old V1/V2 refusal below 1 MiB, load/write limits, forward rollback retaining newer work, lease/work-settlement races, duplicate publication, CAS timeout ambiguity, crash stages before/after every publication and CAS, no-op/no-saving behavior, and bounded parser/index work. Do not pad or settle production data to create a test candidate.
- After surgical regressions, run the **full Steward suite**, without new exclusions or suite deadline: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q -p no:cacheprovider tests/steward`. Preserve repository test safeguards. Reconcile other lanes by non-destructive reviewed integration and rerun affected/full tests on the resulting exact candidate SHA.
- Obtain **fresh independent exact-SHA Terra assurance** of implementation, authority mask and actual-data projection. The old 429-test rejected review and the worker-reported 554 selected passes at 9aa9 are useful history, not new acceptance; no pytest suite was executed by this planner.
- Only after engineering/authority gates may the separately authorized parent take a fresh canonical snapshot/preview, select a genuine positively saving unit, publish/verify/CAS it, and retain before/after receipts. An independent fresh clone with no inherited cache must retrieve exact original source/run/selected bytes and search by actual run/debt/routine/time, preserving every protected hot object. Perform verified forward rollback with intervening legitimate work retained, then the authorized true shared-ledger re-observation. Record exact SHAs/hashes/bytes and distinguish migration, rollback, retrieval and campaign outcome.
- **Closure requires all of those actual proofs**, plus honest scope acceptance if the approved slice is only numeric detail. A synthetic roundtrip, a zero-candidate preview, the 8 MiB cap, or this plan cannot close the archival mission. Keep all remaining gates here in the sprint; no follow-up issue substitutes for them.

## 7. Finite growth and stop controls

Preserve `ledger.py`'s uniformly enforced 8 MiB initial bound/configuration validation, and `fullrun.py:524–603` new-run controls. At the cached size, thresholds are **5,872,026 bytes (70%)** and **7,549,748 (90%)**. Retain explicit stop-new-runs/minimum-headroom controls, rechecked before adoption/lease mutation and on CAS retry. Existing reads/resume/record/rollback remain available subject to their actual hard bounds; reserve estimates cannot guarantee another existing run or rollback fits.

The latest immediate-parent sample is **−1,019 bytes / one generation** (parent `cfc96e862b1d5b70a707ef5b86016f6f12cf92ba`), not a negative-growth forecast. Earlier +79,056 bytes/30 generations and burst statistics are historical context only. Actions, reference lists, work history, replay metadata and per-run pointers still grow; no finite phase/detail scheme provides infinite hot capacity. Stop new growth when protected data/reserve approaches the bound, rather than prune or widen eligibility.

**Verification honesty:** all new results above are offline validation/measurement of local immutable objects and in-memory serialization. One exploratory sizing traversal initially encountered a legacy scalar `retro.sensors` and raised `TypeError`; the corrected traversal explicitly handles list shapes. It was not a migration/test pass and changed no data. No current-origin freshness, full-suite result, external-artifact portability, new patch acceptance, live archival transfer or overall mission completion is claimed.
