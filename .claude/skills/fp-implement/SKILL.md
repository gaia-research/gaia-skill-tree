---
name: fp-implement
description: >-
  Implement a scoped feature-pipeline plan in coherent commits and push each
  meaningful unit. Use for "implement the plan", "apply the plan", or the
  implementation stage; routine lean/economy work does not require
  planApproved, while explicit human gates remain binding.
version: 4.0.0
---

# Implement the plan

**Objective:** leave a tested, inspectable change on the correct feature branch.

## Shared execution contract

Read `../feature-pipeline/SKILL.md` relative to this skill directory. Inherit its
mode, authority, hard stops and finish-state proof. Default is structured economy;
lean mode may combine stages. A routine checkpoint records progress and continues
in lean/economy mode. Only explicit hard-gated milestones or an actual unapproved
authority boundary wait for human approval. Standalone invocation ends when this
skill's scoped deliverable is complete; it does not require approval to perform
already-authorized work. Use the actual harness tools, never invented spawn APIs.

State helper: `bash .agents/skills/feature-pipeline/scripts/state.sh`.
Inspect existing state and Git/PR state before work. State and `planApproved` are
recovery notes, never authorization or L4 approval. Refer to the shared skill's
checkpoint command before advancing; do not classify a real boundary as routine.

## Work and done-check

Read the current plan and finish-state checks; verify actual branch/worktree and
recover existing commits. Phase 3 signals planning is complete. Missing or stale
plan content requires recovery from live evidence, not blind guesses. Never
checkout over unfinished changes or recreate completed work.

For hard-gated mode, require genuine operator approval for M2-plan before code.
For lean/economy mode, `planApproved == false` is not a blocker to ordinary bounded
work. In all modes stop before any actual unapproved authority boundary, even if
`planApproved == true`. Human L4 and CLI authorization are never inferred from it.

Implement coherent units, run appropriate tests, inspect output, repair failures,
and stage only relevant files. Confirm branch immediately before each commit and
push each meaningful commit immediately. No force-push or history rewrite. Keep
commit boundaries reviewable; a plan bullet need not equal one commit.

Registry mutations use canonical CLI commands with authorization, L4, provenance,
evidence and schema checks intact. Never hand-edit registry or timeline data.
Regenerate required Class S artifacts with the canonical builder and include them
with the source change; leave Class P untracked. Do not repeat the old blanket ban
on committing required `docs/graph/*` outputs.

Diagnose import/test failures and fix within scope. Escalate with evidence when
blocked outside authority or after three identical failures with no new diagnosis;
ordinary obstacles do not mandate a user pause. Preserve interrupted work safely
and report the exact incomplete state rather than claiming completion.

Done: scoped behavior and tests pass locally, actual output is inspected and
meaningful commits are pushed. Advance phase to 4, record evidence and continue to
`fp-review` in a full run. Hard-gated M2 waits with the diff and test receipt.
