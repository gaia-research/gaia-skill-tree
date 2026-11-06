# Lane B shared continuation — archive repair checkpoint #2283

## Status and exact content

**Scoped portability/performance repair committed and focused regressions passed. Expanded actual-data archival DoD remains incomplete; this is not merge acceptance or production completion.**

- Branch: `dev/steward-memory-complete-2283`.
- Preserved parent: `598e45b01a848f45be100b06b094e99b5a9f4938`.
- Exact repaired SHA: **`9aa9db35f85da35636130eaf2cad6f4b0311b615`**.
- Commit: `fix(steward): fail closed on untyped archival phase detail`.
- Approved author/committer identity supplied through Git `-c` flags: Marcus Rafael B. Tiongson <153011150+mbtiongson1@users.noreply.github.com>.
- Worktree: `$HOME/.gaia-worktrees/steward-memory-2283-unbounded`.
- Final `git status --porcelain=v1`: empty; `git diff --check`: exit 0. No push, reset, stash, rebase, merge or history deletion.
- Preserved and completed the interrupted workers' dirty work rather than restarting it. Their interrupted test invocations are **not counted** as passing. The recovered pointer assertion is correctly `a.POINTER not in hot["runs"]["run-a"]`.
- Draft PR #2287 remains rejected/DO NOT MERGE pending the parent's fresh independent exact-SHA gate.

## Files in this checkpoint

- `src/gaia_cli/steward/archive.py`: typed complete-tree phase allowlist; explicit historical-observation/current-work distinction; authoritative settlement recheck; linear inline-text scanning.
- `tests/steward/test_archive_phase_schema.py`: exact independent portability counterexample, unknown/nested/scalar/reference shapes, canonical historical schemas and preserved uncertainty, operation-count performance check, cross-clone roundtrip and settlement CAS race.
- `tests/steward/test_archive.py`: tiny no-saving fixture now uses a supported safe observation schema rather than an unknown phase; its no-saving assertion remains intact.
- `founder/steward/MEMORY.md`: eligibility/portability contract, bounded scanner, actual historical zero-eligibility measurements and finer-grained-design limitation.

No ledger/fullrun/CLI implementation changes were needed in this continuation; their existing archive compatibility and transport protections remain covered by regressions.

## Exact portability counterexample: before and after

Synthetic phases, unchanged from the independent rejection:

```python
{"observe": {"receipt": "receipts/proof.bin",
             "evidence": "evidence/build-output", "payload": "x" * 10000}}
```

Executed a read-only extraction of the old `phase_hold` function from `git show 598e45b01a848f45be100b06b094e99b5a9f4938:src/gaia_cli/steward/archive.py` using Python AST, temporarily substituted that function in-process, and used `tests.steward.test_archive.hosts.__wrapped__` under `TemporaryDirectory` for a disposable bare remote. No real ledger or artifact file was opened. Actual output:

```text
BEFORE hold: None
BEFORE eligible: ['run-a']
BEFORE archived: ['run-a']
BEFORE hot phases: {}
BEFORE retrieved references: {'evidence': 'evidence/build-output', 'receipt': 'receipts/proof.bin'}
AFTER hold: phase has unknown, nonportable or unsettled schema data; payload must stay hot
```

This reproduces the old false acceptance, not merely a guessed pre-fix failure. The new exact-counterexample regression additionally proves `plan` and `migrate` return no candidates/transfers, the complete shared ledger/version and remote refs remain unchanged, and cross-clone `show` retains the original phases.

The repair is not an extension/suffix blacklist: each supported phase object, nested object, ID map, array, scalar type and enumerated state has a declared schema. Every unknown field/phase is held even for null, false, zero, empty, nonstring or nested values. Unknown extensionless references remain held. Known inline-prose slots reject slashes/backslashes, tilde, colon and filename-like tokens independent of extension. Only declared identifier/debt-ID slots accept ID references; they are not artifact-byte claims. Nonempty Class C/results/landings/dispatch data and unresolved operational shapes remain hot. Unsupported producer fields require schema review, not coercion or dropping data.

No external files are bundled. Ordinary proof-artifact/receipt/action records outside phases stay verbatim hot; storing a path or hash is explicitly not evidence-byte portability.

## Performance evidence

The assignment reports the earlier interrupted dirty parser used unanchored `re.search(r'[/\\~:]|[\w.-]+\.[\w.-]+', value)` and hung on a multi-MiB dot-free token. That historical hang is operator-provided evidence, not a completed timing run by this continuation; neither interrupted suite is credited. The greedy unanchored dot requirement retries token suffixes when no dot exists. We did not rerun that pathological large regex.

The recovered fix scans characters once with bounded neighbor checks. The committed regression forbids `re.search`, counts actual character visits on a **3,145,728-byte** token, and exercises late dots/paths and repeated dots. It does not truncate, skip large payloads or use a wall-clock deadline. A separate final-SHA measurement produced:

| Input | Accepted | Character visits |
|---|---:|---:|
| `x * 3145728` | yes | 3,145,728 |
| same + `.` | yes | 3,145,729 |
| same + `.bin` | no | 3,145,729 |
| same + `/proof` | no | 3,145,729 |

The tiny exhaustive test compares all 4,681 strings of length 0..4 over `x._-/π :` against the intended conservative token predicate. Existing durable >2 MiB cross-clone migration/hydration/rollback tests also passed; the operation-count test does not substitute for those transfer tests.

## Actual verification commands/results

Environment/options for every pytest command:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q -p no:cacheprovider ...
```

1. Recovered-content surgical check, immediately before committing the identical file content:

```text
tests/steward/test_archive_phase_schema.py tests/steward/test_archive_readers.py
131 passed in 105.68s
```

2. At exact committed SHA `9aa9db35f85da35636130eaf2cad6f4b0311b615`:

```text
tests/steward/test_archive.py
tests/steward/test_archive_cli.py
tests/steward/test_archive_contracts.py
tests/steward/test_archive_phase_schema.py
tests/steward/test_archive_readers.py
tests/steward/test_archive_safety.py
tests/steward/test_ledger.py
tests/steward/test_fullrun.py
413 passed in 649.34s
```

3. Same exact committed SHA:

```text
tests/steward/test_cli.py
tests/steward/test_cli_contract.py
tests/steward/test_fullrun_cli.py
tests/steward/test_fullrun_scenarios.py
tests/steward/test_coverage_regressions.py
tests/steward/test_report_inputs.py
141 passed in 341.62s
```

**554 distinct selected tests passed at the committed SHA.** The earlier 131 overlap and are not added again. No test deadline/turn cap, suite skip, package install or global configuration mutation was introduced. Full Steward regression was not run here and remains a parent gate.

Covered load-bearing behaviors include V1 compatibility/V2 old-reader refusal, ordinary view/resume/replayed-record hydration and missing-object refusal, preserved unknown/partial coverage, >2 MiB durable roundtrip, same-byte/different-source-commit provenance reachable by fresh archive-only fetch, remote readback/immutability/corruption refusal, upload/CAS crash stages and duplicate/ambiguous success, lease/action/current-work protection, lifecycle CAS retry, forward rollback retaining intervening work/index history, and finite-capacity/new-growth stops.

New authoritative settlement race: a canonical historical `debtStatus: open` is allowed only when the current hot work record is explicitly resolved. A second clone changes that work to escalated at `before-cas`; retry returns no archive, leaves original phases hot with no pointer, preserves the escalated work and adds no canonical history event. Historical uncertainty is never normalized to healthy or interpreted as current settlement.

One exploratory measurement failed with `AttributeError: 'int' object has no attribute 'items'` after deliberately replacing the schema predicate with a no-op: a legacy snapshot has a scalar `debtStatus`, which the real typed gate correctly refuses before the settlement traversal. This was an invalid diagnostic precondition, not a test pass or a live mutation. The corrected measurement below invokes the actual predicate unchanged and independently counts protected work references; no code was loosened to accommodate the diagnostic.

## Real eligibility, headroom and growth — local immutable Git objects only

Read only exact `git show COMMIT:ledger.json` objects. These are old snapshots, **not** the current remote ref. No actual-origin archive/ledger/scan/run/record/lease command or shared write was performed.

| Exact snapshot | Hot bytes | Runs / terminal | Eligible terminal | Terminal runs referencing non-resolved work | 8 MiB headroom |
|---|---:|---:|---:|---:|---:|
| `9b3e58abd5117cd7b8c607859ac8cb68525ba999` | 1,005,272 (11.98%) | 13 / 13 | **0** | **13** | 7,383,336 |
| `74d338e498afcc547a089b3379e1398a7ad78085` | 1,124,502 (13.41%) | 14 / 13 | **0** | **13** | 7,264,106 |

Baseline work states: blocked=1, escalated=4, no_change=1; no resolved work. Later snapshot adds verified=1 and retains one lease. Compact runs occupy 757,441 / 860,378 bytes respectively; compact phase JSON totals 559,273 / 617,446 bytes. These non-identical serialization measurements are contributors, not additive physical byte accounting.

Separately measured each exact snapshot against its immediate local Git parent:

- Baseline: +473 bytes / one generation / 589.843537 seconds (~0.801908 bytes/s).
- Later snapshot: +4,781 bytes / one generation / 450.277622 seconds (~10.617894 bytes/s).

The earlier supplied 30-generation observation (+79,056 bytes over 0.5511 hours; maximum +39,775, median zero) is historical context, not a newly measured forecast. Neither a short parent interval nor an older burst predicts future growth. Hot replay/action/work history still grows after phase archival; there is no infinite-capacity claim. Existing 70% planning, 90% new-run refusal, explicit stop/minimum-headroom controls and hard load/write byte bound remain authoritative.

## Residual hard gates / true DoD

1. Parent publishes this local checkpoint and obtains **fresh independent reviewer-shared exact-SHA assurance**; prior rejection/old passing suites do not accept it. Full Steward suite and integration/reconciliation against other lanes remain required.
2. All 13 recorded terminal runs independently retain non-resolved authoritative work. Fixing phase false positives or adding file bundling cannot settle them. Do not manufacture production history, archive pending data, drop Class C/leases/actions or call a no-op preview mission completion.
3. Meaningful actual-data archival requires authorized settlement followed by a fresh eligibility preview, or a separately scoped/reviewed **finer-grained immutable-detail design** that leaves every pending record/reference and replay summary hot. This limited implementation projects all phases of an eligible settled run; it does **not** implement partial-detail archival or work-history externalization. Existing founder authority covers settled terminal detail/fully settled history, not treating decision-linked/pending runs as settled or bypassing protected-detail boundaries.
4. Artifact-bearing phases remain ineligible. Safe rooted/bounded verified artifact-byte bundling is not implemented and cannot be claimed from the retained reference strings. Any actual evidence-byte portability claim needs its own verified transfer proof.
5. No live migration, fresh-host live retrieval, forward rollback or true shared-ledger re-observation was attempted. Those remain parent-owned operations after safety/authority gates. No 8 MiB Lane A acceptance is counted as archival mission completion.

This continuation made no forge writes, trust/rank/registry/intake mutations, Class C actions, policy changes, workflow activation, release/deploy, package/global configuration changes or edits to other workers' files / `founder/MEMORY.md`. Only disposable local remotes were mutated for tests. The in-house plugin/Skills API is unavailable in this harness; repository-required graft was used without installing anything, not represented as Skill Heaven validation.

## Resume

Use the existing clean branch/worktree at `9aa9db35f85da35636130eaf2cad6f4b0311b615`; do not reset/stash/restart. Parent should publish and arrange the independent reviewer/full-suite gates, then address the explicit actual-data eligibility/design boundary before any live transfer. No pending uncommitted implementation edits remain.
