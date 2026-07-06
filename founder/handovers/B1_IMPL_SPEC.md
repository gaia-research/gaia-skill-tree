# B1 Implementation Spec — Public Trust API Projection
**Issue:** #849
**Status:** ⚠️ Partially blocked — CORS/Cloudflare decision needed (Section 5B). All other sections ready for coding agent.
**Authored:** 2026-06-26
**Author:** Opus Planning Agent (via pi orchestrator session)
**Reviewed by:** Marcus Tiongson (pending — CORS decision outstanding)

---

## 1. Goal

Build a static JSON projection pipeline (`scripts/buildApiProjection.py`) that reads `registry/named-skills.json`, `docs/graph/ledger/data.json`, and `registry/schema/meta.json`, and writes a self-describing `docs/api/v1/` directory tree served by Cloudflare as the public Gaia Trust API — enabling AI agent platforms to query skill trust data directly without git clones or scraping.

---

## 2. `docs/api/v1/` Directory Tree

### File Layout

```
docs/api/v1/
├── health.json
├── skills/
│   ├── index.json              # page 1 (default)
│   ├── page-2.json             # page 2
│   ├── page-3.json             # ...up to ceil(N/50)
│   ├── garrytan/
│   │   ├── gstack.json         # full record for named skill
│   │   ├── browse.json
│   │   └── ...
│   ├── mattpocock/
│   │   ├── skills.json
│   │   └── ...
│   └── <contributor>/
│       └── <skill>.json
├── contributors/
│   ├── index.json              # all contributors in one file
│   ├── garrytan.json           # full contributor record
│   ├── mattpocock.json
│   └── <handle>.json
├── leaderboard.json
├── evidence-types.json
└── search-index.json
```

### Design Decisions

| Decision | Choice | Justification |
|---|---|---|
| Per-skill: one file per named skill vs single index | **One file per skill** | CDN cache granularity — agents fetching one skill hit a ~2KB file, not a 500KB index. ~249 skills = 249 files, well within git tracking limits. Cloudflare edge caches each independently. |
| Per-contributor: one file per contributor vs single index | **Both** — `contributors/index.json` (summary list) + `contributors/<handle>.json` (full detail) | The list endpoint is ~10KB total (40 contributors × ~200B each). Detail pages include all skills, so they vary from 1KB–20KB per contributor. |
| Pagination file naming | `skills/index.json` = page 1, `skills/page-{N}.json` for N≥2 | Serves `index.json` at `/api/v1/skills/` for clean URLs. Subsequent pages use numbered files. |
| Page size | **50** per page | Per design doc. Yields ~5 pages for 249 skills. |
| Sort order | Trust Magnitude descending (highest first) | Matches leaderboard and "Ultimate-first" direction rule. |

### File Size Estimates

| Endpoint | Size estimate |
|---|---|
| `health.json` | ~200B |
| `skills/index.json` (1 page) | ~15KB |
| `skills/<contrib>/<skill>.json` (avg) | ~2–5KB |
| `contributors/index.json` | ~8KB |
| `contributors/<handle>.json` (avg) | ~3–15KB |
| `leaderboard.json` | ~60KB (mirrors ledger) |
| `evidence-types.json` | ~8KB |
| `search-index.json` | ~80KB |
| **Total (all files)** | **~1.5–2MB** |

---

## 3. Script Design: `scripts/buildApiProjection.py`

### CLI Signature

```bash
python scripts/buildApiProjection.py --out-dir <path>
```

No `--check` flag on the script itself — `build_docs.py` wraps it with the standard tempdir-diff pattern (same as profiles, badges, etc.).

### Input Sources (explicit paths)

| Source | Path | Class | Notes |
|---|---|---|---|
| Named skills index | `registry/named-skills.json` | P (gitignored) | Primary data source. Must exist or script fails with exit code 1. |
| Ledger data | `docs/graph/ledger/data.json` | S (tracked) | For `/leaderboard` endpoint. |
| Schema metadata | `registry/schema/meta.json` | Tracked | For `/evidence-types` endpoint. |
| pyproject.toml | `pyproject.toml` | Tracked | For health endpoint `version` field. |

### Processing Steps Per Endpoint

#### `/api/v1/health.json`
1. Read `pyproject.toml` → extract version string.
2. Read `registry/named-skills.json` → extract `generatedAt`.
3. Count named skills (all entries in all buckets, non-redacted).
4. Write: `{ "ok": true, "version": "<X.Y.Z>", "registryGeneratedAt": "<ISO>", "namedSkillsCount": N }`.

#### `/api/v1/skills/index.json` + `page-{N}.json`
1. Read `registry/named-skills.json`.
2. Flatten all `buckets` entries into a single list (never read `awaitingClassification`).
3. **Redaction filter**: Exclude any entry where `is_redacted(entry["level"])` → True. Removes all 1★/Awakened skills from the public API.
4. Sort by `trustMagnitude` descending, then by `id` ascending (stable tiebreak).
5. Paginate at page size 50. For each page:
   - Extract the slim projection (see field mapping table below).
   - Write `skills/index.json` for page 1, `skills/page-{N}.json` for N≥2.
   - Include pagination metadata: `{ "skills": [...], "page": N, "totalPages": P, "totalSkills": T, "_links": { "self": "...", "next": "...", "prev": "..." } }`.

#### `/api/v1/skills/<contributor>/<skill>.json`
1. For each non-redacted named skill entry, write one file at `skills/<contributor>/<skill-slug>.json`.
2. Include full record (see full field mapping below).
3. Include `_links` self-describing navigation.

#### `/api/v1/contributors/index.json`
1. Read `by_contributor` from named-skills.json.
2. For each contributor, collect their named skill entries (non-redacted only).
3. **Skip contributors with zero non-redacted skills** (effectively invisible).
4. Compute per-contributor stats:
   - `namedSkills`: count of their non-redacted skills.
   - `topSkill`: the skill with highest TM (`{ "id": ..., "level": ..., "trustMagnitude": ... }`).
   - `prestigeScore`: sum of all their skill TMs (derived — not pre-computed anywhere).
5. Sort contributors by `prestigeScore` descending.
6. Write: `{ "contributors": [...], "totalContributors": N }`.

#### `/api/v1/contributors/<handle>.json`
1. For each visible contributor, write a detail file.
2. Include: `handle`, `namedSkills` (full list of slim skill projections), `topSkill`, `prestigeScore`, grade distribution, `_links`.

#### `/api/v1/leaderboard.json`
1. Read `docs/graph/ledger/data.json`.
2. Reshape to match API schema:
   - Rename `summary` → `distribution`.
   - Rename `rows[].skillId` → `rows[].id`.
   - Rename `rows[].tm` → `rows[].trustMagnitude`.
   - Map `rows[].currentStars` → `rows[].level`.
   - Strip internal fields: `mayStars`, `juneStars`, `g7Stars`, `flag`, `apexResults`.
3. Add `_links.self`.
4. Write.

#### `/api/v1/evidence-types.json`
1. Read `registry/schema/meta.json`.
2. Extract `evidence.types` array and `evidence.gradeThresholds`.
3. Write: `{ "types": [...], "gradeThresholds": {...}, "_links": { "self": "..." } }`.

#### `/api/v1/search-index.json`
1. For each non-redacted named skill, build a search entry:
   - `id`, `name`, `contributor`, `genericSkillRef`, `level`, `trustMagnitude`, `overallTrustGrade`
   - `tokens`: lowercase split of `name` + `description` (first 200 chars) + `tags[]` + `genericSkillRef` (hyphen-split)
2. Write as an array of `{ id, name, contributor, level, grade, tokens: [...] }`.
3. **No embeddings in v1.** (Grep confirmed: zero `embedding` or `vector` fields exist on named-skills records. Token-based search ships now; semantic search is B2 or v2.)

### Field Mapping Table — Skills List (slim projection)

| Source field (named-skills.json) | API field | Notes |
|---|---|---|
| `id` | `id` | `"contributor/skill-name"` |
| `name` | `name` | Display name |
| `level` | `level` | `"5★"` etc. |
| `trustMagnitude` | `trustMagnitude` | Float, 2 decimal places |
| `overallTrustGrade` | `overallTrustGrade` | `"S"`, `"A"`, `"B"`, `"C"`, or `null` |
| `contributor` | `contributor` | Handle string |
| `type` | `type` | `"basic"` / `"extra"` / `"unique"` / `"ultimate"` |
| (computed) | `_links.self` | `/api/v1/skills/<contrib>/<skill>` |

### Field Mapping Table — Skills Detail (full projection)

| Source field | API field | Notes |
|---|---|---|
| `id` | `id` | — |
| `name` | `name` | — |
| `contributor` | `contributor` | — |
| `title` | `title` | May be absent |
| `level` | `level` | — |
| `type` | `type` | — |
| `status` | `status` | Always `"named"` (redacted excluded) |
| `origin` | `origin` | Boolean — surface it (it's meaningful: "canonical reference implementation") |
| `genericSkillRef` | `genericSkillRef` | — |
| `trustMagnitude` | `trustMagnitude` | — |
| `overallTrustGrade` | `overallTrustGrade` | — |
| `apexGateStatus` | `apexGateStatus` | Dict or null |
| `evidence` | `evidence` | Full array |
| `timeline` | `timeline` | Full array |
| `links` | `links` | `{ "github": "..." }` |
| `suiteComponents` | `suiteComponents` | **Array of skill ID strings, NOT inline objects** (see §9.7) |
| `description` | `description` | — |
| `tags` | `tags` | Array or absent |
| (computed) | `_links.self` | `/api/v1/skills/<contrib>/<skill>` |
| (computed) | `_links.contributor` | `/api/v1/contributors/<handle>` |
| (computed) | `_links.generic` | `/api/v1/skills/_generic/<ref>` (reserved path, not generated in v1) |

### Redaction Rule

```python
from gaia_cli.redaction import is_redacted

# In the filtering step:
visible_skills = [e for e in all_skills if not is_redacted(e.get("level", ""))]
```

Any skill where `level_num(level) <= 1` is excluded from ALL API responses. This matches the badge-dir redaction invariant (CLAUDE.md: "1★ skills exist, 1★ badges do not").

`awaitingClassification` entries in named-skills.json must NEVER be read — only `data["buckets"]`.

### Error Handling

```python
def main():
    named_path = ROOT / "registry" / "named-skills.json"
    if not named_path.exists():
        print(f"FATAL: {named_path} not found. Run `gaia dev docs` first.", file=sys.stderr)
        sys.exit(1)
    try:
        data = json.loads(named_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"FATAL: {named_path} is malformed: {e}", file=sys.stderr)
        sys.exit(1)
    if "buckets" not in data:
        print(f"FATAL: {named_path} missing 'buckets' key.", file=sys.stderr)
        sys.exit(1)
```

Never silently produce partial output.

### Pagination Algorithm

```python
PAGE_SIZE = 50

def paginate(skills, page_size=PAGE_SIZE):
    total = len(skills)
    total_pages = max(1, -(-total // page_size))  # ceil division
    pages = []
    for i in range(total_pages):
        page_num = i + 1
        page_skills = skills[i * page_size : (i + 1) * page_size]
        links = {"self": f"/api/v1/skills/{'index.json' if page_num == 1 else f'page-{page_num}.json'}"}
        if page_num > 1:
            links["prev"] = f"/api/v1/skills/{'index.json' if page_num == 2 else f'page-{page_num - 1}.json'}"
        if page_num < total_pages:
            links["next"] = f"/api/v1/skills/page-{page_num + 1}.json"
        pages.append({
            "skills": page_skills,
            "page": page_num,
            "totalPages": total_pages,
            "totalSkills": total,
            "_links": links,
        })
    return pages
```

### Prestige Score Computation

Not pre-computed anywhere. Derive it:

```python
def compute_prestige(contributor_skills):
    return round(sum(s.get("trustMagnitude", 0) for s in contributor_skills), 2)
```

### Estimated Line Count

| Section | Lines |
|---|---|
| Imports + constants | ~30 |
| Input loading + validation | ~40 |
| Health endpoint builder | ~20 |
| Skills flatten + redact + sort | ~30 |
| Skills pagination writer | ~40 |
| Skills detail writer | ~50 |
| Contributors builder | ~60 |
| Leaderboard reshaper | ~40 |
| Evidence-types builder | ~20 |
| Search index builder | ~40 |
| CLI entry + output writer | ~30 |
| **Total** | **~400 lines** |

---

## 4. `build_docs.py` Integration

### Insertion Point

Add `build_api_projection()` after `build_docs_named_index()` (which ensures `registry/named-skills.json` is fresh) and before `build_profile_pages()`.

### New Function (add around line ~570, after `build_docs_named_index`):

```python
def build_api_projection(check: bool) -> bool:
    """Run buildApiProjection.py to a tempdir and diff against docs/api/v1/."""
    script = SCRIPTS / "buildApiProjection.py"
    if not script.exists():
        return False
    committed = ROOT / "docs" / "api" / "v1"
    with tempfile.TemporaryDirectory() as tmp:
        out_dir = Path(tmp) / "v1"
        rc, output = _run_script(script, ["--out-dir", str(out_dir)])
        if rc != 0:
            if check:
                print(f"diff docs/api/v1/ (regen failed: rc={rc})")
                print(output)
            raise RuntimeError(f"docs/api/v1/ regen failed: rc={rc}")
        if not committed.exists():
            if check:
                print("diff docs/api/v1/ (missing)")
            else:
                committed.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(out_dir, committed)
            return True
        drifts = _diff_tree(committed, out_dir)
        if not drifts:
            return False
        if check:
            for d in drifts:
                print(f"diff docs/api/v1/{d}")
        else:
            shutil.rmtree(committed)
            shutil.copytree(out_dir, committed)
        return True
```

### `main()` wiring (pseudocode diff):

```python
# After docs_named_changed line (~line 1048):
api_changed = _run_step("api-projection", build_api_projection, args.check)

# In the changed = (...) aggregation, add api_changed:
changed = (
    assembly_changed
    or readme_changed
    or docs_index_changed
    or html_cache_busted
    or css_tokens_changed
    or named_index_changed
    or docs_named_changed
    or api_changed          # ← ADD
    or profiles_changed
    or og_changed
    or tree_changed
    or ruflo_curation_changed
    or gexf_changed
    or svg_changed
    or sync_assets_changed
)
```

### `--check` mode: FAIL on drift?

**YES.** The API is Class S (tracked in git, served by CDN). Stale API data is a user-facing bug. Include `api_changed` in the `changed` aggregation that drives exit code 1 in `--check` mode.

### Ordering Dependency

`build_api_projection` reads the committed `docs/graph/ledger/data.json` directly — no ordering change to `build_docs.py` needed. If the ledger is stale, the API leaderboard reflects that; acceptable for a "as fresh as last build" system.

The API projection MUST run after the named-index step (`build_docs_named_index`) because it reads `registry/named-skills.json` which that step regenerates.

---

## 5. CORS Configuration — ⚠️ BLOCKED, NEEDS ARCHITECTURE DECISION

### Previous draft assumption (CORRECTED)

The prior draft assumed `docs/_headers` (Cloudflare Pages mechanism) or a Worker patch for CORS. Both were wrong per Marcus's corrections and repo recon. See §5B for the full brainstorm.

### Actual deployment architecture

This project deploys as a **Cloudflare Worker with Static Assets** — NOT Cloudflare Pages:

| Component | Detail |
|---|---|
| **Type** | `wrangler deploy` (Worker with Static Assets) |
| **Entry** | `worker/index.js` |
| **Assets dir** | `docs/` — all static files served via `env.ASSETS.fetch` |
| **`run_worker_first`** | `true` — Worker runs for every request; non-badge paths delegate to `env.ASSETS.fetch(request)` |
| **Custom domain** | `gaiaskilltree.com` (attached in Cloudflare dashboard) |
| **Worker's sole job today** | Badge path validation (`/badges/<handle>/<file>.svg` + `?repo=` checking) — **currently disabled** |
| **Deploy CI** | `.github/workflows/cloudflare-deploy.yml` → `cloudflare/wrangler-action@v3` |

### Key CORS facts

1. **`docs/_headers` does NOT work here.** That is Cloudflare Pages-only. In a Worker with Static Assets deployment, a `_headers` file is served as a plain text download, not interpreted.

2. **Static asset responses (`env.ASSETS.fetch`)** return correct `Content-Type` (e.g., `application/json` for `.json` files) but do **not** add `Access-Control-Allow-Origin` headers automatically.

3. **Badges are disabled for now** — no Worker changes needed for badge logic in B1.

4. **CORS is only required for cross-origin browser `fetch()`.** It is NOT required for:
   - ✅ `curl` / `httpie`
   - ✅ Python `requests`, Node `fetch` (server-side SDKs)
   - ✅ MCP server integrations (all server-side)
   - ✅ Same-origin JS at `gaiaskilltree.com`

5. **The only cross-origin scenario:** a third-party website running browser-side `fetch('https://gaiaskilltree.com/api/v1/skills/garrytan/gstack')`.

### Status: BLOCKED — awaiting Marcus's answers to §5B

The coding agent can proceed with all other sections (§3, §4, §6, §7, §8). CORS is the only outstanding blocker.

---

## 5B. Cloudflare Architecture Brainstorm — Open Questions for Marcus

These must be answered before the CORS approach is decided. The coding agent cannot finalize §5 until Marcus calls it.

---

### Q1: Confirm single-deployment architecture

**Evidence:** The repo has exactly ONE deployment mechanism — `cloudflare-deploy.yml` running `wrangler deploy --minify`. No GitHub Pages workflow. No `pages deploy`. `docs/CNAME` contains `gaiaskilltree.com` — this is the custom domain attached to the Worker in the Cloudflare dashboard.

**Despite the workflow job being named "Deploy to Cloudflare Pages,"** it uses `wrangler-action` (Worker deploy), not `cloudflare/pages-action`. The naming is misleading.

**Question for Marcus:** Is `gaiaskilltree.com` served ONLY by the `gaia-skill-tree` Worker (custom domain attached in Cloudflare dashboard)? If yes, `_headers` is definitively off the table.

---

### Q2: Is cross-origin browser access actually needed in B1?

The primary B1 consumers are server-side:
- AI agents (Claude Code, Cursor, Continue, Codex) — no CORS needed
- `@gaia-registry/api-client` Python + TS SDKs — no CORS needed
- `curl` examples in the `/api/` docs page — no CORS needed
- Same-origin JS on `gaiaskilltree.com` — no CORS needed

**CORS is only needed for third-party websites embedding skill data via browser-side `fetch`.** Is this a B1 requirement or a later concern?

---

### Q3: If CORS IS needed — which approach?

| Option | Change | Scope | Complexity |
|---|---|---|---|
| **A) Minimal Worker patch** | 10 lines in `worker/index.js`: if path starts with `/api/`, add `Access-Control-Allow-Origin: *` header to the static asset response | Production + preview | Low — isolated from badge logic, tested via `wrangler dev` |
| **B) Cloudflare Dashboard Transform Rule** | "Modify Response Header" rule in the Cloudflare dashboard: `URI Path starts with /api/` → add CORS headers | Production only | Zero code — but NOT version-controlled, not in git |
| **C) Defer CORS entirely** | Ship API without CORS in B1. Document it. All B1 consumers are server-side. Add CORS in a B1.5 patch if browser-embed use case materializes | N/A | Zero — no action needed |

**Planning agent recommendation: Option C (defer), with Option A as the ready-to-ship fallback patch.**

Rationale:
- B1's consumers are all server-side. CORS is irrelevant for them.
- Deferring avoids touching `worker/index.js` (badge-validator, currently disabled).
- If a cross-origin browser use case appears in B2 (e.g., embeddable skill cards), Option A is a 10-line patch ready in minutes.

**If Marcus says "ship CORS now" — Option A exact patch:**

```javascript
// In worker/index.js, BEFORE the existing badge logic:
const url = new URL(request.url);

if (url.pathname.startsWith('/api/')) {
  if (request.method === 'OPTIONS') {
    return new Response(null, {
      status: 204,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
      },
    });
  }
  const response = await env.ASSETS.fetch(request);
  const headers = new Headers(response.headers);
  headers.set('Access-Control-Allow-Origin', '*');
  headers.set('Cache-Control', 'public, max-age=300, s-maxage=3600');
  return new Response(response.body, { status: response.status, headers });
}
// ... existing badge logic below ...
```

---

### Q4: `Cache-Control` for API responses

Design doc proposed `max-age=300, s-maxage=3600`. With a Worker deployment, this requires either Worker code (Option A above includes it) or a Cloudflare Dashboard Cache Rule. Static assets get Cloudflare's default edge caching otherwise (typically short TTL).

If Option C (defer CORS), Cache-Control can be deferred too.

---

### Q5: CLAUDE.md accuracy — "GitHub Pages" wording

CLAUDE.md §Current Layout says: `"served as-is by GitHub Pages from main:/docs at gaiaskilltree.com"`. This is factually incorrect — the site is served by Cloudflare Worker with Static Assets. Future agents read CLAUDE.md first and may make wrong assumptions (as this planning session did).

**Recommendation:** Fix CLAUDE.md in the B1 PR (low-priority addition, but prevents future agent confusion).

---

### Marcus's Decision Matrix

| # | Question | Options | Blocks coding agent? |
|---|---|---|---|
| Q1 | Single Worker serves production? | Yes / No (explain if No) | Yes — determines if `_headers` is viable |
| Q2 | Cross-origin browser access needed in B1? | Yes / No | Yes — determines if CORS work happens now |
| Q3 | If yes to Q2 — which approach? | A (Worker patch) / B (Dashboard rule) / C (Defer) | Yes |
| Q4 | Cache-Control headers? | Worker code / Dashboard / Default | No — follow-up |
| Q5 | Fix CLAUDE.md "GitHub Pages" reference in B1 PR? | Yes / Later | No |

---

## 6. `docs/api/index.html` — Docs Page Scope (Issue #850 boundary)

### What #849 MUST do (pre-work for #850):

1. **Create the directory** `docs/api/` (it will contain `v1/` as a subdirectory). The directory is created by the projection script writing to `--out-dir`.

2. **Add `"api/index.html"` to `build_html_cache_busting()`** in `scripts/build_docs.py` — even though the file doesn't exist until #850. The function already does `if not path.exists(): continue`, so this is safe. This is a **hard rule** from CLAUDE.md: any new `docs/<section>/index.html` must be pre-registered.

   ```python
   # In scripts/build_docs.py build_html_cache_busting(), add to filename list:
   "api/index.html",  # pre-registered for #850
   ```

3. **Populate `_links` in every API response** so the #850 docs page can self-discover endpoints. Every endpoint must include:
   ```json
   "_links": {
     "self": "/api/v1/skills/garrytan/gstack",
     "contributor": "/api/v1/contributors/garrytan",
     "list": "/api/v1/skills/index.json"
   }
   ```

### What `docs/api/index.html` must NOT be (boundary for #850):

- Must NOT be generated by `buildApiProjection.py` (it's hand-authored with guild-ledger voice per PRODUCT.md).
- Must NOT carry a version stamp (Issue #807 rule).
- Must load `mounts.js` before `site-nav.js` (already satisfied — `'api'` is in `docs/js/mounts.js`).

---

## 7. Testing Plan

### `tests/test_api_projection.py` — Test Cases

| # | Test | Description |
|---|---|---|
| 1 | `test_health_structure` | Output has required keys: `ok`, `version`, `registryGeneratedAt`, `namedSkillsCount`. Version matches pyproject.toml. |
| 2 | `test_skills_pagination_math` | For 120 skills with page size 50: 3 pages. Page 1 = 50, page 2 = 50, page 3 = 20. `totalSkills` = 120 on all pages. |
| 3 | `test_skills_pagination_links` | Page 1 has no `prev`, has `next`. Last page has `prev`, no `next`. Middle page has both. |
| 4 | `test_redaction_excludes_1star` | Given fixture with 1★ and 2★ skills, only 2★+ appear in output. |
| 5 | `test_redaction_excludes_from_contributors` | A contributor with only 1★ skills has no entry in `contributors/index.json`. |
| 6 | `test_skills_sort_order` | Skills sorted by TM descending. First skill has highest TM. |
| 7 | `test_skill_detail_fields` | A skill detail file contains all expected fields from the mapping table. |
| 8 | `test_skill_detail_links` | `_links.self` and `_links.contributor` are present and correctly formatted. |
| 9 | `test_contributors_prestige` | Prestige score = sum of TMs for that contributor's visible skills. |
| 10 | `test_leaderboard_reshaping` | Ledger `rows[].tm` becomes `rows[].trustMagnitude`; internal fields stripped. |
| 11 | `test_evidence_types_structure` | Output contains `types` array with `id`, `magnitude`, `weight` per entry. |
| 12 | `test_search_index_tokens` | Each entry has `tokens` array; tokens are lowercase; includes skill name words. |
| 13 | `test_empty_named_skills` | Script with empty `buckets` still produces valid (empty) outputs without crashing. |
| 14 | `test_missing_named_skills_json_fails` | Script exits with code 1 and prints FATAL to stderr. |
| 15 | `test_suite_components_are_ids_not_objects` | `suiteComponents` in detail output is list of strings, not nested objects. |
| 16 | `test_no_version_in_non_health_endpoints` | No `"version"` key in skills/contributors/leaderboard outputs (Issue #807 rule). |
| 17 | `test_awaiting_classification_excluded` | Skills from `awaitingClassification` array never appear in any API output. |

### CI Integration

No new CI guard needed. The existing `build_docs.py --check` pipeline (run by CI via `gaia dev docs --check`) now includes `build_api_projection` in its step list. Stale API output = build fails.

### Smoke Test (Post-Deploy)

```bash
# Run after Cloudflare deploy completes:
curl -sS https://gaiaskilltree.com/api/v1/health.json | jq '.ok'
# Expected: true

curl -sS https://gaiaskilltree.com/api/v1/skills/garrytan/gstack.json | jq '.trustMagnitude'
# Expected: a float (the Sprint B kill criterion)

curl -sS https://gaiaskilltree.com/api/v1/skills/index.json | jq '.totalSkills'
# Expected: ~200+ (non-redacted named skills count)
```

---

## 8. Branch & PR Strategy

### Branch Name

```
dev/api-v1-projection
```

`dev/` prefix is unrestricted (any files allowed per CLAUDE.md). This avoids `skip-scope-check` since the PR touches `scripts/`, `docs/api/v1/` (generated), `tests/`, and potentially `worker/index.js` + CLAUDE.md.

### Files in PR

**New files:**
- `scripts/buildApiProjection.py` — the projection generator
- `tests/test_api_projection.py` — unit tests
- `docs/api/v1/**/*.json` — all generated API JSON files (Class S, tracked in git)

**Modified files:**
- `scripts/build_docs.py` — add `build_api_projection()` function + wire into `main()` + add `api/index.html` to cache-busting list
- `.gitattributes` — add `docs/api/v1/**/*.json linguist-generated=true` (collapses PR diffs)
- `CLAUDE.md` — fix "GitHub Pages" wording (if Marcus approves per §5B Q5)
- `worker/index.js` — add CORS handler (ONLY if Marcus approves Option A in §5B Q3)

**NOT included (deferred to #850):**
- `docs/api/index.html` — the human-readable docs page

### Commit Strategy

1. `feat(api): add buildApiProjection.py script`
2. `feat(api): wire api-projection into build_docs.py`
3. `test(api): add test_api_projection.py`
4. `chore: add docs/api/v1/ to .gitattributes as linguist-generated`
5. `chore(api): commit generated docs/api/v1/ (Class S)`
6. *(conditional)* `feat(api): add CORS handler to worker/index.js`
7. *(conditional)* `docs: fix CLAUDE.md Cloudflare hosting reference`

---

## 9. Open Questions / Surfaces to Flag for Marcus

### 9.1 Embeddings — RESOLVED (not present)

Grep across all `registry/named/**/*.md` and `registry/*.json` for `embedding` / `vector`: zero matches. **Token-based search ships in v1. Semantic search deferred to B2 or v2.**

### 9.2 Leaderboard source file — CLARIFIED

Design doc says "leaderboard" but actual file is `docs/graph/ledger/data.json` (generated by `generateLeaderboardData.py`). The API endpoint is named `/api/v1/leaderboard.json` (user-facing term) but sources from the ledger file. **Recommendation: keep `leaderboard.json`** as the public API name.

### 9.3 Prestige Score — RESOLVED (must be derived)

No `prestige` field exists in the codebase. Computed as the sum of `trustMagnitude` across a contributor's non-redacted skills. See §3.

### 9.4 CORS / Cloudflare setup — BLOCKED (see §5B)

Marcus to answer Q1–Q3 in §5B before coding agent proceeds.

### 9.5 `origin` field in API — RESOLVED (include it)

Named skills with `origin: true` indicate the canonical reference implementation. Include in skill detail. It's meaningful signal for agent platforms.

### 9.6 API versioning strategy — RESOLVED (additive only)

URL-path versioned (`/api/v1/`). v1 is permanent — additive changes only. Breaking changes → `/api/v2/` alongside. No deprecation headers needed now.

### 9.7 Suite vs Leaf — `suiteComponents` format — RESOLVED

**Array of skill ID strings, NOT inline objects.** Justification: inline objects would bloat `garrytan/gstack.json` from ~3KB to ~50KB (47 components × ~1KB each). Agents follow the ID to `/api/v1/skills/<contributor>/<skill>.json` for detail.

**Flag for Marcus:** Should we add a `?expand=components` query parameter in a future additive release? (Not needed for B1.)

### 9.8 `docs/api/v1/` gitattributes — RESOLVED (add it)

~300 JSON files in a first commit = large PR diff. Add to `.gitattributes`:
```
docs/api/v1/**/*.json linguist-generated=true
```
Same pattern as `docs/graph/gaia.json`. Include in B1 PR.

### 9.9 CLAUDE.md "GitHub Pages" reference — FLAG FOR MARCUS

CLAUDE.md §Current Layout says "served as-is by GitHub Pages from main:/docs at gaiaskilltree.com." This is factually incorrect. The site is served by Cloudflare Worker with Static Assets. Future agents will make wrong CORS assumptions (as this planning session did). Recommend fixing in the B1 PR — see §5B Q5.

---

## 10. Token Spend Estimate

### For the #849 Coding Agent

| Task | Est. tokens (in/out) |
|---|---|
| Read spec + context files | ~40k in / ~2k out |
| Write `buildApiProjection.py` (~400 lines) | ~20k in / ~15k out |
| Write `test_api_projection.py` (~300 lines) | ~15k in / ~12k out |
| Modify `build_docs.py` | ~10k in / ~4k out |
| Modify `worker/index.js` (if CORS approved) | ~5k in / ~3k out |
| Generate initial Class S output (run + commit) | ~5k in / ~2k out |
| Testing + iteration | ~20k in / ~10k out |
| `.gitattributes` + minor edits | ~3k in / ~2k out |
| **Total** | **~120k in / ~50k out** |

**Estimated cost:** ~$12–15 on Opus, ~$4–6 on Sonnet. Issue states size **L (~100k tokens)** — aligned.

---

## Appendix A: `.gitattributes` Addition

```
# API projection — generated JSON, collapse in PR diffs
docs/api/v1/**/*.json linguist-generated=true
```

## Appendix B: `build_html_cache_busting()` Addition

```python
# In scripts/build_docs.py, add to the filename list in build_html_cache_busting():
"api/index.html",  # pre-registered for Issue #850 (docs page)
```

## Appendix C: Volatile Date Normalization

The `_VOLATILE_DATE_PATTERNS` list in `build_docs.py` should already handle `generatedAt` fields in the API JSON via its existing regex. Verify this in the coding agent pass — if not, add the pattern.

---

## Token Spend

- Scout agent (Haiku): ~25k in / 8k out — ~$0.10
- Planner agent (Opus, pass 1 — full spec): ~180k in / 12k out — ~$4.50
- Planner agent (Opus, pass 2 — CORS correction): ~35k in / 4k out — ~$2.50
- Orchestrator inline (infrastructure clarification pass): ~15k in / 3k out — ~$0.50
- **Total planning session: ~$7.60**

---

## Related Documents

- **Why this API exists (product story):** `founder/API_PRODUCT_STORY.md`
- **API platform design:** `founder/handovers/API_PLATFORM_DESIGN_2026-06-20.md`
- **EPIC:** GitHub Issue #855
