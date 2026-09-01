# Agent playbook contract

Agent playbooks carry Gaia's method above the CLI. The CLI remains the canonical
mutation surface; a playbook fixes the order, authority envelope, stopping rules,
and proof so an agent does not reconstruct them from scattered prose.

This contract generalizes the Steward routine packet. It is opt-in: a canonical
`.agents/skills/*/SKILL.md` becomes a playbook only when its YAML frontmatter has
`playbookVersion: 1`. The `.claude/skills/` tree is a generated mirror and is
never an independent authoring surface.

## Required frontmatter

Alongside the normal `name` and discriminative `description`, a playbook declares:

```yaml
playbookVersion: 1
class: B
objective: Take one bounded input to one reviewable terminal state.
capability: >-
  Apply the named judgment inside the declared envelope. This is a scheduling
  hint, not an authority gate.
preconditions:
  - all required inputs exist
steps:
  - id: inspect
    run: gaia dev list --generic --json > {snapshot}
    proves: snapshot captured
  - id: decide
    judgment: MAP | DUPLICATE | DEFER
    rules: CURATION-CORE.md bounded decision precedence
stopConditions:
  - a Class C ontology ruling is required
proof:
  - every mapped id exists in the recorded snapshot
done: A validated review packet exists and no mutation has crossed its hard stop.
```

- `class` is authority, not difficulty: A is mechanical and reversible, B grants
  bounded interpretation, and C waits for the founder.
- `capability` is prose used for scheduling. It must not name a model, provider,
  harness, or capability tier, and it never widens `class`.
- `preconditions` are evaluated as one set before step 1. Report all failures
  together.
- Every step has a stable `id` and exactly one of `run` or `judgment`.
- A `run` step declares the proof it produces. A `judgment` step declares its
  bounded answer space and the rules governing the choice.
- `stopConditions` must name a real landing place: the rolling lane, a review
  packet, or the founder queue. A stop with nowhere to land is not an escalation.
- `proof` is the terminal evidence set. `done` is a falsifiable terminal state.

The machine-readable shape is
[`playbook.schema.json`](./playbook.schema.json). The checker validates canonical
skills only; mirror integrity is a separate, mandatory gate.

## Command spine grammar

`run:` is data, not an unrestricted shell. The contract checker accepts only:

1. optional leading `NAME=value` environment assignments;
2. a `gaia` command resolved against the checkout's live nested argparse tree; or
3. `python` / `python3` followed by a tracked `scripts/...` path;
4. optional `{lower_snake_case}` placeholders as argument values; and
5. at most one terminal stdout redirect, `>` or `>>`, to a placeholder or path.

The checker rejects pipes, chained commands, command substitution, process
substitution, background execution, and unparsed shell fragments. For `gaia`, it
validates the command path, flags, literal choices, and positional arity without
executing the command. For a Python script, it verifies that the tracked script
exists; that script owns its deeper argument contract until it exposes a parser
the checker can inspect.

This constrained grammar is deliberate. If a step cannot be expressed inside it,
move the mechanism into a tested CLI verb or script and keep the playbook spine
small.

## Proof layers

Every shipped playbook owes four distinct proofs:

1. **Contract:** its frontmatter and every `run:` match the live command surface.
2. **Triggering:** realistic positive and negative prompts select the right entry
   point. Test prompts live under the canonical skill directory and are referenced
   from `SKILL.md`.
3. **Execution:** a fixture run reaches the declared proof without crossing a stop.
4. **Floor:** the weakest reasoner that completes the fixed fixture correctly,
   twice from a cold start. This is measured initially, not a release gate.

The contract and mirror checks are CI gates. Triggering and execution evidence are
required when the first playbook lands. Floor measurements remain advisory until a
later founder ruling.

## Change discipline

- Author once under `.agents/skills/`; sync with
  `python scripts/sync_agent_skill_mirror.py` and gate with `--check`.
- A playbook whose command spine drifts fails CI; fix the playbook or the command in
  the same change that caused the drift.
- Differences in batch size, cadence, or recoverability are parameters of one
  playbook. Different terminal proof or authority is a different playbook.
- Final integration-to-`main` merges remain human decisions regardless of a
  playbook's class or capability prose.

