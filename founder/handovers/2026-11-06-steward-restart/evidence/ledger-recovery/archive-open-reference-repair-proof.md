# #2283 — open-reference settlement repair

**Bounded source repair; not independent acceptance, live migration, or archival DoD completion.** Founder A remains explicitly selected: 8 MiB fallback, whole fully settled runs only, pending/Class C/work/references/leases/actions/outcomes/replay hot. Actual archival DoD remains **OPEN**. Parent owns publication, independent review, integration, CI/full Steward gates and any separately authorized actual-data operation.

## Exact history and composition

- Dedicated feature worktree: `$HOME/.gaia-worktrees/steward-memory-2283-unbounded`, branch `dev/steward-memory-complete-2283`.
- Preserved starting checkpoint: `5432b273c1156b4e31b4170be398410d57897340`.
- Feature-only merge of accepted root `c67d90950b0aa37491f5061e76f6cda3319da568`: **`8268c2c7895b871510bc336d00e4c840ff8729c3`**, parents 5432 and c67. Automatic merged tree exactly **`8833341ab9cf599d1d6c7cd1bcb0ffd4638f0278`**, the independently rejected composition. Both accepted histories remain ancestors; no omissions/cherry-pick/reset/rebase/stash or actual main/integration-ref write.
- First coherent fix checkpoint: **`8dbfcf16d925ad4db4c8a320943713532f381f62`**.
- Final source/test candidate: **`ceb38582008a07002239ec65aa77aa22725e80ab`**, tree **`1562bbec86d3acad5987587ade118fa2fbc04385`**. Second commit completes typed selector/desk-operation joinpoints and consistency controls.
- All three local commits use approved Marcus Rafael B. Tiongson <153011150+mbtiongson1@users.noreply.github.com> identity through Git `-c` flags. No push; parent publishes tested fix and dependency together.
- Fresh root-to-candidate blob comparison: **59/59 accepted root paths byte-equal**, including additions/deletions. Feature delta after the exact merge is only six files: `src/gaia_cli/steward/archive.py`, `tests/steward/test_archive{,_contracts,_phase_schema,_open_references}.py`, and `founder/steward/MEMORY.md`. No other production file, wire format, schema/version, policy, matrix/proof/sensor/watcher/CI/registry or root founder memory was edited by this repair. Unreviewed bb9 prose was not merged.

## Actual before/after counterexample

Read the integrated REJECT, scoped canonical ACCEPT, ambiguity repair proof, root/founder instructions and graft before implementation. Inspected actual Observation/Debt/Receipt/ScanResult models, FullRunner observation/reconcile/triage/reobserve/work/action/desk producers, canonical work validation, reference/projection/read consumers, migration and authoritative Git ledger CAS transition.

The regression was added **before** changing implementation. `open_summary()` constructs actual `Observation`, open `Debt(authority=AuthorityClass.C)`, `Receipt`, `ScanResult`, and invokes **real `FullRunner._observationSummary(scan, ())`**. It emits C=1/openDebt=1, the same canonical debt ID in `openDebtIds` and `freshOpenDebt`, but `debtStatus={}`. Its historical observe-shaped terminal record is accepted by `validate_ledger`; phase portability alone does not hold it. No fake work is produced to hide that missing settlement.

At exact merged pre-fix source 8268c2c (tree 8833341), an actual disposable bare remote/two-store migration printed:

```text
valid True debtStatus {} C 1
phase_hold None eligible True
plan ['run-a']
migrate ['run-a']
phases {} version_changed True
pointer_retains_debt True
proof_receipts_exact True
```

Log: `archive-open-reference-before-migrate.log` in this report's directory. This was the **whole old module and real ledger transition**, not substitution of an extracted old predicate into repaired surrounding code. The two corresponding newly added tests failed before implementation. The first complete-current-producer qualification fixture also initially failed because synthetic kind `synthetic` is not in policy; its recorded `PolicyError` is a fixture failure, not evidence of production reachability. Corrected that isolated test to the existing Class C `generic_mapping` kind; it then passed on the old source (`archive-open-reference-before-qualification.log`). Original failure log remains `archive-open-reference-before-tests.log`.

At final ceb385820, the same actual historical-shaped migration probe printed:

```text
valid True debtStatus {} C 1
phase_hold None eligible False
plan []
migrate []
crossclone_document_and_version_unchanged True refs_unchanged True
protected_phase_exact True
```

The after probe prohibits canonical CAS; it would raise if attempted. New regression additionally checks exact hot run/show, proof/receipt records, source version and all shared refs. Log: `archive-open-reference-after-probes-ceb385820.log`. No referenced external file was opened; all source/evidence values are synthetic. No real data moved.

**Producer reachability qualification remains explicit:** a separate complete current `FullRunner.start(mode='observe')` execution on a disposable fixture repo, real controller and existing Class C policy kind completes with C=1, empty tracked map and no work. Its real reconcile summary includes `integrationBranch='dev/integration'`, which independently fails the existing portability schema. Thus this demonstrates the historical/contract/API defect and its repair, **not** an exploit of today's complete producer path or the existence/eligibility of any live record. No claim that the reconcile refusal itself authorizes settlement.

## Eligibility and authoritative transition

`eligible` remains the one load-bearing entry point used by plan/migrate and authoritative ledger transition. Its internal `settled_references` check:

- Enumerates **typed debt roles**, not arbitrary filenames, sensor/receipt/decision identities or the search index heuristic. Observation and reobservation open/fresh/resolved lists and tracked status keys, resolvedWork, supported triage debt sets, verification expired debts, explicit debtId/debtIds in canonical records, selected `options.debt`, and debt-typed desk operation subjects all require matching current hot work.
- Requires matching `work[debt].debtId`, explicit valid A/B/C `authority`, `state == 'resolved'`, and well-formed history when present. Missing/deleted work, mismatched identity/authority, historically resolved status, terminal labels, absent observations, verified/landed/no_change and pointer retention never authorize settlement. Existing work associated by runId/adoptedBy/reference is also checked. No policy reclassification, automatic Class C decision, fake production work or current-state rewrite.
- Holds unidentified positive open/Class C/triage counts, duplicate/missing open identities, contradictory open/resolved lists/maps and inconsistent authority counts. Positive numeric carried/filtered debt without identities also holds. Typed receipt/sensor identities require no invented work.
- Preserves existing phase allowlist/unknown-text/operational holds, timestamps, leases, action/step/decision statuses and unresolved/deferred refusal. Nonempty triage Class C remains held; no schema relaxation or partial-phase transfer was introduced.

The ledger transition invokes the **same eligibility predicate against both previous and candidate hot authority**, before permitting the lossless full-run projection. A writer cannot delete/escalate/remove authority from work in the same candidate that externalizes phases. Structural `projected` is also used for historical hydration, so reading an old archive is not incorrectly conditioned on today's eligibility; every new writable projection must still cross this authoritative gate. Regression tests submit ledger-valid malformed transfer candidates through real CAS, with no validator bypass; each is refused without canonical state change.

CAS race: initial healthy, eligible selection publishes immutable objects, then a second clone **validly updates the latest run with the real open-C summary but no corresponding work**, immediately before CAS. The real stale CAS conflicts; fresh selection holds. Exactly one before-CAS callback, no canonical archive event, no pointer, newest document/version retained exactly, all original work/leases/lane/operations/action/step/proof/receipt data unchanged except the intentionally concurrent summary. Orphan publication is not canonical archival history. The older ambiguity/lease/adopted-work races remain in the full selection.

## Synthetic positive fixtures and large-byte preservation

No actual data was retagged. Three positive synthetic setups really lacked the newly required settlement/identity/authority consistency:

1. The shared default desk cited `debt-c` but seed had no such work. Seed now explicitly supplies a **synthetic authoritative current resolved C record**, retained hot. The original missing-work desk is retained as an actual no-transfer negative.
2. The contracts search/view fixture labelled `settled` historically resolved without current work. Its positive transfer now explicitly supplies synthetic matching resolved B work; the original historical-only fixture is retained hot as a negative.
3. Canonical historical observation positives used minimal work lacking debtId/authority and a zero authority count despite an identified open B debt. Their synthetic current work/counts now match the declared roles. Missing authority/identity and inconsistent count shapes remain negative controls, including with resolved work. Original reason-bearing unknown/partial fixtures remain exact hot-only negatives; no uncertain historical data was normalized to healthy.

The existing real numeric observation producer scale remains **16,000 distinct 253-character sensor identities**, not generic prose reclassified as IDs. Fresh measurement at ceb385820:

- **4,480,309 packed phase bytes** (unchanged).
- **5,011,483 seeded source bytes**, up **214** from the prior 5,011,269 because the default desk now has mandatory explicit synthetic hot settlement.
- Both valid and eligible with that settlement, still **below unchanged 8 MiB**. No byte-floor reduction, truncation, skip, timeout increase, smaller segment bound or invented deadline.

The full selection retains actual large cross-clone transfer, full original run/source snapshot equality, ordinary load/view/resume, equal-bytes/distinct-commit archive-only source provenance, immutable publication/collision/index/crash controls, leases and forward rollback retaining intervening pending state. Original unknown/generic/path counterexamples, >2 MiB ambiguity holds and explicitly historical permissive V2 uncertainty reader/missing-object tests remain. Old-history reader fixtures are not authority for new transfers or evidence-file portability.

## Verification

Runtime: `PI_PROVIDER=openai-codex`, `PI_MODEL=gpt-6.1-sol`, `PI_REASONING_LEVEL=high`, Python 3.14.6, Git 2.56.0. No fallback or nested agents. Existing project test safeguards unchanged.

All pytest commands use `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q -p no:cacheprovider`.

- Pre-implementation counterexample: two expected assertion failures; initial qualification fixture failure and corrected pass disclosed above.
- Initial focused repair attempt: **47 passed, 4 failed**; four positive triage-role tests incorrectly supplied C authority for A/B typed roles. Corrected synthetic authorities to match the actual roles; no production gate relaxation. Log `archive-open-reference-focused-first.log`.
- First coherent checkpoint focused selection: **60 passed** (`archive-open-reference-focused.log`).
- Superseded 8dbfcf16d broad selection: **737 passed in 1119.86s**, exit 0 (`archive-open-reference-regressions-8dbfcf16d.log`/`.exit`). An interrupt was requested while preparing wider joinpoint coverage, but the background process actually completed before subsequent edits; its complete log/exit, not the stop-intent message, is authoritative. This is not counted as final-candidate evidence.
- Final focused selection: **75 passed in 56.35s** (`archive-open-reference-focused-final.log`); same source/tests later committed at ceb385820.
- **Final exact-ceb385820 broad selection: 753 passed in 1129.99s (0:18:49), exit 0.** Log `archive-open-reference-regressions-ceb385820.log`, adjacent `.exit` records 0. HEAD remained exactly ceb385820 and tracked status was clean after completion. These are 753 distinct selected cases, not the full Steward suite; earlier overlapping focused/checkpoint runs are not added to this count.

Final broad command selects these complete files:

```text
tests/steward/test_archive.py
tests/steward/test_archive_cli.py
tests/steward/test_archive_contracts.py
tests/steward/test_archive_phase_schema.py
tests/steward/test_archive_open_references.py
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

Separate fresh final-source checks: founder issue/workflow locks **42 passed in 10.26s**; `python scripts/check_security_dispositions.py` passed **39 reviewed source-byte rows**, retaining its warning that identity/scanner authority are not authenticated there; `python scripts/sync_agent_skill_mirror.py --check` passed. These are preservation checks, not fresh full security replay or global safety assurance. `git diff --check 8268c2c HEAD` passed, both required parents remain ancestors, 59/59 root blobs retained. Tracked status was clean after the final source commit; this proof lives only at the assigned absolute campaign path outside the feature worktree.

## Remaining gates and limits

No self-accept, fresh live-eligibility observation, real origin/store/ledger/scan/run/record/migrate/rollback/lease operation, GH/forge write, trust/rank/evidence/intake/registry/compile/activation/package/global config/release/deploy, push, main or integration merge occurred. All actual store/producer/migration/rollback test writes targeted disposable local repositories/remotes. Skill Heaven is not available in this harness; existing required native graft was used without installation or global config changes, and no plugin behavioral validation is claimed.

Parent must obtain fresh independent review and CI/full Steward/integration gates at the published tested fix plus accepted dependency. These selected tests do not exhaust all interleavings or prove arbitrary external file portability. Any actual archive requires separate authority, fresh canonical eligibility, verified transfer, independent fresh-host retrieval and forward rollback preserving newly arrived work. Neither old checkpoint acceptance nor synthetic transfer nor the 8 MiB fallback closes that mission.
