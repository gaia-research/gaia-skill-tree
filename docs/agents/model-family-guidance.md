# Model-family authoring guidance

The one reusable layer for how agent-facing instructions are written for the current model family. Skills, playbooks and agent docs inherit it. They state only what is specific to them: the objective, inputs, authority envelope, stop conditions and terminal proof.

Governing issue: #2039. Migration evidence: [`agent-instruction-migration-map.md`](./agent-instruction-migration-map.md). This document is founder-gated policy text.

## 1. What this layer is and is not

- **Is:** the rules for assigning work to a capable agent and for knowing when it is done: objective first, explicit authority boundaries, completion measured by proof.
- **Is not:** role definitions (who does what in a pipeline), repository invariants (CLI-only mutation, schema gates, governance, merge rules), or harness syntax (tool names, spawn calls, model selectors). Those live in `CLAUDE.md`, `AGENTS.md`, `GOVERNANCE.md`, the playbook contract and the harness adapter. When this layer and an invariant disagree, the invariant wins.

## 2. Target family

The current target is the GPT-6 family as named in issue #2039: **GPT-6 Luna**, **GPT-6.1 Sol** and **GPT-6 Astra**, plus their successors. This section is the only place in agent-facing guidance that names them. Skills refer to work by role and mode ("a cheaper worker", "a stronger reviewer", "lean autonomous"), never by model name. Runtime model selection is configuration, not instruction. Harness-specific tier names used by a runner's own configuration are out of scope here.

## 3. Assignment shape: objective first

Prefer an objective-first assignment that makes these explicit; keep short bounded tasks proportional:

1. **Objective:** the result wanted, in one sentence.
2. **Audience:** who consumes the result (a maintainer, the founder, the next agent).
3. **Context and constraints:** only what the agent cannot cheaply discover for itself.
4. **Authority:** what it may do on its own, what needs a named human, and what it must never do (section 4).
5. **Finish state:** falsifiable observable conditions under which the work is done.
6. **Proof:** the evidence the final receipt must contain (section 6).

Do not write a procedural recipe unless the sequence is load-bearing (section 10). A plan is an intermediate artifact, not the deliverable.

## 4. Independent action versus approval boundaries

| Class | The agent may do this on its own | Examples |
|---|---|---|
| **Independent action** | Reversible work inside the authorized objective and working branch or worktree; repository-specific gates still apply. | Read, search, edit in-scope files, run tests and validators, commit and push to the feature branch, open a draft PR, run sandbox checks, re-run CI, repair its own failures. |
| **True boundary (stop)** | Prepare a concrete, reviewable proposal within existing authority; stop before crossing an unapproved boundary and name the decision and evidence. | Destructive or irreversible change (force-push, deleting unmerged work, removing registry or evidence data). Founder design gate (human-gated frontend or visual changes). Schema or ontology ruling. Landing unapproved governance or policy text. Final merge to `main`. Production publish. External contact (issues, PRs, comments) without applicable explicit or standing authorization. Breaking change to an outward contract that users depend on. |
| **Prohibited** | Not a pause. A refusal. | Hand-editing generated or registry data where a CLI verb exists. Bypassing CLI pre-flight checks or authorization. Self-approving a boundary. Relaxing a gate because the model is stronger. |

Rules:

- Existing explicit or standing authorization applies to its stated scope. Do not ask again for the same authorized action; never infer L4 approval from general operator permission. This layer grants no new permission, GitHub-write authority, or merge authority.
- Approval attaches to a **boundary**, never to a phase. "Ask before each phase" is ceremony unless a real boundary sits inside that phase.
- A stop names the boundary it hit. An agent that cannot name one should not stop.
- A stronger model does not remove a boundary. It only removes the need for scaffolding that compensated for a weaker one.

## 5. Persistence and completion

Done means: **implement, test, inspect, repair, prove.**

- **Implement** the objective itself. Do not stop at a plan.
- **Test** with the repository's own gates (named in the skill or in `CLAUDE.md`).
- **Inspect** the actual result: the output, the diff, the rendered artifact. An exit code alone is not inspection.
- **Repair** failures inside the authority envelope. Bounded retry: the same failure three times with no new diagnosis is an escalation with the exact log excerpt, not a fourth blind attempt.
- **Stop** when the finish state holds or a boundary is hit. Not earlier, not later.

## 6. Receipts prove the finish state

A receipt is evidence that the finish state holds. It is not a narration of the process. It contains:

- the changed surfaces (files, PR, branch);
- the commands run and their results;
- commit SHAs and the PR URL;
- CI status at the reviewed SHA; pending checks are a recoverable interim state, not proof of completion. Monitor when the task requires green checks and repair authorized failures;
- any boundary hit, with the decision needed;
- known limits, such as "self-review only" or "CI pending".

Keep it short. Narration requirements ("explain each step") do not improve correctness and are not part of this layer.

## 7. Delegation is a judgment, not a ritual

Delegate when isolation, parallelism or an independent reviewer materially improves the result. Do not delegate to satisfy a phase diagram.

Two forms of delegation are **cost-amplifying** and should be kept where they apply:

- a cheaper worker given an explicit acceptance contract (exact files, exact done-check), so that it does not wander;
- a separate reviewer where a review is a control. A reviewer that is the same agent as the author is still useful, but the receipt must label it as a self-review.

## 8. The three modes

A skill being migrated under this layer declares which mode is its default and how the operator changes it. The operator's words decide first; the skill's declared default decides otherwise.

| Mode | Use when | Stops | Phases and scaffolding | Cost profile |
|---|---|---|---|---|
| **Lean autonomous** | A capable model, a bounded objective, reversible scope, or an operator who asks to "run to green" or not be bothered. | True boundaries only. Ordinary bounded work proceeds without user approval. | None mandated. The agent sequences the work and may delegate as a judgment call. | Lowest orchestration overhead per run. Relies on the model; a failed run costs more than a scaffolded one. |
| **Structured economy** | Any run a cheaper (Flash or Luna class) model may execute, and the default when the operator does not choose. | True boundaries plus bounded stop conditions (for example, the three-failure escalation). | **Kept:** phase decomposition, worker and reviewer tiering, state checkpoints, checklists, explicit done-checks. Phase gates do not pause the run. | Higher scaffolding tokens per run. Lower total cost than a stronger model or repeated failed runs. This is the cost-amplifying case. |
| **Hard-gated** | The operator asks for gates, or the work touches a governed surface where the gate is the point. | Required phase gates (for example approval before implementation and review before merge) plus true boundaries. Nothing else stops the run. | Kept, with the gates made explicit. | Most human round-trips. Reserved for work where the human decision is the value. |

Selection and escalation:

- An agent may **escalate** from lean or economy to hard-gated when a boundary appears.
- An agent may **not** de-escalate a boundary on its own. A boundary removed in lean mode is still a boundary.

## 9. Classification vocabulary

Used by the migration map to classify every structure in an instruction surface:

- **Governance-critical:** required regardless of model. Keep.
- **Reliability-critical:** the task itself benefits from deterministic structure (command spines, pre-flight checks). Keep.
- **Cost-amplifying:** lets a cheaper model perform above its native reliability. Keep, and state the purpose.
- **Legacy ceremony:** no longer pulls its weight: a pause with no boundary, narration nobody reads, tier choreography a stronger model would decide better. Remove or make conditional.

## 10. Cost implications: rules for editing

- Measure before removing. A removed scaffold saves tokens only on runs that would have succeeded without it.
- Removing cost-amplifying structure from a skill that runs on cheap models raises total cost: more failed runs, more human rework, more reruns.
- Lean mode is cheaper per run only with a capable model. Running it on a cheap model shifts cost into failures.
- A procedural step is kept when the sequence is load-bearing: a deterministic mutation, a safety-sensitive ordering, or a step whose output the next step cannot reconstruct. Otherwise the step is a judgment with a done-check.

## 11. Harness adapters

Tool syntax, spawn mechanisms, slash-command names and model selectors belong in the harness adapter section of the relevant skill, or in `CLAUDE.md`. Provider-specific compatibility guidance is allowed only where the harness mechanics genuinely differ. It never restates the objective or the boundaries.

## 12. Authoring checklist

Before a skill or playbook under this layer is merged:

- [ ] Objective, audience, authority, finish state and proof are present (section 3).
- [ ] Every human approval stop names a true boundary from section 4, an explicit operator gate, or a diagnosed blocker outside current authority.
- [ ] Ordered steps appear only where the sequence is load-bearing, and each step is marked as run (strict) or judgment (advisory).
- [ ] The default mode is declared, and the operator's way to change it is stated.
- [ ] No model names outside this document and the migration map.
- [ ] Cost-amplifying structure is labelled with its purpose, so that a later edit does not remove it as ceremony.
