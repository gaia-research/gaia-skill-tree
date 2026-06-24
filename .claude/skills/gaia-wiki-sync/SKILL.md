---
name: gaia-wiki-sync
description: >-
  Syncs the Gaia GitHub wiki to the current state of the registry. Use this
  skill when: the wiki is out of date after a batch of merges; a user asks to
  "update the wiki", "sync the wiki", "regenerate wiki pages", "push docs to
  the wiki", or "refresh the wiki after this PR"; you notice wiki pages are
  stale relative to CLI changes, schema changes, named-skill promotions, or
  policy updates. Fans out parallel sub-agents per source domain and per wiki
  page, then runs a cross-check for terminology drift before committing. Prefer
  this over a manual wiki edit — the fan-out coverage catches drift that a
  single linear pass misses. Resumable if interrupted. Invoke as
  /gaia-wiki-sync.
version: 2.0.0
argument-hint: "[--since <sha|date>] [--resume] [--check]"
---

# gaia-wiki-sync

Keeps the Gaia GitHub wiki at `https://github.com/mbtiongson1/gaia-skill-tree.wiki.git`
in sync with the registry and source code. It analyses what changed, fans out
parallel agents to read each source domain and draft each stale page, then runs
a bounded refuter pass to catch terminology drift before anything is committed.

**When to reach for this skill vs alternatives:**
- `/gaia-wiki-sync` — many commits to process, want parallel coverage and
  cross-page consistency guarantees
- Manual edit — single typo fix on one page where running the full workflow
  would be overkill

---

## How it works — six phases

```
discovery    →  single agent  →  SyncPlan (schema-validated)
source-read  →  parallel/domain →  SourceDigest per domain
page-draft   →  parallel/page   →  PageDraft per stale page
cross-check  →  refuter agent   →  Conflicts[] (skipped if only 1 page)
apply        →  serial agent    →  git commit + push to ../gaia-wiki
ledger-close →  single agent    →  summary returned to user
```

### Phase 1 — discovery

Read `git log` and `git diff --name-only` for the sync window (default: since
last wiki commit). Classify changed paths into **source domains** and map each
domain to the wiki pages that depend on it. Output a schema-validated `SyncPlan`
(`schemas/sync-plan.json`). Halt on malformed plans rather than silently
drafting wrong pages — a bad plan contaminates every downstream agent.

Key plan fields:
- `sourceDomains` — which files to read, keyed by domain (`cli`, `schema`,
  `named`, `policy`, `mcp`)
- `stalePages` — wiki pages that need drafting
- `ciOwnedRegions` — per-page marker pairs to preserve verbatim (e.g.
  `<!-- gaia:cli-start/end -->` in CLI-Reference.md)

### Phase 2 — source-read (parallel, one agent per domain)

Typically 3–5 concurrent agents. Each reads all files in its domain and emits
a `SourceDigest` containing:
- `facts[]` — discrete claims with `id` and `file:line` evidence
- `renames[]` — old-name → new-name pairs since last wiki update
- `deprecations[]` — terms, axes, or commands that no longer exist

Facts are the unit of traceability. Page-drafters cite `factId`s so the
refuter can verify nothing was invented.

### Phase 3 — page-draft (parallel, one agent per stale page)

Each agent receives: current wiki page content, the `SourceDigest`s for its
relevant domains, and the CI-owned region markers to preserve verbatim.

Output is a `PageDraft` with `newContent`, `citedFactIds`, and `unresolvedFacts`.
If `unresolvedFacts` is non-empty, flag the draft for human review and do not
apply it — guessing fills the wiki with plausible-sounding lies.

### Phase 4 — cross-check (skip when only 1 stale page)

A single refuter agent reads all drafts plus the global `renames[]` /
`deprecations[]` from all digests. It emits `Conflicts[]` for terminology
drift or cross-page contradictions. Affected page-drafters re-run with the
conflict list appended — capped at 2 iterations. If conflicts survive after
2 rounds, record `human-review` in the ledger and halt without committing.
The cap prevents infinite loops on genuinely ambiguous source material.

### Phase 5 — apply (serial)

Re-read each target wiki file, splice `newContent` while preserving CI-owned
regions byte-for-byte, stage all changes in `../gaia-wiki`, commit, and push.
Verify that marker pairs exist before splicing — a missing marker means the
file structure changed and the splice would corrupt the page.

### Phase 6 — ledger-close

Mark ledger `complete` and write the summary returned to the user.

---

## Resume protocol

On invocation, scan `generated-output/wiki-sync-ledger/` for ledgers with
`status: in-progress` that are **< 24 hours old**. If one exists, offer:

- `--resume` — reload the plan, skip `complete` phases, re-run `failed` /
  `pending` agents only
- (default) — start a fresh run; rename the stale ledger to `.abandoned`

Ledgers older than 24 hours are treated as abandoned (mirrors the
`promotion-candidates.json` 24h rule in CLAUDE.md).

---

## Ledger shape

`generated-output/wiki-sync-ledger/<runId>.json` (gitignored — never commit)

```json
{
  "runId": "2026-06-06T00:00:00Z",
  "schemaVersion": 1,
  "phase": "page-draft",
  "status": "in-progress",
  "plan": { /* full SyncPlan */ },
  "phases": {
    "discovery":   { "status": "complete", "outputRef": "artifacts/<runId>/plan.json" },
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
        "CLI-Reference": { "status": "complete",   "outputRef": "artifacts/<runId>/draft-CLI-Reference.json" },
        "Home":          { "status": "failed",     "error": "missing factId policy.version", "attempts": 1 },
        "Named-Skills":  { "status": "pending" }
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

Large per-agent outputs live in `artifacts/<runId>/` alongside the ledger so
the ledger itself stays small and diffable.

---

## Source domains → wiki page mapping

| Domain | Source files | Affected wiki pages |
|---|---|---|
| `cli` | `src/gaia_cli/main.py`, `src/gaia_cli/formatting.py`, README `gaia:cli-start/end` region | CLI-Reference, Initiates-Rite |
| `schema` | `registry/schema/*.json`, `CONTEXT.md` | Schema-Reference, Stars-and-Ranks, Skill-Types |
| `named` | `registry/named-skills.json`, `registry/named/` changes | Named-Skills, Ascension-Cycle |
| `policy` | `CONTRIBUTING.md`, `CLAUDE.md`, `META.md` | Contributing, FAQ, Stars-and-Ranks |
| `mcp` | `packages/mcp/src/`, `packages/mcp/package.json` | MCP-Server, FAQ |

---

## Guardrails

- **Wiki repo at `../gaia-wiki`** — clone if missing (`git clone https://github.com/mbtiongson1/gaia-skill-tree.wiki.git ../gaia-wiki`), never delete it between runs.
- **`<!-- gaia:cli-start/end -->`** in CLI-Reference.md is CI-owned — preserve byte-for-byte. The applier verifies markers exist before writing.
- **`rarity` axis is deprecated** (see `CONTEXT.md`) — the refuter must flag any draft that reintroduces it.
- **Banned-synonym list in `CONTEXT.md`** — feed to the refuter as part of `deprecations[]` so banned terms don't sneak back in through paraphrase.
- **Never invent facts** — if a page-drafter has `unresolvedFacts`, flag that page for human review rather than guessing. The wiki is authoritative; a confident wrong answer is worse than an honest gap.
- **`[skip-gen]` in commit message** if any `registry/` artifacts are incidentally touched (defensive; wiki-sync normally should not touch them).

---

## Invocation

```
/gaia-wiki-sync                # full sync from last wiki commit
/gaia-wiki-sync --since abc123 # sync changes since a specific SHA or date
/gaia-wiki-sync --resume       # resume an in-progress run
/gaia-wiki-sync --check        # dry-run: plan + source-read only, no writes
```
