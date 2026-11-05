# Gaia Steward Full — governing campaign checkpoint

Tracking: [#2283](https://github.com/gaia-research/gaia-skill-tree/issues/2283). Lead: **Sol High**. Environment: **Pi / Termux**.

**After compaction, read this checkpoint before reprioritizing.** Then refresh the live ledger, this issue and active ownership. Do not restart an existing writer or infer a debt closure from a merged PR.

## Permanent mission

Systematically eliminate currently authorized actionable technical debt, with measurable canonical resolution and incremental protected main delivery. Infrastructure is an enabler, never the replacement objective. Seven engineering packages are **not** seven canonical debt closures. Do not declare success because tools are complete.

Maintain three productive lanes:

- **A — burn-down:** canonical Class A/B repairs wherever current authority permits. Prioritize impact, risk, dependencies and achievable throughput. Start safe work without waiting for unrelated Routine 19 or archive work.
- **B — minimum infrastructure:** finish the smallest complete safe Routine 19 shared critical-write route. Ordinary observations/noncritical state remain checkout-local. No indefinite architecture program.
- **C — assurance/delivery:** independent per-debt verification, safe integration and a recurring protected main promotion train. Frozen promotion branches must exclude rejected/parked/incomplete work.

No competing shared-ledger writers. Lead alone performs real canonical mutations. Respect CAS, run leases, idempotency, maxDispatchesPerRun=1, maxInFlight=2, maxAttempts=2 and cooldown=3600s. Investigate batching without silently changing these bounds or widening an envelope. Builders never verify themselves. Required checks/protection and explicit founder holds always apply. No disabled write path is bypassed.

## Milestones and exits

| Milestone | Required exit | Current state |
|---|---|---|
| **M0 Recovery** | Verified live baseline, fresh A/B/C census, executable queue, ownership and gates | **IN PROGRESS**: precheck and ledger inventory captured; fresh censuses/observation active below |
| **M1 First main promotion** | Accepted package reaches main through protected PR, or concrete evidenced blocker | Frozen candidate `2d9599c11…`; independent promotion review active; no campaign main promotion yet |
| **M2 Routine 19 readiness** | Complete operational source integration, end-to-end/process/failure tests, independent acceptance and normal promotion; activation only within authority | Core independently accepted, #2296 draft; separate wiring writer active; NOT operationally ready |
| **M3 Batched elimination** | Several individually verified/canonically resolved debts delivered by proven repeatable compatible batching | Feasibility investigation active; no batch-size/cap amendment inferred |
| **M4 Sustained delivery** | Repeating discover → classify → batch → dispatch → verify → integrate → promote → re-observe, with accurate blockers | Not established; only one B debt canonically resolved so far |

## Authoritative observations and accounting

**Fresh recovery census is pending. Do not treat historical 363 as current.**

Last completed canonical observation before recovery: run `run-20261105T071754Z-c2446531`, receipt `steward-20261105T071830Z-0b811d0cd0eade41`, recorded 2026-11-05 07:18:30Z: **A=0, B=323, C=40, total=363**. It observed 424 observations; absent optional browser/advisory inputs were not healthy.

Current recovery observation: **`run-20261105T170320Z-d6eaa3cb`**, mode observe, active at inventory time **2026-11-05T17:08:11.866800Z**. Real issue/PR censuses were refreshed before it; exit/completeness and final receipt must be checked before M0 is marked complete.

Live shared ledger inventory at that instant: version `eff543ba69819f0075a3f9789fefa6209a8ffff1`, **1,307,094 bytes**, 16 runs = 9 completed /6 abandoned /1 active. This is comfortably below the accepted **8 MiB** ceiling; no measured capacity blocker justifies archive resumption. Before starting recovery: no active run, holder or dispatched item. Historical lane counters queued162/escalated2/closed27 are **not debt closure totals**. Seven canonical work records: resolved1/escalated4/blocked1/no_change1.

**Correction to the earlier context-only run receipt:** live ledger identifies `run-20261104T164940Z-0b88036f` as completed observe; the abandoned failed repair run is separately `run-20261104T165527Z-2a808cf3`. The prior compacted account incorrectly conflated them. The completed B repair run is `run-20261104T191141Z-c3a4df1e`; the later observe run is `run-20261105T071754Z-c2446531`. Recovery adds the fifth identified campaign run above; inherited runs are not added again.

Only canonically resolved campaign repair so far: `debt:unused_import:src-gaia-cli-steward-issuehygiene-reconcile-py:d91a57958d7d1622`, resolved by receipt `steward-20261104T235018Z-ca81d01b42dd6c46`. No operational Class C adjudications are claimed. Fresh per-debt reconciliation must distinguish newly introduced/rediscovered/resolved signals from genuine verified repair delivery.

## Integrated versus main-promoted

Integration: `dev/steward-campaign-2026-11-05`, head **`2d9599c11ea91f303b5067c39fb8ea272f119072`**, tree `9b29681b44be112306f8502961f4e67787492d97`.

Fresh main at recovery precheck: **`31b407db65c4e138896780a7319e4a4ce76884eb`**. Main/`8ad344a49926821d2c1b6d4e021b8de6f653649c` are preserved ancestors of integration. No campaign package has yet been promoted to main.

Seven principal integrated packages:

1. #2284 — accepted 8 MiB persistence, bounded configuration, retained history.
2. #2289 — canonical unused-import repair (one real B closure).
3. #2291 — narrowly scoped canonical branch CI repair.
4. #2292 — security source/provenance reconciliation; no blanket clearance.
5. #2293 — founder/watcher identity, counts, locks and source guard fixes.
6. #2294 — one explanatory prose self-match corrected; historical proof preserved/current binding refreshed.
7. #2295 — normal main/campaign preservation join; whole-source independent ACCEPT and applicable CI passed; 120 fresh completion tests, with earlier overlapping groups not summed.

Earlier #2282 initial closeout is separate historical receipt. These PR counts are not canonical debt-closure counts.

M1 promotion must freeze the accepted head on a dedicated branch, not use a mutable integration head. Exclude #2287 archive, #2296 dormant core and ongoing wiring. Revalidate main, exact-head independent review and all required main-PR checks. Normal merge only; no direct/force push, admin override, gate/label bypass or manual release/deploy. The founder's campaign directive authorizes evaluating and normally promoting eligible accepted packages; concrete repository approval/protection gates remain mandatory.

## Active ownership — no duplicate writers

| Lane | Owner / task | Source and authority |
|---|---|---|
| A recovery | Lead Sol High; `b490fa93d` | Real canonical census/observe only. Lead owns global ledger mutations. |
| A executable queue + M3 | shared Luna medium; `b13b588a8` | Read-only queue/envelope/batching investigation. Not a canonical dispatch; cannot alter ledger or manufacture repairs. |
| B Routine19 wiring | shared Sol MAX; `bdc4219e2` | Existing writer, do not restart. Worktree `steward-r19-shared-write-2283`; unpublished integration of core/provider/executor/gate/CLI/runner/local defaults/contracts. |
| C promotion review | shared Sol high; `bc5df0b73` | Independent read-only frozen accepted-head/main eligibility review. No merge authority delegated. |

Maximum four concurrent agents; use remaining slot for an actual canonical builder/verifier when its packet is available. Different branches/worktrees for independent code ownership. Review-only work never mutates a builder's files. All new agent routes explicit `openai-codex` shared personas; no fallback. Parent lead observed `openai/gpt-6.1-sol`, high.

## Locked founder decisions

| ID | Binding decision |
|---|---|
| **C1 Ruflo / AgentDB** | Ruflo canonical parent/capstone, AgentDB legitimate nested suite. Preserve both; watcher identity/version metadata reconciled as B, no hierarchy restructuring. Technical source fixes do not prove canonical metadata or live recovery. |
| **C2 Addy Osmani** | Canonical GitHub identity `addyosmani`, no dash. Broad registry migration deferred for compatibility planning. |
| **C3 GBrain** | Curation deferred to dedicated session. Preserve child issues, provenance and review gates; no automatic acceptance. |
| **C4 Copilot workflows** | No Copilot billing dependency. Manual-only, disabled by default; verified fail-closed threat detection required before separately authorized activation. Source guard work is not compiled/engine/live evidence. |
| **D1 Mirrors** | Latest verified compatible scripts win, synchronize Codex/Claude copies and deduplicate references while retaining provenance. Ordinary mirror drift is A/B, not a new C question. |
| **D2 Fixtures** | Preserve legitimate synthetic credentials and test coverage. Remediate verified real exposures, not pattern matches by assumption. |
| **D3 App security** | All nine application findings, including auth.py/securityScanner.py/jev.py, require evidence-backed investigation. Existing independent assessment is scoped; no blanket dismissal. |

D1–D3 cover **39 original paths /71 occurrences**, not 39 established leaks. Existing accepted classification/provenance evidence is preserved. No indiscriminate issue closure, security-alert dismissal, deferred intake acceptance, trust/rank mutation or workflow activation. Issue-hygiene write opt-in remains false. Preserve corrected hygiene and investigate #2278 without calling source repairs live recovery.

## Parked and blocked work

- **#2287 stays parked/unmerged.** Actual archival DoD open; no broad archive implementation, migration, new profile or manufactured settlement. Remaining local guard history-consistency rejection preserved. Archive is not a dependency of safe A/B repairs.
- **#2296 / Routine19:** core accepted at `6b914723…`, tests373 and fresh independent boundary tests11; exact-head CI completed, not yet integrated/promoted. It remains a dormant module with no production Services. Prototype 512 KiB fits roughly 11 real full-proof records; ongoing minimal wiring must address bounded capacity honestly without pruning proof/reviving archive. No namespace provisioning, time-trust/append-only protection verification, old-writer draining or live operation is claimed.
- Existing trust/rank dispatches blocked/escalated stay blocked; no reset/retry to evade attempt ceilings or L4/data authority.
- Browser-render/advisory absence is not health. Coverage unknown blocks A; optional not-evaluated is reported.
- Main promotion requires actual eligible diff, protected checks and any genuine human gate; record concrete blockers, do not wait for unrelated infrastructure.
- Verification-only v9.3.0 audit remains lower priority; no release publication/promotion authority.

## Exact next actions

1. Collect the recovery observation, verify census completeness and coverage, save authoritative debt inventory/receipt/version, update this checkpoint with fresh A/B/C by kind and timestamp. Do not call M0 complete from a successful process exit alone.
2. Select an executable A/B target from the fresh queue and canonical envelope. Start immediately under existing limits, assign one builder, then a distinct verifier; record actual outcomes through canonical CLI. No raw state edits, self-verification, rank/curation or forbidden-path expansion.
3. Complete frozen accepted-head main promotion review and main-target PR CI; perform normal eligible promotion or document the exact blocker. Verify resulting main source. Keep incomplete R19/archive off the promotion head.
4. Finish the existing Routine19 writer's minimal complete source; independent end-to-end, process/crash/recovery, clock/authority/storage/kill/comment tests before promotion/activation claims. Do not let this suspend lane A.
5. Pilot compatible batching only when envelope and per-debt receipts permit it. If dispatch batching needs a founder-reviewable amendment, report the concrete constraint and continue legal repairs; no cap circumvention/new orchestration framework.
6. Repeat canonical repair → verification → integration → protected main promotion → re-observation. Record per-debt IDs/run/batch/PR, acceptance/rejection, timestamps and blockers. Refresh this checkpoint at each meaningful milestone and before handover/compaction.

## Required metrics

Maintain a simple append-only delivery table here: run/batch, debt IDs, exact build/verifier/merge heads, canonical resolution receipt/time, main commit/time, acceptance/rejection and blocker. Count separately: canonical closures; source packages; main deliveries; actionable/blocked inventories; throughput/time to main; infrastructure time versus repair work. No new orchestration framework is required.

| Run / batch | Canonical result | Integration / main delivery |
|---|---|---|
| `run-20261104T191141Z-c3a4df1e` | One unused-import debt resolved, exact ID/receipt above | #2289 integration; main pending M1 |
| Recovery `run-20261105T170320Z-d6eaa3cb` | Observation pending at this checkpoint revision | Not a repair batch |

Detailed temporary evidence remains in ignored `.gaia/steward/campaigns/2026-11-05/`; durable decisions and milestone receipts belong in this versioned checkpoint and #2283. Keep sensitive raw snapshots and process/session logs out of public reports.
