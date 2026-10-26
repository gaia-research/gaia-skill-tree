# Yggdrasil IV — recovered deliveries and independent review (2026-10-26)

## Control and restart boundary

The campaign remains explicitly resumed. The founder asked to be told when to reset; the answer is **not yet**. Give an explicit **READY TO RESTART** only after recovery tooling is tested/reviewed/installed and critical work is finished or has acknowledged a verified safe checkpoint. Specify Pi reload versus full Termux restart. Do not infer restart permission from a completion notification. No additional campaign jobs before this restart checkpoint: collect existing checks and prioritize reviewed durable-tooling installation. This is restart sequencing, not campaign completion or a new permanent pause.

The parent verification shell groups below were launched without `surviveReload`; even a Pi reload must wait. Existing `bg_run(surviveReload=true)` supports ordinary non-agent commands across same-process reload only, not agents or an OS/application crash. No such broader durability claim is made.

Continue RFC #2148 and held aggregate #2151. Main, canonical/schema/standing/Origin, live issuer/security, founder visuals, actual operational weeks/pilot and release/closure gates remain held.

## Collected deliveries — not acceptance

| Slice | Saved and remotely confirmed source | Evidence / remaining verification |
|---|---|---|
| Publication | `36883266812824dc49de48ffe1bda757d22d45ce`, `dev/yggdrasil-iv-publication-last-mile` | Worker reports **24 context tests passed in 106.10s**, including actual bounded two-root/corruption fixture. Repeated runtime/font hashing diagnosed as expensive work, not deadlock. Context-bound child reuse must still pass independent outer runtime certification. Parent **323 regressions passed in 122.66s**; first full build failed strict OG PNG coverage after541.79s. No second replay or snapshot certification; tracked-source inventory unchanged. Independent runtime-proof P1 is disputed by an actual gate counterprobe; see verification update below. |
| Durable watcher | `d311d9624f0072d17b270f970733d89535e3926c`, `dev/yggdrasil-iv-watcher-transactional` | Worker reports **50 distinct focused passes**, actual two-process/two-clone CAS barriers, crash73after shared save/before materialization, fresh-clone packet restoration and tamper/dedupe probes. Full combined parent suite and independent15-file review launched; not accepted. Default issuer unavailable. |
| Transaction foundation | `e183246809486faec6b3d1016480291e0575e575`, proper feature branch `dev/yggdrasil-iv-canonical-transactions`, draft PR #2161 | Parent **8 tests passed; 5 containment subtests passed in 0.47s**, clean diff; whole source tree byte-identical to deliverededf below. Independent implementation review outstanding. No CLI writer/dual history/migration wired. Real process-coordination proof was not supplied by author. |
| Corpus | Draft PR #2159, head `cc1c3e1735e95a44df94d59145e4b7d5638bcc61` | Initial CI correctly found generated README CLI choices omitted `shadow`; README-only correction matches actual generator (`README_CLI_GENERATOR_PARITY_OK`). Implementation remains exact reviewed/tested `b6103d7bd`: **324 parent tests**, complete **398 named / 299 generic** no-write replay, and **45 independent focused passes**. New-head CI/final applicable visual gate not inferred. |

Worker reports reside in ignored `.gaia/yggdrasil-iv/recovery/`: `publication-crash-resumed-result.md`, `watcher-crash-resumed-result.md`, `canonical-transaction-foundation-result.md`.

## Publication verification update — actual failure and disputed review finding

Parent task `ba7cb70f5` had already failed when cancellation was attempted; no running process was killed. Full result: **323 regressions passed in 122.66s**, first real full-corpus build exit1 after541.79s, total667.28s. `stamp_outputs` refused certification because the actual semantic oracle found **cross-surface OG PNG coverage mismatch**. Second root and byte-equality proof were not run. Before/after tracked/nonignored source inventory is unchanged. Root cause of the coverage difference remains undiagnosed; do not weaken the oracle, discard assets or label it waived environment debt.

The independent review reported a runtime-proof P1, but its claimed outer-call path contradicts exact source and execution. `publication_parity.py:40–56` activates context **without** `inherit_runtime_check=True`; the default is `False`, so actual runtime is checked before the oracle starts. Only inner producer helpers inherit that checked chain. A bounded parent counterprobe exercised actual `_check_semantic_parity` / outer subprocess bootstrap with a matching inherited proof but controlled different runtime: **outer gate rejected the mismatch before the oracle ran**. Direct internal inherited activation accepts matching proof as designed; this alone is not certification.

Preserve the original review, do not silently edit it. Its P1 is **challenged/not reproduced on the certification path**, not a reason to change correct outer validation. This does not establish overall acceptance: the genuine full-corpus OG coverage failure still blocks publication, and independent recheck remains appropriate after repair. No source changes were made for this counterprobe.

Copied evidence/logs/source inventories and SHA256 manifest: `.gaia/yggdrasil-iv/recovery/publication-368-parent-evidence/`. Runtime counterprobe: `publication-368-runtime-gate-counterprobe.json`. Exact temporary source evidence root: `/data/data/com.termux/files/usr/tmp/yggiv-publication-368.zp90do7y`.

## Branch-routing violation and append-only repair

Transaction author incorrectly pushed these three commits directly to `origin/dev/yggdrasil-iv`:

- `b834be0742e5b3e371c63776ca5a044b87afbb35`
- `29542829235c000841d6ff488f8adc4aba0bf817`
- `edf5b0493f6bc4dedb115874fb131576aea3f10e`

No CLI writer was wired; main and registry data remained unchanged. This was a workflow violation, not accepted integration.

Parent preserved the original source on its correctly named remote feature branch, corrected that branch's upstream, and created single revert `a1d90cefe032969c2798c07ace107ec8bbb32c54`. Independent Flash Medium verification checked exact parentage, exclusive removal of the two newly added source/test files, preserved history/backup, correct upstream, clean worktree and **complete tree equality** with previously accepted integration `4b73e62814fca16a01bd1e71325e7abb97316c95`.

[Repair PR #2160](https://github.com/gaia-research/gaia-skill-tree/pull/2160) merged normally at **`fd4038afb9a34062ca993a4eb0878e0464cfe564`**. Parent fetched the actual remote and verified its complete tree equals accepted4b: **`31d6fb4d2ec924cf9ceb64a621d9f95b719ef2cf`**. No reset, force-push, lost work, new numerical adoption or main merge. Mechanical tree verification is not a claim new CI is green or the transaction code is accepted.

Only after restoration, the original feature branch fast-forwarded to repaired integration and reapplied the exact foundation in a new feature-only commit **e18324680**, with empty whole-tree diff against originaledf and freshly confirmed explicit feature push. [Draft PR #2161](https://github.com/gaia-research/gaia-skill-tree/pull/2161) now provides the proper review path. Never merge a foundation based only on eight tests or the mechanical repair review.

**Current integration tip is fd4038a, with the previously accepted4b code tree.** Original4b remains the fixed semantic baseline for in-flight reviews. Main remains `b0f6d9e502369aea2ebebe13eed8d961675094bd`.

## Verification jobs and collected outcomes

| Work | Run/task | Output / namespace |
|---|---|---|
| Publication independent review collected, Luna High; P1 challenged | `1b98475f-9c5b-409f-aa98-52d6d30aed42` | `publication-368-independent-review.md`; detached worktree suffix `publication-review-368` |
| Watcher independent review, Luna High | `7759a499-ff38-4220-be62-cbc8b4fcf4cb` | `watcher-d311-independent-review.md`; suffix `watcher-review-d311` |
| Transaction independent review, Luna High | `cb30f5b8-5d1e-42a7-adb1-ce97160b9286` | `canonical-e183-independent-review.md`; suffix `canonical-review-e183` |
| Parent publication attempt — FAILED/collected; second replay not run | `ba7cb70f5` | `.pi/tasks/01a1753c-3a9c-7024-bcb2-ac1114464e09-10612/ba7cb70f5.output`; durable launch metadata `publication-368-parent-run.json` |
| Parent complete watcher/ledger tests | `bbdc8140c` | Same task directory, `bbdc8140c.output`; disjoint temporary evidence prefix `yggiv-watcher-d311.` |
| Durable Pi tooling phase1 collected, Flash High | `e2c1a27a-7940-4d45-82a3-8b8f92bc9dbc` | External `~/.pi/durable-recovery/{manifest.json,implementation-result.md}`; isolated `~/.pi/worktrees/pi-config-durable-recovery`, branch `feat/durable-subagent-recovery` |

All worktree suffixes above use `~/.gaia-worktrees/yggdrasil-iv-`. Reviewers are read-only on frozen source. Collect terminal results rather than polling or launching duplicate owners. The two original resumed implementation workers and foundation author have completed their bounded deliveries; they are not still actively implementing.

## Durable Pi side-task

Flash Medium research completed at `~/.pi/durable-recovery/research.md`. Node24.17builtin SQLite works; pinned maintained tooling is also being evaluated against actual Pi APIs. Preserve Pi1.4.0 and current subagent0.8.0; no blanket update/reinstall, live reload, unrelated config/routing changes or premature activation. Phase1 is saved at `ea0baf70df532e8d3f38cf041d903a443e963f9a` on `feat/durable-subagent-recovery`; parent freshly verified the remote feature SHA and unchanged master `0e4f0c86aeaf8c5fd1b2d9c42ee5ff861cd254da`. Author reports11Node/95Python passes, not independently accepted. Parent verified the live extension file is absent. Independent Flash High review `36b0bc48-c7ce-4fbe-955f-0edb19a66eba` is assigned in frozen `~/.pi/worktrees/pi-config-durable-review`, output `~/.pi/durable-recovery/independent-review.md`. Contrary to the author report, no feature upstream is configured; use explicit feature push ref. The suggested `~/pi-config/bin` deployment command also depends on integrating the new script first; don't blindly execute an absent or unreviewed master-path helper. Independent Flash review precedes targeted live installation with hash-safe rollback.

Required proof includes real synthetic parent kill/restart, full-session preservation before native cleanup, async launch versus completion, exact process identity/unknown states, concurrent claims, crash/WAL/corruption behavior, installer preservation and rollback. A DB/WAL file or launch receipt is not proof of recovery; uncertain external side effects must not auto-replay. This private operational ledger is not canonical Gaia truth storage.

## Remaining campaign gates

Collect the new reviews/replays and repair concrete failures. Guarded CLI integration, dual timelines, migration/rollback completion, genuine issuer evidence, held evidence/schema adoption, actual Frontier native invocation/separate comparison, cleanup referral dependency, genuine lifecycle producer/native changed-panel renders and founder approval, real operational coverage/pilot and release remain in the original campaign. Do not recast them as follow-up debt or call these bounded deliveries campaign completion.

Historical crash WIP refs, patches, bundles and full-session recovery paths remain preserved under the earlier [crash receipt](YGGDRASIL_IV_CRASH_RECOVERY_2026-10-26.md); they are snapshots, not patches to force-apply over newer source.
