# Execution preflight — 2026-11-15

Campaign: November 2026 Upstream Backlog. Canonical control commit: `692b807e198d8940df58fef8b5aaef1dcc29bbac` (planning PR #2466).

## Current P1 builder/review state

Founder-authorized role reassignment and solo implementation are complete. `worker-sol-shared` returned PASS session `01a1e0e9-13d8-7165-8fcf-e7c16b4afe3f`, actual model `openai-codex/gpt-6.1-sol`, medium; lead verified actual model/effort records. Bounded schema repair, mirrors, persistence tests and watcher docs were delivered. Opus performed inspection only; no account billing/quota inference. Terra independent review is **PENDING**. Builder claims and tests remain BUILDER-REPORTED, not independently verified. Feature changes were merged only into the P1 feature branch for testing. Draft schema PR #2469 (`schema/upstream-contract-2026-11`) targets integration; P1 PR #2468 remains draft and depends on it. No real-runner dispatch, P1 completion, P2, writes, or release approval. This supersedes the old live-preflight-pending text below without deleting history.

## Authority and baseline

- Founder supplied the Sol / Terra / Luna / Hydrogen / Opus roster and a maximum concurrency of four in the execution instruction.
- Founder subsequently confirmed no budget ceiling and an available execution window; then explicitly changed `worker-opus` from Anthropic to Antigravity and directed: "proceed, no fallbacks. Pause only when credit limits are used up."
- This resumption does not manufacture any of the separately required approval labels, repository-variable changes, L4 decisions, issue-hygiene rollout verification, or final main merge.
- Remote `main`, checked with `git ls-remote` and then fetched, is still `9b4d9b98043140188f00b14d0ac8fa6bc02491b7`. No campaign re-planning is required. The supplied planning commit is one documentation commit ahead of that baseline.
- Integration branch: `dev/upstream-backlog-2026-11`, created at the verified baseline. Initial feature worktree: `dev/upstream-backlog-authority-2026-11`. The original dirty checkout is untouched.

## Resolved roster

Installed harness: `@parke.dev/pi-subagent` 0.8.0, backend `pi`. Lead identity comes from Pi's runtime environment; child identities come from their actual session model/effort records, not just persona files.

| Role / agent | Provider / model | Effort | Intended profile and permissions | Dispatch/read access | Timeout | Status |
|---|---|---|---|---|---|---|
| Lead / Sol | `openai/gpt-6.1-sol` | xhigh | Lead tools; code authorship delegated | Active lead session | Active founder window | PASS |
| Small worker / `worker-luna` | `openai/gpt-6-luna` | medium | general; read/bash/edit/write only as individually scoped | Non-mutating file-read probe passed | Probe 180s; work 1800s | PASS |
| Standard worker / `worker-hydrogen-medium` | `antigravity/gemini-4-hydrogen` | medium | general; read/bash/edit/write only as individually scoped | Fresh runtime/HEAD probe passed | Probe 180s; work 1800s | PASS |
| Escalation worker / `worker-opus` | `antigravity/claude-opus-5-5` | medium | general; read/bash/edit/write only as individually scoped | Fresh runtime/HEAD probe passed after founder provider change | Probe 180s; work 1800s | Historical PASS; **retired from this assignment** by founder reassignment |
| Current P1 builder / `worker-sol-shared` | `openai-codex/gpt-6.1-sol` | medium | isolated worker; scoped repair authoring only, not reviewer | Static config readback only; live preflight pending (not yet probed) | 7200s | **LIVE PREFLIGHT PENDING** |
| Independent reviewer / `reviewer` | `openai-codex/gpt-6.1-terra` | high | review; read/grep/find/ls; no authoring | Independent fresh-context file-read probe passed | Probe 180s; review 1800s | PASS |

Terra's read-only review persona cannot run shell tests. Required independent command re-execution will use a separately scoped, non-authoring Terra verification dispatch with explicit shell permission; review remains independent of the builder. A dry-run will precede that dispatch.

Actual probe sessions (local harness evidence, never uploaded as transcripts): Hydrogen `01a1dfe8-8bac-77b4-b387-0c9dfa4a64a1` and fresh `01a1e001-55c9-74ea-90fe-c81c033e347f`; Luna `01a1dfe9-4005-70f9-bd1f-322111f20df1`; Terra `01a1dfe9-3fe7-73f3-b768-4fd502283e71`; Antigravity Opus `01a1e001-f480-733b-9a6c-65ead05bfe31`.

## Initial stop and no-fallback remediation

The first Opus probe on `anthropic/claude-opus-5-5` failed with HTTP 401 `invalid x-api-key`. Despite per-call `fallback_models: []` and `max_retries: 0`, the harness inherited a profile fallback and attempted `antigravity/gemini-4-hydrogen:medium`, which reported unavailable/resource exhausted. Execution stopped before P0. No campaign code or registry data was written.

Inspection of the installed resolver established the cause: `policy.ts` treats an empty per-call fallback list as unspecified and inherits agent/profile defaults; `orchestrator.ts` attempts every supplied fallback even when retries are zero. The founder authorized Antigravity Opus and resumption without fallbacks. Supported agent-definition overrides were therefore applied to the four named campaign personas: `fallback_models: []` and `max_retries: 0`. The resolver preserves an agent-level empty list through nullish precedence; its retry loop consequently has exactly one attempt. No harness code or global profile defaults were changed. Explicit model, effort, empty fallback and zero retry parameters are also retained on dispatches. Failed-primary fault injection was not run; fresh direct probes succeeded without substitution.

## Dispatch and handoff controls

- At most four campaign children concurrently; use any lower effective machine capacity. Observed per-session cap is four, machine-wide cap sixteen; no capacity increase is authorized.
- One owner per write surface. Parallel writers require separate worktrees. The initial campaign checkout is already an isolated Git worktree; shared-mode single builders may use it only while the lead does not mutate its files.
- No silent provider/model/effort substitution, automatic retries, or nested delegation. Runtime-configuration failures are reported rather than bypassed.
- Handoff: PR URL, full commit SHA, repository-relative report, READY FOR REVIEW or BLOCKED; commands, actual results, limitations and next action. Harness sessions remain local; only sanitized summaries and measured usage enter campaign reports.
- Maximum two routine correction rounds per PR. No expensive escalation without scope/risk justification.

## Founder-approved execution timeout addendum — 2026-11-15

The founder authorized virtually unlimited execution within a two-hour per-agent timeout, with no turn caps. Configuration was set to `defaultTimeoutMs: 7200000` and `timeout_ms: 7200000` on each of the four named campaign agents. No turn caps were added. Existing no-fallback and zero-retry settings were left unchanged; no model/provider configuration was changed for this timeout. A dry-run verified the effective `7200000` ms timeout. This supersedes the initial 30-minute work/review timeout values above for subsequent dispatches only; the historical initial setup is retained as recorded.

## Canonical phase ownership

| Phase | Owner / mechanism |
|---|---|
| P0 | `/gaia-orchestrator`; existing Steward decision-record schema and issue-hygiene family-lock consumer |
| P1 | `gaia dev sync-upstream`; Upstream Watcher contract; reviewed CLI/watcher tests and real-runner `apply=false` |
| P2 | Watcher contract section F3a; founder sets repository variables; bootstrap dry run produces the shared census |
| P3 | Steward issue-hygiene proposal/closure machinery; approved manual free-record path; `/gaia-intake-close` only for applicable direct intakes |
| P4 | Canonical human umbrella approval workflow; `gaia dev sync-upstream`; Superpowers canary |
| P5 | Current CLI `freeze`, `update-named --github-link`, `rename`, with per-row structural proof |
| P6 | Conditional `prefill`/`assess`, human L4 packet, then `/gaia-full-pipeline`; no held GBrain work |
| P7 | `gaia dev docs`, plan section D checks, `build_docs.py --check`, independent Terra review, founder final merge |

Only the instructions applicable to the current phase are executed. Subsequent phase skills are loaded before use, not invoked speculatively. No evidence pipeline or generated-artifact rebuild has run.
