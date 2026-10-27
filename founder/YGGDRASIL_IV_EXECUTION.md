# Yggdrasil IV — engineering execution receipt

**Current control: Gaia is the primary mission; recovery tooling is a parked side lane.** The founder explicitly superseded the restart-first/no-new-Gaia-jobs sequencing: proceed with the full campaign using direct work or the roster, without waiting for Pi recovery installation. Read [the current checkpoint and priority override](YGGDRASIL_IV_RESTART_CHECKPOINT_2026-10-27.md) for active owners. The unaccepted Pi tooling remains uninstalled and is not a prerequisite for Gaia. [The delivery/review receipt](YGGDRASIL_IV_DELIVERY_REVIEW_2026-10-26.md) records the preceding deliveries and verification. Integrationfd4038a restores the previously accepted4b code tree after the audited routing repairPR#2160; no new feature acceptance is implied. [The crash-recovery receipt](YGGDRASIL_IV_CRASH_RECOVERY_2026-10-26.md) records the preceding recovery; [the second resume receipt](YGGDRASIL_IV_RESUMED_2026-10-26.md) records the preceding authorization. The [orchestration-pause checkpoint](YGGDRASIL_IV_ORCHESTRATION_PAUSED.md) remains intact as historical recovery evidence; this resume was not inferred from a delayed notification. Main, canonical, schema, issuer/security and visual/operational rollout gates remain held.

Governing issue: [RFC #2148](https://github.com/gaia-research/gaia-skill-tree/issues/2148).
Doctrine: [founder ratification](YGGDRASIL_IV_RATIFICATION_2026-10-25.md), `META.md`, `GOVERNANCE.md`.

## Campaign authority

The founder's full-implementation mission authorizes engineering, tests, staging and preview preparation across P0–P5. It does **not** authorize canonical schema publication/rollout, pilot selection or live standing changes, production trust/rank/evidence/Origin changes, final main merge, registry-wide rollout or RFC closure. Existing schema quorum and frontend/CLI visual review gates remain binding. Preparation is not publication.

The latest founder routing is Flash/Luna for economical scouting, routine review and bounded work; Terra for intermediate implementation and independent review; Sol for difficult architecture/integration. Parent implementation is permitted when it is the smallest effective path; use compact isolated assignments to conserve context, not orchestration for its own sake. Independent review remains required. Use explicit effort, no unapproved escalation or recursive delegation; preserve coherent tested checkpoints so a dropped worker does not trigger a tooling detour or lost work.

## Ground truth — 2026-10-25

- Integration: `dev/yggdrasil-iv`, created and pushed from `origin/main` at `b0f6d9e502369aea2ebebe13eed8d961675094bd` (v8.26.10 release commit).
- Ratification PR #2149 merged at `959e6f5da002bb7b34176efc4ed9452d449cf44a`; confirmed ancestor of baseline. Validate and Docs Cohesion passed at that ratification SHA. This is not a claim all guards ran at the later release SHA.
- Existing scheduled Upstream Watcher succeeded at baseline; a separate Upstream Approve run failed. That historical failure is not evidence challenge monitoring is implemented or working.
- Existing unrelated worktrees and untracked local `.pi/` operational directories are preserved, not staged.
- RFC technical review is historical evidence to reconcile, not current implementation authority. No canonical data or generated public artifacts have been changed by campaign initialization.

## Explicit resume and Frontier reconciliation — 2026-10-26

The founder explicitly resumed this campaign and added the [locked Gaia Frontier ruling](GAIA_FRONTIER_RULING_2026-10-26.md). This supersedes the pause instruction, not accepted engineering or outstanding gates. Keep #2148, aggregate #2151 and `dev/yggdrasil-iv`; no new umbrella or restart. **Frontier discovers; Meta evaluates; Steward maintains reactively; Governance decides.** Native challenger leads remain separate from ordinary `discovery-packet-v2` intake, which still requires real `SKILL.md` and L4 review. Targeted two-sided D8 monitoring follows independent admission, never a mere lead or semantic match.

Independent experimental support, authorized public challenge admission and canonical numerical action are separate decisions. The live issuer remains unavailable; a TEST resolver cannot satisfy that gate. Implementation cleanup must preserve historical truth and supported interfaces, and demonstrate which surviving owner supersedes a removed path.

The founder additionally authorized dependency installs or supported alternatives for environment problems, with code correctness taking priority. Try isolated dependencies first. If an environment issue remains at the end of the full run, provide a precise handover for the other agent before merge; do not waive validation or silently call blocked work complete.

## Dependency chain and workstream ownership

| Slice | Deliverable | Current branch / saved source | Status at resume |
| --- | --- | --- | --- |
| P1 calculation foundation | Opt-in corrections and explicit-context shadow evaluation; defaults preserved | `dev/yggdrasil-iv`, `4b73e6281` / #2156 | Accepted foundation; parent 277 regressions passed; no live scoring adoption |
| P0/P2 challenge proof core | Independent receipt binding, reversible technical status and history | `dev/yggdrasil-iv`, `6aa7aaaed` / #2155 | Accepted domain foundation; live issuer/admission unavailable |
| F0 Frontier discovery / native leads | Invocable mirrored skill, separate versioned lead contract, Meta/audit handoff and actual independent experiment | `dev/yggdrasil-iv-frontier-foundation`, initial `6b0b48b68` | Initial code locally committed; worker 22 tests; binding/provenance completion underway; independent invocation/review still required |
| Architecture consolidation | Retire proven redundant execution stubs, preserve compatibility and reusable primitives | `dev/yggdrasil-iv-curation-scaffold-cleanup` | Caller inventory completed; bounded removal assigned, not yet accepted |
| P1 corpus proof | Final-engine census and cause-classified impact, malformed-input and no-write proof | Saved `0dffcf96ed0a` | Preserved, not accepted; final independent inspection/replay outstanding |
| P2 durable reactive watcher | Fresh-state CAS, shared atomic packet outbox, stable dedupe, input/packet integrity; no outward discovery | `dev/yggdrasil-iv-watcher-transactional`, from rejected `77ab02a` | Correctness repairs assigned; old sequential fixture proof remains insufficient |
| P2 prerequisites / trusted source | Git ref containment, safe dispatch arguments, real protected approval provenance | `cli/yggdrasil-iv-ledger-containment`; `dev/yggdrasil-iv-watcher-workflow-hardening`; saved receipt `a3df0cbd9` | Small repairs resumed; receipt-source preparation still requires independent review and genuine issuer evidence |
| P3 evidence proposal | Immutable lifecycle core and separate held schema proposal | Schema `fa0ba3a9`; core `e7562341` | Independently reviewed source packaged; formal proposals/adoption held; raw-schema baseline errors disclosed |
| P3 canonical transaction foundation | Exact multi-file CAS, guarded provider seam, recoverable journal and rollback before CLI/timeline integration | `dev/yggdrasil-iv-canonical-transactions` | Bounded core implementation assigned; no general canonical CLI transaction/migration delivered yet |
| P4 coherent publication | Actual producer execution, semantic parity, bound inputs/runtime and two-root byte equality | Saved Sol `b21d39177`; `dev/yggdrasil-iv-publication-last-mile` | Parent replay failed only on missing OG rasterizer, no manifest; independent review found ambient-env activation gap; explicit-context fix assigned |
| P4 lifecycle UI | Native Explorer history/status coherence and desktop/mobile/focus evidence | Saved `70239bcee` | New image evidence preserved but not independently accepted; founder visual gate held |
| P5 release preparation | Full integration, actual operational coverage, pilot, impact/rollback and release checks | Aggregate #2151 | Not complete; four elapsed weekly comparisons, live pilot, rollout/main/closure held |

The Frontier lane is additive. It cannot displace corpus correctness, watcher durability, guarded CLI/dual timelines/migration/rollback, coherent publication or release verification. Saved code and worker tests remain distinct from independent acceptance.

Each code slice is independently reviewed before integration, lands by merge commit through a feature PR, and retains proof. No feature branch targets main directly. No production-default calculation correction is silently enabled by a shadow implementation.

## Verification ledger

Baseline at `b0f6d9e502369aea2ebebe13eed8d961675094bd`: `PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 python -m pytest -p no:cacheprovider tests/test_trust_magnitude.py tests/test_row_grading.py tests/test_curation_authority_map.py tests/test_benchmark_catalog.py tests/test_trust_freshness.py tests/test_calibrate_evidence_grades.py tests/steward/test_trust_calibration_regression.py` — **255 passed in 10.29s** (Android, Python 3.14.6). These baseline tests do not prove new Yggdrasil IV behavior. Worker self-reports are not independent review. Later receipts must name exact tested SHA and actual outcomes.

## Recovery and integration receipt — 2026-10-26

- PR #2150 integrated by merge commit `a9a4a624e`: execution baseline and stale Origin vocabulary alignment only. Aggregate draft #2151 targets main and remains held.
- Initial domain, engine, watcher and evidence-rehearsal tests did not prevent substantive independent-review findings. Only reviewed repaired SHAs may integrate; no acceptance inferred from worker self-report.
- Interruption left lost worker runs. Engine repair and challenge hardening survived as pushed commits; corpus/UI survived as local patches. Corpus patch contains stale engine and unwanted doc reversals, so recovery is selective. No lost result is treated as tested.
- Pre-existing case-sensitive GitHub repo matching defect discovered in actual Upstream Approve run `40184391633` is tracked as #2152. Focused fix `fc2b1d147` is under independent verification; no real upstream bootstrap/retry authorized.
- Approval/change-set digests are checksums, not authenticated founder approvals. Domain/rehearsal APIs must preserve that trust boundary.

## Release boundaries and outstanding evidence

1. Shadow time/freshness differences are review observations, not confirmed degradation. Four correctness repairs are `implementation-correction`, not evidence decay.
2. Four **weekly operational shadow comparisons** are required before autonomous expansion under the RFC. Virtual-clock fixtures do not establish elapsed operational coverage; this requirement cannot be silently compressed into a test run.
3. A technical challenge may resolve while approved numerical loss remains: public status must disclose recalibration pending. No challenge core receipt can authorize canonical numerical recovery.
4. A representative pilot must be proposed and approved before any live standing mutation. Registry-wide rollout and final merge require their own founder authorization.
5. No public product deployment, coherent-snapshot migration or release readiness is claimed by this initialization receipt.
