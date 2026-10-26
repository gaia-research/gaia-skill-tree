# Yggdrasil IV — connectivity recovery checkpoint

Captured 2026-10-26. This is an engineering recovery record, not acceptance, publication, rollout or closure authority. For campaign boundaries read `YGGDRASIL_IV_EXECUTION.md` and the ratification first.

## Immediate state

- Integration `dev/yggdrasil-iv`: `2c880b119e86d404f2112542b6fad14269e09def`.
- Draft aggregate PR #2151 remains held from main merge. RFC #2148 is open.
- #2153 merged by merge commit `a0ecfd5e4`: additive memory and interruption recovery receipt.
- #2154 merged by merge commit `2c880b119`: #2152 comparison-only GitHub repository casing fix. Independent before/after reproduction and 34 local tests passed; current-head Actions run `40269406102` passed full tests, build and clean-wheel smoke. No live upstream bootstrap/retry performed; #2152 remains open pending main/release.
- Current source/schema/UI feature branches remain unintegrated. A saved commit or passing worker test is NOT independent acceptance.

## Offline recovery guarantees and limits

User reported intermittent internet. Workers were instructed to checkpoint coherent owned work locally, maintain a named local recovery ref even when detached, push best effort, distinguish local-saved from remote-confirmed, and never exit while owned code is dirty or a background test is still running. Steering reached the active publication and receipt-source workers; other runs had already completed or timed out, so their persisted work was captured directly instead.

Local recovery inventory: `.gaia/yggdrasil-iv/recovery/manifest.json` (ignored, not a canonical input). It records exact worktree/session paths, run IDs, local SHAs, terminal state, recovery refs, tracked binary patches and untracked-file archives. These are point-in-time backups; active workers may advance. Read that file rather than guessing that an old worktree still exists.

At the 05:08 UTC capture:

- Saved 11 task records; completed cleaned-up worktrees are distinguished from existing worktrees.
- Anchored 28 local/cached-remote campaign refs under local `refs/heads/recovery/yggdrasil-iv/saved/`, plus extant task HEAD refs. Cached remote refs were NOT reverified over the network during backup.
- Captured the durable-watcher worker's **17,154-byte uncommitted binary patch** over `bd4aa8159e874eca10429d21c90e9515ca3411d1`; patch SHA-256 `f0a545c04f136a1100c79e42e23553b9052b3f74d5ce7e17d350f238eeb31fb7`.
- Captured the active receipt-source worker's two untracked Python files in a local tar archive; do not assume a plain `git diff` contains untracked new files.
- Saved completed corpus and UI review reports locally. Failed model-request results are recorded as failures, not successful reviews.
- Created and verified an **incremental Git bundle**, `.gaia/yggdrasil-iv/recovery/campaign-checkpoint.bundle`, 157,196 bytes; SHA-256 `6c0d7d6a5e9b6a843d7a1cfa8c783c910d67a7acfcb476bff1e93090d6d65f09`. It requires existing baseline `b0f6d9e502369aea2ebebe13eed8d961675094bd`. `git bundle verify` passed. It includes committed campaign refs, NOT the separate uncommitted patch/tar backups.

No dependency on successful network access is required to inspect these commits, patches or reports. This protects against connectivity/session interruption, not loss of this device/filesystem. Do not silently install backup software or mutate global configuration.

## Saved foundations and remaining verified blockers

| Workstream | Last saved source | Exact outstanding work |
| --- | --- | --- |
| Shadow evaluator | `dev/yggdrasil-iv-shadow-engine`, `6e6c3f08f111e265c2407759a238f8e64558503e` | `380aabc1c` passed 196 targeted tests and fixed pinned-type inheritance, duplicate contributions and registry dependency coverage. Parent then reproduced standalone-suite missing dependencies as evaluated zero. `6e6c3f08f` commits the direct-suite repair, but the final worker response timed out; independently inspect tests/session logs and reverify before acceptance. |
| Challenge domain | Remote last confirmed `a3d6107c55db2bda962f74f63f7c8f3c31143768`; local original hardening branch can still be older | Builder/contributor independence and rehydration chronology improved (11 tests). Parent reproduced a remaining round-trip defect: earlier receipt verification, later publication yields an opening event at receipt time while creation is later, then trusted rehydration rejects it. Fix `open_challenge` to emit publication event at publication time; add earlier-receipt/later-publication round-trip test. Repair request failed; do not assume fixed. |
| Corpus runner | `dev/yggdrasil-iv-corpus-shadow`, `ab726453e7b1fbe4479cdb6cd9b2f88cce82e334` | Destination-file symlink bypass, lost census time pin, duplicate/integrity omission, swallowed registry errors and trustNumber disposition repairs saved. Worker reports 33 focused tests and a clean-manifest pinned run: 398 named, 299 generic, 154 missing-date observations, 480 provenance trustNumber rows. Must merge final reviewed engine, independently review corpus repairs and rerun; present impact as provisional until then. |
| Evidence schema | `dev/yggdrasil-iv-evidence-schema`, `3b233b8d5daf12660d26ff591d3f6f119f188d3e` | Exactly 12 schema files; separate from executable core. Founder/two-Core approval held. Subsequent repair request timed out; do not treat proposed schema as accepted. |
| Evidence core | `dev/yggdrasil-iv-evidence-core`, `1f9b76f6c5a6a5d70a04151aec641cd474cae574` | Exact recovered two-file core, stacked on schema. Independent review still blocks partial lifecycle migrations reactivating revoked rows, incomplete revision/actor/time history, optional refresh provenance and naive timestamps. Legacy `verified` is existing metadata, not an approval token; do not break legacy rows to manufacture authentication. RFC applies assertion lifecycle to starless generic evidence too. Production assertion-state consumption remains held. |
| Durable watcher | `dev/yggdrasil-iv-challenge-watch-durable`, `bd4aa8159e874eca10429d21c90e9515ca3411d1` plus saved patch | Merged latest available core dependency. Four dirty owned files captured before model timeout. Persistence, two-run CAS/retry/partial coverage/trusted-status tests still require completion and independent review. Existing watcher prototype is NOT a trusted receipt source. |
| Governed receipt source | `dev/yggdrasil-iv-challenge-receipts`, starting `a3d6107c5`; task `f15b2fcb` index 1 | Active at capture; new source/test files archived. Required protected-workflow/environment provenance must be checked through real issuer APIs; no actor-name/JSON/hash bypass. Existing curation `_verifyTrustedEnvelope` remains intentionally disabled and must not be weakened. External protected-environment setup/security approval remains a real gate. |
| Lifecycle UI | `design/yggdrasil-iv-challenge-history`, `386335c1f8e32b33940c58268de9db1accee7bb1` | Independent review blocks unpinned snapshot shown as approved and string `"false"` coercing material-Origin challenge to true. Parent/reviewer inspected synthetic screenshots: heading clips at 390px and hero TM 125 disagrees with panel TM 105. Three-section preview harness is not actual five-section Explorer integration evidence. Require real coherent before/after Explorer screenshots at desktop/mobile including 320px; visual approval remains held even for integration. |
| Coherent projections | Task `36566dd2`, starting integration `2c880b119` | Active at capture; shared context across existing named/graph/ledger/API/profile/timeline/badges builders is assigned, not delivered. No new trust DB or formula; no canonical/generated writes or invented approval. |

## Resume without losing or overwriting work

1. Read this record, `YGGDRASIL_IV_EXECUTION.md`, and ignored recovery manifest. Consult current Git state before interpreting these historical SHAs.
2. Inspect local branches and recovery refs before any fetch. A remote outage does not erase local commits. Verify incremental bundle against its baseline before using it; `git bundle list-heads` lists anchors. Recover into a new isolated worktree, not by resetting an existing one.
3. For completed tasks, read saved report/session evidence. For a failed task with a preserved worktree, resume the exact recorded child session/cwd or delegate a new authorized worker with the exact SHA/patch base. Recheck dirty source first. Never replay a patch wholesale onto a changed engine or apply corpus-patch doc reversals.
4. For the durable-watch patch, inspect the four-file diff against `bd4aa8159` before applying in a new worktree. For new receipt-source files, inspect the separate archive as well as tracked diffs. Parent does not author implementation code.
5. Finish the two small engine/domain corrections and their independent review before integrating them. Continue evidence/UI repairs, then transaction/CLI/dual-timeline migration and rollback work; none is follow-up debt or assumed complete.
6. Commit coherent local units before long tests/network operations. Anchor detached commits. Collect background tests before ending a child, or stop them explicitly and preserve logs. A prior full-suite engine task was killed by child shutdown; its result was not a pass.
7. Push only when possible. Verify exact remote SHA separately; unavailable remote = unconfirmed, not delivered. No force pushes, branch/worktree deletion, stash-only storage, global installs, direct main commits or automatic canonical rollout.

## Later receipt-source result

The final `f15b2fcb` delivery was collected after its terminal notification. The durable-watcher task timed out; its partial four-file patch remains the saved recovery source. The companion receipt-source task completed an engineering-preparation unit:

- `dev/yggdrasil-iv-challenge-receipts`: `a3df0cbd9c5e513fb508ae282f91eeb4ba769134`.
- Local recovery ref `refs/heads/recovery/yggdrasil-iv/challenge-receipts` at the same SHA. Push was acknowledged by the remote; no independent post-push fetch was performed.
- Worker reports **39 passed** across `tests/steward/test_challenge_receipts.py` and `tests/test_challenge_domain.py`, diff check passed and clean working tree. This is worker evidence, not independent acceptance.
- Two committed files provide bounded full-payload ZIP packaging, context/transcript/notification binding, deployment configuration validation and a fail-closed resolver. Synthetic positives are contract fixtures, not live authorization evidence.
- **Live adapter remains unavailable:** available GitHub REST evidence did not establish completed-run protected-environment approval actor/history. No environment, producer workflow, token, repository setting or privilege was provisioned; the existing curation authorization refusal remains unchanged.
- Remaining implementation/security gate: an independently verifiable authenticated approval-history source, protected producer source and configured prevent-self-review/required-reviewer environment. No working operational watcher or end-to-end authentication is claimed.

## Corrected publication assignment and persistent worktrees

Collected final `36566dd2` output: **no projection producer or tests were implemented**. Its `dev/yggdrasil-iv-trust-publication` branch at `a2c2b3bb8b63ca834568ae9dc1d3828326a767c3` contains only forced-in recovery notes, not functional code. Local HEAD and cached remote ref are equal at that SHA; the worker's contradictory “one commit behind” statement is not evidence of a delivery gap. Do not merge this notes-only branch.

The actual RFC review exists at `$TMPDIR/yggdrasil-iv-rfc/0.md`; `technical0.md` was an ambiguous shorthand, not a missing campaign document. Live approved-source absence blocks activation, not implementation of a strictly labeled rehearsal producer. Parent corrected the assignment to require `mode=rehearsal`, `approval=unavailable` throughout staged outputs, default behavior unchanged, and live-approved publication fail-closed.

New dispatches use **parent-created permanent isolated worktrees**, not disposable worker-managed worktrees:

- `b12b7a17-2af3-42ba-8dbb-c21d517d6bd2`, Luna High: `dev/yggdrasil-iv-trust-publication-build`, starting pending-review engine `6e6c3f08f`; worktree `$HOME/.gaia-worktrees/yggdrasil-iv-publication-build`. Implements shared context through actual existing generators and scratch build proofs. Assigned, not delivered.
- `1fedea77-a31f-43f8-b880-6017b3e6e58b`, Flash High: `dev/yggdrasil-iv-challenge-publication-time`, starting `a3d6107c5`; worktree `$HOME/.gaia-worktrees/yggdrasil-iv-challenge-time`. Implements the independently reproduced publication timestamp round-trip correction and focused tests. Assigned, not delivered.

Both must commit locally first, maintain named recovery refs, keep recovery notes ignored (never force-add `.gaia`), push best effort, preserve dirty source on failure, and collect or stop tests before ending. No source acceptance, integration merge or publication authority is inferred from a launch receipt.

## Challenge publication-time fix — independently verified

Flash High completed `1fedea77` at `b358ea3a2f5fd337ddbc29b42cc29969ee148c02` on `dev/yggdrasil-iv-challenge-publication-time`, with recovery ref `refs/heads/recovery/yggdrasil-iv/challenge-publication-time`. Worker independently checked both remote refs at that SHA. Permanent worktree remains `$HOME/.gaia-worktrees/yggdrasil-iv-challenge-time`; local recovery note is ignored, not committed.

Parent Sol independently reviewed the entire final two-file delta, reran **12 domain tests (12 passed in 0.23s)** and repeated the formerly failing runtime probe: receipt verification 11:00, publication and opening event 12:00, trusted rehydration succeeds. Earlier identity/proof/closure gates are unchanged; diff check passed and worktree clean.

Opened **PR #2155**, domain-only foundation into `dev/yggdrasil-iv`; exactly `src/gaia_cli/challengeDomain.py` and `tests/test_challenge_domain.py`. Current-SHA CI is pending (bounded watcher `b6b91a4f5`). No merge performed and no live receipt authentication or operational watcher readiness claimed. Receipt producer authentication remains separately unavailable. The original domain timestamp blocker is now fixed; do not restart that repair from the older snapshot above.

## Publication rehearsal implementation recovered — verification pending

Collected `b12b7a17`: actual implementation exists at `41e05570a36bfabca17870d60dfdb48b20d88029`, recovery ref `refs/heads/recovery/yggdrasil-iv/publication-build`. Five files changed relative to pending-review engine `6e6c3f08f`: shared `scripts/publication_context.py`, existing docs/named/ledger builders, and focused tests. The permanent publication worktree survived the child ending; source/tests are committed, with only local task logs untracked. Worker reports final remote SHA independently matched.

Worker reports 62 focused tests and an earlier-revision 5,107-artifact scratch replay. **That is not final-HEAD proof.** Final replay task `b8b84f8c8` was killed with SIGTERM during child shutdown, despite the final response saying it was running. Do not count that replay as passed.

Parent took ownership of final-HEAD verification: task `bb899e5ff` runs the 62-test selection and actual builder replay in a fresh external scratch root, pinned `2026-10-25T12:00:00Z`. Independent read-only source review `047af142-f423-482d-a7f6-1ddcbd639d21` is assigned, with durable output at ignored `.gaia/yggdrasil-iv/recovery/publication-review-41e05570a.md`. No acceptance, PR or merge for the publication code yet. Verify semantic cross-surface values, complete consumed-input identity, safe output containment and reproducibility—not only matching snapshot markers.

**Execution discipline change:** parent owns long validation/replay commands after delivery. Writers should commit coherent source and run short synchronous checks; repeated child-finalization has killed their background tests. Persistent worktrees/local refs preserve implementation, but do not turn an interrupted check into evidence.

## Still binding human gates

Schema adoption, pilot/live standing and canonical trust/rank/evidence/Origin decisions, security/protected-environment activation, visual approval, final main merge, registry-wide rollout and RFC closure remain held. Four weekly operational shadow comparisons require real elapsed operational evidence, not a virtual-clock fixture. All implementation remains engineering preparation until those gates are met.
