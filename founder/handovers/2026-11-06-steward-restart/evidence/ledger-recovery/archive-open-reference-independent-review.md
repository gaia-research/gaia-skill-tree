# Independent focused parked archive guard review

## Findings first — REJECT bounded source guard at ceb385820

**High — contradictory or malformed current work history is accepted as settlement.** `src/gaia_cli/steward/archive.py:485-489` checks only that `history` is a list, defaulting a missing history to `[]`; it does not validate its entries or reconcile its latest transition with `state`. `src/gaia_cli/steward/ledger.py:257-258` also checks only the container type. Consequently a ledger-valid hot work item claiming `state: resolved` whose latest history transition says `resolved -> escalated` authorizes archiving a run with that debt in its open C references. This violates the assigned boundary that missing/mismatched authority/history and nonresolved work cannot settle known open references. Repair by defining and checking sufficient current settlement/history consistency at this guard, fail closed on malformed or contradictory history, and add validator-preserving regression cases through the real authoritative transition. Handle genuinely absent legacy history conservatively under the same specified boundary; do not manufacture settlement.

**Fresh real-transition reproduction:** in a temporary bare local Git remote and one disposable clone, used `open_summary()` with 400 synthetic observations (the real `_observationSummary` producer), a ledger-valid terminal historical-shaped run, and matching C work whose current state was `resolved` but whose sole history entry ended in `escalated`. No validator or predicate was bypassed. `validate_ledger` returned true, `eligible` returned true, `plan` selected `run-a`, and `migrate` actually transferred `run-a`; hot `phases` became `{}` while the contradictory work remained unchanged. This is a contract-level synthetic historical counterexample, not a demonstration of live records or of today's complete observe producer being eligible. A smaller independent in-memory probe also found that `history=['junk']` and omitted history each pass validation and `eligible`; the actual transfer repro uses the stronger contradictory transition. Original missing-work counterexample is fixed, but this is a distinct remaining authority/history gap in the same guard.

**Verdict: REJECT** the bounded changed guard/source at exact `ceb38582008a07002239ec65aa77aa22725e80ab`. This is not an unpark, merge, whole-feature or mission verdict. Founder has parked the archive draft and prioritized routines. Founder A's 8 MiB whole fully settled-run boundary remains unchanged; actual archival DoD remains **OPEN**.

## Exact scope, composition and runtime

HEAD `ceb38582008a07002239ec65aa77aa22725e80ab`, tree `1562bbec86d3acad5987587ade118fa2fbc04385`; parent `8dbfcf16d925ad4db4c8a320943713532f381f62`, then feature-only merge `8268c2c7895b871510bc336d00e4c840ff8729c3`, whose parents are `5432b273c1156b4e31b4170be398410d57897340` and accepted root `c67d90950b0aa37491f5061e76f6cda3319da568`. The supplied previous independent review identifies merge tree `8833341ab9cf599d1d6c7cd1bcb0ffd4638f0278` as rejected. Fresh `git diff --stat 8268c2c HEAD` shows exactly six files: `src/gaia_cli/steward/archive.py`, `tests/steward/test_archive.py`, `tests/steward/test_archive_contracts.py`, `tests/steward/test_archive_phase_schema.py`, `tests/steward/test_archive_open_references.py`, and `founder/steward/MEMORY.md`. No schema, policy, producer or source metadata file is in this repair delta. `git diff --check 8268c2c HEAD` passed; tracked status was clean.

Fresh root preservation: enumerated `git diff --name-only 6bc3688705c14b10f7ded3e6caeb721dd278c3bd c67d90950b0aa37491f5061e76f6cda3319da568` (59 paths), compared each root path's `git rev-parse c67d...:<path>` against `HEAD:<path>`, including absent-path handling; zero differences. This is a source blob preservation check, not a replay of the founder/security scanner.

Runtime: `PI_PROVIDER=openai-codex`, `PI_MODEL=gpt-6.1-terra`, `PI_REASONING_LEVEL=high`, Python 3.14.6, Git 2.56.0. No fallback or nested agent. Read root and founder CLAUDE, graft skill, lead repair proof and integrated independent review. Graft refreshed its ignored retrieval cache; no tracked source/config was edited.

## Guard, test results and before/after qualification

The old whole-source disposable migration reported in the integrated review and repair proof selected and transferred the valid historical-shaped C=1/openDebt=1, `openDebtIds`+`freshOpenDebt`, empty `debtStatus` record without C work. The current fresh selected test `test_missing_c_reference_actual_migration_keeps_document_and_version` confirms no CAS, no transfer, exact cross-clone document/version and refs preservation; `test_real_producer_missing_c_work_is_not_settlement` confirms the real producer-shaped summary is held. The complete current observe producer is independently held by its reconcile phase (`integrationBranch`); neither the old exploit nor the new history counterexample demonstrates present real-record reachability. No live data was inspected.

Fresh command:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q -p no:cacheprovider tests/steward/test_archive_open_references.py tests/steward/test_archive_readers.py
79 passed in 131.35s
```

This small selection covers mixed resolved B/untracked C, deleted/mismatched/missing authority and nonresolved states including `verified`/`no_change`, a matching resolved positive, the real valid concurrent C update before CAS, and real CAS refusal when candidate projection deletes/escalates/removes authority. It also covers typed desk/options/record/phase roles and nondebt IDs, and read-only legacy V2 hydration uncertainty. The reader fixture uses a narrowly scoped `phase_hold` override solely to construct a historical legacy archive; it is not before-fix evidence and does not bypass ledger validation. No old predicate was substituted into the repaired transition for before evidence. The three updated synthetic positive fixtures and retained missing-state negatives are disclosed in the builder proof; the selected tests include the retained negative desk and historical-only cases. The builder's 753 selected cases remain builder evidence, not independent execution here.

Source inspection: `eligible` runs the phase allowlist then `settled_references`; typed debt references and related/adopted work require matching ID, explicit A/B/C authority and resolved current state, with count consistency checks. `verify_transition` checks eligibility on both the previous document and candidate against the old run before accepting lossless projection; `projected`/hydration remain structurally separate from current eligibility so historical reads do not silently settle data. The finding is precisely that the supposed current authority check does not validate history content or consistency, not that historical labels, terminal labels, counts or pointers alone prove settlement. Existing checks correctly hold the original missing-work case and the specified nonresolved state controls, but do not cover inconsistent `state` versus history. No automatic C decision or fake work was introduced by this review.

Independent reproduction commands were inline `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python - <<'PY'` scripts using `empty_ledger`, `validate_ledger`, `open_summary`, `historical_record`, `settled`, `GitRefLedgerStore`, `seed`, `update`, `plan` and `migrate`. Printed results:

```text
malformed entry valid=True eligible=True
contradictory latest valid=True eligible=True
absent valid=True eligible=True
validator True eligible True last-history escalated work-state resolved
plan ['run-a']
migrate ['run-a']
hot phases {} work unchanged True
```

All fixture subjects, histories and remotes were synthetic and temporary. The migration probe is not an actual production migration.

## Verification limits and parked status

Full Steward, main/CI, mission and actual-data gates were intentionally not run. No full 4.48 MB transfer suite, actual origin/ledger/store, live scan/run/record/migrate/rollback/lease, GitHub write, push, actual merge, credentials, rank/trust/evidence, compile/activation, release/deploy or package/global configuration change occurred. No claim is made about arbitrary interleavings, external-file portability, production reachability or independent fresh-host retrieval. Skill Heaven was unavailable in this harness; no plugin validation is claimed. Separate authorization and gates would still be needed for any future actual archival work.
