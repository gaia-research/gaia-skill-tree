# P1 partial source checkpoint — paused, unreviewed, not execution-ready

**Status: PAUSED / PARTIAL / UNREVIEWED / NOT EXECUTION-READY.** This is a preservation and partial-review publication checkpoint, not an acceptance or readiness verdict. The user paused engineering; no further code, test, build, watcher dispatch, data action, phase work, or merge is authorized by this checkpoint.

## Source checkpoint

- Integration branch/worktree: `dev/upstream-backlog-watcher-2026-11`, base branch `dev/upstream-backlog-2026-11`.
- Last existing commit before this partial checkpoint: `4e5792a664fa08c4163fbcef961c122b021e62c7`.
- Local checkout has the 15 listed implementation/test paths below changed or new. No preexisting coherent local commit was found by the current checkout status/log inspection; the partial source bytes are preserved as-is, without cleanup, formatting, or repairs.
- Existing exact founder policy JSON `P1_IDENTITY_FOUNDER_DECISIONS.json` is preserved verbatim. Its choices remain `repo_envelope` and `preserve_plan`; its standing code-only implementation authority does not supersede the current explicit pause.
- No active pytest/test writer process was observed. The requested source session ID `01a1ebc0-742d-70cd-b683-866509322a45` could not be located in Pi session files; no matching worker process was present. A separate Pi-cost report is for this admin session, not evidence of that source session's telemetry.

## Changed source scope (15 paths)

1. `.github/workflows/upstream-approve.yml`
2. `.github/workflows/upstream-close-children.yml`
3. `.github/workflows/upstream-reject.yml`
4. `scripts/upstream_watcher/approval.py`
5. `scripts/upstream_watcher/releaseidentity.py`
6. `scripts/upstream_watcher/watcher.py`
7. `scripts/upstream_watcher/envelope.py`
8. `scripts/upstream_watcher/legacy_plan_policy.json`
9. `scripts/upstream_watcher/repository_batch.py`
10. `tests/test_upstream_approve_workflow.py`
11. `tests/upstream_watcher/test_count_2278.py`
12. `tests/test_repository_envelope_workflow.py`
13. `tests/upstream_watcher/test_repository_envelope.py`
14. `tests/upstream_watcher/test_repository_envelope_cached_case.py`
15. `tests/upstream_watcher/test_repository_envelope_records.py`

No focused/adversarial test verdict is available for this current diff. Previously mentioned focused command output ended after partial dots and has no final summary; no pass count is inferred. No current full regression/parity was run. Old Terra 238 and parent 1204 results at `d176e98` apply to an earlier protocol/diff only and do not review or validate this source.

## Explicit unfinished work / next orchestrator checklist

- Complete and integrate the repo-envelope implementation; obtain the source author's completion verdict. The current code is a draft and remains unreviewed.
- Finalize a coherent protocol/runbook for repository envelope identity, approvals, legacy selection, digests and carry-forward.
- Run and capture the complete focused/adversarial tests, then independent Terra review of the new diff.
- Run parent full regression/parity against the exact new diff and perform normal read-only acceptance only after the required reviews and any outstanding data/contract gates are resolved and a fresh authorization permits continuation.
- Resolve—not infer—the implementation boundaries covering CLI source eligibility, unknown legacy state, selected named-digest scope, carry-forward, journal behavior, fanout, and guard/caller closure.
- Keep legacy migration planning distinct from migration approval or execution. No issue #1833 body/history changes, actual held-repository writes, or registry/data actions are authorized.
- Do not advance P2–P7, request ready/review status, merge, alter labels/variables/permissions, or dispatch workflows under this pause.

The prior normal run 44135214784 remains a failure and the conditional normal allowance is paused, not consumed by this code checkpoint. Preserve the correction: historical raw body bytes are 2,112 bytes with SHA-256 `ae62e163b04c2b24057d629ff1024a19982c8180d88a7ad2c5b64707f3ab8d1a`; SHA-256 of `(body + '\n').encode()` is `9344b0c025eea552cd461bb892ef82e1b88d5530a495f347bfd71f1daac74cc6`, matching the original approved packet scheme (CLI stdout added a final LF; the worker used raw API bytes). This is a digest-scheme difference, not evidence that #1833 changed. Preserve original JSON and describe schemes explicitly; neither digest is execution approval.

Protected checkpoints reported by the prior campaign record remain unchanged by this partial source work: integration `bfed2d777b76448f6ede5d40e1a834050dff07d0`, schema `6bed0edf324d49e42cd8953351deaccaa733d22f`; canonical registry/trees/graph unchanged. These refs/files are not modified here. P1 remains blocked at the identity/migration gates.

## Verification limits

Before admin documentation edits, SHA-256 hashes were recorded for all 15 source/test paths; after these documentation-only edits, hashes were rechecked and were byte-identical. `git diff --check` was run and passed. No source tests, parity, build, full regression, Terra review, or watcher run was performed in this pause checkpoint.
