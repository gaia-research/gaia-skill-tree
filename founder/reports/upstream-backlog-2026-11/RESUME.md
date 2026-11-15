# Upstream Backlog Campaign — Resumable Pause Handoff

**PAUSED by founder. No further work until the operator explicitly resumes. No merges of any kind.** This handoff is portable: an incoming orchestrator can continue from the Git state below without access to the private conversation or session. Preserve all worktrees and branches. Do not reset, discard, delete, or recreate them. The original dirty root checkout is off-limits.

## Current state and stop boundary

- P0 was completed internally on the integration branch previously; PR #2467 is already merged there. This does **not** authorize a merge to `main`.
- P1 repair candidate is built and pushed, but awaits an independent final Terra verdict. Latest Terra attempt `caae8998` was **CANCELLED**, exited **143**, and supplied **NO FINAL VERDICT**. Do not resume that attempt; do not infer PASS or FAIL from its cancellation. A previous independent Terra report had findings in non-suite compatibility classification.
- P2–P7 have not started. No real-runner `apply=false` observation has been performed after the current repair.
- No main merge, approval label, repository variable/write-switch change, closure, or merit/history mutation was performed. No campaign workflow dispatch is permitted while paused.
- Both feature PRs are OPEN/DRAFT and target the integration branch. Do not mark ready, merge, rebase, squash, or create another PR.

## Exact Git inventory

| Purpose | Branch | Worktree (optional local path) | Exact HEAD | PR |
|---|---|---|---|---|
| Integration; pre-existing P0 merge | `dev/upstream-backlog-2026-11` | May be available in an integration worktree | `bfed2d777b76448f6ede5d40e1a834050dff07d0` | PR #2467 already merged to this branch; do not merge onward |
| P1 feature candidate | `dev/upstream-backlog-watcher-2026-11` | `~/.gaia-worktrees/upstream-backlog-2026-11-p1` | `591264b3bc1d7607e1074411f1c0a77b541515d9` | [#2468](https://github.com/gaia-research/gaia-skill-tree/pull/2468), OPEN/DRAFT, base `dev/upstream-backlog-2026-11` |
| Contract/schema dependency | `schema/upstream-contract-2026-11` | `~/.gaia-worktrees/upstream-backlog-contract-2026-11` | `6bed0edf324d49e42cd8953351deaccaa733d22f` | [#2469](https://github.com/gaia-research/gaia-skill-tree/pull/2469), OPEN/DRAFT, base `dev/upstream-backlog-2026-11` |

The source-code candidate checkpoint is `591264b3bc1d7607e1074411f1c0a77b541515d9`; the schema checkpoint is `6bed0edf324d49e42cd8953351deaccaa733d22f`. This report and pause bookkeeping are a later **report-only** P1 commit; its SHA is intentionally not self-referenced here. Repair code is already pushed and does not depend on local uncommitted work.

Incoming Git procedure: fetch before resuming and verify the refs and exact heads. Do not trust default upstream tracking or implicit push destinations. For a future authorized feature push, use explicit refs, e.g. `git push origin HEAD:refs/heads/dev/upstream-backlog-watcher-2026-11`; never accidentally push to `main` or integration. Keep schema work on its named branch. No push is authorized while paused except this completed report-only handoff.

## Active roster and execution constraints

The incoming orchestrator may take over; the previous private lead/session is not required. Current intended roster:

| Role | Provider/model | Effort | Boundary |
|---|---|---|---|
| Lead/orchestrator | Sol `openai/gpt-6.1-sol` | xhigh | Current lead was Sol; any incoming orchestrator can own resumption |
| Small/admin worker | `worker-luna`, `openai/gpt-6-luna` | medium | Admin-sized bounded work |
| Standard worker | `worker-hydrogen-medium`, `antigravity/gemini-4-hydrogen` | medium | Standard bounded work |
| Sole current contract-repair role | `worker-sol-shared`, `openai-codex/gpt-6.1-sol` | medium | Opus is exhausted/retired; do not substitute another provider/model/effort |
| Independent reviewer | `reviewer`, `openai-codex/gpt-6.1-terra` | high | Must be independent of builder; prior attempt cancelled without verdict |

No fallback, retries, nested agents, or provider/model/effort substitution without explicit operator instruction. No turn cap; per-agent timeout 2h (7200000 ms); concurrency 1–4, bounded further by operator or actual harness capacity. Agent definitions must use `fallback_models: []` and `max_retries: 0`; installed resolver behavior can treat an empty per-call fallback list as unspecified and inherit profile defaults, so verify effective configuration rather than assuming it. General profile/read-bash is appropriate for non-authoring Terra command verification; review profile is read-only and lacks bash. Never use nested writers or parallel writers in shared checkout.

On authorized resumption, the new harness should plan and live-verify the roster and worktree/ref state as appropriate. Do not infer a probe passed merely from static configuration.

## Verification evidence — keep attribution precise

1. An earlier Terra review at source `93d4718cc14522109f767ccbbb02a36eb46c71c9` verified 23 suites, 254→0 errors, AgentDB 11→0; 1015 + 160 + 179 tests; parity and mirrors; and 869 protected files unchanged. It nevertheless had findings involving non-suite compatibility and was **not a final PASS** for the current candidate.
2. `worker-sol-shared` builder reported at current P1/schema candidate: all 320 eligible unfrozen records conform, 23 suites valid; 1015 required + 410 focused tests PASS; parity true; two non-suite CLI `--dry-run` probes and AgentDB safe dry-run passed with zero hash change; 869 protected files unchanged. These are **builder-reported**, not independent certification. Builder classified `ruvnet/v3-ddd-architecture` root `role: variant` as a structural role, not `evidence.role`; independent reviewer must confirm the classification. `google-deepmind/workflow-skill-creator` legacy author/notes timeline and that root structural role were the last recorded findings.
3. The current final Terra attempt `caae8998` was cancelled, exit 143, **no final verdict**. Candidate `591264…` / schema `6bed…` are not independently PASS.
4. No actual real-runner `apply=false` run yet. Full `gaia dev validate` is not claimed green: its 11/11 `scripts/validate.py` checks passed, but the whole command exited 1 because generated Class P `registry/named-skills.json` is absent. Do not generate it during this pause.

## Resume sequence (only after operator explicitly resumes)

1. Load `/gaia-orchestrator`, repository root rules, this `RESUME.md`, and the campaign controls. Verify current Git refs, PR state, worktree cleanliness, and roster/config. Preserve this pause state until an explicit resume instruction.
2. Independently review exact source `591264b3bc1d7607e1074411f1c0a77b541515d9` with schema dependency `6bed0edf324d49e42cd8953351deaccaa733d22f`. Re-execute/verify required tests and the reported 410 focused tests, parity, schema mirrors, 320-record/23-suite local validation, SAFE CLI probes, and protected-file hash preservation. Confirm the root `role: variant` classification rather than accepting builder interpretation. Do not repeat upstream/backlog/evidence crawls.
3. Only after independent PASS may an authorized operator consider real-runner dry-run with `apply=false`; require exit 0 and empty `unknownEvidence`. A `#2278` count/refusal or protected-contract conflict is a stop, not something to bypass. No workflow dispatch while campaign remains paused.
4. P2/F3a activation requires founder-set repository variables. All founder labels, L4 decisions, issue-hygiene writes, and main-merge gates remain intact. The current pause instruction explicitly says **NO MERGES**; this handoff does not renew merge authorization. Do not progress into later lanes without required operator/founder authorization.

## Canonical pointers and accounting

- [CAMPAIGN.md](CAMPAIGN.md) — control file and chronological history.
- [P1_CONTRACT_REPAIR.md](P1_CONTRACT_REPAIR.md) — bounded persistence-contract diagnosis and builder evidence.
- [P1_HANDOFF.md](P1_HANDOFF.md) — technical handoff and historical review receipts.
- [P1_BLOCKER.md](P1_BLOCKER.md) — current gate and preserved findings.
- [PREFLIGHT.md](PREFLIGHT.md) — roster/preflight history and controls.
- [COSTS.md](COSTS.md) — accounting checkpoints.

Campaign-complete usage/cost is **UNAVAILABLE** (parent-session/interrupt accounting gap); actual billing is unknown. `$4.907920` is **P0-only partial**, not campaign total. Do not retry the price tool, guess, extrapolate, or claim zero. No raw prompts, transcripts, credentials, private personal data, or sensitive session artifacts belong in this handoff. Optional retained Terra context `01a1e076-8adf-75c1-899d-93c7c7297971` may exist but is **not a resume dependency**; a fresh independent reviewer in any harness can review the uploaded Git state.
