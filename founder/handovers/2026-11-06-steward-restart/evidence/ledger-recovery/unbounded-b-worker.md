# Worker assignment — Lane B, issue #2283

You are the engineering worker, not the lead or campaign driver. Use the appended worker-sol persona. Your exact required runtime is `openai/gpt-6.1-sol`, high. Antigravity and model switching are prohibited. No delegation. There is no imposed task timeout or turn budget; complete the scoped implementation and evidence rather than stopping at a plan.

## Context and authority

Read `CLAUDE.md`, the graft skill and the live read-only issue #2283. Founder authorizes non-destructive archival memory, safe migration/rollback/corruption recovery and the initial 8 MiB active ledger. All Class C execution, history deletion/rewriting, trust/rank/evidence mutations, release and deployment remain prohibited. Another sensor PR will land on main first; do not rebase or reset any integration branch, and do not overwrite their work. Lead will reconcile actual main changes later.

Your dedicated worktree starts at checkpoint `d58f6b1bf2a42b6929b903b6c3f584c11d119a0e` on a feature branch. This preserves the prior Sol worker's partial implementation; do not restart from scratch. Parent checkpoint includes its last unverified edit after a 30-minute native-runner timeout. The original complete prototype is commit `7712a5d92123e1c866ebea1dcc89eba3b73ffe58`; A was merged at `869b14a8de8b41a982d9c56098da48b2cb80125c`.

Lane A is independently accepted at `6bc3688705c14b10f7ded3e6caeb721dd278c3bd`: merge that commit into your feature branch, preserving your memory schema and FullRunner reader changes. It adds the invalid-config load-entry checks and strengthens tests. All 134 independently selected A tests passed. Two old tests now explicitly assert preservation instead of intentional data loss.

## Existing work to inspect

- `src/gaia_cli/steward/archive.py`: immutable Git archive, exact source snapshots, linked searchable index pages, migration, rollback, retrieval, capacity reports and eligibility.
- `src/gaia_cli/steward/ledger.py`: current checkpoint introduces archive-aware ledger schema V2, while preserving legacy V1 reads.
- `src/gaia_cli/steward/fullrun.py`: ordinary reader hydration changes.
- `src/gaia_cli/commands/steward.py`: show/history/archive/rollback surfaces.
- `tests/steward/test_archive.py`, `test_archive_safety.py`, `test_archive_readers.py`.

Before timeout, 19 selected safety tests passed. A later selection had eight passed and one growth-rate fixture failure (expected a 24-hour interval but actual next-generation timestamps differed). The last edit was not rerun; do not claim a green checkpoint. The original prototype's 42 archive tests passed but independent review found critical gaps.

## Mandatory acceptance requirements

1. Hot state retains active/queued/blocked/escalated/decision-pending work, current leases, actions/outcomes and necessary replay/idempotency/dedup references. Eligibility is lifecycle-based, never just age or a terminal label. Open Class C references remain hot and unchanged.
2. Non-destructive transfer: publish immutable versioned content-addressed shared Git archive -> verify remote size/hash/schema/identity/read-back -> only then canonical hot CAS. Recompute eligibility on conflict. Crash/timeout after upload or CAS and duplicate retries must be safe; no silent pruning, no GC or expiry.
3. All ordinary FullRunner read paths depending on archived phases must hydrate or explicitly refuse missing/corrupt data. `_view`, resume and repeated record results must never convert missing `coverageUnknown`/`notEvaluated` into empty/healthy observations. Test view equivalence and missing-segment refusal.
4. Enforce a compatibility boundary: pre-change V1 readers must refuse migrated V2 even when the hot ledger is below 1 MiB. Ordinary writes must not silently discard archive metadata or treat missing history as complete. New clients must still read V1. Preserve CAS, leases and action replay behavior.
5. Evidence retrieval means bytes, not local-path strings. Bundle safely rooted, bounded referenced proof/receipt/diff bytes with hashes and independently fetch them from another clone; OR keep such records ineligible/hot and explicitly disclose the limitation. If refusing those records leaves no real historical data eligible, implement safe bundling sufficient for a genuine migration rather than claiming a no-op as completion. Never archive arbitrary files, credentials or unrelated paths. Keep available canonical evidence and provenance exact; do not invent or rewrite it.
6. A valid >2 MiB terminal payload under the supported initial 8 MiB ledger must be archivable. Fix the prototype's smaller segment bound with a bounded representation/chunking or justified compatible limit and regression tests.
7. Snapshot content addressing must preserve the exact provenance commit even when identical ledger bytes occur at different commits. The original prototype reused a same-digest snapshot without ensuring the current `sourceCommit` was reachable. Bind source commit identity or provide a separately verified durable provenance anchor; test fresh-clone retrieval through archive refs.
8. Search by run/debt/routine/time must work on actual canonical phase shapes, with bounded page reads, safe cursors and tested index growth. Preserve source Git ancestry and distinguish current-snapshot roundtrip from reconstruction of material pruned before this feature.
9. Provide measured capacity/headroom, 70/90 alerts and explicit growth-stop controls. Baseline: 1,005,272-byte hot ledger; 13 terminal runs; runs dominate. Last 30 committed generations grew 79,056 bytes over 0.5511 hours; max single increase 39,775, median zero. This is descriptive, not a reliable forecast. Phase-only archiving still leaves replay metadata growing: bound/minimize what is safe, surface remaining hot growth and do not promise infinite capacity.
10. Test safe forward-CAS rollback retaining intervening work and archive history, corruption/missing-object recovery or precise refusal/repair paths, concurrent writers/lease holders, CAS timeout ambiguity, duplicate/colliding publication, interruption stages, cross-clone retrieval and protected-state equality.

## Execution boundaries

- You may edit/commit in your feature worktree and use disposable temporary Git remotes for tests.
- No actual shared-ledger writes, campaign scans/runs/records, archive --apply on origin, GitHub writes, global configuration changes, main/integration commits or model calls beyond your own pinned route. Lead alone owns live operations.
- No timeout or max-turn wrappers. For long tests, do not impose a new artificial task/test-suite deadline. Preserve existing repository test safeguards.
- Do not install packages or alter global Pi settings. Built-in read/bash/edit/write are sufficient; graft CLI is available, ripgrep is broken on this Termux environment.
- Commit coherent checkpoints with the repository's existing approved Marcus identity. Never discard partial work.

## Completion and proof

Implement and repair the requirements, run the archive/reader/safety/ledger/CLI regressions, inspect actual outputs, and commit a reviewable feature. Lead will run the full Steward suite and obtain fresh independent Terra assurance before live migration; do not claim those gates yourself.

Write a concise final proof report to the absolute authorized handoff path:
`$HOME/gaia-skill-tree/.gaia/steward/campaigns/2026-11-05/ledger-recovery/lane-b-unbounded-proof.md`

Include exact feature branch/SHAs, affected files, commands/results, new CLI usage, architecture and rollback/repair contract, external-artifact eligibility behavior, growth limitations and any unmet Definition-of-Done items. Do not claim actual shared-ledger migration, live retrieval or production readiness before lead verification.
