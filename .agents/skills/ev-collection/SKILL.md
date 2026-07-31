---
name: ev-collection
description: >
  Phase 1 of the Gaia evidence verification pipeline. Use this skill whenever you need to gather, consolidate, or refresh raw evidence for named skills in the registry. Trigger phrases: "collect evidence", "populate the data lake", "gather sources", "run ev-collection", "Phase 1", "compile the evidence index", "refresh the unified lake", "aggregate skill evidence", "build the evidence database". Also invoke as the first step before running ev-star-verification, ev-adversarial-audit, or ev-link-validation — nothing downstream is meaningful without a fresh, compiled index. Covers GitHub repo links, stargazer signals, YouTube showcases, arXiv papers, peer reviews, benchmark results, blog/newsletter posts, and self-attestation artifacts.
---

# Evidence Collection (ev-collection)

Phase 1 materializes and compiles the evidence lake. It is the foundation for star verification, adversarial audit, and link validation.

## Type-First Evidence Lake Contract (#1148)

The evidence lake is **type-first**. The primary working set is `evidence/by-type/<canonical-evidence-type>.md`. Legacy `evidence/tier_*.md` files may still be emitted as coexistence artifacts, but they are **not** the semantic routing key.

## Multi-Target Peer-Review Source Packets (#1418)

If one real peer-review source URL covers multiple named skills, materialize a temporary peer-review partition before compile instead of cloning intake rows or editing canonical evidence artifacts:

```bash
python evidence/scripts/peer_review_source_packets.py \
  --manifest /path/to/manifest.json \
  --by-type-dir /tmp/ev1418/by-type
```

This helper is `peer-review`-only, writes scratch `peer-review.md`, and emits one row per reviewed skill even when the same URL legitimately appears under each target. Reject strength/scoring fields anywhere in the packet (`trustNumber`, `grade`, `class`, `tier`, `level`, `stars`, `rank`). Do not commit scratch manifests or generated partitions without human approval.

## What Phase 1 does

1. Reads active source inputs, collector channels, and named-skill evidence rows.
2. Normalizes evidence row types, including legacy aliases such as `repo` → `repo-own` and `github-stars` → `github-stars-own`.
3. Writes deterministic primary partitions under `evidence/by-type/`.
4. Compiles `evidence/unified_evidence_lake.md` from by-type partitions.
5. May emit `evidence/tier_*.md` only for coexistence with older scripts.

## Commands

```bash
python evidence/scripts/generate_source_dump.py \
  --output-dir evidence \
  --by-type-dir evidence/by-type

python evidence/scripts/compile_data_lake.py \
  --sources evidence/by-type \
  --lake evidence
```

For deterministic temp-dir validation or tests, add `--skip-live-stars` and `--no-legacy-tiers` to `generate_source_dump.py`. Do not commit generated lake artifacts unless a human gate explicitly approves them.

## Completion Criteria

- `evidence/by-type/<type>.md` is current and is the primary downstream input.
- `evidence/unified_evidence_lake.md` was compiled from by-type files, not stale tier files.
- Collector rows are not re-parsed by default when by-type files exist, avoiding duplicate ingestion from coexistence dual-writes.
