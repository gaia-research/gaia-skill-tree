# Yggdrasil IV — environment-crash recovery (2026-10-26)

## Current control

The founder returned after an environment crash and explicitly instructed: **“Recover and continue as instructed.”** Engineering remains resumed under the [second resume receipt](YGGDRASIL_IV_RESUMED_2026-10-26.md). This is not a new campaign or an authorization to bypass any gate.

Continue RFC #2148, aggregate #2151 and integration `dev/yggdrasil-iv` at `4b73e62814fca16a01bd1e71325e7abb97316c95`. Main, canonical/schema/standing/Origin changes, live issuer/security activation, founder visuals, elapsed operational coverage/pilot and release/closure remain held.

## Recovered verification, not merely a completion notification

The reloaded shell task registry no longer recognized `bdb8b0209`, but its output and verification files survived. The original durable completion notification says exit0; recovered output independently records:

- Exact source `b6103d7bd42eb7a73b1e7366cc335400b8fcd375`.
- **324 tests passed in 65.56s.**
- Actual pinned complete CLI replay: **398 named records / 299 generic nodes; 398 evaluated / zero not-evaluated**; explicit complete-registry scope, no validation findings and a clean before/after input manifest.
- Parent inventory: **zero changed source paths**; both pytest and CLI exit0.
- Fourteen TM deltas and eight grade differences are diagnostic observations only, not canonical recalibration or confirmed degradation.

Independent review survived as `corpus-b610-independent-review.md`: **45 focused tests passed**, no remaining P0/P1 blockers in the four reviewed integrity areas, clean review worktree. Its two omitted full-corpus tests were covered by the successful parent run.

Opened **[draft PR #2159](https://github.com/gaia-research/gaia-skill-tree/pull/2159)** into `dev/yggdrasil-iv`, exact headb610. Stored body/head/base/draft status verified. It is **not merged**; final integration and applicable CLI visual gates remain explicit.

## Interrupted implementations preserved

The two implementation runs were marked `orphaned-dead`; their recorded processes/groups were absent. Unrelated running applications were left alone. No success is inferred from the stale result files left by older failed startup attempts.

Recovery directory: `.gaia/yggdrasil-iv/recovery/crash-2026-10-26-1857/`.

| Source | HEAD at capture | Preserved edits | Separate recovery-only snapshot |
|---|---|---|---|
| `watcher-transactional` | `a84f65358817b2a9ae5c7e23625a84e21ac01f3a` | Two tracked files; 36,564-byte binary patch. The worker had already committed ledger/workflow prerequisites. | `c4641a32b5e0cb7294f47a9b5c54f49f36ed886e` |
| `publication-last-mile` | `049c8ce4cd8871010f7f9c549e86adef398cd73f` | Four tracked files; 5,033-byte binary patch. Runtime-inheritance optimization remains unaccepted. | `525439aa6c30033be610a4e987d8c7005840d5dc` |

Snapshots were created through a separate temporary Git index: worker branches, working files and their real indexes were not moved. Patch hashes, source statuses, copies of the surviving child logs and parent corpus evidence are local recovery material. Do not merge the recovery-only snapshots, force-apply their patches or infer tests passed before the crash. Local recovery is not off-device backup.

## Actual resumed sessions

Unlike the older digest-only handles, these two interrupted workers had surviving full JSONL sessions. Resume used their actual file paths. Post-resume inspection confirmed all three processes alive, with matching assigned worktree CWDs:

| Assignment | Current run | Session |
|---|---|---|
| Sol High watcher fresh-state CAS/shared packet outbox | `ff9cb8c4-41d9-4db6-8b71-30506f6f99eb` | `01a17940-3dd2-7563-8e9a-203a914fdb23` |
| Luna High publication parity diagnosis/strict verification | `1fa936dc-5944-4dad-ac0b-d3d16c6718ea` | `01a17940-3e10-751a-b239-e750b4f98846` |
| Luna High canonical transaction foundation, from clean integration4b | `1ddd123e-5220-4347-9ced-340a93f95e1e` | `01a17998-2103-764c-acfc-956d05edf62b` |

These are observed startup facts, not completed delivery. No second Sol implementation worker was launched. Authors must commit tested coherent units early, retain recovery refs, distinguish local save/push/fresh remote verification, and leave long combined/full-corpus replays to the parent.

Publication may optimize repeated runtime hashing only while retaining actual validated outer/runtime boundaries and independent certification checks. `runtime_verified_by_parent=True` is not proof by itself; wrong or mutated runtime must not certify successfully. No semantic/PNG checks are waived.

The transaction increment must default to an unavailable approval provider and support exact CAS, durable preimages/journal, pending-write guards and compare-safe recovery. Cooperative locking/recoverability is **not** multi-file linearizability for unlocked legacy readers. CLI/dual-history/migration completion remains in this campaign.

## Additional parent check

At cleanup source `f39a859caed64db39bd0baf7b5fb3a395fee97b0`, parent inspected the pruning/compatibility changes, ran **20 tests in 0.98s**, checked skill mirror parity and whitespace. The new referrals point to `gaia-frontier`, which is not yet on integration. Keep its landing dependency explicit rather than presenting the new referral as usable now. Frontier native invocation/separate comparison, lifecycle producer/rendered panel evidence, evidence adoption and live issuer proof remain unfinished.
