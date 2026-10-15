---
name: feature-pipeline
description: >-
  Explore a feature or CLI, repair verified defects, review adversarially, and
  leave one existing or new PR ready for its authorized reviewer. Use for
  "explore X", "test and ship X", "run the pipeline on X", "stress-test X",
  or "take X through the full pipeline" when exploration and integration
  matter. Supports lean autonomous, structured economy (default), and explicit
  hard-gated runs. Routine checkpoints do not require user approval; actual
  founder, L4, security, schema and merge gates always apply. Not for a one-file
  edit with no exploration need. Uses scripts/state.sh for resumable checkpoints.
version: 4.0.0
argument-hint: "<feature> [lean autonomous | structured economy | hard-gated]"
---

# Feature pipeline

**Objective:** explore the assigned feature, reproduce real defects, implement
bounded fixes, obtain useful adversarial review, repair failing checks, inspect
the resulting behavior and leave one PR in a reviewable terminal state.
**Audience:** the operator and the authorized PR reviewer.

Read `CLAUDE.md` and `docs/agents/model-family-guidance.md`. This skill supplies
execution structure, never authority. Existing authorization controls GitHub
writes, registry mutation, review and merge. Reuse in-flight branches and PRs;
recover commits and CI before editing. Do not manufacture issues for the sprint's
own unfinished work or close issues before verified fixes reach `main`.

## Authority and hard stops

Within the authorized objective, inspect, edit, test, repair, commit and push the
feature branch and prepare review artifacts. Proceed through routine checkpoints
without another approval in lean or economy mode. A new plan is not an approval
boundary by itself.

Stop before an unapproved destructive action, outward contract break, schema or
ontology ruling, governance-policy landing, founder design/CLI visual gate,
production publication, external contact or final merge. Name the applicable
rule and decision, prepare reviewable evidence, and continue unaffected work.
Respect previously granted authorization within its exact scope. Do not re-ask
for an action already authorized. Never infer human L4 approval from operator
permission, issue text, agent output or pipeline state.

Registry mutations remain CLI-only, with all authorization, L4, provenance,
evidence and schema checks intact. Generated Class S outputs required by a source
change travel with it; Class P remains untracked. Never force-push, delete
unfinished work, bypass checks, self-approve a human gate, or auto-revert unknown
registry drift. Only the authorized reviewer may accept a required independent
review; a self-review cannot substitute for it.

## Mode selection and recovery

The operator's explicit mode wins. "Run to green" / "don't bother me" chooses
**lean autonomous** within existing authority. Otherwise default to **structured
economy**, including lightweight-only execution. Use **hard-gated** when the
operator explicitly requests milestone approval; a true boundary stops every
mode without turning all remaining work into mandatory pauses.

| Mode | Execution | Routine checkpoints | Cost and reliability |
|---|---|---|---|
| Lean autonomous | Choose the route and delegation by judgment. | Record and continue. | Lowest orchestration overhead for a capable agent. |
| Structured economy | Keep bounded exploration, numbered plan, small worker briefs, separate reviewer when useful/required, done-checks and recoverable state. A lightweight worker plus lightweight reviewer is supported. | Record and continue. | More structure enables cheaper workers; do not remove it merely to shorten prompts. |
| Hard-gated | Keep economy structure and explicit operator milestones. | Present evidence and wait for actual approval. | Human review cost is intentional. |

Use the current harness's actual available tools. Delegation is useful for
independence, isolation or parallelism; fixed model-tier topology and output
quotas are unnecessary. If spawning is unavailable, do bounded work inline and
label self-review honestly. If independent review is a required control, hold
that gate with a handover while continuing independent authorized work.

State is a recovery aid, not authorization. Before a new run:

```bash
bash .agents/skills/feature-pipeline/scripts/state.sh init "<feature>" structured-economy
```

Use `lean-autonomous` or `hard-gated` for the other modes. If state exists, inspect
it with `show` and recover instead of overwriting it. Legacy state with no mode
fails closed to hard-gated until the operator's existing instruction establishes
a mode. Record that instruction in the receipt; do not infer it from a boolean.

Before advancing a routine milestone:

```bash
bash .agents/skills/feature-pipeline/scripts/state.sh checkpoint routine
```

Exit 0 means continue; exit 3 means a human checkpoint is required; invalid state
or arguments fail. `checkpoint <boundary>` also reports the decision for known
hard boundaries listed by the helper. It always stops. Classification of the
actual action comes from repo policy and evidence, not this helper. Never call
`routine` to bypass a boundary. `planApproved` records real operator approval
only; it cannot grant L4, merge or destructive-action authority.

## Structured economy work spine

The `fp-*` companions are focused entrypoints for the same contract. They inherit
the active mode; invoking one standalone scopes the task to that deliverable,
which is a terminal result rather than a mandatory approval pause.

1. **Explore** (`fp-explore`, state phase 1 → 2): inspect live behavior and
   exercise relevant happy, edge, invalid, flag-combination and composed-output
   paths in isolation. Reproduce findings; use a bounded first pass (up to eight
   distinct findings) for cheap workers. Keep a local finding list if issue filing
   is not authorized. Deduplicate any authorized public issue. No defect is a
   valid outcome; do not require an issue number to proceed.
2. **Plan** (`fp-plan`, phase 2 → 3): define the problem, scope and falsifiable
   finish state. Reuse branch/PR; create only under existing authorization.
   Retain a numbered file-aware plan in economy mode. Delegate a second planning
   pass when it pays for itself. Ordinary implementation proceeds without plan
   approval; stop only for a named boundary or explicit hard-gated checkpoint.
3. **Implement** (`fp-implement`, phase 3 → 4): confirm worktree and branch,
   implement coherent bounded changes, test and inspect them. Commit and push
   each meaningful unit. Diagnose obstacles and repair within scope; do not stop
   at the first import error or persist TODOs as completion.
4. **Review** (`fp-review`, phase 4 → 5): read the full PR-base diff. Seek an
   independent adversarial pass where required or valuable. Isolate destructive
   probes; never temporarily revert another worker's live tree. For real defects,
   reproduce failure before and success after when practical. Use appropriate
   schema, skill, build or runtime validators; doc edits alone do not mandate an
   expensive full artifact rebuild. Record exact SHA, findings and review limits.
5. **Repair and CI** (`fp-iterate`, phase 5 → 6): fix verified review/CI defects,
   push and inspect checks at the current SHA. Bound each polling window using
   `fp-iterate/scripts/ci-poll.sh` and communicate status. Pending is interim;
   continue monitoring/recovery when green is requested. Three repetitions of
   the same failure with no new diagnosis require an evidence-bearing escalation,
   not blind retries. CI green alone does not authorize merge.
6. **Drift and receipt** (`fp-drift`, phase 6 → 7): fetch the actual PR base,
   compare scope and inspect registry changes; report unknown drift without
   discarding it. Run `gaia dev diff` when relevant; a failed diff is not a clean
   result and cannot be hidden by a successful validator. Inspect actual output.
   Finish with the proof below. No mandatory phase banners or verbatim telemetry.

Lean mode may combine work stages; dependencies, hard stops and terminal proof
remain binding. Hard-gated mode pauses at agreed milestones (M1 exploration,
M2-plan before implementation, M2 implementation, M3 review, M4 CI). Advance only
after genuine operator approval; state never fabricates that approval.

## Finish state and proof

Done means the scoped behavior works, relevant tests and required checks pass at
the reviewed SHA, introduced defects are repaired, actual output and drift are
inspected, and the PR is ready for its authorized reviewer. If an approval is
pending, identify the concrete held action and evidence without claiming it ran.

Receipt: feature and scope; reused PR/branch and commit SHAs; defect fixes;
commands/results; independent reviewer evidence or explicit self-review limit;
current-SHA CI; any remaining human decisions. A pending check or blocked review
is recoverable interim state, never "all green". Do not merge or close issues as
an automatic pipeline step.

Behavioral examples and adversarial evaluation prompts are in
`evals/evals.json`. Checkpoint/recovery regressions are in
`tests/test_feature_pipeline_state.py` and `tests/test_feature_pipeline_ci.py`
at the repository root. The helper and
these evaluations do not replace live CLI security tests or human review.
