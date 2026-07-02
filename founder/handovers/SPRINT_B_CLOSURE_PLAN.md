# Sprint B Closure — Master Execution Plan

**Created:** 2026-06-30  
**Status:** Ready for execution  
**Integration branch:** `dev/sprint-b-closure` (off `main` at v5.8.2, commit `46a98b77`)  
**Branching model:** Feature branches → `dev/sprint-b-closure` → `main` at sprint end  
**Kill criteria remaining:** 2 of 3 (KC#2: trending data, KC#3: tweetable URL)

---

## Executive Summary

Sprint B has 5 remaining open issues. The audit revealed that #651, #697, #698, and #851 were **prematurely bulk-closed** — the scripts exist but were never wired into the build pipeline, and the SDK was never built. This plan closes Sprint B in 4 workstreams ordered by effort (easiest first).

| # | Workstream | Issues | Size | Kill Criteria Impact |
|---|---|---|---|---|
| **W1** | 🔌 Trending Wiring | #651, #697, #698 | **S** | ✅ Closes KC#2 |
| **W2** | 🏆 Hall of Heroes | #854 | **L** (high-craft + iteration) | ✅ Closes KC#3 |
| **W3** | 📡 RSS + Ascended/Contested | #852, #853 | **M** | Polish (enriches trending surface) |
| **W4** | 📦 API Client SDK | #851 | **M** | Completeness (SDK consumers) |

**Estimated total:** ~20 hours across agents. Budget: ~$15–25 in tokens.

---

## W1 — Trending Wiring (EASIEST WIN)

**Branch:** `feat/sprint-b/trending-wiring` → `dev/sprint-b-closure`  
**PR title:** `feat(b2): wire trending engine into build pipeline`  
**Resolves:** #651, #697, #698  
**Effort:** ~2 hours  

### Problem

`scripts/buildTrendingProjection.py` (513 lines, 9 tests) is fully implemented but **never called** by `scripts/build_docs.py`. No JSON files exist at `docs/api/v1/trending/`. The frontend shell at `docs/trending/` fetches from these endpoints and shows nothing.

### Solution

Wire the existing script into `build_docs.py` using the same tempdir-diff pattern as `build_api_projection`.

### File Changes

| File | Change |
|------|--------|
| `scripts/build_docs.py` ~line 670 | Add `build_trending_projection(check)` function |
| `scripts/build_docs.py` ~line 1140 | Register `_run_step("trending", ...)` AFTER api-projection |
| `scripts/build_docs.py` ~line 1209 | Add `or trending_changed` to `changed` aggregate |
| `scripts/build_docs.py` ~line 389 | Add `"trending/index.html"` to cache-busting list |

### Implementation Detail

```python
def build_trending_projection(check: bool) -> bool:
    """Run buildTrendingProjection.py and diff against docs/api/v1/trending/."""
    script = SCRIPTS / "buildTrendingProjection.py"
    if not script.exists():
        return False
    committed = ROOT / "docs" / "api" / "v1" / "trending"
    with tempfile.TemporaryDirectory() as tmp:
        out_dir = Path(tmp) / "v1"
        # Seed prior state so deltas can be computed
        if committed.exists():
            (out_dir / "trending").mkdir(parents=True, exist_ok=True)
            snapshot = committed / "snapshot.json"
            if snapshot.exists():
                shutil.copy2(snapshot, out_dir / "trending" / "snapshot.json")
            hist = committed / "history"
            if hist.exists():
                shutil.copytree(hist, out_dir / "trending" / "history")
        # Run script
        rc = subprocess.run([sys.executable, str(script), "--out-dir", str(out_dir)]).returncode
        if rc != 0:
            raise RuntimeError(f"buildTrendingProjection.py failed: rc={rc}")
        generated = out_dir / "trending"
        if not generated.exists():
            return False
        # Diff and copy (same pattern as build_api_projection)
        ...
```

**Critical ordering:** Must run AFTER `build_api_projection` because the trending script reads from `docs/api/v1/skills/index.json`.

### Commit Sequence

1. `feat(b2): wire buildTrendingProjection into build_docs pipeline`
2. `test(b2): add trending wiring integration test`
3. `chore(b2): seed initial trending snapshot via gaia dev docs`

### Verification

1. `python -m pytest tests/test_trending_script.py -v` — 9 existing tests pass
2. `python scripts/build_docs.py` — exits 0, prints trending step
3. `docs/api/v1/trending/7d.json` exists and is valid JSON
4. Open `docs/trending/index.html` — no 404s, cards render (zero-state on first run)
5. `python scripts/check_nav_mounts.py` — passes

---

## W2 — Hall of Heroes (HIGH-CRAFT → KC#3)

**Branch:** `feat/sprint-b/hall-of-heroes` → `dev/sprint-b-closure`  
**PR title:** `feat(b3): Hall of Heroes — /heroes/ prestige showcase`  
**Resolves:** #854  
**Effort:** ~8–12 hours (includes design iteration)  
**Quality bar:** `/impeccable` — sky-high design expectations. This is a prestige showpiece.  
**Approach:** Opus planner with /impeccable → Opus worker → iterate on localhost  

### Vision

`docs/heroes/` **supersedes** the existing Hall of Heroes elements (`docs/index.html` HoH section + `docs/js/hoh-modal.js`). This is a standalone prestige page that celebrates the registry's highest-achieving contributors with custom per-hero animations and a share-first social design.

### MUST RETAIN (non-negotiable)

These features from the current HoH implementation MUST be preserved or improved:
1. **Share modal** — per-hero share flow (copy link, social buttons)
2. **SVG share** — exportable SVG card per hero for embedding
3. **HTML share** — embeddable HTML snippet per hero
4. **Ultimate/Apex/Unique prestige hierarchy** — these TOP over regular 4★ contributors BY A LOT. Custom animations per tier:
   - **Ultimate (◆)**: bespoke animation per hero (there are only a few — take time to make each feel unique)
   - **Apex/Extra (◇)**: distinguished motion + metallic treatment
   - **Unique 4★+**: dignified entrance, below apex but clearly prestige-tier

### Design Freedom

This is a **NEW state** — fresh page, fresh identity. Deviations from general DESIGN.md tokens are allowed:
- ✅ New fonts (pick what fits the prestige aesthetic — recommended automatically, no need to surface to founder)
- ✅ Introduced colors for hero-specific accents (as long as tier/rank/honor-red colors stay canonical)
- ✅ Custom keyframe animations per hero skill (ultimates get the most craft)
- ❌ No hex color values (use oklch/rgb/design tokens)
- ❌ Don't break the rank color system (`--rank-1` through `--rank-6`, `--honor-red`, `--apex-gold`)

### Deliverables

1. **`docs/heroes/index.html`** — standalone prestige showcase
2. **`docs/heroes/heroes.css`** — bespoke prestige aesthetic, per-tier animations
3. **`docs/heroes/heroes.js`** — fetches data, renders hero cards with tier-specific treatments, share modal, SVG/HTML export
4. **`docs/api/v1/heroes.json`** — static JSON of heroes (4★+, sorted by prestige)
5. **Nav/CTA wiring** — mounts.js, site-nav dropdown, homepage CTA, leaderboard cross-link
6. **Share infrastructure** — modal with copy-link, SVG export, HTML embed snippet per hero
7. **Custom animations** — unique per ultimate hero, distinguished per apex, dignified per 4★+

### Architecture Notes

- Study `docs/js/hoh-modal.js` for the share/SVG/HTML patterns to carry forward
- Study `docs/index.html` HoH section for prestige hierarchy logic
- The new page replaces both — once merged, the homepage HoH section becomes a "preview strip" linking to `/heroes/`
- Each hero card should feel like an achievement unlocked — not a list item

### File Changes

| File | Change |
|------|--------|
| `docs/js/mounts.js` | Add `'heroes'` |
| `docs/js/site-nav.js` | Add Hall of Heroes to dropdown |
| `docs/index.html` | Replace HoH section with preview strip → `/heroes/` CTA |
| `docs/trust/leaderboard/index.html` | Add cross-link to /heroes/ |
| `scripts/build_docs.py` | Add `"heroes/index.html"` to cache-busting |

### New Files

- `docs/heroes/index.html`
- `docs/heroes/heroes.css`
- `docs/heroes/heroes.js`
- `docs/api/v1/heroes.json`

### Commit Sequence (many — design iteration expected)

1. `feat(heroes): scaffold /heroes/ route with prestige page structure`
2. `feat(heroes): add /api/v1/heroes.json endpoint`
3. `feat(heroes): implement hero cards with tier-specific animations`
4. `feat(heroes): add share modal with SVG + HTML export`
5. `feat(heroes): wire nav + mounts + cache-busting`
6. `feat(heroes): homepage preview strip + leaderboard cross-link`
7–N. `fix(heroes): design iteration commits` (expect 5–10 iteration commits)

### Verification

1. `python scripts/check_nav_mounts.py` — passes
2. `python scripts/build_docs.py --check` — cache-busting covers new page
3. **Localhost visual review** — open `http://localhost:8091/heroes/` for Marco's design nitpicks
4. Share modal works — generates valid SVG, valid HTML embed
5. Ultimate heroes have unique animations; apex heroes have distinguished motion
6. Mobile responsive (single column, animations still smooth)
7. DevTools: no errors, no hex colors, no undeclared variables

### Iteration Model

W2 will NOT auto-merge. After initial implementation:
1. Open localhost (`python -m http.server 8091` from `docs/`)
2. Marco reviews visually and provides nitpicks
3. Iterate (5–10 commits expected for design polish)
4. Only merge to `dev/sprint-b-closure` after Marco approves

---

## W3 — RSS + Ascended/Contested (MEDIUM)

**Branch:** `feat/sprint-b/rss-ascended-contested` → `dev/sprint-b-closure`  
**PR title:** `feat(b2): RSS feed + Ascended/Contested sections on /trending/`  
**Resolves:** #852, #853  
**Effort:** ~3 hours  

### What exists

- `buildTrendingProjection.py` already outputs `ascended.json` and `contested.json`
- `docs/trending/trending.js` exists but may not have sections for ascended/contested rendering
- No `feed.xml` generation exists in the script

### Tasks

**RSS feed (#852):**
1. Add `_write_rss(out_dir, trending_7d, generated_at)` to `buildTrendingProjection.py`
2. Generate valid RSS 2.0 (use `email.utils.format_datetime()` for RFC 2822 dates)
3. Top 20 skills from 7d list, each `<item>` links to `/named/#explorer/{skill_id}`
4. Add RSS icon/button to trending page UI
5. Add `.gitattributes` entry: `docs/api/v1/trending/feed.xml linguist-generated=true`

**Ascended/Contested sections (#853):**
1. Verify `ascended.json`/`contested.json` output correctness
2. Add rendering sections to `docs/trending/trending.js`
3. "Recently Ascended" — skills with rank_up events, gold accent cards
4. "Most Contested" — genericSkillRef buckets with ≥2 implementations, competition visual

**Weekly digest (auto-post):**
1. `scripts/buildTrendingDigest.py` — reads `7d.json`, writes `docs/trending/weekly/YYYY-WNN.md`
2. `.github/workflows/trending-digest.yml` — Monday 07:00 UTC cron

### Commit Sequence

1. `feat(trending): add RSS 2.0 feed.xml generation`
2. `feat(trending): add Ascended + Contested sections to /trending/ UI`
3. `feat(trending): add weekly digest workflow + script`
4. `chore: add .gitattributes entry for trending feed.xml`

### Verification

1. Validate `feed.xml` with `feedparser` (Python) — no warnings
2. `docs/trending/index.html` renders ascended section (gold cards) + contested section
3. RSS icon visible and links to `feed.xml`
4. Graceful degradation: empty data shows "no activity yet" message

---

## W4 — API Client SDK (MEDIUM)

**Branch:** `feat/sprint-b/api-client-sdk` → `dev/sprint-b-closure`  
**PR title:** `feat(b1): @gaia-registry/api-client — Python + TypeScript SDK`  
**Resolves:** #851  
**Effort:** ~14 hours  

### Architecture

| Package | Location | Registry | Approach |
|---------|----------|----------|----------|
| TypeScript | `packages/api-client-ts/` | npm `@gaia-registry/api-client` | `openapi-typescript` (types) + hand-crafted fetch client |
| Python | `packages/api-client-py/` | PyPI `gaia-registry-client` | `datamodel-codegen` (Pydantic models) + `httpx` client |

### TypeScript SDK

- Zero runtime dependencies (native `fetch`)
- ESM + CJS dual-publish via `tsup`
- `GaiaClient` class: `getHealth()`, `listSkills(page?)`, `getSkill(c, s)`, `listContributors()`, `getContributor(h)`, `getLeaderboard()`, `getEvidenceTypes()`, `getSearchIndex()`
- Types auto-generated from `docs/api/v1/openapi.json`
- Tests: Vitest + MSW mocks

### Python SDK

- `httpx` based (sync + async)
- Pydantic v2 models auto-generated
- `GaiaClient` + `AsyncGaiaClient` classes
- Python 3.10+ required
- Tests: pytest + respx mocks

### CI Workflows

| Workflow | Trigger | Purpose |
|---------|---------|---------|
| `sdk-codegen.yml` | Push to `openapi.json` | Drift detection |
| `sdk-tests.yml` | Push to `packages/api-client-*` | Test matrix |
| `publish-sdk.yml` | `sdk-v*` tags | npm + PyPI publish |

### Commit Sequence

1. `feat(sdk): scaffold @gaia-registry/api-client TypeScript package`
2. `feat(sdk): add openapi-typescript codegen + generated schema types`
3. `feat(sdk): implement GaiaClient with typed fetch wrappers`
4. `test(sdk): add unit + integration tests for TypeScript SDK`
5. `feat(sdk): scaffold gaia-registry-client Python package`
6. `feat(sdk): add datamodel-codegen + generated Pydantic models`
7. `feat(sdk): implement sync/async GaiaClient with httpx`
8. `test(sdk): add pytest unit + integration tests for Python SDK`
9. `ci(sdk): add codegen drift check, test matrix, and publish workflows`
10. `docs(sdk): add README with usage examples for both packages`

### Key Decision: Separate Version Cadence

SDK versions start at `0.1.0`, NOT in lockstep with the CLI's v5.8.x. The `sdk-v*` tag pattern is independent. `verify_lockstep.py` only checks the 4 known manifests — SDK packages are excluded.

---

## Execution Order & Dependencies

```
Phase 1:  W1 (Trending Wiring) ──────► REVIEW ──► merge to dev/sprint-b-closure
                                                        │
Phase 2:  W2 (Hall of Heroes) ──────► REVIEW ──► localhost iteration (design nitpicks)
          [Opus planner /impeccable → Opus worker → iterate]
                                                        │ (stays open for iteration)
Phase 3:  W3 (RSS+Ascended) ─────┐                     │
          W4 (SDK) ──────────────┤► REVIEW ──► merge to dev/sprint-b-closure
                    (parallel)    │                     │
                                                        │
Phase 4:  W2 design iteration ──► Marco approves ──► merge to dev/sprint-b-closure
                                                        │
Final:    dev/sprint-b-closure ────────────────────────► PR → main (sprint close)
```

### Dispatch Rules

1. **W1 first** — easiest win, unblocks KC#2, unblocks W3
2. **W2 after W1 completes** — high-craft, gets dedicated opus attention without distraction
3. **W3 + W4 parallel after W2 initial implementation** — while waiting for design iteration
4. **Reviewer agents** at the end of each workstream before merge approval
5. **W2 does NOT auto-merge** — stays open for design nitpicks on localhost

### Agent Assignment

| Workstream | Planning | Implementation | Review |
|------------|----------|----------------|--------|
| W1 | — (plan ready) | Sonnet worker | Reviewer agent |
| W2 | Opus planner + /impeccable | Opus worker | Reviewer agent + Marco visual |
| W3 | — (plan ready) | Sonnet worker | Reviewer agent |
| W4 | — (plan ready) | Opus worker (TS) + Sonnet worker (Py) parallel | Reviewer agent |

### Worker Discipline (all dispatches)

Every worker prompt MUST include:
- "Commit after every logical unit (one function, one file, one section). Push immediately after each commit."
- "If you hit 80k tokens, commit+push what you have and report progress."
- "Report SHA + push status after each commit, not in a final summary."

---

## Kill Criteria Closure Map

| KC | Criterion | Closed by |
|----|-----------|-----------|
| ✅ KC#1 | API returns TM + grade | Already done (PR #857) |
| 🎯 KC#2 | `/trending/7d` shows real movement Monday morning | **W1** (seeds data) + stargazer heartbeat cron (provides real deltas over time) |
| 🎯 KC#3 | Tweet-pitch URL | **W2** delivers `gaia.tiongson.co/heroes/` |

**After W1 + W2 merge, Sprint B kill criteria are all met.** W3 and W4 are "completeness" items that ship before the sprint formally closes but aren't blocking.

---

## Risk Register

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Trending first-run shows all zeros (no historical data) | KC#2 technically unmet until first Monday after merge | Acceptable — seed run creates snapshot; second run (triggered by any merge to main) produces real deltas |
| `heroes.json` needs generation step long-term | Staleness if contributors change | For now: hand-craft from existing `contributors/index.json`. Follow-up: add to `buildApiProjection.py` |
| SDK codegen tools may have version issues | Blocks W4 | Pin exact versions; test in CI matrix |
| `build_docs.py` ordering — trending must run after API | Script crash if API files don't exist | Explicit ordering in `main()`, guard in function |

---

## Token Budget Estimate

| Workstream | Model | Est. Cost |
|------------|-------|-----------|
| W1 — Trending Wiring | Sonnet | ~$1.50 |
| W2 — Hall of Heroes (Opus planner + Opus worker + iteration) | Opus | ~$12.00 |
| W3 — RSS + Ascended | Sonnet | ~$2.00 |
| W4 — SDK (TS + Py) | Opus + Sonnet | ~$8.00 |
| Integration + review | Orchestrator + reviewers | ~$3.00 |
| **Total** | | **~$26.50** |

Well within the Sprint B budget of $25.
