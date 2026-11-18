# P1 resumption: tier-first routing and queued integration update

## Current authority and state

The founder resumed the P1 task after publishing the paused partial checkpoint. Code-only implementation and offline verification may resume. The partial source checkpoint is `827c588e0666acfa3f905afea0e22268438bad79`; the published pause/cost handoff is `ba0e6a05c3d818b8360a6aa1a501f7c3dbf2fc96`. This is **resumed implementation, still PARTIAL / UNREVIEWED / NOT EXECUTION-READY**, not P1 acceptance. Historical pause reports and all prior receipts remain preserved.

## Founder-confirmed routing

The founder's tier clarification, verbatim:

> Yep. Luna shared L1 for very bounded tasks. L2 default standard tasks. L3 escalste to terra shared. L4 Argon. L5 Opus.

| Tier | Route | Use |
|---|---|---|
| L1 | Luna shared, `openai-codex/gpt-6-luna`, medium | Very bounded administration/mechanical work |
| L2 | Hydrogen, `antigravity/gemini-4-hydrogen`, medium | Default standard implementation work; start here |
| L3 | Terra shared, `openai-codex/gpt-6.1-terra`, high | Escalation when justified; also the independent reviewer role |
| L4 | Argon, `antigravity/gemini-4-argon` | Further escalation, not default assignment |
| L5 | Opus, `antigravity/claude-opus-5-5`, medium | Exceptional escalation only; extremely limited availability |

Required independent Terra review is separate from escalating implementation. No evidence-based L2 implementation escalation has been established. An Argon no-tool runtime probe ran, but no Argon implementation was started. Sol is no longer the assigned implementation route. No automatic retries/fallbacks, nested agents, or silent route/effort changes. No turn cap; retain the campaign's two-hour worker limit and single-author discipline. Escalations must identify the concrete blocker and why the next tier is needed.

## Queue the branch update; do not integrate the pending branch now

The founder corrected the update premise:

> My bad, integration/tstack-suite-2472 is the one landing soon but not yet. Plan to queue update or rebase later down the line

Observed refs at resumption: `main` remains `9b4d9b98043140188f00b14d0ac8fa6bc02491b7`; pending `integration/tstack-suite-2472` was `66784d81c248c4abf5c12965d6bee971c18aa1b1`. These are observations, not future pins or a claim that the pending branch landed. Continue P1 on its current base for now. Do not merge/rebase/cherry-pick the unlanded branch as a prerequisite.

When the pending work lands, pin the then-current main and P1 tips; preserve recoverable Git checkpoints for both histories and any uncommitted work; compare overlapping changes and canonical data. Rehearse the chosen feature update in an isolated worktree. Preserve valid changes from both sides, including schema, named records, evidence/history, decision JSON, and receipts. Never resolve conflicts with blanket ours/theirs or discard/recreate data. Verify ancestry/diffs and rerun affected tests before proposing any replacement of published history. An update/rebase may be used later as authorized, but this is not permission to merge PRs, rewrite main/integration, or force-push blindly.

## Immediate L2 objective and remaining gates

Hydrogen resumes the ratified repository-envelope draft, recovers current behavior through graft and offline tests, repairs verified in-scope defects, and records exact local commits and complete test summaries. The ratified `repo_envelope` / `preserve_plan` JSON is unchanged. One repository envelope must retain separate exact named findings and their identity, source/version, digest, carry-forward and authorization scope. AgentDB remains a distinct release source from Ruflo.

Preserve #1833 body/history and every actual held-repository write block. The raw-body versus CLI-added-final-LF digest distinction is already explained in the historical pause report; neither digest grants migration execution approval. Unknown/corrupt claimed targets fail closed. No live backlog crawl, issue/registry/schema/trust/permission/label/variable mutation, migration, or P2–P7 advancement. No workflow dispatch by the implementation worker. No merges.

Next gates: finished focused/adversarial results; independent Terra-shared review of the exact immutable candidate; non-author full regression/parity including the new root workflow test; publication through the existing draft PRs. The single conditional ordinary `apply=false` allowance remains unconsumed and can be considered only after those gates and all remaining safety/data requirements. A known legacy hold or a successful planner alone is not P1 PASS or write readiness.

Retain the pause cost snapshot as historical partial accounting; it is not a complete campaign cost or invoice. Preserve `founder/MEMORY.md` and existing raw receipts. This record updates routing and continuation status, not data authority.
