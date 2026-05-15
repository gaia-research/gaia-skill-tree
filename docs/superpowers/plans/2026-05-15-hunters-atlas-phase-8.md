# Hunter's Atlas — Design Unification (Phase 8)

## Context

The Phase 1–7 rollout established the Hunter's Atlas visual language (Diamond Seal, EB Garamond + Bricolage Grotesque + Departure Mono, honor-red contributor handles, plaque token set in `docs/css/plaque.css`, tier-aware coloring via `data-type`), but applied it selectively. Three surfaces still render in the older pre-Atlas language and one nav surface (profile pages) was never unified:

- **Hall of Heroes plates** (`docs/js/page-ia.js:226–238`, `docs/css/styles.css:.hoh-plate`) — hybrid. EB Garamond fonts landed but card chrome is still the bordered `rgba(255,255,255,.02)` look, the glyph is a plain text symbol (not the orb), and the contributor handle is a non-clickable `<div>`.
- **Named Skills Explorer** (`docs/js/named-skills.js:48–75`, `.ns-tile/.ns-list-row/.ns-dag-card` in `docs/css/styles.css`) — tile / list / flow views all on system-ui borrowed from the old design.
- **Skill Detail Overlay** (`docs/js/skill-explorer.js:71–104`, `.se-hero-card/.se-desc-panel/.se-evidence-row` in `docs/css/styles.css`) — bordered `var(--surface)` panels, system-ui body, evidence rows that emit deprecated "CLASS A · SS" strings.
- **Profile-page nav** (`scripts/generateProfilePages.py:163–177`) — only 2 items (Hall of Heroes / Codex) where home + codex have 5.

Three smaller drifts compound the inconsistency:

- **Deprecated evidence-class suffixes.** `plaque-reveal.js:62–67`, `generateProfilePages.py:79–92`, `generateOgCards.py:61–74` all emit strings like `"CLASS A · SS"`, `"CLASS S · V"`, `"AWAITED · I"`. Per `CONTEXT.md`, the canonical labels are "Class A / Class B / Class C" with stars-and-rank-name for tier; the letter-grade suffix is deprecated.
- **Ascension Cycle tier colors** (`.asc-tier--2..5` in `styles.css:2117–2120`) don't match the `DESIGN.md:62–67` rank table. Should be Teal `#63cab7` (II), Violet `#a78bfa` (III), Fuchsia `#e879f9` (IV), Amber `#fbbf24` (V); shipped wrong.
- **Contributor handles are plain text in 13 of 14 surfaces.** Only `page-ia.js:144` (Path B claimed rows) links to `/u/{handle}/`. The user wants every contributor mention site-wide to link to its profile page — including in `docs/tree.md`, the explorer overlay, plaque cards, and the markdown projections under `registry/skills/**/*.md`.

Plus a content-level identifier mismatch: visitors see `karpathy/autoresearch`, `/autonomous-research-agent`, `"AutoResearch"`, and `/autoresearch` for what is conceptually one named skill. The user wants the **second segment of the NAMED ID** (`/autoresearch`) rendered in **honor red** as the **primary** identifier wherever a named skill appears — Hall of Heroes plates, Named Skills tiles, profile-page plaques, skill detail overlay, and Path B claimed rows.

User-locked decisions:
- HoH "scrolling plaques" → **ambient drift at idle, paused under `prefers-reduced-motion`, paused on hover/`:focus-within`, manual scroll/drag takes over**.
- Profile pages get the **full 5-item nav** (Registry · Hall of Heroes · The Codex · Tree · search-icon), same as home and Codex.

## Approach

Eight surgical phases ordered by the user's stated priority. Each phase is independently committable so we can preview after each.

### Phase A — Token foundation (fast)

- **Fix Ascension star colors** in `docs/css/styles.css` `.asc-tier--N`. Replace with the `DESIGN.md:62–67` palette: I `#38bdf8`, II `#63cab7`, III `#a78bfa`, IV `#e879f9`, V `#fbbf24`, VI `var(--apex-gold)` w/ extra glow.
- **Add reusable helpers** in a new tiny module `docs/js/atlas-helpers.js` (loaded before `page-ia.js`, `named-skills.js`, `skill-explorer.js`):
  - `namedSlug(entry)` → second segment of `entry.id` (`karpathy/autoresearch` → `/autoresearch`). Falls back to `'/' + entry.genericSkillRef` for entries without a `/`.
  - `profileHref(handle)` → `./u/{encodeURIComponent(handle)}/`. Use `'../../u/...'` from generated profile pages.
  - `handleLink(handle, opts)` → `<a class="atlas-handle" href="...">@handle</a>`. Already-existing styled class `.ult-contrib` becomes a generalization called `.atlas-handle`.
- **Python mirrors** in `scripts/_atlas_helpers.py` (new): `named_slug(entry)`, `profile_href(handle, rel='./u/')`, `handle_link(handle, rel)`. Import from both `generateProfilePages.py` and `generateProjections.py`.

### Phase B — Drop deprecated evidence-class suffixes

Three near-identical `evidence_class()` functions emit "CLASS X · {Roman/letter}". Replace each with the simpler `"CLASS A"` / `"CLASS B"` / `"CLASS C"` (no `· SS` etc.) per `CONTEXT.md` glossary:

- `docs/js/plaque-reveal.js:62–67`
- `scripts/generateProfilePages.py:79–92`
- `scripts/generateOgCards.py:61–74`

Add a one-line footnote in `DESIGN.md:55–67` rank table marking the "Class" column (D/C/B/A/S/SS) as historical/internal; visitor-facing label is the rank name + star count.

### Phase C — Slash-name priority + honor-red everywhere

For every render-site of a named skill identifier, switch to `namedSlug(entry)` in honor red. Concrete edits:

- **Hall of Heroes plates** (`docs/js/page-ia.js:226–238`) — change the `.hoh-skill` div to render `namedSlug(entry)` in `var(--honor-red)`, not the canonical id in white.
- **Path B claimed rows** (`page-ia.js:140–151`) — use `namedSlug(claim)` instead of the canonical slash.
- **Path B unclaimed rows** — keep canonical slash but in muted color (no honor red — there's no name to honor).
- **Named Skills Explorer tile/list/flow** (`docs/js/named-skills.js:56,68,133`) — primary line becomes `namedSlug(ns)` in honor red; secondary muted line carries the title.
- **Skill Detail Overlay** (`docs/js/skill-explorer.js:88–89`) — primary `<div class="se-skill-name">` becomes `namedSlug(ns)` in honor red; the title moves to subtitle position.
- **Profile-page plaques** (`scripts/generateProfilePages.py:99–115`) — add a new `<div class="plaque-named-slug">` line beneath the skill name, showing `/autoresearch` in honor red. Add CSS rule in `plaque.css`.

### Phase D — Unified plaque variants

Add size variants to `docs/css/plaque.css` so the same visual language scales across surfaces. All inherit the gold-hairline border + corner ornaments + EB Garamond skill name + Bricolage handle + Departure Mono mono accents + `data-type`-driven tier color (already wired in Phase 7).

- `.plaque--mini` — Hall of Heroes plate. ~200px wide, ~220px tall. Single orb glyph + named slug + linked handle + 6★ row + level chip.
- `.plaque--tile` — Named Skills Explorer tile view. Replaces `.ns-tile` chrome (keeps the existing grid container).
- `.plaque--row` — Named Skills list view. Horizontal flex layout, ~80px tall.
- `.plaque--detail` — Skill Detail Overlay hero. Replaces `.se-hero-card` chrome.

The orb glyph (currently `docs/css/styles.css:.se-node-orb--basic/--extra/--ultimate/--unique/--vi`) becomes the **canonical tier icon** used in every variant. Generalize the selector from `.se-node-orb` to `.plaque-orb` (alias the old class so the skill-explorer hero keeps working through the transition).

### Phase E — Hall of Heroes restructure

- In `docs/index.html`, wrap `.hoh-plates` in `<div class="hoh-track-wrap"><div class="hoh-track" id="hohPlates">...</div></div>`.
- `docs/js/page-ia.js` — render plates as `.plaque.plaque--mini` (orb + named slug in honor red + linked handle + star row). Duplicate the rendered string (`+ rendered`) so the marquee can loop seamlessly. Click → `openSkillExplorer`. No hover-opens.
- `docs/css/styles.css`:
  - `.hoh-track-wrap { overflow:hidden; mask-image: linear-gradient(90deg, transparent, #000 8%, #000 92%, transparent); }`
  - `.hoh-track { display:flex; gap:1rem; width:max-content; animation: hoh-drift 60s linear infinite; }`
  - `@keyframes hoh-drift { from { transform: translateX(0); } to { transform: translateX(-50%); } }`
  - `.hoh-track:hover, .hoh-track:focus-within { animation-play-state: paused; }`
  - `@media (prefers-reduced-motion: reduce) { .hoh-track { animation: none; overflow-x: auto; scroll-snap-type: x mandatory; } .hoh-track > * { scroll-snap-align: start; } }`
- Add a small JS handler: on `pointerdown` over `.hoh-track`, switch the track to `overflow-x: auto` + animation paused for that session (manual override). Restore on `mouseleave` after 4s of idle. Honor `prefers-reduced-motion` (skip the drift entirely; stay manual).

### Phase F — Universal nav header

- Replace `NAV_HTML` in `scripts/generateProfilePages.py:163–177` with the full 5-item nav matching `docs/index.html:29–35`. Cross-page anchors: Registry → `../../#paths`, Hall of Heroes → `../../#hall-of-heroes`, Codex → `../../codex.html`, Tree → `../../#tree`, search-icon → `../../#search`. The home page already has handlers in `page-ia.js:298–315` for both `#tree` and `#search`.
- Regenerate all 29 profile pages.
- Audit `codex.html` for parity (already mostly correct after Phase 7).

### Phase G — Named Skills Explorer redesign

- `docs/js/named-skills.js:48–61, 63–75, 121–139` — replace tile, list-row, and DAG-card markup to use `.plaque.plaque--tile/--row` shells with orb glyph from Phase D.
- Primary line: `namedSlug(ns)` in honor red (EB Garamond). Secondary line: title (Bricolage muted). Tertiary: level chip + tags (Departure Mono).
- Contributor handle on hover-reveal or always-shown (small) — linked.
- Keep `.ns-controls` filter UI and the tile/list/flow view toggle intact.

### Phase H — Skill Detail Overlay redesign

- `docs/js/skill-explorer.js:71–104` `renderHero()` — rebuild on the `.plaque.plaque--detail` shell:
  - Left column: orb (`plaque-orb plaque-orb--{type}`), named slug in honor red, linked contributor handle, level + class badges, install command.
  - Right column: description in Bricolage, tags in Departure Mono.
- `docs/css/styles.css` `.se-*` selectors — keep for backwards compatibility but layer plaque overrides. (Or delete `.se-hero-card` chrome and let `.plaque--detail` carry the visuals.)
- Evidence section, upgrade section, timeline section all switched to plaque-typography (EB Garamond headings, Bricolage body, Departure Mono mono).
- Drop "· SS" et al. from the evidence chip (already covered in Phase B's `plaque-reveal.js` fix; also strip if `skill-explorer.js` constructs its own labels).

### Phase I — Contributor handles always clickable

Audit revealed 13 unlinked sites. Patch each to wrap the handle in `handleLink()`:

- `page-ia.js:234` (HoH plate)
- `skill-explorer.js:89` (hero), `skill-explorer.js:468, 471` (unnamed popup)
- `plaque-reveal.js:93–94` (plaque template)
- `scripts/generateProfilePages.py:104` (plaque card on the contributor's own profile page — link to other contributors if their plaque is rendered; self-link harmless)
- **Tree projection**: `scripts/generateProjections.py` — when emitting `karpathy/autoresearch` in `docs/tree.md` or `registry/skills/**/*.md`, wrap the leading contributor segment as `[@karpathy](u/karpathy/)`. Use relative paths that work from where the file is served (`docs/tree.md` is served from `/tree.md` so use `u/karpathy/`).
- **Registry index documents** — `registry/registry.md`, `registry/combinations.md` (these reference skill IDs but rarely standalone handles; check the generator's output and only patch where handles appear standalone).

### Phase J — Verification

```
python -m pytest tests/test_docs_site.py -q              # 5 passed
PYTHONPATH=src python3 scripts/build_docs.py --check     # up to date
python scripts/generateProfilePages.py                   # regen 29 pages
python scripts/generateOgCards.py                        # regen 49 SVG+PNG
python scripts/generateProjections.py                    # regen tree.md + per-skill md
for f in docs/js/*.js; do node -c "$f"; done             # syntax check
curl -sIo /dev/null -w "%{http_code}\n" http://localhost:8000/{,codex.html,u/karpathy/,u/openai/,u/mattpocock/}
```

Visual review via the localhost server at `http://192.168.86.20:8000`:
- HoH drift pauses on hover; manual drag works; respects reduced motion
- Click any plaque → explorer opens in new design language
- Every contributor handle is a hover-underlined link
- `/autoresearch` shows in honor red across all surfaces; `/autonomous-research-agent` only appears for unclaimed Ultimates (in muted text)
- Ascension Cycle stars cycle teal → violet → fuchsia → amber per DESIGN.md
- No "· SS", "· V", "· IV" strings anywhere

## Critical files to modify

| File | Phase | Change |
|---|---|---|
| `docs/css/styles.css` | A, E, G | Ascension tier colors; `.hoh-track*`; trim `.ns-*` overlap with plaque variants |
| `docs/css/plaque.css` | D | New size variants `.plaque--mini/--tile/--row/--detail`; `.plaque-orb` + `--{type}` |
| `docs/js/atlas-helpers.js` *(new)* | A | `namedSlug`, `profileHref`, `handleLink` |
| `docs/js/page-ia.js` | C, E, I | HoH plate render; Path B slug+handle |
| `docs/js/named-skills.js` | C, G, I | Tile/list/flow render |
| `docs/js/skill-explorer.js` | C, H, I | `renderHero`, unnamed popup, evidence chip |
| `docs/js/plaque-reveal.js` | B, I | Evidence string; plaque template handle |
| `docs/index.html` | E | HoH track wrapper |
| `scripts/_atlas_helpers.py` *(new)* | A | Python mirrors |
| `scripts/generateProfilePages.py` | B, F, I | Nav, evidence, linked handles |
| `scripts/generateOgCards.py` | B | Evidence strings |
| `scripts/generateProjections.py` | I | Markdown link around contributor mentions in tree.md + registry/skills/**/*.md |
| `DESIGN.md` | B | Footnote on deprecated Class letter column |

Plus regenerated artifacts (committed as part of each phase): `docs/u/**/*.html`, `docs/og/**/*.{svg,png}`, `docs/tree.md`, `registry/skills/**/*.md`, `registry/registry.md`, `registry/combinations.md`.

## Existing utilities to reuse

- `LEVEL_META` (`docs/js/named-skills.js:13–24`) — rank color/badge metadata. Authoritative for tier coloring; align with DESIGN.md.
- `LEVEL_META_SE` (`docs/js/skill-explorer.js`) — explorer-side rank metadata. Consolidate into a single source if drift exists.
- `.plaque-*` token system (`docs/css/plaque.css:1–155`) — already established; size variants slot in cleanly.
- `.se-node-orb--*` (`docs/css/styles.css:1553–1561`) — canonical orb visual, generalize to `.plaque-orb`.
- `openSkillExplorer(id)` (`docs/js/skill-explorer.js`) — single entry-point; all plaques call it on click.
- `openUnnamedPopup(skill)` (`docs/js/skill-explorer.js:442`) — Claim button entry-point.
- Profile-page route convention: `./u/{handle}/` with handle in registry case (`mattpocock`, `0xdarkmatter`, `Manavarya09`). `encodeURIComponent` preserves casing.

## Risks / open items

- **Cross-page Tree on profile pages**: profile pages don't load `page-ia.js`, so the `#tree` hash handler doesn't run. Add a 6-line inline script in the profile-page template that watches for `#tree`/`#search` in the URL and redirects to `../../index.html` with the same hash — the home page's existing handler takes over.
- **Auto-drift accessibility**: the HoH drift must pause under `prefers-reduced-motion` AND on hover/focus. Verify keyboard navigation: tabbing into a plate should pause the drift via `:focus-within`.
- **Registry markdown changes** (`registry/skills/**/*.md`): the `design/` branch scope is HTML/CSS/JS in `docs/`. The markdown generator changes touch files outside that scope. Mitigation: keep this Phase I change inside `scripts/generateProjections.py` (which is allowed) and either (a) regenerate and commit on the same branch with an explanatory commit message and the `skip-scope-check` label if CI blocks, or (b) split Phase I's registry-markdown sub-task to a follow-up `dev/` branch.
- **"SS" in `DESIGN.md`**: not a runtime label; the user asked to stop emitting "SS" on the *skills page*. Approach: leave the historical column in `DESIGN.md` with a deprecation note rather than rewriting the table, because the letter-class is referenced in older registry annotations.
