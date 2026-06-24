---
name: gaia-wiki-sync
description: >-
  Dynamic-workflow wiki sync for the Gaia registry. Instead of a single linear
  pass, this skill fans out parallel sub-agents per source domain and per wiki
  page, then runs a bounded convergent cross-check for terminology drift before
  committing. Resumable via a per-run ledger. Use when you want the wiki
  comprehensively synced to the latest merged changes — /gaia-wiki-sync.
version: 2.0.0
argument-hint: "[--since <sha|date>] [--resume] [--check]"
---

# gaia-wiki-sync (dynamic workflow)

A **dynamic-workflow** implementation of wiki sync, designed so the fan-out
width adjusts at runtime to however many source domains changed and however many
wiki pages are stale. Modelled on the same principles as `/gaia-curate-dynamic`.

> *Claude analyses the commit range, fans out parallel source-reader agents (one
> per changed domain), fans out parallel page-drafter agents (one per stale
> page), then runs a bounded terminology cross-check before committing. Nothing
> lands until the refuter failed to find drift.*

Prefer the `update-docs` skill for a quick, focused patch on a handful of
pages. Use this skill when the sync window spans many commits and you want
parallel coverage with cross-page consistency guarantees.

---

## Six-Phase Architecture

```
discovery      → single agent  → SyncPlan (schema-validated)
source-read    → parallel/domain → SourceDigest per domain
page-draft     → parallel/page  → PageDraft per stale page
cross-check    → refuter agent  → Conflicts[] (skipped if only 1 page)
apply          → serial agent   → git commit + push
ledger-close   → single agent   → summary
```

### Phase 1 — discovery

Single agent. Reads `git log` and `git diff --name-only` for the sync window,
classifies changed paths into **source domains**, and maps each domain to the
wiki pages that depend on it.

Output is a `SyncPlan` (see `schemas/sync-plan.json`). Schema-validated — the
workflow halts on malformed plans rather than silently drafting wrong pages.

Key plan fields:
- `sourceDomains` — which files to read, keyed by domain name (`cli`, `schema`,
  `named`, `policy`, `mcp`)
- `stalePages` — wiki pages that need drafting
- `ciOwnedRegions` — per-page marker pairs to preserve verbatim (e.g.
  `gaia:cli-start/end` in CLI-Reference)

### Phase 2 — source-read (parallel per domain)

One agent per domain — typically 3–5 concurrent agents. Each reads all files in
its domain and emits a `SourceDigest` containing:
- `facts[]` — discrete claims with `id` and file:line evidence
- `renames[]` — old-name → new-name pairs since last wiki update
- `deprecations[]` — terms / axes / commands that no longer exist

Facts are the unit of traceability. Page-drafters cite `factId`s; the refuter
checks cited IDs against the global rename/deprecation lists.

### Phase 3 — page-draft (parallel per stale page)

One agent per stale page. Each agent receives:
- Current wiki page content (read from `../gaia-wiki/`)
- The `SourceDigest`s for the domains that affect its page
- The CI-owned region markers to preserve verbatim

Output: `PageDraft` with `newContent`, `citedFactIds`, `unresolvedFacts`.
If `unresolvedFacts` is non-empty, the draft is flagged for human review rather
than applied — no invented content.

### Phase 4 — cross-check (skip if only 1 stale page)

Single refuter agent reads all drafts and the global `renames[]` /
`deprecations[]` from all digests. Emits a `Conflicts[]` array (terminology
drift, cross-page contradictions). If conflicts exist, affected page-drafters
are re-run with the conflict list appended — capped at 2 iterations. If
conflicts survive after 2 rounds, the ledger records a `human-review` entry and
the run halts without committing.

### Phase 5 — apply (serial)

Single agent. Re-reads each target wiki file, splices `newContent` while
preserving CI-owned regions byte-for-byte, stages all changes in `../gaia-wiki`,
commits, and pushes.

### Phase 6 — ledger-close

Marks ledger `complete`, writes the summary returned to the user.

---

## Resume Protocol

On invocation, scan `generated-output/wiki-sync-ledger/` for ledgers with
`status: in-progress`. If one exists and is **< 24 hours old**, offer the user:

- `--resume` — re-load the plan, skip `complete` phases, re-run `failed` /
  `pending` agents only
- (default) — start a fresh run; rename the stale ledger to `.abandoned`

Ledgers older than 24 hours are stale and treated as fresh-run candidates
(mirrors the `promotion-candidates.json` 24h rule in CLAUDE.md).

---

## Ledger Shape

`generated-output/wiki-sync-ledger/<runId>.json` (gitignored)

```json
{
  "runId": "2026-06-06T00:00:00Z",
  "schemaVersion": 1,
  "phase": "page-draft",
  "status": "in-progress",
  "plan": { /* full SyncPlan */ },
  "phases": {
    "discovery":   { "status": "complete", "completedAt": "...", "outputRef": "artifacts/<runId>/plan.json" },
    "source-read": {
      "status": "complete",
      "agents": {
        "cli":    { "status": "complete", "outputRef": "artifacts/<runId>/digest-cli.json" },
        "schema": { "status": "complete", "outputRef": "artifacts/<runId>/digest-schema.json" }
      }
    },
    "page-draft": {
      "status": "in-progress",
      "agents": {
        "CLI-Reference":  { "status": "complete",  "outputRef": "artifacts/<runId>/draft-CLI-Reference.json" },
        "Home":           { "status": "failed",    "error": "missing factId policy.version", "attempts": 1 },
        "Named-Skills":   { "status": "pending" }
      }
    },
    "cross-check":  { "status": "pending" },
    "apply":        { "status": "pending" },
    "ledger-close": { "status": "pending" }
  },
  "convergence": { "iteration": 0, "maxIterations": 2 },
  "lastError": null
}
```

Large per-agent outputs live in `artifacts/<runId>/` alongside the ledger.
The ledger itself stays small and diffable.

---

## Constraints

- **Wiki repo at `../gaia-wiki`** — clone if missing, never delete.
- **`<!-- gaia:cli-start/end -->`** in CLI-Reference.md is CI-owned — preserve
  byte-for-byte. The applier verifies markers exist before writing.
- **`rarity` axis is deprecated** (CONTEXT.md) — the refuter must flag any
  draft that reintroduces it.
- **Banned-synonym list in `CONTEXT.md`** — feed to the refuter as part of
  `deprecations[]`.
- **Never invent facts** — if a page-drafter lists an `unresolvedFact`, halt
  that page's draft and flag for human review rather than guessing.
- **`[skip-gen]` in commit message** if any `registry/` artifacts are touched
  (defensive; wiki-sync normally shouldn't touch them).

---

## Source Domains → Wiki Page Mapping

| Domain | Source files | Affected pages |
|---|---|---|
| `cli` | `src/gaia_cli/main.py`, `src/gaia_cli/formatting.py`, README `gaia:cli-start/end` region | CLI-Reference, Initiates-Rite |
| `schema` | `registry/schema/*.json`, `CONTEXT.md` | Schema-Reference, Stars-and-Ranks, Skill-Types |
| `named` | `registry/named-skills.json`, `registry/named/` changes | Named-Skills, Ascension-Cycle |
| `policy` | `CONTRIBUTING.md`, `CLAUDE.md`, `META.md` | Contributing, FAQ, Stars-and-Ranks |
| `mcp` | `packages/mcp/src/`, `packages/mcp/package.json` | MCP-Server, FAQ |

---

## Entrypoint

The Workflow script is at `workflow.mjs` in this directory. Invoke via:

```
/gaia-wiki-sync
/gaia-wiki-sync --resume
/gaia-wiki-sync --check        # dry-run: plan + source-read only, no writes
```
