# Sprint D CONTEXT — Content Engine + Benchmark MVP

**Read this before every Sprint D coding-agent dispatch.** Do not onboard from anywhere else.

**Authoritative plan:** `founder/handovers/SPRINT_D_EPIC_PLAN.md`
**Roadmap:** `founder/GAIA_ROADMAP v4 (BUILD).md` § Sprint D
**Integration branch:** `dev/sprint-d` (already cut off `main` HEAD at 3bc629be9, 2026-07-05)
**EPIC issue:** #902 · Milestone: `Sprint D — Content Engine + Benchmark MVP` (target 2026-08-01)

---

## Kill criteria (Sprint D done when all four green)

- **KC1** — First Monday auto-report ships without orchestrator intervention (behind manual-publish gate `GAIA_CONTENT_ENGINE_PUBLISH`).
- **KC2** — `gaia push --benchmark humaneval --score X` writes a valid `benchmark-result` evidence row; verifier gate OR CI check enforces trust.
- **KC3** — `gaiaskilltree.com/reports/YYYY-WW/` returns a permanent, indexed, tweetable URL.
- **KC4** — At least one skill has a live benchmark score visible on its explorer page.

---

## Workstream map

| # | Workstream | Class | Branch | Model | Depends on |
|---|---|---|---|---|---|
| W1 · #903 | Content Engine MVP + weekly auto-report | Splurge | `dev/sprint-d-content-engine` | Opus max | Sprint B trending API (already live) |
| W2a · #904 | Benchmark evidence schema | Splurge | `dev/sprint-d-benchmark-schema` | Opus max | none |
| W2b · #905 | Benchmark #1 pipeline (HumanEval CLI+CI) | Splurge | `dev/sprint-d-benchmark-pipeline` | Opus high | W2a merged |
| W3 · #906 | Benchmark #2 mirrored ingest (MMLU) | Satisfice | `dev/sprint-d-benchmark-mirror` | Sonnet | W2a merged |
| W4 · #907 | Benchmark leaderboard page (**FRONTEND — Marcus reviews before merge**) | Satisfice | `dev/sprint-d-benchmark-leaderboard` | Sonnet | W2b merged |
| W5 · #908 | SEO surface (meta + sitemap + JSON-LD + `/skills/` index) | Satisfice | `dev/sprint-d-seo-surface` | Sonnet | none |

> **Branch-prefix decision (2026-07-05):** the EPIC plan's `feat/sprint-d/*` naming **fails `branch-scope.yml`** — `feat/*` isn't recognized and falls to `other` (hard reject). All Sprint D feature branches use `dev/sprint-d-<workstream>` (single-dash) — `dev/*` is unrestricted per branch-scope.yml. This avoids splitting scope-crossing workstreams (W1, W2a) into multi-PR chains.

---

## Files-that-matter (upstream / seed points)

| Path | Role |
|---|---|
| `scripts/buildTrendingProjection.py` | Upstream data source for W1 |
| `docs/api/v1/trending/{7d,30d,ascended,contested}.json` + `feed.xml` | Input to W1 Content Engine (live post-Sprint B) |
| `registry/schema/skill.schema.json` | Base schema — W2a extends for benchmark-result |
| `registry/schema/evidence/benchmark-result.schema.json` | **NEW in W2a** — reference for W2b/W3/W4 |
| `src/gaia_cli/commands/push.py` | W2b extends with `--benchmark` + `--score` flags |
| `src/gaia_cli/commands/dev/evidence.py` | Already emits `benchmark-result` type strings; W2b hardens validation |
| `docs/trust/leaderboard/leaderboard.js` | Aesthetic pattern to reuse for W4 (do NOT redesign) |
| `docs/js/mounts.js` + `docs/js/site-nav.js` | W1, W4 must register new routes; Guard D CI enforces |
| `scripts/build_docs.py` | W1 registers `content_engine` step; W5 adds SEO post-render pass |
| `scripts/check_verifier_signoffs.py` | W2b extends for benchmark provenance path (a) |

---

## Invariants — do NOT break

- **URL structure** `/reports/YYYY-WW/`, `/benchmarks/`, `/skills/` frozen for Sprint F React/Node migration.
- **Class P vs Class S:** `registry/gaia.json` (Class P) is gitignored — never commit. `docs/graph/*` (Class S) always committed alongside source changes.
- **CLI Pre-Flight Rule** (root CLAUDE.md) applies to every mutating `gaia dev` verb — validate the schema-invariant that would be produced BEFORE writing.
- **Timeline events** written ONLY via `gaia dev timeline` (never hand-edit frontmatter — root CLAUDE.md).
- **Benchmark evidence provenance:** verifier-attested OR ci-reproduced ONLY. Self-attested rows land as `provenance: pending` and are rejected by the validator at merge time. Mirrored (W3) rows appear as citations only, excluded from Trust Magnitude.
- **Migration Notes block** in PR body required for any PR touching >50 LoC / schema / URLs / user-visible surfaces (see §9 of the EPIC plan).
- **Worktree rules** (root CLAUDE.md §"Worktree warmup boilerplate") — branch from `origin/dev/sprint-d`, commit + push after each logical unit, never batch pushes, revert generated Class P artifacts (`registry/gaia.json`, `docs/graph/*` if timestamp-only) before committing.
- **No underscores** in JS/Python function/variable names unless already present (root CLAUDE.md workspace rules). Dunders exempt.

---

## Branch strategy (mirrors Sprint B closure model)

```
main
└── dev/sprint-d                                ← integration (already cut)
    ├── dev/sprint-d-content-engine
    ├── dev/sprint-d-benchmark-schema
    ├── dev/sprint-d-benchmark-pipeline         (depends on schema)
    ├── dev/sprint-d-benchmark-mirror           (depends on schema)
    ├── dev/sprint-d-benchmark-leaderboard      (depends on pipeline; FRONTEND — hold for Marcus)
    └── dev/sprint-d-seo-surface
```

Feature PRs → `dev/sprint-d`. NEVER squash. Final PR: `dev/sprint-d` → `main` at sprint close (v6.0.0).

---

## Auto-merge policy

Satisfice PRs (W3, W5) that are <100 LoC net-new, CI green, non-schema, and don't touch URL structure get the `auto-merge-eligible` label after opening. W4 is Satisfice but frontend — never auto-merges (Marcus review gate).

---

## Publish gate (KC1 requirement)

Env var `GAIA_CONTENT_ENGINE_PUBLISH` (workflow-level, pulled from a `content-engine-live` GitHub Environment).
- Unset / `0` → generate to `docs/reports/DRAFT/YYYY-WW.md` (gitignored — never leaves runner). GH Actions summary artifact posts the draft.
- `1` → write to `docs/reports/YYYY-WW/index.html`, open auto-PR against `main`, label `content-engine`.

Default: OFF for first 4 weeks. Marco flips it weekly after review.

---

## CLI gap policy (Marcus directive, 2026-07-05)

**No follow-up issues.** If a Sprint D workstream discovers a CLI gap that would otherwise ship as a "known gap in PR body," the orchestrator opens a **separate PR branch** (`cli/sprint-d-<gap>`) targeting `dev/sprint-d` to close the gap. Merge order: fix PR first, then the workstream PR consumes it.

---

## Session provenance

- Sprint D groundwork by orchestrator, 2026-07-05
- Cut off `main` at `3bc629be9` (v5.11.13 canary head)
- Blocker PR #895 confirmed merged 2026-07-02
