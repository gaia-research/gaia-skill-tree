# Yggdrasil IV — restart checkpoint NOT ready (2026-10-27)

## Current control

Founder asked to be told when to reset and then explicitly said **Continue**. Continue the safe Pi recovery-tooling repair; **do not issue READY TO RESTART yet**. No additional Gaia campaign jobs before this restart window. This is temporary execution sequencing, not a campaign restart, permanent pause, completion claim or waiver of the original mission.

All previously assigned Gaia implementation workers, independent reviews and parent shell tests are now terminal and collected. The old tooling review's assertion that publication task `ba7cb70f5` remains live is stale. The first Pi repair and lifecycle scout are also now collected. That subsequent review and first actual-SDK probe are now also collected. Product repair2 is now also collected. Independent78b review is now collected and REFUTED. Actual-SDK continuation is now collected and remains RED on transcript preservation. Current work is complex safety implementation and the corrected isolated parent regression retry; the SDK verifier waits for exact replacement source before resuming.

## Campaign state safely saved

- Integration **`fd4038afb9a34062ca993a4eb0878e0464cfe564`** has exactly the accepted `4b73e6281` code tree after audited restoration PR #2160; main remains `b0f6d9e502369aea2ebebe13eed8d961675094bd`. No canonical trust/schema/standing/Origin or security activation occurred.
- Watcher **`d311d9624f0072d17b270f970733d89535e3926c`**: parent complete watcher+ledger suite **231 tests passed in 64.50s**, unchanged tracked/nonignored source inventory. Independent full 15-file review **conditional pass/no P0/P1**, including actual process/CAS, recovery/tamper/preservation/dedupe and workflow probes. Unmerged; live issuer unavailable; audited legacy v1 migration and elapsed operational gates still required. Evidence copied under `.gaia/yggdrasil-iv/recovery/watcher-d311-parent-evidence/`.
- Publication **`36883266812824dc49de48ffe1bda757d22d45ce`**: **323 regressions passed in 122.66s**, but actual full-corpus first build failed strict OG PNG coverage after 541.79s; no second replay or certified snapshot. Source unchanged. Runtime-proof P1 in independent report is challenged by actual outer-bootstrap source and a counterprobe rejecting runtime mismatch; don't blindly change a correctly fresh outer check. Real coverage failure remains. Evidence under `publication-368-parent-evidence/` and `publication-368-runtime-gate-counterprobe.json`.
- Transaction foundation **`e183246809486faec6b3d1016480291e0575e575`**, draft PR #2161: independent review **REQUEST CHANGES**. `_hash` at `canonicalTransaction.py:61` treats absence as literal `b"<absent>"`, colliding with a present file containing those bytes. Actual probe prepared a create plan, introduced that file, and apply overwrote it rather than raising CAS conflict. Fix with unambiguous domain separation and a regression before acceptance. Existing 8 tests passed; actual two-process lock/pending-guard probe passed. This does not validate the defective CAS or provide unlocked-reader linearizability. No CLI writer wired; no production issuer.
- Corpus draft PR #2159 at **`cc1c3e1735e95a44df94d59145e4b7d5638bcc61`**: README-only CLI generated-reference fix atop tested/reviewed `b6103d7bd`; no merge or visual approval inferred. Original324-test/no-write/independent proof retained.

These remaining defects stay in the original campaign queue for after the restart checkpoint, not follow-up debt. Older recovery WIP/bundles and unrelated `.pi/` remain untouched. See [the delivery receipt](YGGDRASIL_IV_DELIVERY_REVIEW_2026-10-26.md) for routing repair and historical captures.

## Pi tooling: failed candidate remains uninstalled

Source **`ea0baf70df532e8d3f38cf041d903a443e963f9a`** on `feat/durable-subagent-recovery` is preserved remotely, not accepted. Parent verified live extension absent and pi-config master unchanged at `0e4f0c86aeaf8c5fd1b2d9c42ee5ff861cd254da`. Feature upstream is unset despite author report; use explicit feature refs, never master.

Independent Flash review **REFUTED deployment**. Report: `~/.pi/durable-recovery/independent-review.md`. Concrete reported blockers to reproduce and repair:

1. Actual SDK event ordering / async receipt handling leaves native run/PID/session correlation absent, so final completion cannot update the right job.
2. Marking native records `state=terminal` avoids one cleanup but removes busy-session/live-worktree protection from maintenance.
3. Generated resume calls omit required `task`; real native policy rejects them.
4. Unknown/permission-denied liveness can acquire resume leases.
5. Corruption rotates to empty DB and discards active safety/lease state.
6. Startup does not actually preserve full sessions before pruning; helper-only tests do not prove the actual native lifecycle.
7. Installer/rollback lacks required atomic deployment and hash-conflict safety.

Do not blindly apply every reviewer suggestion: native IDs here are UUIDs, not necessarily `run_...`; a fabricated `protected` field is ineffective unless real native code honors it; shared-state root semantics must match actual installed tooling. The assertion that full Termux restart is necessary is **not established**. Test actual SDK reload behavior; a fresh Pi process is narrower than restarting unrelated Termux processes.

## Current tooling assignments

| Owner | Run | Source / output |
|---|---|---|
| Flash High implementation repair | `72a32019-ccd0-4d2a-9f1d-59b9ef9a1170` | Existing `~/.pi/worktrees/pi-config-durable-recovery`; output `~/.pi/durable-recovery/repair-result.md` |
| Flash Medium read-only native lifecycle design | `d0ccf113-6088-4a6d-b77e-319f0a81973a` | Frozen `~/.pi/worktrees/pi-config-durable-review`; output `~/.pi/durable-recovery/native-lifecycle-design.md` |

Repair continues existing source, not a fresh implementation reset. Preserve early tested commits, recovery refs and explicit feature push/fresh remote confirmation. No nested agents, package upgrades, live vendor patches, config changes, signals to real workers or reloads are authorized in this repair phase. Own synthetic processes in fully isolated tests are allowed. If unavoidable, stage a narrow version/source-hash-guarded compatibility patch for independent review; never silently patch live vendor code.

Prefer supported mechanisms or honest logical recovery over fighting native lifecycle with false states. Require actual SDK/event/async binding, native cleanup/distillation/worktree tests, policy-valid absolute-path recovery, identity/unknown-state safety, lease handoff/expiry, fail-closed corruption with DB/WAL/SHM preserved, privacy/bounds/migration and atomic hash-safe installer/rollback. WAL/FULL alone is not lossless admission, process resurrection or external exactly-once proof.

### Latest: genuine SDK recovery failure; regression harness correction

Actual-SDK continuation **eeb5ed78** is **partial/collected**, not active. It saved clean test commit **`899fec56dda93b721ca011362800558a8e5d3be3`** on `test/durable-recovery-real-sdk`. It now genuinely exercises real Pi CLI child/session, counted localhost transport, pinned child settings/read-only tools, native completion, synthetic parent SIGKILL, fresh SDK startup/native reconciliation, SDK-authored transcript loading/distillation and manual cross-CWD native resume. **Automatic product preservation remains RED** against baseline and frozen78b: native record is already terminal/orphaned-dead before the recovery handler, and neither product preserves the transcript. Manual resume uses a separately identified operator copy, not proof that product recovery works. Frozen78b retains route fields; branch baseline loses them. Stock Android native startTime0 remains. Report: `~/.pi/durable-recovery/actual-sdk-proof-continuation.md`; exact commands/limits in test branch `tests/ACTUAL_SDK_SUBAGENT_RECOVERY.md`.

Safety implementer **4582923b** has these real failing fixtures and must fix ordering/actual metadata binding, not merely claim startup capture in helper tests. The verification author will continue only after an exact coherent replacement commit/patch is available; do not leave an idle model waiting or treat partial as accepted. Guarded fixture runs detected no global content-hash changes; an earlier unguarded settings watcher event remains unattributed. No blind restoration.

Parent regression task **b36a02e4e** is terminal **FAILED**:95tests,1failure/1error/1skip,14.678s, tracked source bytes unchanged. Errors were ENOENT executing existing `#!/usr/bin/env` scripts (new installer and mock codex). Parent isolated harness had stripped essential Termux **LD_PRELOAD**. A controlled separate Python-process probe reproduced ENOENT without that platform shim and `SHEBANG_OK` with it, without source or assertion changes. Evidence: `~/.pi/durable-recovery/termux-exec-probe-20261027T055345Z/result.json`. This harness correction does not waive real software defects or the Android startTime bug.

Retry task **`b5e99e731`** runs the same frozen78b full Python discovery with platform-only environment preserved (including Termux exec shim), provider credentials cleared, isolated HOME, byte/mode source inventories. Operational runner: `~/.pi/durable-recovery/run-parent-regressions.py`; results under `parent-78b6310-platform-regressions-*`. Collect terminal output before any claim of green. One installed-Pi loader skip under the isolated HOME is disclosed, not a full SDK acceptance.

Current model worker: **Luna High safety implementation4582923b** in the new safety worktree. Actual-SDK verifier/eeb and independent reviewer/6f are both finished/collected. Still no installed extension, applied native patch or READY TO RESTART.

### Earlier: repair2 refused; complex safety repair and concrete exploit

Independent review **`6f05b8b5`** returned **partial/source-level REFUTED**; no tests run by that reviewer. Report `~/.pi/durable-recovery/independent-review-78b.md` confirms:

- Staged Android compatibility treats unknown live legacy identities as dead, permitting destructive native cleanup.
- Startup converts unknown/unverifiable liveness to `interrupted`; claim only rechecks `running`/`resuming`, making that unknown live worker claimable.
- Lineage binds during observational event admission, with no valid reservation owner/token/expiry check, before successor admission/native dispatch. Suffix `LIKE` lookup is ambiguous; pre-launch crash can permanently strand the predecessor while leaving queued successor state.
- Installer and doctor `eval` assignments derived from manifest text. Retained preimage contents/mode are not verified.

Parent independently **reproduced actual installer shell execution** against frozen78b: isolated first install, crafted manifest backupPath with benign command substitution, same-version reinstall exits0 and creates a private marker. Evidence `~/.pi/durable-recovery/manifest-eval-probe-78b-20261027T054547Z/{crafted-manifest.json,first.log,second.log,result.json}`. All install paths were isolated; live extension remains absent and native SHA remains stock5cf89e…b2702. This is concrete negative runtime evidence, not model agreement or positive deployment proof.

Complex implementation now moves to authorized **Luna High** rather than another Flash patch round. Existing Flash work/history remains preserved:

| Owner | Run | Scope / output |
|---|---|---|
| Luna High safety implementation | `4582923b-05dc-41b0-b610-ddd6211c7ede` | NEW permanent `~/.pi/worktrees/pi-config-durable-safety`, branch `fix/durable-recovery-safety` from78b; unknown/claim state, exact reservation/lineage pre-dispatch atomicity, safe structured manifest/preimage handling, conservative Android identity/cleanup patch; `~/.pi/durable-recovery/safety-repair-result.md` |
| Resumed Luna actual-SDK verifier | `eeb5ed78-9a98-4449-85cc-df47494ee57d` | Continues its separate test branch; genuine child/session/completion/crash/native-resume proof, not manual callback simulation |
| Parent isolated Python regressions | task `b36a02e4e` | Original78b feature worktree stays FROZEN until collected; no competing product edits there |

Source-only review findings must gain composed regression proof. Unknown/dead/pending launch remain distinct; reserve/consume exactly once before actual native side effects using a real blocking hook, not unawaited event observation. No automatic replay of ambiguous launches, no stale/foreign claim, no manifest `eval`, no unverified backup. Native unknown must not signal OR prune live state; boot/reuse/permission safety and real Android behavior need actual tests. No full Termux restart is required; activation remains held until reviewed installation and verified checkpoints.

### Earlier: repair2 saved; independent native-safety gate

Product repair2 **`78b63102fa64867cc2b7cb9edfe6f198d87b1b87`** is clean and matches the fresh feature remote, through coherent ec6b39f/02f12e3/b342023/78b6310 commits. Master still0e4. Author reports18 Node/helper tests,3 mock-contract subtests and3 Python tests passing. Claims include schema2 execution pins/support matrix, transactional predecessor/successor lineage, preimage preservation, removal of automatic quarantine and truthful docs/mock labels. **Not independent acceptance or SDK recovery proof.**

The speculative detached-mode patch was replaced by an **unapplied**33-line Android/proc safety patch. Parent inspected its actual code and found a source-backed cleanup hazard: `isAlive` returnsfalse for a legacy identity with missing birth time when current `/proc` ticks are readable. Native `reconcileOrphans` then marks the record dead and drops busy/live-worktree protections even though the worker is actually alive. Refusing one signal is not sufficient if cleanup deletes live state. Unreadable-proc/boot/reused-PID behavior also needs independent verification. Do not install this patch based merely on successful positive Android tick capture.

Current jobs:

| Owner | Run | Scope / output |
|---|---|---|
| Resumed Luna actual-SDK verifier | `eeb5ed78-9a98-4449-85cc-df47494ee57d` | Continuing real child/session/completion/kill/recovery proof from saved session; exact78b available for isolated copies; no blanket patch approval |
| Luna High independent78b reviewer | `6f05b8b5-0f90-41dd-894b-7a19147c6b64` | Frozen `~/.pi/worktrees/pi-config-durable-review-78b`; full feature/lineage/rollback and actual native unknown/boot/cleanup adversarial review; `~/.pi/durable-recovery/independent-review-78b.md` |
| Parent full Python regressions | task `b36a02e4e` | Sanitized isolated HOME, complete unittest discovery, tracked-source before/after inventories; durable results under `~/.pi/durable-recovery/parent-78b-regressions-*`; shell log in current `.pi/tasks/` |

Flash repair2 owner c3f6e953 is **completed/collected**, not active. No live extension/vendor patch/config installation; source and tests remain separate from deployment. Do not confuse helper regression success with actual SDK recovery or original campaign completion.

### Earlier: repaired candidate refused; actual Android probe

Independent re-review **REFUTED a761** (`~/.pi/durable-recovery/independent-review-a761.md`):

- `buildResumeSpec` drops profile/backend/model/thinking/agent/tools: an original read-only explore request becomes general/write-capable and routing can change.
- Claimed original resumes are never linked to the new child; after60s an expired lease can permit a second live worker on the same session/worktree.
- Same-version reinstall nulls backup fields in deployment manifest, so rollback loses the true preimage.
- Explicit DB quarantine can rename an inode with active SQLite writers and initialize a split-brain store.
- Managed worktree cwd alone is not preservation; stale docs still describe rejected terminal-lock protection/corrupt-state reset.

Real SDK fixture **`86898a46608e25d8acfb169c1410841dd1771187`**, branch `test/durable-recovery-real-sdk`, is an honest **partial negative probe**. It uses actual `createAgentSession`, extension runtime/native factory and a counted localhost transport, observing real tool dispatch/UUID lock record. But child launcher is `/bin/false`, so no real child JSONL/completion/recovery is proved. It fails on native `process.startTime=0`. Parent independently confirmed **Node reports `process.platform='android'`**, while stock `process-lock.ts:128–142` reads `/proc` only for `linux`. Prior blanket native PID-reuse-protection claims do not hold on this Termux stack. No pretending the platform is Linux or substituting a late PID observation for trusted birth identity.

The following assignments are historical (repair2 has since completed; resumed verifier continues, see current table above):

| Owner | Run | Scope / output |
|---|---|---|
| Flash High product repair2 | `c3f6e953-23b9-4ff9-8395-de1ebcd402f5` | Existing feature worktree; privilege/routing, resume lineage/lease, rollback, corruption and truthful support fixes; `~/.pi/durable-recovery/repair2-result.md` |
| Resumed Luna High actual-SDK verification | `eeb5ed78-9a98-4449-85cc-df47494ee57d` | Same isolated test branch, continued from full saved JSONL rather than restarted; `~/.pi/durable-recovery/actual-sdk-proof-continuation.md` |

No live installation or vendor patch. The old detached-mode bypass remains unaccepted/unnecessary. A **different, narrowly version/hash-guarded Android process-identity compatibility fix** may be staged if needed, with actual unknown/reused/boot safety tests and independent review before live use. Preserve logical recovery, not claimed process resurrection. Support actual permanent/shared Pi workflow; unsupported formats/managed WIP must be enforced nonresumable, never silently widened. Keep valid original preimages, refuse uncertain takeover and remove unsafe automated quarantine rather than shipping an unproven repair escape hatch.

### Earlier repaired candidate and contract-test snapshot

Repair/scout above are **completed and collected**. Source **`a7611a2d33ea0dfce3319f5dc973ea0514810d9a`** is clean and matches the fresh feature remote; master remains0e4. No live extension or vendor patch installed. The source adds event/UUID/command/corruption/liveness/installer repairs and an optional **unapplied** detached-mode patch. Prefer non-mutating logical recovery; live process survival is not required.

Author reports17 Node subtests,3 fixture subtests and3 Python tests passing. Parent inspected all370lines of `tests/test_real_integration_fixture.mjs`: it registers through **`mockPi`**, manually emits SDK-named events, handwrites a simplified native record/session, imports native policy only, and starts a loopback server without using it. These are contract/helper tests, **not actual SDK/native end-to-end proof**. Preserve the report but don't accept the label.

Those now-collected independent lanes, each in a permanent isolated worktree:

| Owner | Run | Scope / output |
|---|---|---|
| Luna High verification author | `14389bb1-4673-432d-acbe-fb1658d67a7f` | Actual SDK/native launch, completion and crash/recovery fixtures; `~/.pi/worktrees/pi-config-durable-sdk-proof`, branch `test/durable-recovery-real-sdk`; `~/.pi/durable-recovery/actual-sdk-proof-result.md` |
| Flash High independent re-review | `372e4708-0096-40a6-99d7-4177521342f8` | Frozen a761 full feature/contracts/adversarial review, no product edits; `~/.pi/worktrees/pi-config-durable-review-a761`; `~/.pi/durable-recovery/independent-review-a761.md` |

Flash remains product implementation owner. Failing genuine fixtures are useful; do not alter expectations or invent native metadata to make them pass. No source installation, actual vendor patch, global config write or real model/API call is authorized in these lanes. Fully isolated, deterministic loopback transport and own synthetic processes are allowed.

Scout found no supported native config/env/hook to bypass orphan reaping while keeping busy/live tracking. It confirmed native distillation deletes non-busy raw sessions and managed worktree pruning is separate. Verify preservation before that actual path, including append/rewrite/WIP limits; hardlinks alone are not immutable snapshots. A fresh Pi process is sufficient OS isolation; full Termux restart is unnecessary. Actual `/reload` adequacy is not yet proven.

## Environment preservation and readiness

Read-only private baseline saved at **`~/.pi/durable-recovery/environment-baseline-20261027T035205Z.json`**: 110 paths fingerprinted, no credential contents copied. Verified **Node v24.17.0 / Pi 1.4.0 / subagent 0.8.0**. Auth may legitimately refresh independently; never blindly restore old auth bytes because a hash changed. No settings or packages were modified by baseline capture. A later read-only check (`environment-after-a761-source-only.json`) found2changed paths: auth.json and settings.json; all other108fingerprints match and the live extension is absent. Current nonsecret settings routing matches a Flash High child; ordinary SDK/CLI model persistence is possible, but cause is not yet established. Reviewer is tracing actual writes and verification author must isolate SDK imports/settings explicitly. Do not claim all110remain unchanged or blindly roll back either file. Recheck immediately around any eventual installer.

READY TO RESTART requires:

1. Repaired exact source passes independent Flash re-review with actual integration proof, not only helper tests.
2. Targeted reviewed installation from the actual pinned source (or properly integrated pi-config master), with reversible deployment and unchanged unrelated settings/auth/models/packages. The suggested new helper is not yet present in old `~/pi-config` master; do not blindly run it there.
3. Current critical jobs finished or acknowledge a verified safe checkpoint; source and required sessions/results preserved. No automatic replay of uncertain Git/API side effects.
4. Explicit tested activation instruction: Pi `/reload`, fresh Pi process, or only if genuinely necessary a broader restart. Do not disturb unrelated applications.

After activation, verify the extension and durable state in the real harness before claiming end-to-end success, then resume queued Gaia repairs and all original acceptance gates. Canonical/schema, genuine issuer, founder rendered visuals, real weekly coverage/pilot and main/release/RFC closure remain held.
