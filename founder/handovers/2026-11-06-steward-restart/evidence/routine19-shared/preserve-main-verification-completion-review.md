# Independent preservation verification completion

## Status
clean — **whole joined PRESERVATION SOURCE ACCEPT** at exact **`b04a6c34974e0ce25a8a6ff43bc676dd864c3264`**, tree **`9b29681b44be112306f8502961f4e67787492d97`**.

## Findings
No actionable merge-introduced correctness, regression or security defect was found. All assigned missing join/interface, resource and archive-exclusion checks are complete. This is the whole bounded preservation-source verdict, combining the completed checks below with explicitly identified prior independent assurance, not merely acceptance of a new test slice.

Terra's `preserve-main-independent-review.md` remains unchanged and honestly BLOCKED at its historical incomplete-coverage stage. Its SHA-256 is `e86037cc236efec1d1dac29bbb950f3e67ce9ca70ad3872ea627db14c6c4a451`. That report established no concrete merge-introduced defect; this completion supplies its missing coverage rather than overriding a defect or treating uncompleted work as a pass.

**No main-merge, operational, activation, closure, credential-clearance, release or campaign-completion approval is granted.** This is faithful preservation of accepted integration plus pinned main, not acceptance of the separately owned unpublished coordination feature or the parked archive feature. Normal remote CI, protection and human gates remain parent-owned.

## Exact identity and runtime

- Independent reviewer-shared, separate from preservation and core implementers. Observed harness environment: `PI_PROVIDER=openai-codex`, `PI_MODEL=gpt-6.1-sol`, `PI_REASONING_LEVEL=high`; Python **3.14.6**, Git **2.56.0**, Termux. Provider-side routing is not independently attested. No nested agents or fallback.
- Assigned cwd `$HOME/.gaia-worktrees/steward-preserve-main-review-2283`; initial and final `git status --porcelain` empty. Root/founder CLAUDE and required graft instructions were loaded before source investigation.
- Candidate's source parent is `9dca3c6574701f57473e0cc3f52606600b1466ee`, tree `4d24241bd375324aecbba51e3fbd1cf47f1583ab`, parents `ae0598f0aaedc7505a8d2f96d95d585a6ee47ec0` and `31b407db65c4e138896780a7319e4a4ce76884eb`.
- Fresh `git merge-base --is-ancestor 8ad344a49926821d2c1b6d4e021b8de6f653649c HEAD`: **exit 0**. No mutable remote tip was substituted for these pins.

## Fresh structural and carry-by-identity checks

Inline read-only `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python - <<'PY'` programs used `git diff --name-only`, `git rev-parse <revision>:<path>`, `git show`, SHA-256, JSON/YAML parsing and AST comparisons. These were independently authored assertions, not builder probe scripts. Results:

1. Relative to merge base `1963a47f480251d79d98c6a13b8c272444996467`, integration changes **64 paths**, main **266**; overlap exactly `src/gaia_cli/steward/fullrun.py` and `tests/steward/test_fullrun.py`. **62/62 integration-only** and **264/264 main-only** paths have identical candidate/parent blob IDs, with absence handled as absence.
2. Candidate versus source parent adds exactly `docs/agents/security/2283-main-preservation-proof.json` and `.md`. Its complete base-relative changed-path set is exactly the union of both parents' changes plus those two documents: **330 paths**, no unexpected path.
3. Read both parent diffs for both overlapping files. After normalizing **only** the `_compact` function body, the candidate's **entire `fullrun.py` AST equals pinned main's AST**. Thus main's PR action, record, phase, lease and routine-19 behavior has not acquired an unrelated semantic resolution. Candidate versus main tests changes only the two compaction expectations into complete-document equality assertions; main's routine-19 coverage assertion remains.
4. The automatic merge-tree reconstruction was completed independently by Terra and returned the actual source-parent tree. That reconstruction is carried as prior evidence; no new merge-tree run is claimed here.

### All six accepted campaign units

Prior reports below were read in full under `$HOME/gaia-skill-tree/.gaia/steward/campaigns/2026-11-05/` (the ledger-recovery and founder-reconciliation directories are siblings of routine19-shared).

| Accepted unit / prior evidence | Fresh binding and carry conclusion |
|---|---|
| Lane A capacity/history: `ledger-recovery/lane-a-ready.json`, `lane-a-live-assurance.json` | Candidate `ledger.py` is exactly accepted Git blob **`dae7b0d3bc2fd3f04ba82b978e66d2c0ca92b0cd`**. The historical live receipt is snapshot evidence, not a new remote load. The deliberate no-op and current PR-proof retention were separately checked below. |
| CI branch scope: `ledger-recovery/ci-scope-independent-review.md` | Workflow and `test_landing.py` both exactly equal accepted `c5de985cb18515ceb245fb91ebc3053b94c18ece` blobs. Prior scope/fork checks carry without weakening the canonical Class B branch restriction. |
| Unused import composition: `ledger-recovery/unused-import-composition-independent-review.md` | Founder subsequently changed reconciliation semantics. Candidate reconciliation is independently proved byte-for-byte equal to accepted founder input `42322964` **minus only `from pathlib import Path\n`**; it also equals combined accepted `5cbe7e80`. The earlier import-only report is not misrepresented as review of the later founder logic. |
| Security source: `founder-reconciliation/security-aggregate-independent-review.md` | Both entire Impeccable subtrees equal independently audited `166e855` trees. All 39 current bound source paths equal `3f4c46fe` and their reviewed SHA-256. Scanner/redactor/public scanner equal that checkpoint. The changed-watcher gate is supplied by the next accepted combined report, not waived. |
| Founder/watcher composition: `founder-reconciliation/founder-verification-completion-review.md` | Enumerated operative source, test, workflow and lock/decision paths changed by its accepted unit. **41 paths**, excluding only the two present merge overlaps, equal accepted `5cbe7e80` blobs exactly. This includes watcher callers/identity/count transport, issue-hygiene callers and workflow source. The overlaps have the separate semantic proof above. |
| Evidence prose/proof: `founder-reconciliation/evidence-prose-independent-review.md` | All **four** historical prose/matrix/proof paths changed since `c67d90950` equal accepted `bb9abb0f` and integration exactly. No historical proof was rewritten to adopt the joined policy. |

The prior 23 security controls, 42 adapted official compatibility tests, comprehensive 39-row semantic assessment and watcher-specific independent probes carry through these actual source identities and accepted reports. They are **not new executions**, not a whole-file security certificate and not independent approval of every main change.

## Missing semantic joins and caller interfaces — completed

### C1/C3 and existing holds

Read actual `questions.py:28-67`, `reconcile.py:662-709`, `sensor.py:104-122`, `executor.py:270-332`, the C1/C3 decision records and founder-lock boundary document. Graft identified all four production `loadIssueDecisions` callers: sensor reconciliation, reconciliation CLI, CLI apply path and closure gate. These source blobs remain combined-accepted bytes.

- Exact question/debt/resolution/authority bindings and the marker-plus-four-record requirement remain enforced. Missing, renamed, open or malformed locks do not release holds.
- C1 is **technical reconciliation only**, preserving distinct Ruflo/AgentDB source/version identities; it grants no release, registry, trust, intake, L4 or closure approval.
- C3 remains a family/descendant hold, preserving child payloads/history and L4 gates even when a child could otherwise have closure proof. C2 namespace migration remains deferred. Unrelated genuine questions are not silently answered.
- The new main decision record is a different ID and is not selected by the four-question loader. Fresh `_check_record` and `load_decision_records` AST comparisons equal accepted founder source, despite main's added PR-specific founder presentation. Existing issue-question routing remains distinct from `routine-pr/...` routing.
- Fresh old-parser/old-policy versus current-parser/current-policy dataclass comparison preserves **every old parsed value**, not just old YAML spelling. Main's additions do not change old authority, priority, routing, Class B quotas or issue-hygiene configuration.

Fresh focused tests exercise real sensor/CLI/closure re-derivation on damaged locks, C1 technical classification, C3 descendants/stale approval, body preservation, unrelated questions, strict generated watcher identity, mixed-case same-run cache behavior, typed counts and pagination refusal. These supplement, rather than repeat, the prior exhaustive semantic/caller audits.

### FullRunner / Routine 19

The join retains Lane A's 8 MiB default, 1 KiB–64 MiB bounded override, fail-closed capacity handling and size-only telemetry through exact accepted ledger identity. `_compact` remains a deliberate no-op. An independently constructed **70-terminal-run** in-memory document containing merge actions, phase receipts, proof artifacts, CI results, assignments and desk state was deep-compared before/after `_compact`: **unchanged**.

Manually inspected `_emitPrMaintenance`, `_recordPrWrite` and `_phaseClassB` with their parent diffs. Main's exact behavior survives: at most one PR action emitted at a time; exact head/base verification required for emission; successful write reporting requires matching durable outcome; no-agents emits no PR write; pending actions participate in the existing lease/TTL mechanism. Class B's original dispatch/in-flight/attempt/cooldown limits remain unchanged. This does not certify inherited local JSONL coordination against concurrent live writers.

Pinned main's unattended driver remains byte-identical. It aborts routine PR actions instead of performing their merge/closure; the dedicated PR driver owns that route. Both sensors consume local census inputs. No new actual forge grant or unattended-driver bypass is introduced by preservation.

### C4 pause and closure authority

All **eight** compiled build/verify wrappers are byte-identical to both accepted founder source and pinned main. Fresh YAML parsing asserts that each has **only `workflow_dispatch`** and activation condition **`${{ false }}`**. The shared hardened source is preserved; no compilation or synchronization is claimed. Existing compiled-source/engine/credential/activation gates remain open.

Runtime policy still has `issue_hygiene.writesEnabled == False`; `closureAuthorityApproved(root) == False`. Credential-leak authority remains C. This preservation does not convert paused workflows into GitHub API-disabled evidence or authorize closing #2126/#2127.

## Version, CLI, producer and ratified-policy resources — completed

Fresh exact-main comparisons passed for **13 explicit paths**: both version manifests; main/impl/Steward CLI; POLICY; producer registry; PR authority record; routine coverage/catalog; routine-19 documentation; unattended driver; dedicated PR and census scripts. All **15 PR-maintenance source files** also equal pinned main.

- `pyproject.toml` and npm manifest parse as **9.3.0**. Actual checkout `version_command` with explicit checkout registry prints **9.3.0**. No installed package-version or release-publication claim is substituted.
- Actual public parser accepts routine 19, `--no-agents`, `--ledger local`, JSON. Focused CLI tests also execute every catalogued routine and reject invalid bounds. No production run was executed by these probes.
- Actual `loadRegistry(root)` accepts the shipped registry: schema **`steward-pr-producers-v1`**, revision 1, **three** producers, enabled scope only `gaia-research/gaia-skill-tree`, merge methods all `merge`. Census source constant is **`steward-pr-census-v1`**. Skill Heaven remains explicitly deferred/unknown.
- Actual `StewardPolicy.load(root)` loads main's separately ratified PR route and decision record unchanged. Missing authority, invalid ceilings, malformed/absent sections, squash and unscoped producer enablement are covered by fresh tests. This is preservation of already published main authority, not independent re-ratification or permission to exercise it.
- Fresh runtime checks preserve canonical B `maxDispatchesPerRun=1`, `maxInFlight=2`, `maxAttempts=2`, cooldown 3600 seconds, old security C authority and all four finalized founder bindings.

## Parked archive exclusion — completed

Fresh ancestor checks on **both** `5432b273c` and `ceb38582008a07002239ec65aa77aa22725e80ab` return **1**, not ancestors. Enumerated their added paths relative to the actual common base and selected those absent in **both** candidate parents. Every such path is absent in the candidate:

- Common eight: `founder/steward/MEMORY.md`, `src/gaia_cli/steward/archive.py`, and `tests/steward/test_archive{,_cli,_contracts,_phase_schema,_readers,_safety}.py`.
- The later parked composition additionally introduces `tests/steward/test_archive_open_references.py`: **nine** excluded paths at that checkpoint, not eight plus nine distinct files.

Read the actual parked diffs on existing ledger/fullrun/CLI surfaces. Their V2 archive schema, pointers/hydration/transition verification, growth-stop/headroom controls and memory/transfer CLI were not inherited. Current source has no `ARCHIVE_LEDGER_SCHEMA`, `_stewardArchive`, `_verifiedRun` implementation from the feature, `_executeMemory`, or the feature's two full-run stop/headroom environment controls. Fresh runtime validation rejects `steward-ledger-archive-v1`; actual parser rejects **show/history/archive/rollback**, all exit 2. No archive-owned profile appears through an extra path: the complete changed-path union and actual main roster-source identities were checked.

This is feature exclusion, **not** a ban on every use of the word archive. Accepted Lane A capacity/history safeguards and historical references remain correctly present. Archive data DoD and whole-settled-run migration remain outside this accepted unit.

## Sidecar and historical proof

Fresh source/tree and hash assertions agree with actual Git objects:

- Sidecar source `9dca3c65`, tree `4d24241b...`, and two actual parents are correct.
- POLICY changed from historical **`58af7eb1d4915970e2b8ffa8b55f4c96f5f79b7cd330b316c1d05ff534a28278`** to joined/main **`db34e81bb502dc5a5097b41e7e8c69cc7d288905fbad7b3be491e5324b235246`**.
- Recursive actual YAML comparison finds exactly **18 additions**: eight authority, eight priority, one founder route and `prMaintenance`; **no old key removed or old value changed**. Added-path set equals the sidecar's declared list. Joined POLICY bytes equal main.
- Historical matrix **`da5b7a39f3a261cc82fcf74e88038c122c9d5b035da5dab7957b8aea66d940e6`** and proof **`e10b20d2657ed511ff9e6ab8585784510e26bacccd1bc631d42557ab5e9a7867`** remain unchanged. Scanner/redactor/public scanner hashes match sidecar and historical checkpoint.
- Terra independently verified **39 current paths / 71 current findings** (D1 30, D2 24, D3 17), exact current line/pattern/fingerprint multiplicities and zero sidecar self-matches **at this same frozen candidate SHA**. These results carry with fresh source/hash and artifact identity checks above; no new matcher or control replay is claimed here.

The historical proof remains historical; its unchanged-full-policy statement is not extended to the joined tree. Checker success still does not authenticate finding identity or scanner authority. The published inventory/final-debt digest and separately supplied metadata snapshot remain different historical snapshots; no new historical final-debt bytes were supplied or authenticated.

## Actual fresh commands and results

The complete new focused pytest command was:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q -p no:cacheprovider \
  tests/steward/issuehygiene/test_founder_locks_2283.py \
  tests/steward/prmaintenance/test_policy_receipts_state.py \
  tests/steward/prmaintenance/test_sensor.py::test_registry_never_represents_squash_or_unscoped_enablement \
  tests/upstream_watcher/test_identity_2283.py::test_mixed_case_fanout_uses_one_canonical_cache_without_display_rewrites \
  tests/upstream_watcher/test_identity_2283.py::test_generated_invalid_identity_refuses_before_any_write \
  tests/upstream_watcher/test_count_2278.py::test_metadata_disagreement_requires_exact_typed_counts_and_two_full_walks \
  tests/upstream_watcher/test_count_2278.py::test_count_fallback_never_erases_a_pagination_failure \
  tests/steward/test_fullrun_cli.py::test_every_catalogued_routine_is_accepted_by_the_run_command \
  tests/steward/test_fullrun_cli.py::test_bad_run_arguments_exit_two \
  tests/steward/test_fullrun_cli.py::test_run_defaults_are_safe \
  tests/steward/prmaintenance/test_runner.py::test_with_verification_one_merge_is_emitted_and_integration_stays_sequential \
  tests/steward/prmaintenance/test_runner.py::test_a_driver_cannot_claim_a_merge_the_store_does_not_hold \
  tests/steward/prmaintenance/test_runner.py::test_no_agents_means_no_pr_merge_or_closure_action_either
```

**120 passed in 18.27s**, exit 0, no skips. No deadline/timeout setting, assertion, source fixture or skip condition was changed. Test stores/repos were disposable fixtures only.

Additional independent inline Python commands described in the sections above passed their final assertions: complete parent/path/blob composition; six-unit operative identity; fullrun AST join; resource/version parsing; old/new parser-policy comparison; producer and founder decision loading; archive ancestor/path/CLI/schema exclusion; 70-run proof retention; eight-wrapper pause and sidecar/hash bindings. `git diff --check`: **exit 0**.

Probe-development failures are disclosed, not counted as passes: first attempted to feed old policy into the new parser, which correctly requires its new main founder route; corrected by loading each actual historical/current parser with its corresponding policy. Initial direct parser probe incorrectly guessed ledger spelling `file` (actual CLI is `local`), then guessed namespace attribute `no_agents` (actual is `noAgents`). These exited 1/2/1 respectively; the corrected parser and remaining assertions passed. No failed pytest test or candidate defect was concealed.

Terra's prior fresh **41**, **109** and **19** groups overlap and are not summed as distinct tests. Builder **650** source cases and **14** sidecar cases remain background receipts, not new executions by this reviewer. Older independent reports retain their own execution/checkpoint limits.

## Verification Limits

No full repository/Steward/archive suite, release/package publication audit, website-wide verification, new official upstream fetch or full original security audit was repeated. That is deliberate bounded preservation coverage, not a claim that unreviewed future operations are safe. Current remote CI was not queried or certified green; pending CI is not itself a technical preservation blocker and all normal parent-owned merge gates still apply.

No actual origin/store/ledger read or write, canonical scan/run/record/lease, issuer or credential probe, GitHub/forge write, push, merge, rebase, registry/trust/rank/evidence-intake mutation, compilation, activation, deployment, release, package installation or global configuration edit occurred. Graft's ignored retrieval cache and temporary offline fixtures were the permitted local side effects; this assigned report is the only authored durable output. Source/config/tracked files and the Terra report were not modified.

Inherited general shared-ledger selection and local JSONL coordination races remain separately targeted feature work. They neither become certified operationally safe nor constitute a newly introduced merge defect in this faithful preservation unit.

**Final whole joined PRESERVATION SOURCE verdict: ACCEPT — `b04a6c34974e0ce25a8a6ff43bc676dd864c3264`.**
