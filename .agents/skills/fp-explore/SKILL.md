---
name: fp-explore
description: >-
  Explore a feature or CLI, reproduce defects and record bounded findings. Use
  for "explore X", "find issues with X", or the exploration stage of feature-
  pipeline; standalone runs return findings without automatically expanding
  scope.
version: 4.0.0
---

# Explore the feature

**Objective:** give the operator or next worker a reproducible view of defects.

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

Resolve the feature from the operator's instruction, then state. If both are
missing, request the target. Exercise relevant happy, edge, invalid-input,
flag-combination and composed-output cases in a sandbox. Retain this decomposition
for cheap workers; avoid arbitrary probes that do not apply to the feature.
Capture expected/actual behavior, exact reproduction and severity. Bound the
initial pass to eight distinct findings; prioritize real high-impact problems.

Deduplicate before any authorized issue filing and use `--body-file`. Existing
operator instructions may prohibit new issues; keep findings locally or in the
existing PR instead. Record each finding/authorized issue immediately. No findings
is a valid outcome; do not fabricate an issue to unlock planning.

Done: findings are reproducible and scoped, no forbidden external action occurred,
and state phase advances from 1 to 2. In a full authorized pipeline continue to
`fp-plan` after a routine checkpoint; in hard-gated mode present M1 evidence and
wait. A standalone exploration returns the finding receipt.
