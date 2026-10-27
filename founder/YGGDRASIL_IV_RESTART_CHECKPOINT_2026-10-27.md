# Yggdrasil IV — restart checkpoint NOT ready (2026-10-27)

## Current control

Founder asked to be told when to reset and then explicitly said **Continue**. Continue the safe Pi recovery-tooling repair; **do not issue READY TO RESTART yet**. No additional Gaia campaign jobs before this restart window. This is temporary execution sequencing, not a campaign restart, permanent pause, completion claim or waiver of the original mission.

All previously assigned Gaia implementation workers, independent reviews and parent shell tests are now terminal and collected. The old tooling review's assertion that publication task `ba7cb70f5` remains live is stale. Only the newly assigned Pi tooling repair/research below should be treated as current work.

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

## Environment preservation and readiness

Read-only private baseline saved at **`~/.pi/durable-recovery/environment-baseline-20261027T035205Z.json`**: 110 paths fingerprinted, no credential contents copied. Verified **Node v24.17.0 / Pi 1.4.0 / subagent 0.8.0**. Auth may legitimately refresh independently; never blindly restore old auth bytes because a hash changed. No settings or packages were modified by baseline capture.

READY TO RESTART requires:

1. Repaired exact source passes independent Flash re-review with actual integration proof, not only helper tests.
2. Targeted reviewed installation from the actual pinned source (or properly integrated pi-config master), with reversible deployment and unchanged unrelated settings/auth/models/packages. The suggested new helper is not yet present in old `~/pi-config` master; do not blindly run it there.
3. Current critical jobs finished or acknowledge a verified safe checkpoint; source and required sessions/results preserved. No automatic replay of uncertain Git/API side effects.
4. Explicit tested activation instruction: Pi `/reload`, fresh Pi process, or only if genuinely necessary a broader restart. Do not disturb unrelated applications.

After activation, verify the extension and durable state in the real harness before claiming end-to-end success, then resume queued Gaia repairs and all original acceptance gates. Canonical/schema, genuine issuer, founder rendered visuals, real weekly coverage/pilot and main/release/RFC closure remain held.
