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
| **M0 Recovery** | Verified live baseline, fresh A/B/C census, executable queue, ownership and gates | **COMPLETE**: fresh receipt, inventory and safe one-debt queue verified below; first canonical repair run launched |
| **M1 First main promotion** | Accepted package reaches main through protected PR, or concrete evidenced blocker | **BLOCKED, source eligible**: frozen `2d9599c11…`, exact-head CI 17 success /2 skipped; effective main protection absent and shown CLI-warning approval pending. No main merge. |
| **M2 Routine 19 readiness** | Complete operational source integration, end-to-end/process/failure tests, independent acceptance and normal promotion; activation only within authority | Core independently accepted, #2296 draft; separate wiring writer active; NOT operationally ready |
| **M3 Batched elimination** | Several individually verified/canonically resolved debts delivered by proven repeatable compatible batching | Feasibility reconnaissance complete: singular packets/one dispatch; compatible delivery waves only. No batch-size/cap amendment inferred |
| **M4 Sustained delivery** | Repeating discover → classify → batch → dispatch → verify → integrate → promote → re-observe, with accurate blockers | Not established; only one B debt canonically resolved so far |

## Authoritative observations and accounting

**M0 fresh census: A=0, B=325, C=40, total=365, observed 2026-11-05 17:03:50Z.** Run `run-20261105T170320Z-d6eaa3cb` completed with receipt `steward-20261105T170350Z-4f8f0d6cc2fed42c`; coverage checker passed, zero unknown coverage, two optional inputs not evaluated. Three findings were created and the one explanatory-document self-match naturally resolved. This is **not net debt reduction** and does not add a B repair or authorize security-alert dismissal.

Fresh kinds: trust-calibration122; browser-sink61; swallowed-exception42; unused-import39; workflow-hygiene39; credential-pattern39; code-duplication5; issue-suite-review5; frozen-skill-drift4; unsafe-execution2; CI-failure2; frontend-contract2; benchmark-source1; ungated-mutation1; routine-PR-founder-decision1. B classification alone does not waive rank/L4/frozen/frontend or envelope gates. Original 39 credential-shaped paths remain positive and are not 39 established leaks.

Last completed canonical observation before recovery: run `run-20261105T071754Z-c2446531`, receipt `steward-20261105T071830Z-0b811d0cd0eade41`, recorded 2026-11-05 07:18:30Z: **A=0, B=323, C=40, total=363**. It observed 424 observations; absent optional browser/advisory inputs were not healthy.

Recovery observation **`run-20261105T170320Z-d6eaa3cb`** was active at the inventory snapshot **2026-11-05T17:08:11.866800Z**, and subsequently completed. Both real census collectors exited 0. The final result has no unresolved run work or actions. Snapshot activity below is historical, not a claim that the observation is still active.

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

Last assigned ownership (terminal notifications must still be collected before claiming completion):

| Lane | Owner / task | Source and authority |
|---|---|---|
| A canonical repair | shared Luna medium; `b13c9cb2d` | Run `run-20261105T172246Z-e34944e8`, build `build:638fb01c8655:1`, dispatch `dispatch-2beea7af972331dae185`. Separate worktree `steward-roster-burn-638fb01c8655`, exact branch `steward/b/unused-import-638fb01c8655`; only roster.py. No ledger, push, integration or self-verification. Lead records outcomes. |
| A queue + M3 | shared Luna medium; `b13b588a8` completed | Read-only feasibility delivered; no multi-debt envelope/cap amendment. |
| B Routine19 wiring | shared Sol MAX; `be87430e0` | SAME session/sole writer resumed after `bdc4219e2` ended PARTIAL. Preserved provider checkpoint `2614c9d20e9ab94d3539bf56882e34f81de62546` and nine WIP files; no final wiring proof existed. First slice's 22 builder tests are NOT whole-feature acceptance. No competing writer, reset or restart. |
| C promotion review | shared Sol high; `bc5df0b73` completed | Frozen source eligible; positive evidence of ineffective main protection plus CLI human gate. Main-PR CI subsequently completed successfully. No merge authority delegated. |
| Non-Steward review-page helper | Flash low; `b5dcb87b3` | Only isolated ignored `.pi/probes/steward-main-gates-2283/index.html`; two unselected founder decision cards, no network/state execution. Parent serves only that directory, never raw campaign evidence. |

Maximum four concurrent agents. Canonical Steward builders/verifiers use explicit `openai-codex` shared routes, no fallback. Latest founder instruction permits Flash for non-Steward work, including bounded Routine19 engineering; that does not require changing or duplicating an existing writer. Current wiring owner remains shared Sol MAX; the local HTML helper uses `antigravity/gemini-3.8-flash` LOW. Different worktrees/files for independent ownership; reviews do not mutate candidate source.

## M1 concrete founder gates

Independent review found no new source correctness/security defect. Exact frozen-head #2297 checks: **17 SUCCESS /2 irrelevant SKIPPED**, all completed. This clears the earlier missing-CI item, not the two remaining gates:

1. Fresh accessible GitHub reads show main `protected:false`, effective branch rules HTTP-success `[]`, and active Main Ruleset **18124772** with empty `conditions.ref_name.include` and `exclude`. Configured checks are therefore not effective main protection. No admin/settings mutation is authorized merely by conditional promotion authority. Proposed narrow founder decision: include only `refs/heads/main`, retain existing rules, strict checks, active enforcement and no bypass actors; then verify effective protection.
2. Founder CLI-output review is pending for additive ledger warning. Synthetic message-level comparison: before, no telemetry warning; after, `Steward ledger size telemetry: direction=read bytes=6291456 limit_bytes=8388608 percent=75.0 threshold=70%`. This is not a successful old-main 6 MiB read or terminal screenshot. Old cap was 1 MiB.

Two decisions are being prepared as one local HTML review-page fallback (no Artifact tool); no options preselected and choices do not execute anything. Record founder choices verbatim before acting. Neither decision authorizes archive/Routine19 activation, registry/trust/L4 changes, release or deployment. Existing `[skip-gen]` generation guard can keep source-only delivery from unapproved auto-regeneration/release/deploy without bypassing required CI. Re-read current main/head/checks/protection before any normal merge; no override/unprotected merge.

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
- **#2296 / Routine19:** core accepted at `6b914723…`, tests373 and fresh independent boundary tests11; exact-head CI 11 SUCCESS /2 irrelevant SKIPPED, not yet integrated/promoted. Core remains dormant; separate unpublished wiring is partial at provider checkpoint `2614c9d20…` plus WIP. No whole-feature/provider/rollout acceptance follows from the core's acceptance. Prototype 512 KiB fits roughly 11 real full-proof records; ongoing minimal wiring must address bounded capacity honestly without pruning proof/reviving archive. No namespace provisioning, time-trust/append-only protection verification, old-writer draining or live operation is claimed.
- Existing trust/rank dispatches blocked/escalated stay blocked; no reset/retry to evade attempt ceilings or L4/data authority.
- Browser-render/advisory absence is not health. Coverage unknown blocks A; optional not-evaluated is reported.
- Main promotion requires actual eligible diff, protected checks and any genuine human gate; record concrete blockers, do not wait for unrelated infrastructure.
- Verification-only v9.3.0 audit remains lower priority; no release publication/promotion authority.

## Exact next actions

1. M0 completed: retain fresh inventory and receipt above. Do not merge PR/dispatch counters with debt closure counters.
2. Drive the launched canonical run for `debt:unused_import:src-gaia-cli-steward-prmaintenance-roster-py:0d3bca3f7369f4af` (unused timezone; all observed findings sideEffectPossible=false). The emitted packet has been read and shared Luna builder assigned. Collect its exact diff/proof/head and runtime identity, record the canonical build through the CLI, then dispatch a distinct verifier using the emitted verifier prompt. Integrate only accepted work. No raw state edits, self-verification, rank/curation or forbidden-path expansion. Many other unused-import rows contain sideEffectPossible=true or intentional public re-exports and are not interchangeable safe targets.
3. Main review and exact-head CI are collected; M1 is blocked on effective main protection and the warning presentation approval above. Present the two-card founder page, retain normal protected-PR gates, and continue lane A while waiting. Verify resulting main source. Keep incomplete R19/archive off the promotion head.
4. Finish the existing Routine19 writer's minimal complete source; independent end-to-end, process/crash/recovery, clock/authority/storage/kill/comment tests before promotion/activation claims. Do not let this suspend lane A.
5. Initial M3 finding: packets are singular-debt and unused-import envelopes require one subject file; maxDispatchesPerRun=1 remains. Do not invent a multi-file diff/aggregate packet or loop starts to evade the cap. Existing legal delivery batching may group separately completed and individually verified canonical repairs into a frozen main-promotion wave. A true multi-dispatch/multi-debt repair pilot needs an explicit bounded amendment; prepare that decision only after first measured safe delivery, without suspending current legal repairs.
6. Repeat canonical repair → verification → integration → protected main promotion → re-observation. Record per-debt IDs/run/batch/PR, acceptance/rejection, timestamps and blockers. Refresh this checkpoint at each meaningful milestone and before handover/compaction.

## Required metrics

Maintain a simple append-only delivery table here: run/batch, debt IDs, exact build/verifier/merge heads, canonical resolution receipt/time, main commit/time, acceptance/rejection and blocker. Count separately: canonical closures; source packages; main deliveries; actionable/blocked inventories; throughput/time to main; infrastructure time versus repair work. No new orchestration framework is required.

| Run / batch | Canonical result | Integration / main delivery |
|---|---|---|
| `run-20261104T191141Z-c3a4df1e` | One unused-import debt resolved, exact ID/receipt above | #2289 integration; main pending M1 |
| Recovery `run-20261105T170320Z-d6eaa3cb` | Completed: A0/B325/C40; one explanatory-document signal naturally resolved; 3 created | Not a repair batch; no new B closure |
| Roster `run-20261105T172246Z-e34944e8` | Awaiting build outcome; Luna `b13c9cb2d`; debt `...roster-py:0d3bca3f7369f4af` | No new closure/integration/main claim yet |

Detailed temporary evidence remains in ignored `.gaia/steward/campaigns/2026-11-05/`; durable decisions and milestone receipts belong in this versioned checkpoint and #2283. Keep sensitive raw snapshots and process/session logs out of public reports.
