---
name: ev-star-verification
description: >
  Phase 2 of the evidence verification pipeline. Validates GitHub star counts in registry skill files against live GitHub API data and flags stale or inflated metrics without repartitioning evidence by rank. Use this after /ev-collection has compiled the unified data lake and before /ev-adversarial-audit begins. Trigger phrases: "verify stars", "check star counts", "refresh stargazer metrics", "run star verification", "ev-star-verification", "Phase 2", "live star check".
---

# Live Star Verification (ev-star-verification)

Phase 2 verifies live GitHub stargazer counts and records discrepancies. It no longer owns semantic partitioning.

## Type-First Evidence Lake Contract (#1148)

The evidence lake is **type-first**. The primary working set is `evidence/by-type/<canonical-evidence-type>.md`. Legacy `evidence/tier_*.md` files may still exist as coexistence artifacts, but they are **not** the semantic routing key.

## Required Behavior

- Read the current by-type working set and named-skill metadata.
- Query GitHub for live stargazer counts where star evidence is relevant.
- Flag stale, inflated, missing, or unreachable star metrics in the source report/audit notes.
- Preserve `evidence/by-type/` as the primary routing surface.
- Do **not** repartition evidence by star rank. `tier_*.md` files are coexistence-only and must not drive Phase 3 routing.

## Preflight

```bash
gh auth status
```

If GitHub auth is missing or rate-limited, stop or run deterministic validation rather than recording zero/placeholder star counts as truth.

## Handoff

After star verification, hand Phase 3 the by-type files. Mention any stale star findings in the report so adversarial reviewers can inspect the affected rows.
