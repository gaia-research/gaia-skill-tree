---
name: fp-review
description: >-
  Adversarially review the full relevant PR diff with isolated probes and
  meaningful before/after checks. Use for "review the PR", "sandbox review",
  or the review stage; retain required reviewer independence and report self-
  review limits honestly.
version: 4.0.0
---

# Review the complete change

**Objective:** give the authorized reviewer evidence of correctness and defects.

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

Recover the PR base and current SHA (phase 4 follows implementation). Review the
full relevant diff against that base, including original commits and outward
contracts, rather than a convenient last commit or assumed `origin/main` base.
Use a fresh independent reviewer and isolated worktree when required or valuable.
Cheap worker + cheap reviewer is a supported economy path; independence does not
require a fixed higher model tier.

Reproduce relevant defects before the fix and success afterward when practical.
Run adversarial boundary cases for changed authorization or input handling and
appropriate existing validators. Schema changes use graph validation; canonical
skills use quality/playbook/mirror checks; generated artifact changes use their
builder checks. A prose-only edit does not itself require rebuilding every doc.
Never revert another worker's live worktree to produce a RED test.

Return SHA, changed surfaces, commands/results, findings with file/line and verdict.
Post a PR comment only if authorized; otherwise save the review locally. Record
its path or authorized URL. Do not approve your own required independent control.
If no independent reviewer is available, record self-review honestly, continue
independent work and hold the required review/merge gate with a concrete handover.

Done: review evidence exists and limits are explicit. Advance phase to 5; verified
findings go to `fp-iterate`. In hard-gated mode M3 presents the review and waits.
No implementation commits are authored by this read-only review entrypoint.
