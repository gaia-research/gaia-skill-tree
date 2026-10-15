---
name: fp-plan
description: >-
  Turn verified findings into a bounded file-aware plan and reuse or prepare a
  draft PR. Use for "plan the fix", "draft the implementation plan", or the
  planning stage of feature-pipeline; preserve actual human gates without
  making every plan require approval.
version: 4.0.0
---

# Plan the bounded change

**Objective:** give the implementer a scoped plan with observable done-checks.

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

Read findings and relevant source; issue numbers may legitimately be empty.
State phase 2 expects recovered exploration evidence, not necessarily public
issues. Write the problem, constraints, file-aware plan and finish state. In
structured economy, keep a small numbered plan with change/rationale/check per
item and bounded worker briefs; request a separate planner only when useful.

Reuse the existing branch and PR, and verify their actual base. Create a branch
or draft PR only within current authorization. Use real newlines and `--body-file`
for PR text; link governing issues without closing any prematurely. Persist branch,
PR number/URL and the plan reference for recovery.

In lean/economy mode a routine plan needs no user approval: leave `planApproved`
false and advance state to phase 3. In hard-gated mode present the concrete plan at
M2-plan and await explicit approval before implementation; record `planApproved`
true only after receiving it. A true schema/ontology/design/security boundary
stays held in every mode. State cannot approve it. Continue unaffected work.

Done: the implementer can locate the plan, branch, finish-state checks and held
decisions. Continue to `fp-implement` in an authorized full run; a standalone plan
returns that deliverable without implementing unrequested work.
