---
name: gaia-curate-dynamic
description: >-
  Wide-sweep curation extension. Runs the canonical Gaia curation core first,
  then adds runtime source sharding, proposer/refuter convergence, and a
  resumable ledger. Use for broad or high-stakes sweeps.
version: 2.0.0
argument-hint: "<broad-curation-goal>"
---

# Gaia Curate Dynamic

This is an extension of `/gaia-curate`, not an independent curation workflow.
Execute `.agents/skills/gaia-curate/CURATION-CORE.md` for every source cluster
first. The core owns canonical source handling, generic lookup, mapping,
evidence representation, proposal taxonomy, review, and mutation rules.
Dynamic orchestration may parallelize those core units, but must use the same
packet contract and must not invent alternate rules.

## Extension-only stages

1. **Plan:** choose source shards, candidate concurrency, and convergence-round
   budget; record the core contract version/digest.
2. **Discover in parallel:** dispatch source-shard workers and merge only
   normalized core candidates.
3. **Adversarial convergence:** dispatch an independent proposer and refuter for
   each candidate. Iterate up to the configured round limit; unresolved cases
   become `needs-evidence` for human review.
4. **Synthesize:** apply the core's existing-generic-first mapping and preserve
   `contributor/skill-name` named IDs plus `genericSkillRef`.
5. **Human checkpoint:** present converged accepts and unresolved disputes using
   the core review table. Require explicit decisions.
6. **Mutate and ship:** use `gaia dev`, validate, regenerate, and open one PR.

## Resumable ledger

Store state in `generated-output/curate-dynamic-ledger.json` (gitignored):

```json
{
  "contractVersion": "core-v1",
  "stage": "plan|discover|converge|review|ship",
  "corePacket": "generated-output/curation-core-packet.json",
  "plan": {"sources": [], "validationRounds": 2},
  "discoveries": [], "candidates": [], "decisions": [], "prUrl": null
}
```

Resume must revalidate the contract and generic mappings. Schema/context drift
invalidates mappings and mutation plans, but does not require discarding raw
discovery evidence.

## Gates

Every candidate must have a resolvable evidence source before review. Every
named candidate must resolve `genericSkillRef` (CLI: `--generic-ref`) against
`gaia dev list --generic --json`. Run:

```bash
gaia validate
gaia dev docs --check
```

Do not use deprecated `--class`, manually authored trust values, or copied
legacy taxonomy checks. Derived evidence scoring remains Gaia's responsibility.
