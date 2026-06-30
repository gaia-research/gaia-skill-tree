# W2 — Hall of Heroes Implementation Spec

**Status:** Ready for Opus worker  
**Branch:** `feat/sprint-b/hall-of-heroes` → `dev/sprint-b-closure`  
**Quality bar:** /impeccable  
**Resolves:** #854  

---

## Visual Design Concept

**Aesthetic:** Dark ceremonial gallery — museum exhibition for digital legends. Each hero occupies a "stage" (full-width theatrical viewport slice). Scroll through stages vertically; each feels like turning a page in a prestige folio.

**Font additions (auto-picked):**
- **Cinzel Decorative** — ceremonial display for hero names/section titles
- **EB Garamond** — retained for body/epithets
- **Departure Mono** (or Space Grotesk tabular) — stats/TM numbers

**Color tokens (no hex!):**
- `--heroes-bg-deep: oklch(0.12 0.02 250)`
- `--heroes-gold-warm: oklch(0.78 0.15 80)`
- `--heroes-frost: oklch(0.92 0.01 220)`
- All tier colors stay canonical

---

## Per-Hero Animations (Ultimate ◆ 5★+)

| Hero | Skill | Animation |
|------|-------|-----------|
| garrytan | gstack | "Constellation Assembly" — 47 dots drift in from edges, assemble into pattern, card materializes |
| ruvnet | ruflo | "Sovereign Emergence" — rises from below with vertical light-beam column, hexagonal grid behind |
| mattpocock | skills | "Type Forge" — lightning arcs converge, clip-path wipe reveal, glitch text resolves |
| obra | superpowers | "Plugin Cascade" — cards fan out then collect into one, ephemeral sub-cards orbit then merge |

**Below Ultimate:**
- Apex/Extra 5★+: Gold border sweep, scale-in from 0.95, subtle particle dust
- Unique 4★+: Violet edge-glow pulse, fade-up, ornamental corner marks
- Named 3★+: Clean fade-up, tier-colored accent bar slides in

---

## Component Architecture

```
docs/heroes/
├── index.html          — page shell, stages, share modal DOM
├── heroes.css          — all styles (~400 lines)
├── heroes.js           — orchestrator: fetch, rank, render, IntersectionObserver
├── hero-animations.js  — per-hero animation controllers (~500 lines)
└── hero-share.js       — gallery share enhancements (~60 lines)
```

---

## Share Modal (MUST RETAIN)

- Duplicate `#hohFullscreenModal` DOM into heroes page (same IDs, same data attributes)
- Load `hoh-modal.js` as-is (delegated events auto-wire)
- `hero-share.js` adds: "View in Gallery" scroll-to-stage on modal close
- OG path resolution unchanged: `docs/og/<handle>/<slug>.svg`

---

## Data Flow

1. Fetch `/api/v1/contributors/index.json`
2. Filter: topSkill.level ≥ "4★"
3. Sort by prestigeScore descending
4. For ultimates: fetch `/api/v1/contributors/<handle>.json` for full skill list
5. Render stages with tier-specific treatment

---

## Responsive Strategy

| Breakpoint | Behavior |
|---|---|
| ≥1200px | Full theatrical — 100svh stages, canvas particles, all animations |
| 820–1199px | 80svh stages, particles reduced 50%, card scale 0.9 |
| 560–819px | Auto-height stages, particles disabled, simplified animations |
| <560px | Single column, no canvas, prefers-reduced-motion respected |

---

## Performance Budget

- JS payload: ≤80KB uncompressed
- Canvas particles: ≤120 @ 30fps, paused off-screen
- IntersectionObserver threshold: 0.3
- Fonts: preload + swap
- Total page weight: ≤150KB first paint
- Canvas cleanup when stage >200vh away

---

## Commit Sequence

1. `feat(heroes): scaffold page shell + mounts registration`
2. `feat(heroes): page CSS — layout, stages, responsive`
3. `feat(heroes): core orchestrator — fetch, rank, render stages`
4. `feat(heroes): per-hero bespoke animations`
5. `feat(heroes): share modal integration`
6. `feat(heroes): homepage cross-link`
