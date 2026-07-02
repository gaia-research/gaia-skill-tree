---
name: gaia-integrity
description: >
  Run this skill whenever you need to answer "is the registry coherent?" — before
  opening a PR, after a merge or curation pass, when CI reports schema or validation
  failures, when someone asks to "check the registry", "validate the registry",
  "find orphan nodes", "check for missing documentation", "run integrity checks",
  or "clean up stale skill files". It runs three checks in one pass: canonical schema
  validation (gaia validate), documentation-alignment (every node has a matching .md),
  and orphan detection (stray .md files with no backing node). Also covers safe
  archival of orphaned docs without deleting history.
---

# Gaia Registry Integrity

This skill answers one question: **is the registry internally consistent?** Three things
can go wrong silently — a node fails schema validation, a node exists without a
documentation file, or a documentation file exists without a backing node. This skill
catches all three in a single pass and gives you a safe path to fix what it finds.

## Run the full integrity check

```bash
./.agents/skills/gaia-integrity/scripts/check_integrity.sh
```

The script runs three sequential checks and colour-codes the results:

| Step | What it checks | Fail signal |
|---|---|---|
| 1 — Canonical validation | `gaia validate`: schema compliance, no cycles, all cross-references resolve | Red ✗ |
| 2 — Documentation alignment | Every `registry/nodes/{type}/{id}.json` has a matching `registry/skills/{type}/{id}.md` | Red ✗ — "Missing documentation" |
| 3 — Orphan documentation | Every `registry/skills/{type}/{id}.md` has a matching node in `registry/nodes/` | Yellow ! — "Orphan documentation" |

Missing docs (step 2) are hard errors — a node with no documentation is incomplete.
Orphan docs (step 3) are warnings — they're usually leftovers from a rename or type
change, not broken references.

## Archive orphaned documentation

When step 3 reports orphans and you want to clean them up, use the archive script
instead of deleting them. Files are moved, not deleted, so history is preserved:

```bash
./.agents/skills/gaia-integrity/scripts/archive_orphans.sh
```

Files land in `registry/archive/YYYYMMDD_HHMMSS/{type}/`, preserving the original
type-folder structure. The archive script skips suite files (`skills.md`,
`setup-*.md`) automatically.

After archiving, check whether the removed files were part of the generated graph —
if so, run `gaia dev docs` to rebuild Class S artifacts.

## Pre-PR checklist

Before opening any PR that touches `registry/nodes/` or `registry/skills/`:

1. Run `gaia validate` — fix any schema or reference errors it reports.
2. Run `check_integrity.sh` — resolve or explicitly justify every Missing and Orphan entry.
3. If nodes were added or removed, run `gaia dev docs` and commit the updated `docs/graph/` artifacts in the same PR (CI Guard E in `docs-cohesion.yml` enforces this).

Leaving "Missing" entries unresolved means CI will reject the PR anyway — resolving
them here saves a round-trip.
