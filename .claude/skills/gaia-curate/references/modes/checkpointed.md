# Checkpointed mode

Use when a bounded source or small batch needs recoverability more than
throughput. Process exactly one active candidate at a time.

Persist `generated-output/curate-discovery/<run-id>/run.json` with the core
contract digest, generic-snapshot digest, source cursor, active candidate ID,
completed candidate IDs, deferred rows, and next instruction. Write a temporary
file, validate it, then atomically rename it. Never leave a partial checkpoint.

Capture the complete generic snapshot once before the first candidate. Every
checkpoint in the run records and reuses that same snapshot digest; do not
recapture it mid-run. If the snapshot is missing or its digest changes, stop and
record the exact action to restart or explicitly begin a new run.

Advance only after the current packet validates and its input digest matches
the checkpoint. On resume, revalidate the core and frozen snapshot digests.
Preserve raw source records,
but move stale mappings to `DEFER` rather than silently recomputing them.

Retry only the failed field for the failed candidate: at most twice for a
transient fetch failure and once for invalid structured output against the same
frozen input. Do not blindly retry deterministic schema, hash, or generic-ID
failures. Exhausted or ambiguous work becomes `DEFER` with candidate ID, failed
field, validator code, source cursor, and exact operator action.

If input originated in a pending-intake workflow, preserve its `batchId` and
issue/PR links in the handoff record so a downstream human does not submit it
twice. The record is data only; this mode still stops at validated L4 packets.
