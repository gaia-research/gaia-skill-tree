---
name: fp-drift
description: >-
  Inspect scope and unexpected registry drift against the actual PR base and
  leave a concise final receipt. Use for "check for drift", "wrap up the
  pipeline", or the final stage; never silently discard unknown changes or
  infer a clean diff from validator success.
version: 4.0.0
---

# Inspect drift and prove the finish state

**Objective:** leave a reviewable PR with honest final evidence and held decisions.

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

Recover live PR base, tip, review evidence and CI. Fetch the actual base and inspect
its diff, not an assumed main branch. A standalone drift audit can run with CI
pending but must report that limit. A full pipeline cannot claim complete until
required checks are green at the reviewed SHA.

Inspect changed files and, where relevant, `gaia dev diff` against registry state.
A failed diff is an inspection failure; do not hide it with `|| gaia dev validate`.
Validation proves integrity, not absence of drift. Classify changes against the
objective. If unexpected registry/evidence changes have no known owner, stop the
affected decision, show ID/field/base/branch values and request disposition; do
not silently revert, normalize or accept them. Continue independent work.

When available, `python scripts/ci_churn.py <pr-number>` can inform a concise cost
receipt; missing telemetry is not a task blocker. No mandatory verbatim report.

Done: behavior, tests, review, scope and current-SHA CI are inspected. Receipt
includes feature/scope, PR/base/branch/SHA, fixes, commands/results, review identity
and independence limits, CI and any concrete founder decision still required.
Record phase 7 only when terminal proof holds; retain actual `ciStatus` green
rather than replacing verification status with a vague done flag. Never merge or
close issues as an automatic terminal action.
