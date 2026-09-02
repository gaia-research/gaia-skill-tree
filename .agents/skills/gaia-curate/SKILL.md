---
name: gaia-curate
description: >-
  Compile one or more public skill sources into validated Gaia L4 discovery
  packets. Choose single, checkpointed, dynamic, or trending mode from the
  requested scale and recoverability; stop before evidence, intake, registry,
  Git, or PR work.
version: 4.0.0
argument-hint: "<source-url-or-manifest> [single|checkpointed|dynamic|trending]"
playbookVersion: 1
class: B
objective: >-
  Turn bounded public skill sources into schema-valid discovery-packet-v2
  artifacts and an L4 human review presentation without mutating Gaia.
capability: >-
  Preserve source provenance, apply deterministic deduplication and bounded
  generic-mapping judgment, and assemble reviewable discovery packets.
preconditions:
  - A public source URL or bounded source manifest and the requested operating mode are known.
  - Each review candidate can resolve to an actually fetched upstream SKILL.md or land as DEFER or NOT_A_SKILL.
  - The checkout provides the live Gaia CLI, the canonical packet schemas, and the packet validator.
  - Output paths and any checkpoint or concurrency limits are fixed before processing begins.
steps:
  - id: snapshot-generics
    run: gaia dev list --generic --json > {generic_snapshot}
    proves: The complete generic snapshot used by every mapping decision was captured.
  - id: prefill-candidate
    run: gaia dev prefill {candidate_id} --name {candidate_name} --description {candidate_description} --url {source_url} --source-lane {source_lane} --json > {prefill_packet}
    proves: Deterministic artifact, dedupe, and bounded mapping inputs were produced by the live CLI.
  - id: decide-disposition
    judgment: MAP | NEW_GENERIC | DUPLICATE | NOT_A_SKILL | DEFER
    rules: CURATION-CORE.md decision precedence; select only supplied strong mappings and defer ambiguity.
  - id: validate-packet
    run: python3 scripts/validate_discovery_packet.py --generic-snapshot {generic_snapshot} {packet}
    proves: The canonical validator accepted the completed discovery-packet-v2 against the independent generic snapshot.
stopConditions:
  - An unresolved source or exhausted bounded retry lands as a DEFER packet in the L4 review queue with an exact resume action.
  - Ambiguous topology, competing strong mappings, or any requested ontology ruling lands as DEFER for L4 human review.
  - Any request to gather evidence, create intake, mutate the registry, change stars, regenerate docs, use Git, or open or merge a PR stops at the validated L4 packet and returns that boundary to the caller.
proof:
  - Every candidate records canonical source provenance, fetched frontmatter, and an immutable content hash or a stable defer reason.
  - Every mapping option and selected generic exists in the captured generic snapshot and carries its prefilled similarity and match tier.
  - Every terminal candidate packet passes the canonical discovery-packet-v2 validator against the separately persisted snapshot.
  - The L4 presentation shows the chosen disposition, its signal and matched source, all deferrals, and the packet paths.
done: >-
  All bounded candidates have a validator-accepted L4 packet or an explicit
  deferred packet with a resume action, the human review presentation exists,
  and no downstream mutation or delivery action occurred.
---

# Gaia Curate

This playbook is a discovery compiler. Read [CURATION-CORE.md](CURATION-CORE.md)
before processing candidates; it owns the packet lifecycle, deterministic
decision precedence, schema, proof, and hard L4 stop.

## Choose one mode

Mode changes scheduling and recovery, never authority or terminal proof.

| Mode | Select when | Load only |
|---|---|---|
| `single` | One manually selected page, at most five candidates | [references/modes/single.md](references/modes/single.md) |
| `checkpointed` | A small/bounded batch needs atomic resume and field-level repair | [references/modes/checkpointed.md](references/modes/checkpointed.md) |
| `dynamic` | A bounded broad manifest benefits from measured parallel capacity and cost receipts | [references/modes/dynamic.md](references/modes/dynamic.md) |
| `trending` | Configured public sources must be snapshotted and prioritized by source-native trend bands | [references/modes/trending.md](references/modes/trending.md) |

If the caller does not name a mode, use `trending` only when trend ranking is
the objective, `dynamic` only when bounded parallel work is requested,
`checkpointed` when resumability is requested, and otherwise `single`. Batch
size and recoverability are parameters; they do not create another workflow.

## Shared execution

1. Evaluate all frontmatter preconditions together. If any fail, report the
   complete set and create no partial output.
2. Load only the selected mode reference. Freeze the source bound, output
   ceiling, and recovery/concurrency parameters it requires.
3. Run `snapshot-generics` exactly once for the run before candidate work.
   Persist the complete output and its digest. Every candidate and every
   checkpoint in that run must reuse those exact bytes; never refresh the
   snapshot between candidates.
4. For each candidate, repeat only `prefill-candidate`, bounded judgment,
   packet assembly, and `validate-packet`. `gaia dev prefill` supplies the
   artifact gate, exact dedupe, and no more than three mapping options. Apply
   the decision precedence in [CURATION-CORE.md](CURATION-CORE.md) without
   re-scoring its results.
5. Validate each `discovery-packet-v2` against the run's frozen generic
   snapshot, and write accepted packets under
   `registry-for-review/discovery-packets/`. Runtime/checkpoint artifacts stay
   under `generated-output/curate-discovery/<run-id>/`.
6. Present the L4 review surface and stop. L4 discovery approval is not intake
   or registry acceptance.

The command-spine validator is the tracked
[`scripts/validate_discovery_packet.py`](../../../scripts/validate_discovery_packet.py)
adapter to this skill's canonical
[`scripts/validate_discovery_packet.py`](scripts/validate_discovery_packet.py).
Schemas and bounded fixtures live under [schemas/](schemas/) and
[fixtures/](fixtures/). The deterministic
[`scripts/run_fixture_dry_run.py`](scripts/run_fixture_dry_run.py) invokes the
live snapshot and prefill commands, assembles and validates a packet, and emits
an L4 presentation in a caller-supplied temporary directory; its isolated
dependencies are documented in
[`fixtures/playbook-runtime/FIXTURE.md`](fixtures/playbook-runtime/FIXTURE.md).
[`fixtures/playbook-l4-packet.json`](fixtures/playbook-l4-packet.json) remains a
completed V2 example for standalone validator regression checks. The realistic
positive and negative prompt corpus is in
[`evals/triggering.json`](evals/triggering.json); use it for independent forward
selection trials when changing the description or mode router. Its hand-authored
expected fields are test cases, not behavioral proof by themselves. The observed
2026-09-02 cold-trial outcomes and their explicit proof limits are in
[`evals/forward-selection-results.json`](evals/forward-selection-results.json).

Never gather or score evidence, assign grades/classes or stars, calculate Trust
Magnitude, create intake, mutate the registry, regenerate docs, commit, push,
or open or merge a PR. Final integration-to-`main` is always a founder decision
outside this playbook.
