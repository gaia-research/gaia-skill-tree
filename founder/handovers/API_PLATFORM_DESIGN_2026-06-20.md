# GAIA API Platform Design (Sprint B)

**Status:** design draft. Implementation begins Sprint B (July 2026, post-PR #742 merge).
**Authored:** 2026-06-20.
**Replaces:** GAIA_ROADMAP v2 Phase 7 (which had the API at M6–10; v3 brings it forward).

---

## Why this exists

Today, anyone wanting to embed Gaia trust data has two options:

1. **Scrape `gaia.tiongson.co`** — fragile, breaks on every redesign.
2. **Git clone the registry** — works for one-shot reads, doesn't work for production agent platforms that need fresh data on demand.

Neither is "infrastructure". A read-only public API is the **single highest-leverage Sprint B deliverable** because it converts Gaia from a website into something Claude Code, Cursor, Windsurf, and Continue can call directly. **One API → N consumers.**

---

## Design principle: git-as-database, no real backend

Marco's question, paraphrased: *"For API any 'hidden fees' or anything need to be wary? Assuming we are just git as database..."*

**The answer is: yes, stay git-as-database.** Build the API as a **build-time projection**, not a runtime service.

| Approach | Cost | Hidden fees |
|---|---|---|
| **Static JSON over CDN** ✅ chosen | Free (Cloudflare Pages free tier handles 100k req/day easily) | None — already paying for the static site hosting |
| FastAPI / Express server on a VPS | $5–20/mo | Rate limit enforcement complexity, scaling, cold starts |
| AWS Lambda / Cloudflare Workers (compute) | Pay-per-request, ~$0.50/M requests | Logs cost, observability cost, vendor lock-in |
| Postgres + REST | $20+/mo + dev time | Migration burden, backup story, snapshot fidelity vs git |

**Recommended: build-time projection.** During the existing `gaia docs build` pipeline, generate a static JSON tree at `docs/api/v1/...` that mirrors what the API would return. Cloudflare Pages serves it under `gaia.tiongson.co/api/v1/...`.

**Hidden fees: zero** beyond the existing static site cost.

---

## Endpoints (read-only, v1)

All endpoints return JSON. No auth. Rate-limited at the Cloudflare edge (anonymous = ~100k requests/day per IP — should never be hit by legitimate use).

### `/api/v1/health`

```json
{
  "ok": true,
  "version": "5.0.0",
  "registryGeneratedAt": "2026-06-20T14:32:00Z",
  "namedSkillsCount": 249
}
```

### `/api/v1/skills/`

List all named skills (paginated, 50 per page).

```json
{
  "skills": [
    { "id": "garrytan/gstack", "name": "Founder Mode", "level": "5★", "trustMagnitude": 589.32, "overallTrustGrade": "S" },
    ...
  ],
  "page": 1,
  "totalPages": 5,
  "totalSkills": 249
}
```

### `/api/v1/skills/<contributor>/<skill>`

One named skill, full record.

```json
{
  "id": "garrytan/gstack",
  "name": "Founder Mode",
  "contributor": "garrytan",
  "title": "Gstack — Garry Tan's full discipline library",
  "level": "5★",
  "type": "ultimate",
  "status": "named",
  "origin": true,
  "genericSkillRef": "founder-mode-orchestration",
  "trustMagnitude": 589.32,
  "overallTrustGrade": "S",
  "apexGateStatus": { "..." : "..." },
  "evidence": [ { "..." : "..." } ],
  "timeline": [ { "..." : "..." } ],
  "links": { "github": "..." },
  "suiteComponents": [ "garrytan/browse", "..." ],
  "_links": {
    "self": "/api/v1/skills/garrytan/gstack",
    "contributor": "/api/v1/contributors/garrytan",
    "generic": "/api/v1/skills/_generic/founder-mode-orchestration",
    "evidence": "/api/v1/skills/garrytan/gstack/evidence"
  }
}
```

### `/api/v1/contributors/`

List, with prestige + counts.

```json
{
  "contributors": [
    { "handle": "garrytan", "namedSkills": 47, "topSkill": { "id": "garrytan/gstack", "level": "5★" }, "prestigeScore": 720 },
    ...
  ],
  "totalContributors": 40
}
```

### `/api/v1/contributors/<handle>`

One contributor, with all their named skills, badges, prestige history.

### `/api/v1/leaderboard`

The existing `docs/graph/leaderboard/data.json` exposed under the API namespace.

```json
{
  "generatedAt": "2026-06-20T14:32:00Z",
  "distribution": { "S": 4, "A": 42, "B": 56, "C": 77, "ungraded": 70 },
  "rows": [ { "..." : "..." } ]
}
```

### `/api/v1/trending/<window>` *(Sprint B B2 deliverable; depends on the trending engine)*

`<window>` ∈ `{24h, 7d, 30d}`. Returns rank-ups, evidence deltas, new skills.

### `/api/v1/evidence-types`

Schema metadata — list of canonical evidence types, weights, magnitude formulas. Mirrors `registry/schema/meta.json` evidence section.

### `/api/v1/search?q=<term>`

Pre-built inverted index over `name`, `description`, `tags`, `genericSkillRef`. Ships as a static JSON file the client filters in the browser (or a hosted edge function if it grows).

### `/api/v1/openapi.json`

Self-describing — the spec for the API itself (OpenAPI 3.1).

---

## What we deliberately don't ship in v1

- **POST / mutating endpoints.** Mutations route through `gaia` CLI + git PRs. Forever, not just v1.
- **GraphQL.** REST is sufficient for a read-only projection of structured data.
- **Webhooks.** Add in Sprint E if a customer asks.
- **WebSocket / SSE for trending.** Static JSON updated every build cycle is enough; clients poll.
- **Per-user API keys.** Anonymous-only in v1; authenticated tier in Sprint E if rate limits become real.
- **CORS allowlist.** Public read API; CORS `*` is correct.
- **Stale-while-revalidate / cache invalidation.** Cloudflare Pages handles this; we set `Cache-Control: public, max-age=300, s-maxage=3600` and let the build pipeline invalidate on push to main.

---

## Versioning

- URL-path versioned: `/api/v1/`. **`v1` is permanent and never breaks** — additive changes only. If we need a breaking change, ship `/api/v2/` alongside.
- `Accept` header negotiation NOT used. Simpler.
- Schema changes that ARE additive (new optional field in a response) ship in v1 without warning. Schema changes that REMOVE a field require v2.

---

## Build pipeline

Add a new step to `gaia docs build`:

```bash
# scripts/buildApiProjection.py
python3 scripts/buildApiProjection.py \
  --in registry/named-skills.json \
  --in skill-trees/ \
  --in docs/graph/leaderboard/data.json \
  --out docs/api/v1/
```

Reads:
- `registry/named-skills.json` — primary source for skills + contributors.
- `skill-trees/<handle>/skill-tree.json` — for prestige history per contributor.
- `docs/graph/leaderboard/data.json` — for the leaderboard endpoint.
- `registry/schema/meta.json` — for `evidence-types`.

Writes static JSON files matching the URL structure:

```
docs/api/v1/
├── health.json
├── openapi.json
├── skills/
│   ├── index.json                          # paginated list
│   ├── _generic/
│   │   └── founder-mode-orchestration.json # bucket view
│   ├── garrytan/
│   │   ├── gstack.json
│   │   ├── gstack/
│   │   │   ├── evidence.json
│   │   │   └── timeline.json
│   │   └── ...
│   └── mattpocock/
│       └── ...
├── contributors/
│   ├── index.json
│   ├── garrytan.json
│   └── ...
├── leaderboard.json
├── trending/
│   ├── 24h.json
│   ├── 7d.json
│   └── 30d.json
├── evidence-types.json
└── search-index.json
```

CDN serves these as-is. Cloudflare Pages already does this for `docs/`.

---

## Costs (annualised)

| Line item | Cost |
|---|---|
| Cloudflare Pages free tier (100k builds/mo, unlimited requests) | $0 |
| Build time additional (~3s per build for the projection step) | $0 |
| Storage additional (~5 MB JSON + ~100 KB OpenAPI spec) | $0 |
| Dev time to build (Sprint B B1) | ~150k tokens / ~$15 |
| Annual maintenance | $0 |
| **Total year 1** | **~$15** |

Compare to even a $5/mo Hetzner VPS: $60/year + dev time + ops complexity. Static is free.

---

## Risks + mitigations

| Risk | Mitigation |
|---|---|
| Stale data — the API is only as fresh as the last `gaia docs build`. | Trigger a build on every merge to main (already done via Auto-Sync). Document the freshness lag (≤5 minutes typical) in the API docs. |
| File size — paginated `/skills/` index could grow. | Pagination caps payload at 50 skills/page. Search index is currently <100 KB. Re-evaluate at 500 skills. |
| Search quality — pre-built inverted index won't beat a real search service. | v1 ships basic substring + tag match. If users need fuzzy / semantic, ship v2 with a hosted edge function (still cheap on Cloudflare Workers free tier). |
| Embed clients abuse the data — scrape, rebrand. | License is Apache 2.0; this is the bargain. Mitigation is reputation: "powered by gaia.tiongson.co" badge convention encouraged but not required. |
| Rate limits — Cloudflare anonymous 100k/day per IP. | Surface in OpenAPI spec. If a real consumer needs more, Sprint E adds an authenticated tier with keys + 5k/day. |
| Schema drift — the static JSON shape changes when the registry adds fields. | OpenAPI spec is regenerated each build; consumers read the spec to detect changes. Schemas are versioned (v1 frozen, v2 alongside if breaking). |

---

## Implementation order (Sprint B B1)

1. **Day 1–2** — Author `scripts/buildApiProjection.py`. Wire to `gaia docs build`. Land a happy path for `/skills/` and `/contributors/`.
2. **Day 3–4** — Add `/api/v1/leaderboard`, `/api/v1/skills/<contrib>/<skill>`, `/api/v1/skills/<contrib>/<skill>/evidence`, `/api/v1/skills/<contrib>/<skill>/timeline`.
3. **Day 5** — Generate OpenAPI spec from the implemented endpoints. Smoke test with `swagger-codegen` in Python + JS.
4. **Day 6–7** — Search index + `/api/v1/search?q=`. **Semantic-first** per Marco's call: if `registry/named-skills.json` already carries embeddings, project them into a static `search-vectors.json`; else add a one-time embedding step (cached) to the build pipeline. Substring fallback always present.
5. **Day 8** — Documentation page at `gaia.tiongson.co/api/` with copy-pastable curl examples.
6. **Day 9–10** — Cross-link from CLI, README, MCP server. Each says "or use the public API at gaia.tiongson.co/api/v1/...".
7. **Day 11–13** — `@gaia-registry/api-client` SDK (Python + TS). Generated from OpenAPI spec; published to PyPI + npm alongside the API. Includes typed `searchSkills(query, mode='semantic')` helper.

`/trending/` defers to Sprint B B2 (depends on the trending engine landing first).

---

## Testing

- `pytest tests/test_api_projection.py` — round-trip from `registry/named-skills.json` → API JSON → parse → assert structure invariants.
- `pytest tests/test_api_openapi.py` — validate OpenAPI spec is well-formed; every endpoint exists; no orphan schemas.
- Smoke test: `curl -sS https://gaia.tiongson.co/api/v1/health | jq` returns 200 with valid JSON post-deploy.

---

## Affects

- New: `scripts/buildApiProjection.py`
- New: `docs/api/v1/` (generated; gitignored)
- New: `tests/test_api_projection.py`, `tests/test_api_openapi.py`
- New: `docs/api/index.html` — human-readable API documentation
- Modified: `scripts/buildDocs.py` (or equivalent docs build entry) — adds the projection step
- Modified: `README.md` — adds the API mention
- Modified: `CONTRIBUTING.md` — explains the projection-from-registry contract

---

## Marco's calls — RATIFIED 2026-06-20

1. **API base URL: `gaia.tiongson.co/api/v1/`** ✅ — same Cloudflare Pages project, no new DNS surface.
2. **Anonymous rate limit posture: Cloudflare defaults** ✅ — revisit only when a real consumer hits the cap.
3. **Search quality bar: SEMANTIC from day one** ✅ — Marco's lean: *"I believe I have the embeddings already in the json..."* The v1 search index becomes a vector-augmented inverted index. Implementation note for Sprint B B1: detect existing embeddings on `registry/named-skills.json` records (look for `embedding`, `vector`, or analogous field). If present, ship semantic-first. If absent, ship substring v1 and queue embeddings as a B1 sub-task before the SDK lands. Either way: substring is the always-available fallback.
4. **Ship `@gaia-registry/api-client` SDK in Sprint B** ✅ — wraps the JSON-on-HTTP. Two language targets: Python (matches CLI) + TypeScript (matches MCP). Day-1 bonus: agent platforms (Claude Code, Cursor, Continue) get a typed import on the same week the API ships.

All four ratified. Sprint B B1 implementation order updated below.

---

*Authored: 2026-06-20. Aligns with `founder/GAIA_ROADMAP v3 (BUILD).md` Sprint B B1 deliverable. Implementation begins post-merge of PR #742.*
