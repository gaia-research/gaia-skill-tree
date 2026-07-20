## Yggdrasil II — CHECKLIST completion (ship-blockers + easy-wins + overhauls)

Completes the entire pre-merge design review: `founder/reports/design-review-2026-07-20/CHECKLIST.md`. One PR, one fix per commit, each approved via `/design-iteration` before landing. Targets `dev/yggdrasil-ii-staging` (head of draft PR #1185 → main).

Handover: `founder/reports/design-review-2026-07-20/HANDOVER-checklist-fixes.md`.

### Scope

**Fixed** — ship-blockers SB1, SB2, SB3; easy-wins P1, P3, P4, P5, P6, P7, P8, P9, P10, P11, P12, P13, P15, P16, P17, P19, P20; overhauls O1 (token migration), O2 (explorer mobile reflow = SB1), O3 (3D label LOD), O4 (heroes mobile stage).

**Deliberately skipped (Marco ruled 2026-07-20 — do not re-open):**
- **SB4 / O5** — /named grouping-label rework. Deferred post-merge.
- **P2** — trust-leaderboard bars color by evidence *grade* (S=platinum), not rank. Working as intended; consistency note only.
- **P14** — "10 Unique" is accurate to the served `gaia.json` (10 starless nodes carry `branch:'unique'` after the 4★ origin-gate restorations). A curation verify on the registry, not a design edit.

**Not touched (INSIGHTS Bucket-2/3):** the marooned cherry-pick commits were already recovered (Bucket-1, PR #1241) or would silently regress the §8 sampler order / named-grid architecture. This PR does not re-apply any of them.

### The structural fix — O1 token migration

Ygg II token regen dropped `--tier-extra*` (~60 consumers) and `--tier-ultimate*` (~29 consumers), leaving ~90 live consumers resolving to nothing. Per Marco's ruling: `--tier-extra*` → fusion family; `--tier-ultimate*` → rank-driven (5★-suite gold today, rank-aware switch for future 5★-unique/6★). Also fixes the `--grade-s/a/b/c` lowercase/uppercase case-bug (grade A was rendering amber, not `#d4af37`). O1 resolves SB3, P9, and the genuine 6★-cyan prestige inversion on `/trust/ledger/` (P18).

### Entrypoints

- **P15** adds `<nav id="site-nav">` + `<div id="site-footer-mount">` mount elements to `/api/index.html` (copied from `docs/named/index.html`) — the page previously shipped scripts with no mount targets, so nav + footer rendered nothing. Guard D misses this (checks GAIA_MOUNTS + script load, not element presence).
- All other fixes touch existing surfaces; no new pages/sections/mounts. Cache-busting: SB2 wires report detail pages into `build_html_cache_busting()`.

### Branch-scope note

Several fixes touch **generated surfaces** whose source lives outside `docs/` (SB2 → `report.html.j2` + `build_docs.py`; P13 → `generateProfilePages.py`; O1 → `generateCssTokens.py`). These cross the `design/` branch-scope; commits touching them carry `[skip-scope-check]` per Marco's standing call (same as Fix 4 last session). Flagged per commit below.

### Per-fix outcomes

_(filled in as each fix lands — ID · outcome · SHA)_

| ID | Fix | Outcome | SHA |
|---|---|---|---|
| O1 | `--tier-extra`/`--tier-ultimate` token migration + grade case-bug | | |
| SB1/O2 | Explorer mobile single-column reflow + scrollable body | | |
| SB2 | Report detail nav version bump (nav no longer hidden) | | |
| SB3 | Duplicate "SHOW ULTIMATE PATH" → rank-word by branch | | |
| P1 | Nav links → one neutral color | | |
| P3 | 1★ `@[anonymous]` → designed empty state | | |
| P4 | /named 16px desktop horizontal overflow | | |
| P5 | Agent-prompt preview text clipping | | |
| P6 | Review-showcase empty terminals sizing + mid-word wrap | | |
| P7 | Badges `graph/gaia.json` 404 relative-path | | |
| P8 | Badges "HONESTY ON" pill overlaps H1 | | |
| P9 | Named-card stray gold underline (O1) + install-cmd ellipsis | | |
| P10 | Explorer duplicate "Fuse skills" CTA | | |
| P11 | Explorer mobile FAB overlaps evidence bar | | |
| P12 | Homepage HoH FAB overlaps share button (mobile) | | |
| P13 | Profile duplicate FILTER controls (mobile) | | |
| P15 | /api nav + footer mount elements | | |
| P16 | /api endpoint table mobile reflow | | |
| P17 | /api example URLs clip (desktop) | | |
| P18 | /trust/ledger 6★ cyan prestige inversion (via O1) | | |
| P19 | /about pull-quote orphaned closing glyph | | |
| P20 | /trending award cards all-gold border (Marco call) | | |
| O3 | 3D explorer label declutter / LOD | | |
| O4 | /heroes mobile full-viewport stage | | |

### Verification

Playwright (per CHECKLIST method — `/browse` is banned) vs `http://localhost:8090/`, desktop 1280×900 + mobile 390×844. Ship-blockers + overhauls carry before/after screenshots. Post-edit invariants re-checked: `skill-explorer.js` five sections render; `badges/?u=mattpocock&s=grill-me` renders; `skill-graph.js` hydrates from real data (not FALLBACK_SKILLS); fixed-nav clearance holds.
