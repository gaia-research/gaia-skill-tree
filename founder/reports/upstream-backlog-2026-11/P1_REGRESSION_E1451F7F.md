# P1 independent regression — failed at `e1451f7fc`

**Handoff status: BLOCKED.** [Draft PR #2468](https://github.com/gaia-research/gaia-skill-tree/pull/2468), checked SHA `e1451f7fc5db2cb149e6bce30eb023c020c6cd8c`, source-equivalent to repair `3fdd6d7573ce3cec922babba8b3c82eaf952dbd2` outside campaign reports. Tests ran in a clean, separate detached worktree. [Draft PR #2469](https://github.com/gaia-research/gaia-skill-tree/pull/2469) was not changed or accepted by these checks.

## Actual validation

| Check | Result | Scope |
|---|---|---|
| Non-author pytest | **1,275 passed, 61 failed in 341.54 s** (exit 1; no skips reported) | `tests/upstream_watcher`, `tests/test_upstream_approve_workflow.py`, `tests/test_repository_envelope_workflow.py`, `tests/test_dev_upstream_verbs.py`, `tests/test_named_persistence_contract.py`, `tests/test_upstream_persistence_contract.py`; cached #1833 fixture enabled via `P1_LEGACY_CACHE`. No failures listed for the cached case, new root envelope workflow file, CLI verbs, or persistence files. |
| `python3 tests/upstream_watcher/parity_2283.py` | **Exit 0** | `stagedRowsEqualBatchRows=true` and `stagedRowsEqualDailyUnstagedRows=true` in the retained #2283 parity fixture. Does not prove new envelope routing or staged apply readiness. |
| `git diff --check <PR base>...HEAD` | **Exit 0** | Base `bfed2d777b76448f6ede5d40e1a834050dff07d0`; pinned HEAD and tracked files rechecked on exit. |

Durable task `b04efdcf0` exited 1. Completion marker: `P1_NON_AUTHOR_COMPLETE sha=e1451f7fc5db2cb149e6bce30eb023c020c6cd8c regression=1 parity=0 diffcheck=0`. Raw outputs are local in `$TMPDIR/upstream-backlog-2026-11/p1-resume-e1451f7fc/`, not committed. SHA-256 for `regression.log`: `69403bd2da9bce3eaffff484a11a604763e3a81bd6ebf1c2f4ade09eda46f5b1`; `parity.json`: `e11f464db6696231c3354d072e55935b38e003c1bd598db6a1a544b05589e0c9`. No Actions dispatch or live mutation was involved. No additional model was used for the test command; no token estimate.

## Failure triage and next gate

- **40 failures stop on obsolete watcher patch targets** (`run_batch` 27, `escalate_candidate` 10, `create_issues` 3). They show the full behavioral fixtures are not reaching the new production routing; they do not establish that their original invariants are covered or that behavior is correct. Repair or replace fixtures only after mapping each invariant to the current route and proving outcomes with defensive mutator/fail-closed checks.
- **21 other failures** include approval/child-close cascade expectations, rollout/default and workflow byte snapshots, permission A/B ordinary-job snapshots, and changed report-phase assertions. Triage old expectations versus unintended behavior explicitly; do not merely bless new golden hashes or weaken permission, diagnostic-isolation or fail-closed tests. This run did not compare all 61 with the old candidate or attribute them all to `3fdd6d757`.
- **Independent [Terra FINDINGS](P1_REREVIEW_E1451F7F.md) remain blocking** irrespective of whether test adapters are stale. An explicit one-round code-only exception on #2468 remains the recommended founder decision under the per-PR correction cap. Its proposed scope now includes restoring meaningful full regression coverage, plus the existing review findings. Without an exception, hold the drafts. No schedule/variables/write approvals or migration are implied.
- After an authorized repair: verify the final reconciled source against the pinned main and PR base, rerun the full suite and parity, then obtain a fresh independent `pi-reviewer` verdict on that exact source before considering acceptance. No merge, schedule rollout, issue/registry write, or P2 advancement. The sole conditional ordinary `apply=false` run remains unused.
