---
name: gaia-curate-chain
description: >-
  Fixed-topology, discovery-only extension for Gaia curation. Atomically
  checkpoints each candidate transition, retries only the failed field, and
  stops at human L4 review.
version: 3.0.0
argument-hint: "<source-or-small-batch>"
---

# Gaia Curate Chain

Read `../gaia-curate/CURATION-CORE.md`; it owns the lifecycle and packet. Use this extension when recoverability matters more than throughput.

## Checkpoint contract

Persist a run ledger under `generated-output/curate-discovery/<run-id>/run.json` containing the core contract digest, generic snapshot digest, source cursor, active candidate ID, completed candidate IDs, deferred rows, and next instruction. Write to a temporary file, validate it, then atomically rename it; never leave a partially written checkpoint.

Process exactly one candidate at a time. Validate its `discovery-packet-v1` after every transition. Advance only when the current transition validates and its input digest matches the checkpoint. On resume, revalidate contract and generic snapshot digests; preserve raw source records but move stale mappings to `DEFER`.

## Bounded repair

Route only the failing candidate and field back to its worker. Allow at most two retries for transient fetch failure and one Luna High/equivalent repair for invalid structured output. A deterministic schema, hash, or generic-reference failure is not blindly retried.

If retries are exhausted or output remains invalid/ambiguous, emit `DEFER` with the stable core reason code and exact resume instruction: candidate ID, failed field, validator code, source cursor, and required operator action. Never synthesize or infer a decision.

The chain ends at L4 human review. It does not collect evidence, calculate trust, mutate the registry, regenerate docs, create intake batches, commit, push, or open a PR.

## Explicit downstream handoff

After an L4 decision, write a handoff record; do not silently end the caller:

- New external discoveries: serialize only approved rows to the canonical `skills.yml` intake schema, then require the operator to run `gaia push --from-file skills.yml` or use the issue form.
- Rows that already came from `/gaia-draft-curate`: preserve `batchId` and issue/PR links, return them as `needs-evidence` to `/ev-pipeline`, then hand verified rows to a maintainer on `review/meta/*` for the CLI-only meta-shift in `CONTRIBUTING.md` §1C. Do not submit the same intake twice.

Record the route, artifact path, remaining gate, and exact next command. This compatibility handoff is data only; the chain remains discovery-only.
