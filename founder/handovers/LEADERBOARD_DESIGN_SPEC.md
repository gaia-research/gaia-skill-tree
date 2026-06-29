# Trust Leaderboard — Design Spec
**Status:** Implemented — pending visual review  
**Branch:** dev/leaderboard-redesign → dev/sprint-b2-trending  
**Author:** Opus planning agent, 2026-06-28  
**Estimated complexity:** L (~800 LOC across 3 files)

---

## Data model summary

### Sources
| Endpoint | Contents | Availability |
|----------|----------|--------------|
| `../../api/v1/leaderboard.json` | `distribution` + flat `rows[]` with `{id, trustMagnitude, grade, level}` for all 249 skills sorted by TM desc | ✅ |
| `../../api/v1/skills/index.json` + page-2, page-3 | `{id, name, level, trustMagnitude, overallTrustGrade, contributor, type, _links}` | ✅ |
| `../../api/v1/trending/7d.json` | `{window, firstRun, skills: [{id, tmDelta, trendingScore, …}]}` | ⚠️ Graceful 404 fallback |

### Three lanes (by type + grade)
| Lane | Filter | Count |
|------|--------|-------|
| **Suites** | `type === 'ultimate'` | 4 (garrytan/gstack 589.32, ruvnet/ruflo 482.27, mattpocock/skills 480.29, obra/superpowers 445.15) |
| **Named Skills** | `grade !== 'ungraded' && type !== 'ultimate'` | ~175 (TM range: 270→30) |
| **In Registry** | `grade === 'ungraded'` | ~70 (TM range: 6.3→0) |

### Suite metadata
Hardcoded component counts as fallback: gstack=43, ruflo=20, skills=34, superpowers=12.  
Detail JSONs fetched in parallel after initial render for progressive enhancement.

---

## Layout architecture

```
┌─────────────────────────────────────────────────┐
│  <nav> site-nav                                 │
├─────────────────────────────────────────────────┤
│  HEADER: h1 + subtitle + distribution pills     │
│  CONTROLS: Sort toggle group + Grade filter     │
├─────────────────────────────────────────────────┤
│  § SUITES LANE (4 hero cards with TM bars)      │
├─────────────────────────────────────────────────┤
│  § NAMED SKILLS LANE (dense bar chart rows)     │
├─────────────────────────────────────────────────┤
│  § IN REGISTRY LANE (muted compact list)        │
├─────────────────────────────────────────────────┤
│  § CTA FOOTER                                   │
├─────────────────────────────────────────────────┤
│  <footer> site-footer                           │
└─────────────────────────────────────────────────┘
```

**Max width:** `min(1440px, 96vw)` centered.  
**Responsive breakpoints:**
- `≥1024px` — full layout, all columns visible
- `720px–1023px` — trending column hidden (`display:none`)
- `<720px` — grade/stars columns hidden, suite cards compact, controls stack

---

## Suite lane design

Section title: `◆ Ultimate Suites` (display font, 1.5rem)

Each suite renders as a card with:
- Left platinum border accent (`border-left: 3px solid var(--evidence-platinum)`)
- Header row: rank · name + contributor + badge · TM value
- TM bar: `height: 6px`, fill = `width: calc(TM / 600 * 100%)`, platinum gradient
- Description: fetched from skill detail JSON, hardcoded fallback counts while loading

Hover: border brightens with `rgba(var(--evidence-platinum-rgb), 0.4)`.

---

## Named Skills lane design

Column grid: `3rem (rank) | 1fr (id) | 40% (bar+tm) | 2.5rem (grade) | 3rem (stars) | 4.5rem (trend)`

Key details:
- **Bar scale:** `TM / maxTmInLane * 100%` (not global 600 ceiling — uses 270 = max for this lane so bars span the full track width)
- **Bar color by grade:** A=gold-rgb, B=silver-rgb, C=bronze-rgb (all via `rgba(var(--evidence-X-rgb), Y)`)
- **Contributor in honor-red**, skill slug in default text color
- **Trending delta:** `+12.3` (tier-extra purple) / `-5.1` (honor-red) / `—` (muted) — sign IS the direction, no arrow glyph
- **Row height:** 36px min — data-dense, not cards

---

## Starless / In Registry lane design

- Grouped by contributor handle
- Handle in italic muted mono, skill names inline with `·` separator
- Initial display: 3 contributor groups + "Show all N contributors →" toggle
- Section separated by `1px dashed var(--border)`
- No TM bars (all ungraded)

---

## Header + controls design

**Distribution pills:** inline-flex chips per grade (S/A/B/C/—), grade letter colored by evidence token, count in mono.

**Sort controls:** TM (default) | Trending 7d | Grade — button group with `is-active` state. "Trending 7d" disabled with tooltip when 7d.json 404s.

**Grade filter:** All | S | A | B | C — hides/shows rows client-side. When filter=A/B/C, Suites lane hidden.

---

## CTA footer design

Copy: *"Is your AI skill missing? Push it to the registry. Evidence gets you on the board."*  
Code snippet: `gaia push` in mono with `.cmd { color: var(--tier-basic) }`  
Link to CONTRIBUTING.md.

---

## Files

| File | Lines | Status |
|------|-------|--------|
| `docs/trust/leaderboard/index.html` | ~80 | ✅ Implemented |
| `docs/trust/leaderboard/leaderboard.css` | 109 | ✅ Implemented — zero hex |
| `docs/trust/leaderboard/leaderboard.js` | 310 | ✅ Implemented |
| `scripts/build_docs.py` | +1 line | ✅ cache-bust registered |

---

## Key design decisions

1. **CSS `width` bars, not SVG** — simpler, transitions for free, responsive by default
2. **Suite cards vs rows** — elevated visual weight (card, platinum border) justified by 4× TM advantage
3. **Bar scale is lane-relative** — named lane bars scale to maxTmInLane (270), not global 600. Suites use 600 (absolute). Each lane communicates relative standing within its tier.
4. **Trending delta as rightmost column** — sign as direction (`+12.3` / `-5.1`), colored purple/red. No arrow glyphs.
5. **Grade filter drives suite lane visibility** — filtering to A/B/C hides the suites lane entirely (suites are all S-grade)
6. **Progressive suite detail loading** — page renders immediately, descriptions update via deferred fetch
7. **No mounts.js change** — `trust` mount already covers `trust/leaderboard/` at depth-2

---

## Localhost preview

```bash
cd docs && python3 -m http.server 8080
# Open: http://localhost:8080/trust/leaderboard/
```

For firecrawl screenshot (if available):
```bash
firecrawl screenshot "http://localhost:8080/trust/leaderboard/" -o .firecrawl/leaderboard-desktop.png --viewport 1440x900
firecrawl screenshot "http://localhost:8080/trust/leaderboard/" -o .firecrawl/leaderboard-mobile.png --viewport 375x812
```

---

## Token budget (actual)

| Phase | Model | Notes |
|-------|-------|-------|
| Opus planning pass | Opus | Design spec, data model, component spec |
| Worker implementation | Sonnet | ~654 tests passing, 0 hex violations |
| **Estimated total** | | **~$3–4** (cache-dominant) |
