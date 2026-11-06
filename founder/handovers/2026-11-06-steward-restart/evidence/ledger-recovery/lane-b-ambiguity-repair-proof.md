# Lane B #2283 — generic-text ambiguity repair

**Scoped ambiguity repair committed; 682 selected exact-SHA regressions passed. This is not independent acceptance or completion of the archival mission.**

## Candidate and preserved history

- Worktree: `$HOME/.gaia-worktrees/steward-memory-2283-unbounded`.
- Branch: `dev/steward-memory-complete-2283`.
- Preserved starting SHA: `9aa9db35f85da35636130eaf2cad6f4b0311b615`.
- Repair checkpoint: `259537410a03ad4ac8369655eb1759c9c677935d`.
- Fixture constructor correction: `081106e14d6e27449e3873ba4874e40acd17b9fa`.
- Preserved fixture-adaptation checkpoint: `922cf1c672bd158326f094094daf490bff0fcf80`.
- **Review candidate: `5432b273c1156b4e31b4170be398410d57897340`.** This retains/increases large fixture bytes while reducing incidental object cardinality; no production code or test safeguard changed.
- All four commits use the approved Marcus Rafael B. Tiongson <153011150+mbtiongson1@users.noreply.github.com> identity through Git `-c` flags. No amend/reset/stash/rebase, push or merge.
- Tracked status after committing: clean. `git diff --check 9aa9db35f85da35636130eaf2cad6f4b0311b615 HEAD`: exit 0.

Changed files (only the authorized lane scope):

1. `src/gaia_cli/steward/archive.py` — remove generic text grammar as a portability gate; fail closed on ambiguous values.
2. `tests/steward/test_archive.py` — actual canonical observation producer fixture instead of ambiguous legacy text padding.
3. `tests/steward/test_archive_phase_schema.py` — exact new counterexample, all generic-text slots, supported typed and original held uncertainty, preserved nesting/linear scanner regressions.
4. `tests/steward/test_archive_readers.py` — supported >2 MiB transfer/hydration/rollback, original large-shape holds, larger archive-only provenance, historical V2 uncertainty-reader coverage.
5. `tests/steward/test_archive_contracts.py` — supported search/view fixtures, original reason-bearing fixture held unchanged, exact CAS preservation, >2 MiB CAS ambiguity race.
6. `tests/steward/test_archive_safety.py` — legacy-byte-limit transfer fixture uses supported canonical numeric summaries.
7. `founder/steward/MEMORY.md` — conservative eligibility, producer justification and historical-read versus new-transfer limits.

No ledger, FullRunner, CLI implementation, wire format/version, policy, security sensor/mirror, other-worker file, root memory or founder root memory was changed.

## Exact independent counterexample: actual before and after

Unchanged phases:

```python
{"observe": {"payload": "proof"}, "retro": {"detail": "x" * 10000}}
```

Before editing implementation at the starting SHA, executed the new regression: **2 failed, 125 deselected in 18.66s**. Both absent-file and safe fixture-file cases failed because `phase_hold(phases)` returned `None`.

Also actually ran the old candidate end to end, using `TemporaryDirectory` and the existing disposable `hosts.__wrapped__` fixture, twice (without and with synthetic `one/proof` bytes):

```text
BEFORE exists: False hold: None eligible: ['run-a']
archived: ['run-a'] hot phases: {}
BEFORE exists: True hold: None eligible: ['run-a']
archived: ['run-a'] hot phases: {}
```

This was actual old-candidate behavior, not an extracted predicate calling the repaired schema. It does not claim the reference denotes a file in real data or that artifact bytes were bundled.

After repair, the exact-counterexample and original receipt/evidence tests passed: **3 passed, 124 deselected in 4.00s**. The new regression guards `builtins.open`/`Path.open` against opening the isolated artifact, prohibits any canonical CAS, checks no eligible/archived runs, identical shared ledger/version and remote refs, unchanged hot phases and cross-clone show, and checks the synthetic file remains byte-exact. These tests are also included in the final candidate regression command below.

An early checkpoint fixture mistake omitted FullRunConfig's required store argument: its immediate surgical run had three TypeErrors, not passes. The next preserved commit supplied an inert FileLedgerStore; no store method is used by the summary producer. No failure was hidden or history replaced.

## Why the gate is now semantic rather than filename-shaped

Inspected actual `FullRunner._observationSummary` (1447–1488), `_normNotEvaluated`, `_phaseReobserve` (2423–2490), `_phaseRetro` (2507–2570), reconcile producer, and `_observationOf`/`_view` consumers. Observation/retro reason slots copy sensor, optional-input, skipped-subject or exception strings; their producers do not establish a non-reference text contract.

- Legacy generic `observe.payload` / `retro.detail` are unsupported and held for every value.
- Generic coverage reasons, notEvaluated reasons, partial reasons, retro sensor reasons, reobserve notes, integration-head reasons and class-B reasons are held even when empty, null or spelled `proof`. Empty collections may remain supported, but no original nonempty collection is emptied by migration code.
- The only supported prose literal is the **existing exact** no-mutation `reobserve.reused` producer constant. Its test verifies the constant exists in `_phaseReobserve.__code__.co_consts`, accepts only that literal and refuses additions/other arbitrary values. No tagged format was invented.
- Typed sensor/routine/debt/receipt IDs remain references in their declared semantic roles, not claims of artifact bytes or universal filename absence. Numeric counts, enums and booleans retain their existing schema.
- Complete-tree unknown-field/type/reference refusal and current-work/CAS checks remain. Unknown/partial/not-evaluated original data is never rewritten into healthy or omitted to become eligible.
- `phaseText` is retained solely as the bounded lexical diagnostic with the unchanged 3,145,728-character actual-operation-count, late path/dot, repeated-dot and 4,681 short Unicode/dot/slash semantic cases. **It grants no eligibility.** Passing its grammar cannot establish file absence.

## Supported large producer and retained regressions

`observation_phases(16000, identityParts=12)` constructs real `Observation`, `Receipt` and `ScanResult` objects and calls the existing `FullRunner._observationSummary` method. Each synthetic source is a namespaced sensor identity, 253 characters long, within the existing unrestricted nonempty Observation.source and ASCII archive-ID contracts. The method emits `observationsBySensor` numeric drift/healthy counts plus its canonical typed receipt/debt/coverage summaries. It does not copy subject data, prose or external artifact references. These are semantic sensor IDs supplied as Observation.source, not strings reclassified as IDs to rescue a legacy payload. This is a deliberately large supported-producer scale fixture, not a statement about the production fleet or eligibility.

Measured directly from the candidate using real serialization:

- 16,000-sensor **packed phase payload: 4,480,309 bytes** (>2 MiB).
- Serialized otherwise-empty ledger containing that complete run: **5,009,488 bytes**; actual disposable seeded Git source: **5,011,269 bytes**, below the unchanged 8 MiB bound. The durable and provenance tests independently assert actual seeded source bytes are at least 4,381,488 and below 8 MiB. The packed-payload lower assertion is at least 2,400,309 bytes, preserving the preceding larger-than-2-MiB fixture's byte floor rather than shrinking it.
- No smaller segment bound, new format, truncation, test skip or timing deadline was introduced. The ordinary supported fixture is also physically large rather than replacing removed text with a no-saving tiny record.

The large durable regression retains full original run equality, exact original snapshot bytes, cross-clone hydration/load/view/resume, positive net saving and forward rollback retaining intervening pending operations/work and index history. The equal-bytes/different-source-commit archive-only fresh-fetch test now also uses this large producer output. A new large CAS test introduces `payload="proof"` from a second clone before CAS: retry must hold the newest run, preserve all hot phase bytes and protected work/leases/lane, and add no canonical archive event.

Original >2 MiB text payloads remain >2 MiB in explicit held regressions, both `observe.payload` and `retro.detail`; no shrinking/silent dropping makes them eligible. Original reason-bearing canonical fixtures likewise remain intact and hot. The ordinary-reader missing-object regression additionally constructs an explicitly labelled **historical permissive V2 archive** under an exact-fixture-only legacy predicate override, then restores the real gate and checks exact uncertainty/read/replay/missing-object behavior. That is backward-reader testing, not valid-new-transfer or artifact-portability evidence.

## Verification

All pytest invocations use:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q -p no:cacheprovider ...
```

An intermediate fixture-adaptation run (not the final committed test image) completed **307 passed in 294.61s** across phase-schema/readers/safety/contracts. It overlaps the final selection and is not added to its count.

The first committed 922cf1c67 full selection **did not complete**: the repository's existing per-test timeout terminated the large roundtrip while deep-copying its 60,000-entry map. Exit 1; no completed passing-suite claim or count. Its log is retained as `lane-b-ambiguity-regressions-922cf1c67.log`. The repair does not disable/raise that safeguard, delete operations, or shrink byte coverage: it uses 16,000 existing-contract namespaced identities, yielding MORE bytes and fewer incidental nested objects. All original hydration/view/resume/snapshot/rollback/history operations remain in the large test.

After that adaptation, the complete large roundtrip passed **1 passed in 39.31s**; large archive-only distinct-commit provenance and large CAS ambiguity retry passed **2 passed in 26.15s**. These surgical runs overlap the final selection and are not added to it.

**At exact candidate `5432b273c1156b4e31b4170be398410d57897340`: 682 passed in 1192.39s (0:19:52), exit 0**, for the complete selection:

```text
tests/steward/test_archive.py
tests/steward/test_archive_cli.py
tests/steward/test_archive_contracts.py
tests/steward/test_archive_phase_schema.py
tests/steward/test_archive_readers.py
tests/steward/test_archive_safety.py
tests/steward/test_ledger.py
tests/steward/test_fullrun.py
tests/steward/test_cli.py
tests/steward/test_cli_contract.py
tests/steward/test_fullrun_cli.py
tests/steward/test_fullrun_scenarios.py
tests/steward/test_coverage_regressions.py
tests/steward/test_report_inputs.py
```

Log: `$HOME/gaia-skill-tree/.gaia/steward/campaigns/2026-11-05/ledger-recovery/lane-b-ambiguity-regressions-5432b273c.log`; adjacent `.exit` records **0**. No new task/suite deadline or skip was set; repository test safeguards remain unchanged. These are 682 distinct selected tests, not the entire Steward suite. After completion, HEAD remained the exact candidate, tracked status was clean, and the baseline-to-candidate diff-check again passed.

## Actual-data ineligibility and authority boundary

Independently reevaluated only the local immutable cached object `6cb42c90bbc40ce000e67fcbfac895eda2c5af63:ledger.json` with the candidate's unchanged pure `eligible` entrypoint: generation **392**, **1,204,756 bytes**, SHA-256 `cecda4873e5cd1bb90712a376f39940aecbd62b4f86fc313dc13abb233cb6838`, **0/14 eligible terminal runs**. This is **not a fresh origin measurement**. No store/load/migrate/scan/run/record/rollback/lease operation targeted a real ledger.

Nothing here settles pending work, interprets a terminal label as settlement, authorizes partial archival/schema extension, externalizes pending/Class C references, or bundles proof files. The unit remains whole settled terminal phases; generic-text refusal is more conservative, not an authority expansion. All actions/outcomes/steps, leases, desks/decisions, receipts/proof records, work/history and replay/dedup references retain the existing hot-preservation rules.

Parent still owns publication, fresh independent exact-SHA review, full Steward/integration gates, any fresh canonical observation and separately authorized live operations. The full Steward pass and CI at 9aa9 reported in the assignment do not accept this new SHA. The finer-grained founder decision remains unselected. There has been no production migration, live fresh-host retrieval or live forward rollback, and no no-op/8 MiB fallback is called mission completion.

Runtime observed: `PI_PROVIDER=openai-codex`, `PI_MODEL=gpt-6.1-sol`, `PI_REASONING_LEVEL=high`; no fallback or nested agents. Read required graft/root/founder instructions and assignment sources. Used existing graft without installing packages or changing global configuration. The in-house plugin/Skills API is unavailable in this harness; this is not plugin validation. No forge writes, live/origin operations, trust/rank/registry/evidence/intake/activation/release/deployment or other-worker edits occurred. Disposable local test remotes alone received test writes.
