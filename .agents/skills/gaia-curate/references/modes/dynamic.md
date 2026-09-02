# Dynamic mode

Use for a bounded broad manifest when measured concurrency materially improves
discovery. Runtime/provider choices are operator configuration and never widen
this Class B envelope.

## Capacity preflight

Resolve the configured worker runtime without editing user configuration. Run a
read-only one-worker canary, then a two-worker wave. Effective concurrency is
the minimum of requested capacity, observed capacity, remaining shards, and
remaining budget. If routing or capacity cannot be established, continue
sequentially or stop with the exact missing operator action.

Persist `preflight.json` with runtime/version, spawn mode, requested and observed
concurrency, structured-output support, usage/budget reporting, and resolved
worker roles. Do not store prompts, transcripts, secrets, or auth files.

## Sharding and convergence

- Shard by source or repository affinity with a bounded source list and output
  ceiling; do not create one process per raw lead.
- Validate and exact-dedupe mechanically before mapping or adversarial review.
- Give a mapper one candidate and no more than three prefilled generic options.
- Skip adversarial work for exact duplicates and a single strong mapping.
- Use isolated proposer/refuter passes only for `NEW_GENERIC`, fusion proposals,
  attribution conflicts, and unresolved semantic duplicates. Freeze identical
  input and hide their responses from each other.
- Arbitrate disagreements centrally. Conflicts become `DEFER`, never a silent
  merge.

Retry transport overload, timeout, or 5xx failures at most twice with backoff
and reduced concurrency. A capacity rejection downshifts the wave. Invalid
structured output gets one repair against frozen input; validator/reference
failures do not get blind retries. Never rerun a successful shard.

Append one `usage.jsonl` event per attempt with run/task/shard IDs, attempt,
role, runtime, start/end, status, input/output digests, failure class, and usage
or cost fields. Use observed values; store `null` when unavailable. All shards
reuse the single generic snapshot captured before dispatch; no worker may
refresh it. Resume only failed/incomplete tasks after validating the core and
snapshot digests.

When the fixed budget is exhausted, stop dispatching new work immediately.
Preserve every accepted packet, partial result, checkpoint, and usage receipt;
mark the run `blocked`; and record the exact resume action, including the run ID,
next incomplete task, and additional budget or capacity the operator must
provide. Do not discard partials, silently extend the budget, or launch another
wave. Assemble the valid completed outputs into the shared L4 presentation and
stop with incomplete rows called out.
