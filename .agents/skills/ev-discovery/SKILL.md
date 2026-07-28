---
name: ev-discovery
description: >
  Skippable Phase 0 of the Gaia evidence verification pipeline. Use this skill
  only on DECLARED need for higher-quality Stage-2 evidence — a promotion
  candidate, or a skill that gaia-meta-sweep flagged as under-evidenced. Given a
  skill id, its source repo/context, and the evidence types needed (a subset of
  benchmark-result, arxiv, peer-review, social-signal), it runs Firecrawl web
  searches with type-appropriate queries, scrapes the top hits to markdown, and
  appends the discovered sources as fresh rows into the correct
  evidence/collectors/technical|social files so Phase 1 ev-collection picks them
  up on its next compile. Trigger phrases: "discover evidence", "find new
  evidence", "Phase 0", "run ev-discovery", "search for benchmarks/papers", "the
  skill is under-evidenced", "promotion candidate needs stronger proof". This is
  the ONLY ev-* skill that searches the web for NEW evidence — the others
  aggregate or verify what already exists. Requires FIRECRAWL_API_KEY; skips
  gracefully when absent.
---

# Evidence Discovery (ev-discovery)

Phase 0 of the evidence verification pipeline — a **skippable** discovery pass
that searches the web for **new** Stage-2 evidence and appends it to the
collector channels. It sits *before* Phase 1 `ev-collection`, feeding freshly
discovered rows into the same collector files that `ev-collection` compiles.

> **Pipeline position:** Optional. Runs before `/ev-collection` (Phase 1) **only
> when higher-quality evidence is explicitly needed**. When skipped, the pipeline
> starts at Phase 1 exactly as before. This is a continuous additive loop, not a
> gated pass — Phase 0 only *appends* rows; there is **no green gate**.

---

## When to run this (declared need only)

Phase 0 is **not** part of the common ingest path. Keep the common path cheap:
Stage-1 evidence (`github-stars-own`, `repo-own`, `self-attestation`) is written
at curation by a different workstream and needs no web discovery. Invoke Phase 0
**only** when a higher evidence bar is explicitly declared, e.g.:

- A **promotion candidate** needs stronger proof to justify a star bump.
- `/gaia-meta-sweep` (or a maintainer) **flags a skill as under-evidenced** for
  its current or target tier.

If neither condition holds, **skip this skill** and start the pipeline at
Phase 1.

## Scope — Stage-2 evidence types only

Phase 0 discovers the four **Stage-2** types and nothing else:

| Declared type | Channel file it appends to | Collector dir |
|---|---|---|
| `benchmark-result` | `benchmark_results.md` | `technical/` |
| `arxiv` | `academic_papers.md` | `technical/` |
| `peer-review` | `peer_reviews_audits.md` | `technical/` |
| `social-signal` | `blogs_newsletters.md`, `youtube_showcases.md` | `social/` |

Do **not** discover or write the cheap Stage-1 types here. If a caller asks for
`github-stars-own`/`repo-own`/`self-attestation`, that belongs to the
curation-time workstream, not Phase 0.

---

## Prerequisite — FIRECRAWL_API_KEY

Phase 0 orchestrates the existing `firecrawl` skill's CLI primitives; it does
**not** reimplement any web tool. Read the `firecrawl` skill for exact
invocation. It requires an API key:

```bash
export FIRECRAWL_API_KEY=fc-...
```

**Graceful degradation:** if `FIRECRAWL_API_KEY` is unset, do **not** attempt
discovery and do **not** error the pipeline. Print a single stderr note —
`ev-discovery skipped: FIRECRAWL_API_KEY not set; run Phase 1 on existing
evidence.` — and hand off to Phase 1 unchanged. Discovery is skippable by
design, so a missing key is a skip, never a failure.

---

## Inputs

- **skill id** — e.g. `safishamsi/graphify`.
- **source repo / context** — the skill's `links.github` blob URL and a short
  topic phrase (the technique the skill implements).
- **declared evidence types** — a subset of
  `benchmark-result` / `arxiv` / `peer-review` / `social-signal`.

---

## Workflow

### Step 1 — Build type-appropriate queries

For each declared type, construct one or more Firecrawl search queries seeded
from the skill's topic phrase. Suggested query shapes:

| Type | Query shape |
|---|---|
| `arxiv` | `"<topic> arxiv"` |
| `benchmark-result` | `"<topic> benchmark results"` |
| `peer-review` | `"<topic> audit OR review"` |
| `social-signal` | `"<topic> showcase OR blog"` |

### Step 2 — Discover with `firecrawl search`

Run one search per query (see the `firecrawl` skill for exact syntax):

```bash
firecrawl search "<topic> arxiv"
```

Collect the top hits. Prefer authoritative sources per type (arxiv.org for
`arxiv`; recognised benchmark leaderboards for `benchmark-result`; published
audits/reviews for `peer-review`; substantive blog posts or YouTube showcases
for `social-signal`).

### Step 3 — Scrape the top hits

For each selected hit, scrape it to markdown so the extracted metadata (title,
authors/date, URL, a factual one-line relevance note) is grounded in the page,
not guessed:

```bash
firecrawl scrape "<url>" -o /tmp/ev-discovery-hit.md
```

### Step 4 — Append fresh rows into the correct collector file

Append each discovered source as a **fresh row** in the exact block format the
compiler (`evidence/scripts/compile_data_lake.py`) reads. The compiler matches a
block to a skill when the block's header title **contains the skill id** (or the
id contains the title), so every appended block header MUST carry the skill id
in backticks.

Block delimiters per file (match the existing rows — inspect the file before
appending):

- `technical/academic_papers.md` — detail blocks start with `### ` (e.g.
  `### N. \`<skill-id>\``)
- `technical/benchmark_results.md` — detail blocks start with `### `
- `technical/peer_reviews_audits.md` — blocks start with `## `
- `social/blogs_newsletters.md` — blocks start with `### `
- `social/youtube_showcases.md` — blocks start with `## `; the compiler matches
  these by **contributor** appearing in the title, so lead with the contributor
  handle.

Keep the body factual (title, author/date, URL, a one-line relevance note) —
strip evaluative language so the Phase 3 adversarial audit does not flag it.
Use `blob/<branch>/<path>` for any GitHub URL, never `tree/`.

**Do NOT add the `<!-- injected: … -->` comment.** That flag is written by
`ev-collection` after it compiles a row. Phase 0's job is to leave fresh,
unmarked rows so `ev-collection` picks them up on its next pass. Marking them
here would make the compiler skip your discoveries.

### Step 5 — Hand off to Phase 1

Report which files were appended and how many rows per type, then hand off to
`/ev-collection`. No gate, no pass/fail — the appended rows flow through the
normal additive loop (collect → star-verify → adversarial-audit → link-validate).

---

## Attribution-scope guard

**A suite-wide source MUST NOT be copied as full-strength proof for every
component.** When a discovered source is about a suite as a whole (or its
mothership repo), attribute it to the suite/parent skill — do not duplicate the
same URL as a full-strength row under each individual component. Per-component
evidence must be about that component specifically. This mirrors the
same-source dedup and mothership-discount learnings in the curation guidelines.

---

## Output

On completion:

- Fresh, **unmarked** discovered rows appended to the correct
  `evidence/collectors/technical|social/*.md` file(s).
- A short summary of discoveries per declared type (skill id, type, source URL).
- Handoff to `/ev-collection` (Phase 1) in the continuous additive loop.

Nothing in the canonical registry (`registry/nodes/`, `registry/named/`) is
touched. Phase 0 only augments the raw evidence lake.
