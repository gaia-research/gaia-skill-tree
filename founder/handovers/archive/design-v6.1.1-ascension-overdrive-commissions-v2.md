# Ascension Overdrive Commissions — v2 Addendum (Bold Direction)

> Addendum to `design-v6.1.1-ascension-overdrive-commissions.md`. v1 assets (A–E) are all still in play. v2 adds Assets F, A-v2, G. Vendor briefing note at bottom.

## Terminology corrections for v2 (operator-ratified 2026-07-06)

When labeling asset files, use:
- 4★ Unique → **`unique-4`** (no sub-name in filenames)
- 5★ Unique → **`unique-5-ultimate`** (drop `gravitational`)
- 6★ Unique → **`unique-6-impossible`** (formally *Unique Apex*; prestige name *Unique Impossible*)

## Asset F — Six rank hero plates (new)

**Purpose.** v2 renders each rank as a ~100vh sticky-pinned scene. The scene needs a full-viewport backdrop that carries the rank's identity at bleed scale. v1's 1254×1254 square stamps are perfect for card-scale composition but read small when the composition is viewport-scale. Asset F fills that gap.

**Deliverable.**
- 6 plates, one per rank (Awakened / Named / Evolved / Hardened / Transcendent / Apex)
- **2560×1440** minimum; 3840×2160 preferred if the illustrator's workflow supports
- Format: WebP primary + PNG source; ≤200KB WebP per plate
- Alpha channel not required for the backdrop layer *if* the ground colour is solid and easily masked with CSS; alpha REQUIRED on the rank stamp/subject if the vendor delivers as a layered PSD

**Composition per plate.**
- Rank stamp / subject (a stylized rank icon) sits centered vertically at ~60% frame height
- Generous negative space at all edges — the typography overlays this at viewport scale, so leave the upper third and lower third mostly empty
- Ground: single flat colour in the rank's `--rank-N` family, subtly textured with ledger-paper grain at low opacity
  - Rank 1 Awakened → warm graphite blue ground
  - Rank 2 Named → teal-gray ground
  - Rank 3 Evolved → violet-gray ground
  - Rank 4 Hardened → warm rose-plum ground
  - Rank 5 Transcendent → soft gold ground
  - Rank 6 Apex → deep near-black with faint gold flecks

**Anti-references (do NOT produce):**
- Detailed background scenes (v1 stamps had complex grounds that don't composite over the ledger)
- Ornate borders or decorative frames within the plate (typography and CSS handle framing)
- Gradients from edge to edge (flat ground preferred; gradient reads as "web design", not "atlas plate")
- Realistic rendering (keep the natural-history-atlas / illuminated-manuscript register from v1)

**Pegs.**
- Kate Baylay atlas plates: single-subject compositions, generous margins, flat coloured grounds
- Emily Carroll compositional restraint (v1 anchor illustrator, unchanged)
- Contemporary reference: Nick Sherman's *Fonts In Use* full-viewport specimen plates

**Estimate.** $800–1600 for the set of 6, 2–3 weeks. Higher end reflects the resolution jump (2560×1440+ vs. v1's 1254² is ~2.6× the pixel area).

## Asset A-v2 — Bleed-composed Apex arch (supplement or replacement to Asset A v1)

**Purpose.** v2's Apex Gate scene pins for ~150vh with the arch as the visual anchor and the six brass-tag predicates arranged as a staircase below it. v1's Asset A (1536×1024) is a beautifully composed tight vignette but doesn't leave room to *breathe* at viewport scale — the predicates and closing type crowd against the arch's lower edge.

**Deliverable.**
- Single plate, 3840×2160 (16:9 bleed) OR 3840×2560 (3:2 vertical bleed if the composition prefers)
- Format: WebP + PNG source; ≤400KB WebP
- Alpha REQUIRED on the arch and background elements (single-flat-colour ground is fine, but the arch itself must be alpha-keyed for compositing over the ledger)

**Composition.**
- Same subject family as v1 Asset A: columns, arch, gate, obelisk, stele
- Arch positioned in the **upper third** of the frame
- **Lower two-thirds mostly empty** — this is where the predicate staircase renders in CSS
- Ground: same near-black / gold-fleck treatment as Asset F Rank 6
- The arch subject can be more elaborate than v1 (more architectural detail, more decorative flourish) — v1 was a museum vignette, v2 wants a *destination monument*

**Alternate direction (if illustrator prefers):** a single tall vertical composition (3:5 or 9:16) where the arch is at the top and a stair-step of subordinate architecture leads down to the viewer's eye level. The predicates then illuminate along the stair-step. This reads more literally as "ascension → gate → apex" than a horizontal composition.

**Estimate.** $700–1500, 2 weeks.

## Asset G — Parallax fog / haze layer (optional, valuable)

**Purpose.** v2's parallax has multiple z-planes (ledger, risers, main content, arch, thread). A single atmospheric layer between the ledger and the risers adds real depth on the bleed direction — the sensation of *looking into* the scene, not *at* the scene.

**Deliverable.**
- 1 plate, 2560×1440 or 2000×1200
- Alpha channel REQUIRED
- Format: WebP + PNG; ≤120KB WebP
- Subject: faint atmospheric wisps in warm sepia — think lantern-lit dust motes at midnight in a museum

**Composition.**
- Fully alpha-keyed atmospheric layer, no hard subject
- Subtle warm sepia tone (matches the ledger's palette family)
- Wisps concentrated at rank-transition y-axes (subtle "risers separate here" atmospheric cue)
- Overall opacity in-canvas 30–50% (CSS will further modulate)

**Estimate.** $300–700, 1 week. Optional — v2 shape can ship without this and add later.

## Vendor briefing note (resend + new asks combined)

When re-engaging the illustrator with the v1 asset resend AND the v2 commissions, include this briefing:

> **Direction change for v2:** The section is being re-executed at viewport scale (each rank fills the browser viewport as the user scrolls; the composition has real depth-parallax across multiple layers). This means:
>
> 1. **Backgrounds must be easy to remove.** v1's assets had detailed ground illustrations that don't composite cleanly over the ledger paper base. For v2, ALL new assets need a single flat coloured ground (or full alpha transparency). If the vendor's workflow prefers layered PSDs, ship both the flat-ground composite and the alpha-keyed subject layers.
> 2. **Higher resolutions for bleed.** v1's 1254×1254 stamps read small when the scene is viewport-scale. New assets should be 2560×1440 minimum; hero plates 3840×2160 preferred.
> 3. **Generous negative space.** Viewport-scale typography overlays the assets. Leave the upper third and lower third of each plate mostly empty so display type has room to sit.
> 4. **Alpha channel required on resends.** v1's PNGs are opaque; v2 needs the alpha-key versions promised in the original commission. The vendor's Asset C `Variations/ascension-overdrive-rank-stamps-variant-1-v1.png` proves the capability; extend to all primary assets.
> 5. **Filename-to-visual audit.** v1 delivery had rank stamps where filename didn't consistently match visible star count (e.g. `rank-2-named.png` showed a 3★ compass). Provide a written key with the resend: `awakened = candle | named = signet | evolved = compass | hardened = anvil | transcendent = laurel | apex = arch (Asset A)`.
> 6. **Half-Merged voice preserved.** No fantasy-game / sci-fi / SaaS drift. 19th-century natural-history-atlas / illuminated-manuscript register from v1 stays.

## Storage on delivery

- Vendor drops → `founder/handovers/design-v6.1.1-assets/Asset [X]/` (mirror v1 folder convention)
- Served kebab-case primaries → `docs/assets/ascension-overdrive/` (matches existing served path)

## Budget summary

| Asset | Purpose | Range | Priority |
|---|---|---|---|
| A resend (transparent) | Alpha-key v1 arch | included in original commission | P1 |
| C resend (transparent) | Alpha-key v1 rank stamps + filename fix | included in original commission | P1 |
| D resend (transparent) | Alpha-key v1 Unique glyphs | included in original commission | P1 |
| E recompression | Reduce unique-5-loop to <500KB + WebM siblings | $200–500 | P1 |
| **F — 6 rank hero plates** | Viewport-scale rank backdrops | **$800–1600** | **P2** |
| **A-v2 — bleed apex arch** | Viewport-scale Apex Gate anchor | **$700–1500** | **P2** |
| **G — parallax fog layer** | Depth between ledger and risers | **$300–700** | **P3 (optional)** |

**Total new commission budget for v2**: $2000–4300 on top of v1's original commission spend. Operator has approved unlimited budget for this section (per prior handover ratification).

## When to send

Send the vendor:
1. This addendum
2. The v1 resend list (from the original commissions doc)
3. The v2 shape brief (`design-v6.1.1-ascension-overdrive-shape-v2.md`)
4. Both v1 and v2 preview URLs (PR #988 for v1; forthcoming for v2) so they see the actual context their assets will live in

Two-way iteration expected: after v2 preview ships and Asset F drafts arrive, the illustrator and operator refine composition against the actual rendered scenes.
