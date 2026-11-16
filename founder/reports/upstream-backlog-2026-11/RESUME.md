# Upstream Backlog Campaign — Resumable Pause Handoff

**STOPPED AT FOUNDER GATE — #2278 refusal reproduced; P1 blocked; NO MERGES.** Actual run 43896669237 failed with exit 3 at source `fa6ca42ab8c56ded58f340165388a69ae1957a7a`. Preserve receipt at [P1_RUNNER_REPORT.md](P1_RUNNER_REPORT.md) and exact JSON. `EXECUTOR_PROMPT.md` requires stop/return to founder: no investigation, repair, monitoring, rerun, or P2–P7. Await explicit founder authorization for bounded #2278 repair before any code change or redispatch. Terra code PASS is not runner PASS/P1 completion. PRs #2468/#2469 remain OPEN/DRAFT. Preserve prior history/worktrees.

## Current state and stop boundary

- P0 was completed internally on the integration branch previously; PR #2467 is already merged there. This does **not** authorize a merge to `main`.
- P1 candidate is builder-delivered and remains awaiting an independent final Terra verdict on source `591264b3bc1d7607e1074411f1c0a77b541515d9` + schema `6bed0edf324d49e42cd8953351deaccaa733d22f`. Latest Terra attempt `caae8998` was **CANCELLED**, exited **143**, and supplied **NO FINAL VERDICT**. Do not resume that attempt or infer PASS/FAIL. Terra is running independently; this admin task makes no monitoring/polling or independent-review claim.
- P2–P7 have not started. No real-runner `apply=false` observation has been performed after the current repair. Terra PASS is recorded below and in CAMPAIGN.md; the exact P1 generic dry-run command is validated and **NOT YET DISPATCHED**.
- No main merge, approval label, repository variable/write-switch change, issue write/closure, or merit mutation is authorized or performed. No historical rewrites; the original P1 canonical CLI's `upstream_synced` and note provenance appends remain preserved. The contract repair and prior pause changed no registry or history. The reported 869-hash comparison is a **pre-contract-repair checkpoint**, not a comparison against original `main`. Current resumption does not authorize any workflow dispatch; P1 run remains behind Terra PASS.
- Both feature PRs are OPEN/DRAFT and target the integration branch. Do not mark ready, merge, rebase, squash, or create another PR.

## Current independent verification receipt (2026-11-16)

Terra PASS, no actionable findings, at source `591264b3bc1d7607e1074411f1c0a77b541515d9` + schema `6bed0edf324d49e42cd8953351deaccaa733d22f`. Actual independent commands: required watcher/workflow/CLI pytest **1015 passed**; requested two files `tests/test_named_persistence_contract.py tests/test_upstream_persistence_contract.py` **70 passed** (not builder's broader 410); parity 0 with both booleans true; inventory **320** eligible unfrozen named records / zero errors; **23** suites **254→0**; two non-suite safe CLI probes and historical AgentDB dry-run, zero writes; protected 869-file digest `fbe0843d2fcb303538918ed4ffe38b0898fcd096cf91b023548eb3cb8bdbe3d7`; mirrors, frozen checks, negative controls and diff checks passed. The digest checkpoint is pre-contract `1e7fcda223700cfbbe85cb790a1d55ed31b49fa0`, not original main. Root structural `role: variant` is not `evidence.role`; unknown fields remain rejected. Named-evidence `updatedAt` provenance was added by contract repair; no formula/rank/grade/Origin/Star Bar/gate/actor-approval implementation changed, and raw registry/history remained unchanged. Full `gaia dev validate` is not green/claimed: Class P generated index missing. Independent code review is not release approval.

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

## Current bounded continuation (operator resumed administration only)

1. Preserve the separate Terra review at pinned source `591264b3bc1d7607e1074411f1c0a77b541515d9` + schema `6bed0edf324d49e42cd8953351deaccaa733d22f`; do not monitor or poll it from this task. Wait for its independent PASS receipt before considering dispatch.
2. Exact prepared P1 generic runner command is recorded in [P1_HANDOFF.md](P1_HANDOFF.md). It uses workflow `.github/workflows/upstream-watcher.yml`, explicit ref `dev/upstream-backlog-watcher-2026-11`, `apply=false`, `child_mode=batch`, `staging=off`, `staging_bootstrap=false`, empty/false remaining inputs. It is **NOT DISPATCHED**. On an authorized later run, require workflow exit 0 and inspect artifact `upstream-watcher-report` (`generated-output/upstream-watcher-report.json`) for `unknownEvidence: []`; also verify no issue/registry writes. Any nonzero exit or unknown evidence stops.
3. This is not the P2/F3a bootstrap. That separate founder-controlled operation would use `child_mode=batch`, `staging=weekly`, `staging_bootstrap=true`, `apply=false` and require the repository variables and documented bootstrap gates. Do not perform it or set variables here.
4. NO MERGES remains binding. No labels, repository variables, issue writes/closures, ready status, other workflow dispatch, P2–P7, or founder-gated action is authorized. P2–P7 remain not started.

## Canonical pointers and accounting

- [CAMPAIGN.md](CAMPAIGN.md) — control file and chronological history.
- [P1_CONTRACT_REPAIR.md](P1_CONTRACT_REPAIR.md) — bounded persistence-contract diagnosis and builder evidence.
- [P1_HANDOFF.md](P1_HANDOFF.md) — technical handoff and historical review receipts.
- [P1_BLOCKER.md](P1_BLOCKER.md) — current gate and preserved findings.
- [PREFLIGHT.md](PREFLIGHT.md) — roster/preflight history and controls.
- [COSTS.md](COSTS.md) — accounting checkpoints.

Campaign-complete usage/cost is **UNAVAILABLE** (parent-session/interrupt accounting gap); actual billing is unknown. `$4.907920` is **P0-only partial**, not campaign total. Do not repeatedly retry the price tool against the missing old parent-session path or guess paths. An incoming new session may collect its own canonical telemetry, while retaining this historical gap and not claiming complete campaign billing. Do not guess, extrapolate, or claim zero. No raw prompts, transcripts, credentials, private personal data, or sensitive session artifacts belong in this handoff. Optional retained Terra context `01a1e076-8adf-75c1-899d-93c7c7297971` may exist but is **not a resume dependency**; a fresh independent reviewer in any harness can review the uploaded Git state.
