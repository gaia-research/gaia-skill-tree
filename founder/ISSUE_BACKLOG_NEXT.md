# Issue Backlog Next Queue — after eradication sprint

Generated: 2026-08-04  
Branch: `dev/issue-backlog`  
Governing integration PR: #1395

This file replaces the active use of `founder/BACKLOG_ERADICATION_TRACKER.md`, which is archived at:

- `founder/handovers/archive/BACKLOG_ERADICATION_TRACKER_2026-08-04.md`

The old tracker remains the audit record. This file is the short next-action queue for readying `dev/issue-backlog` for the final integration merge to `main`.

## Backlog eradication math

### Original tracker scope

- Original tracker issue count: **97**.
- Live GitHub state now: **48 closed / 97 total = 49.5% closed**.
- Still open from the original tracker: **49**.

### Integration-adjusted read

Several issues are implemented on `dev/issue-backlog` but remain open until #1395 merges to `main` and GitHub applies closing keywords or maintainers close them manually.

Close-ready after #1395 lands:

| Issue | Why close-ready |
|---|---|
| #868 | Implemented by #1436, Trust Leaderboard polish and CTA fix merged to `dev/issue-backlog`. |
| #1004 | Implemented by #1434, skill-fuse surfaces merged to `dev/issue-backlog`. |
| #1268 | Implemented by #1435, frontend + Trust Leaderboard performance pass merged to `dev/issue-backlog`. |
| #1419 | Implemented by #1428, #1429, #1431, #1432, #1433, benchmark-source registry and simplified TM lanes merged to `dev/issue-backlog`. |

If those four are counted as effectively done, the nearby sprint/original-tracker read is roughly **52 done / 97 = 53.6%**. Current live repo-wide open issue count is **67**; after those four close, it should be about **63**.

**Bottom line:** the sprint crossed the halfway mark only when integration-ready work is counted. It did not erase the whole backlog by raw issue count. The win is that the high-risk integration branch is now coherent and nearly ready for final review, not that every historical issue is gone.

## Do not open more PRs onto `dev/issue-backlog`

Founder direction, 2026-08-04:

- No more feature PRs target `dev/issue-backlog`.
- From here until the final #1395 merge decision, commits land directly on `dev/issue-backlog` under superadmin/founder orchestration.
- Only final review, hygiene, closeout comments, and release-readiness fixes belong here.

## Immediate final-review queue

1. **Review the integration branch locally.**
   - Serve `docs/` from `dev/issue-backlog`.
   - Check the homepage, Trust Leaderboard, benchmark pages, badges/named surfaces touched by the sprint, and any obvious nav/footer regressions.
2. **Watch #1395 CI until fully green and stable.**
   - Current branch: `dev/issue-backlog`.
   - Current integration PR: https://github.com/gaia-research/gaia-skill-tree/pull/1395
3. **Decide whether to close or annotate close-ready issues after #1395.**
   - #868, #1004, #1268, #1419 are the first pass.
4. **Cleanup only after final review.**
   - Remove merged local worktrees/branches for #1433–#1436 and stale preview logs if Marcus is done with them.
5. **Only then prepare #1395 for the big merge to `main`.**
   - This remains founder-gated.

## Next issues after #1395, grouped by action

### A. Close or verify-close after #1395

| Issue | Action |
|---|---|
| #868 | Close after verifying Trust Leaderboard polish is live from `main`. |
| #1004 | Close after verifying skill-fuse surfaces and profile/API artifacts are live from `main`. |
| #1268 | Close after verifying homepage/graph/profile and leaderboard perf changes are live from `main`. |
| #1419 | Close after verifying benchmark-source registry, Phase 2B docs, and TM lanes are live from `main`. |
| #1194 | Verify whether TM-over-time remains real work or can finally close. It is still open and should not be assumed done. |

### B. Held / do not touch without explicit founder release

| Issue | Reason |
|---|---|
| #1028 / PR #1401 | Shared registry helper package remains draft-held and failing/stale. Do not revive unless Marcus explicitly releases it. |
| #1060 | Destructive history rewrite / binary prune. Needs its own founder gate and rehearsal, not a casual cleanup before #1395. |
| #1336 | Roadmap v5 EPIC. Broad umbrella, not part of final #1395 hardening. |

### C. Strong next engineering candidates after the big merge

These are good candidates once `dev/issue-backlog` is safely merged, not before.

| Issue | Why next |
|---|---|
| #1201 | Small schema/docs correctness: live graph `$schema` points to a dead path. |
| #1202 | Schema/feed/source field mismatch. Important correctness work, likely schema-scoped. |
| #1230 | Dead type-enum reads still exist in shared scripts/CLI. Cleanup tail from Yggdrasil II. |
| #1231 | Taxonomy logic triplication umbrella. Decide after #1230/#1264 disposition. |
| #1264 | `share.py` still has retired type-symbol mapping. Small CLI cleanup, but branch-aware design needed. |
| #1375 | `docs/en` still documents a local `packages/mcp` build that no longer exists. Small docs correction. |
| #1404 | Five `mbtiongson1` descriptions still carry the banned construction. Small registry/content cleanup. |
| #1393 | Karpathy/autoresearch re-home/recalibration audit. Good focused curation follow-up. |

### D. Product/RFC decisions, not implementation-first

| Issue | Decision needed |
|---|---|
| #990 | Commit identity/security posture for delegated worker commits. |
| #1101 | Evidence Model & Integrity umbrella: choose which subparts become real work. |
| #1104 | Governance of canonical graph: ratify authority/quorum/dispute model. |
| #1178 | Decide whether `skill-trees/` leaves this repo. |
| #1302 | Lexicon-of-record RFC. Blocks several semantics-poisoning cleanups. |
| #1267 | Source-of-truth / stale-doc archival depends on #1302 direction. |
| #1307 | Agent Skills install standard; EPIC #1336 adjacency. |
| #1308 | Automate curate-trending and evidence ingest; broader discovery automation. |
| #1309 | Blog publishing pipeline; EPIC #1336/content system adjacency. |

### E. Evergreen/community issues to leave open

These are intentionally not eradicated by count; they are standing contributor invitations or lower-priority long-tail work.

- #844, #845, #847, #848, #983, #984 — good-first/community contribution surfaces.
- #494, #495, #455, #1326 — badge roadmap/assets family.
- #565, #638, #652, #858, #952, #964, #973, #1001, #1102 — deferred roadmap/research/architecture issues.

## Current open issue count snapshot

As of the check that generated this file:

- Repo-wide open issues: **67**.
- Original tracker live-closed: **48 / 97 = 49.5%**.
- Integration-adjusted done estimate after #1395 closes four direct issues: **~52 / 97 = 53.6%**.
- Expected repo-wide open count after those four close: **~63**.

