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

### Step 4 — Build a JSON row per discovery and run `ev_append.py`

For each discovered source, build a JSON object with all fields you were able
to scrape from the page. **Do not hand-write collector blocks directly** —
`ev_append.py` is the canonical append path; it handles numbering, dedup,
date-stamping, and correct block format for each file type.

**JSON row schema:**

```json
{
  "skillId":      "safishamsi/graphify",
  "namedSlug":    "safishamsi/graphify",
  "evidenceType": "arxiv",
  "url":          "https://arxiv.org/abs/2408.03910",
  "title":        "CodexGraph: Bridging LLMs and Code Repositories via Code Graph Databases",
  "notes":        "Foundational methodology paper for AST-guided code graph queries — directly models Graphify's approach.",
  "grade":        "A",
  "isNew":        true,
  "citations":    89,
  "reviewers":    null,
  "percentile":   null,
  "views":        null,
  "likes":        null,
  "comments":     null
}
```

**TM numeric fields — scrape these during Step 3 (same page, no extra call):**

| Field | Relevant type | Where to find it | If not visible |
|---|---|---|---|
| `citations` | `arxiv` | arXiv abstract page — "Cited by N" or Semantic Scholar count | `null` |
| `reviewers` | `peer-review` | Journal/conference page — reviewer/committee count | `null` |
| `percentile` | `benchmark-result` | Leaderboard page — rank percentile among submissions | `null` |
| `views` | `social-signal` | YouTube: always present. Blog: visible on some platforms (dev.to, Substack) | `null` |
| `likes` | `social-signal` (YouTube only) | YouTube like count | `null` |
| `comments` | `social-signal` (YouTube only) | YouTube comment count | `null` |

**Judgment rule for `views`:** YouTube always has a view count — always scrape it.
For non-YouTube pages: if a numeric view/read count is visibly rendered on the
scraped markdown, record it; otherwise leave `null`. Do not estimate or infer.
A `null` is honest and scores 0 TM; a fabricated number is a registry corruption.

> **Model routing:** Steps 1–3 (query building, Firecrawl search/scrape) and
> building the JSON rows are mechanical — a fast/cheap model is sufficient.
> The one judgment call is relevance assessment (does this paper actually support
> the skill's technique?). If routing phases, use a capable model for relevance
> and a fast model for the scraping + JSON serialisation.

**Save rows to a temp file and run the script:**

```bash
# Save discovered rows
cat > /tmp/ev_discovery_rows.json << 'EOF'
[ ... your rows ... ]
EOF

# Dry-run first
python3 scripts/ev_append.py --dry-run --input /tmp/ev_discovery_rows.json

# Write if output looks correct
python3 scripts/ev_append.py --input /tmp/ev_discovery_rows.json
```

The script writes `<!-- appended: YYYY-MM-DD -->` date-stamps above new rows and
skips any URL already present (dedup). It does **not** add the
`<!-- injected: … -->` comment — that is written by `ev-collection` after
compilation. Do not add that comment manually.

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
