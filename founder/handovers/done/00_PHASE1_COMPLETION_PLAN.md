# Phase 1 Completion Plan: Trust Infrastructure

This document outlines the final sequence of Pull Requests required to reach 100% completion for Phase 1 (Trust Infrastructure). It serves as the master roadmap for the remaining deliverables, pointing to specific handover documents for individual coding agents.

## Goal
Finalize the trust infrastructure by enforcing rank gates, implementing the security scanner, rolling out the 4-tier verification workflow, drafting the benchmark specification, and wrapping up the CLI share UI.

## PR Sequence

| Order | PR / Issue | Deliverable | Handover Document | Subagent Weight |
|---|---|---|---|---|
| **PR-1** | #699 | **Rank Gates** | `RANK_GATES_HANDOVER.md` | Medium |
| **PR-2** | #185 | **Security Scanner** | `SECURITY_SCANNER_HANDOVER.md` | Heavy |
| **PR-3** | #658 | **Verification Workflow** | `PR3_VERIFICATION_WORKFLOW_HANDOVER.md` | Heavy |
| **PR-4** | #649 | **Benchmark Framework Design** | `PR4_BENCHMARK_FRAMEWORK_HANDOVER.md` | Light (Research) |
| **PR-5** | #128 | **Gaia Share Static Page** | `PR5_GAIA_SHARE_PAGE_HANDOVER.md` | Medium |
| **PR-6** | #642 | **Narrow-Path Tree Rendering** | `PR6_NARROW_PATH_TREE_RENDER_HANDOVER.md` | Light |
| **PR-7** | N/A | **CI Workflow Trigger Fix** | `PR7_CI_WORKFLOW_TRIGGER_FIX_HANDOVER.md` | Light |
| **PR-8** | #155 | **Auth Logout Revoke Patch** | `PR8_AUTH_LOGOUT_REVOKE_PATCH_HANDOVER.md` | Light |

## Dependencies & Constraints
- **Sequential Execution**: PR-1 (Rank Gates) MUST land before PR-3 (Verification Workflow), as the Verification tiers directly depend on the Overall Trust Grades enforcing ranks.
- **Documentation Integrity**: All agents must respect `CONTEXT.md` terminology (e.g., using "evidence grades" instead of "classes", "trust numbers" instead of "scores").
- **Phase 2 Boundary**: No features from Sprint 2 (Trending Engine, Rising Skills) should be implemented during these PRs.

## Non-Code Follow-ups (Orchestrator Scope)
- **#647 Database Limits 1-Pager**: The orchestrator will draft a 1-page note detailing git-as-database limits and Supabase/Dolt migration triggers, parking it directly as a comment on issue #647.
- **Mid-July Recalibration RFC**: The orchestrator holds a scheduled task to open the Trust Model recalibration RFC ~1 month post-ship to revisit pillar rule thresholds.

Once PR-8 merges and the 1-pager is posted, Phase 1 is officially complete and we transition immediately to Phase 2 (Sprint 2).
