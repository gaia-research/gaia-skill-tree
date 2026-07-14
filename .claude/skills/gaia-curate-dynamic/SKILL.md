---
name: gaia-curate-dynamic
description: >-
  Harness-neutral, discovery-only Gaia curation extension. A Sol/Terra-class
  orchestrator preflights capacity, shards safe volume work to configurable Luna
  workers, converges risky cases, and stops at human L4 review.
version: 3.0.0
argument-hint: "<broad-source-manifest>"
---

# Gaia Curate Dynamic

Read `../gaia-curate/CURATION-CORE.md`. Every worker returns one schema-valid `discovery-packet-v1`; this extension may orchestrate packets but may not relax the core lifecycle or cross its L4 stop.

## Roles

| Role | Default tier | Bounded responsibility |
|---|---|---|
| orchestrator | Sol preferred; Terra acceptable | preflight, source shards, budgets, merge, arbitration, L4 synthesis |
| harvester | Luna Light | fetch/parse/normalize a bounded source shard |
| mapper | Luna Light | choose among at most three supplied generic options or defer |
| proposer/refuter | Luna High or equivalent | isolated adversarial review of risky candidates only |
| repair | Luna High or equivalent | one schema-repair attempt against frozen input |
| assembler | deterministic first | validate, dedupe, merge, persist, render L4 output |

Model names are runtime configuration, not part of this skill. Do not silently substitute an unapproved model tier.

## Mandatory runtime preflight

Discovery is read-only. Before dispatch, resolve the active harness through explicit overrides such as `CLAUDE_BIN`, `CODEX_BIN`, or `HERMES_BIN`, then PATH. Do not assume a binary location and never edit user configuration.

Persist `preflight.json` with:

```json
{
  "harness": "claude-code|codex|hermes|other",
  "version": "...",
  "spawnMode": "subagent|process|sequential",
  "requestedConcurrency": 3,
  "observedConcurrency": 1,
  "structuredOutput": true,
  "usageReporting": "native|external|null",
  "budgetEnforcement": "native|orchestrator|null",
  "models": {"orchestrator": "...", "lunaLight": "...", "lunaHigh": "..."}
}
```

A config value is advisory. Establish capacity with a read-only canary: one Luna Light task, then a two-worker wave. Increase only after both succeed. Effective concurrency is the minimum of requested capacity, observed harness/provider capacity, remaining shards, and remaining budget. On 429/overload, reduce concurrency; do not increase retries. If routing or capacity cannot be established, continue sequentially or stop with the exact missing operator action.

Harness recipes, when configured:

```bash
# Claude Code
"$CLAUDE_BIN" -p --model "$LUNA_LIGHT_MODEL" --output-format json < "$PROMPT_FILE"

# Codex; read-only sandbox, explicit working directory
"$CODEX_BIN" exec -m "$LUNA_LIGHT_MODEL" -s read-only -C "$WORKTREE" - < "$PROMPT_FILE"

# Hermes one-shot process; children spawned with delegate_task inherit the parent model
"$HERMES_BIN" chat -Q -q "$BOUNDED_PROMPT" -m "$LUNA_LIGHT_MODEL" \
  --provider "$HERMES_PROVIDER" --max-turns 12 --source tool
```

Use only the recipe supported by the active harness. Never expose prompts, transcripts, secrets, or auth files in the ledger.

## Sharding and convergence

1. Shard by source or repository affinity, with a bounded source list and output ceiling per harvester. Do not create one process per raw lead.
2. Validate and exact-dedupe mechanically before semantic or adversarial work.
3. Send each mapper one candidate plus at most three generic options. Invalid or ambiguous output becomes `DEFER`; do not infer intent.
4. Skip adversarial calls for exact duplicates and straightforward existing-generic mappings.
5. Run isolated proposer/refuter passes only for `NEW_GENERIC`, fusion proposals, attribution conflicts, and unresolved semantic duplicates. Freeze identical input and hide each response from the other.
6. Sol/Terra arbitrates disagreements only. Conflicting mappings become `DEFER`, never a silent merge.
7. Present one consolidated L4 checkpoint and stop.

## Retry and budget policy

| Failure | Action |
|---|---|
| 429, overload, 5xx, transport timeout | retry at most twice with backoff; reduce concurrency |
| capacity rejection | split/downshift the wave; do not count as candidate failure |
| invalid structured output | one Luna High repair against the same frozen input |
| validator or generic-reference failure | no blind retry; defer with exact validator output |
| unavailable or contradictory source | defer |
| budget exhausted | stop dispatch, preserve partials, mark run blocked |

Never rerun a successful shard.

## Resumable state and cost log

Use `generated-output/curate-discovery/<run-id>/`. Write state atomically and append one `usage.jsonl` event per attempt:

```json
{
  "runId": "...", "taskId": "...", "shardId": "...", "attempt": 1,
  "role": "harvester", "tier": "luna-light", "harness": "...",
  "modelResolved": "...", "startedAt": "...", "finishedAt": "...",
  "status": "succeeded", "inputTokens": null, "outputTokens": null,
  "cacheReadTokens": null, "estimatedCostUsd": null, "pricingSource": null,
  "failureClass": null, "inputDigest": "sha256:...", "outputDigest": "sha256:..."
}
```

Use native usage when exposed, or an approved external cost tool. Store `null` when unavailable; never invent token or cost values. Resume only failed/incomplete tasks after revalidating the core contract digest and generic snapshot digest.

Discovery mode has no mutation or ship stage. It must not edit registry/generated files, create intake batches, branches, commits, issues, or PRs.
