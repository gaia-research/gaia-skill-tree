# Commission asset brief — Ascension Cycle Overdrive (v6.1.x)

> Vendor-facing shopping list for the illustration/motion assets required by `founder/handovers/design-v6.1.1-ascension-overdrive-shape.md`. This document is safe to share externally with commissioned illustrators / motion designers.
>
> Tracking issue: **TBD** (filed alongside this brief). Ship target: PR follows once assets land.

---

## Project context (for the illustrator)

Gaia is an evidence-backed skill registry for AI agents, presented as a public ledger with the ceremonial gravity of a guild admissions register. The homepage's Ascension Cycle section teaches how ranks (0★ Basic through 6★ Apex) actually work, plus a parallel prestige class called **Unique** that non-suite skills earn at 4★+.

**Reference anchors (mood board):**
- 19th-century natural history atlas plates — Ernst Haeckel's *Kunstformen der Natur*; Charles Darwin's *Origin* first-edition plates; Alexander von Humboldt's *Cosmos*
- Museum specimen annotation — brass identification tags, plate cartouche labels, hairline plate rulings
- Ceremonial admissions register — leather-bound ledger books; hand-ruled pages; ink-and-lamp-oil lighting
- Solo Leveling guild-registry gravity, without any anime UI

**Anti-references (do not deliver):**
- No hand-sketchy woodcut clip art
- No AI-generated illustration
- No Fiverr / vector-stock generic "atlas" imagery
- No fantasy-game gates or portals
- No sci-fi space-scene renderings
- No decorative "aged parchment" textures with fake weathering

---

## Asset A — Apex Gate arch (Tier 1, priority signature)

**Purpose:** the visual backdrop of the Apex Gate predicate panel. Six-columned or six-arched atlas plate rendering that anchors the six named predicates displayed in front of it.

**Deliverables:**
- One primary illustration, ~1200×800px display size
- Formats: transparent PNG (retina 2400×1600 source), plus SVG source (Illustrator .ai or Figma export acceptable)
- Style: single-plate natural-history-atlas rendering, hairline linework, restrained cross-hatching. Six architectural elements (columns, arches, gates, or steles) arranged in a plate composition. The plate should read as *"the six conditions of admission"* metaphorically, not as a fantasy portal.
- Colour: **monochrome greyscale linework only** — CSS filter will tint the delivered asset with `--apex-gold` (#d4af37) at 6–10% opacity. Do not deliver pre-tinted or coloured. Fine linework must survive at 10% opacity over a near-black background.
- Composition weight: content clusters in the horizontal middle band; leave top and bottom quarters clean so the panel eyebrow and caption sit against negative space.

**Failure conditions:**
- Reads as a fantasy game portal
- Any element feels illustrated recently (2020s vector aesthetic)
- Linework too heavy to remain visible at 10% opacity
- Symmetrical composition that looks generic rather than plate-specific

**Estimated budget:** $600–1400 depending on illustrator tier.
**Turnaround:** 2–3 weeks including one revision round.

---

## Asset B — Ledger paper base texture (Tier 1, atmospheric foundation)

**Purpose:** the section-wide background texture blended `multiply` at 8–12% opacity over `--bg` (#030712), giving the whole plate a ledger-paper substrate.

**Deliverables:**
- One high-resolution image, ~2000×3000px
- Formats: WebP (primary, ≤80KB after optimization) + JPEG fallback (≤120KB)
- Source: preferably a genuine period ledger page scan from a public-domain archive (British Library, MET Open Access, Internet Archive, National Archives). Alternatively, a hand-photographed scan of aged paper with hairline rulings.
- Colour: warm-cool neutral, low saturation (chroma near 0.02 in OKLCH — i.e. *desaturated near-neutral*, not warm beige). At 8–12% opacity over near-black `--bg`, the texture reads as substrate, not stain.

**Failure conditions:**
- Any AI-generated paper texture
- Overtly "aged" or "distressed" — the ledger should read as *kept*, not *ruined*
- Warm beige at high saturation (this lands on PRODUCT.md's saturated-warm-neutral anti-reference)

**Estimated budget:** $0 if sourced from public-domain scans; $50–150 for licensed period paper stock; $200–400 for a commissioned scan.
**Turnaround:** days if public-domain-sourced; 1 week if commissioned scan.

---

## Asset C — Six rank-glyph atlas stamps (Tier 2, elevates the whole section)

**Purpose:** one small hand-drawn atlas-plate stamp above each rank card, matching Asset A's linework style so all elements read as one plate family.

**Deliverables:**
- Six illustrations delivered as **one coherent series**, ~200×200px each display size (retina 400×400 source)
- Formats: transparent PNG per stamp, plus one combined SVG sprite (Illustrator source)
- Style: single-mark atlas plate stamps in the same linework language as Asset A. Each is one clear iconic subject, hairline execution.
- Colour: monochrome greyscale linework — CSS will tint each to its rank token (`--rank-N`) at display time

**Six subjects (fixed, not for reinterpretation):**

| Rank | Subject | Metaphor |
|---|---|---|
| 1★ Awakened | A candle or single ember | *verified as real, not yet named* |
| 2★ Named | A signet stamp or wax seal impression | *RPG title assigned* |
| 3★ Evolved | A brass compass with visible verified point | *blob link verified* |
| 4★ Hardened | An anvil, or a stylised shield | *security-reviewed* |
| 5★ Transcendent | A laurel wreath, half-open | *enterprise-ready* |
| 6★ Apex | *Reserved* — this rank uses the Apex Gate arch (Asset A) instead of an individual stamp |

Note: only five stamps are actually commissioned. The 6★ slot is rendered by Asset A.

**Failure conditions:**
- Any two stamps read as siblings but not as *the same illustrator's hand*
- Any stamp reads more literal than iconic (e.g. a photo-realistic anvil rather than an illustrated plate stamp)
- Style drift from Asset A's linework

**Estimated budget:** $600–1500 for five stamps as a coherent series from the same illustrator as Asset A.
**Turnaround:** 2–3 weeks; commission alongside Asset A for style consistency.

---

## Asset D — Three Unique class glyphs (Tier 2, signature)

**Purpose:** the three Unique cards on the parallel branch, each with its own colour treatment representing the class's evolution across 4★ → 5★ → 6★. This is the section's most distinctive visual argument.

**Deliverables:**
- Three illustrations delivered as **one coherent evolution series**, ~240×240px each display size (retina 480×480 source)
- Formats: transparent PNG per glyph, plus one combined SVG source. Assets D2 and D3 optionally also delivered as looping WebM+MP4 pair (see Asset E for motion spec).

**Three subjects (color pegs operator-ratified):**

### D1 — Unique 4★ (violet, *structural*)
- Subject: a struck coin or medallion in the atlas-plate stamp style, bearing the `◉` glyph in the centre
- Colour: monochrome linework, CSS-tinted to `--tier-unique` (#7c3aed) at display
- Metaphor: *the structural off-ramp — a Basic/Extra skill that stayed non-suite*

### D2 — Unique 5★ (**black hole + gold**, *gravitational*)
- Subject: a gravitational singularity rendered in the atlas-plate style — a deep near-black core with a hairline gold accretion ring at ~85% of the outer radius. The `◉` glyph sits at the centre, low-luminance gold.
- Style: still readable as atlas-plate illustration (hairline linework at the ring's edge and gold cross-hatching or engraved detail on the accretion band), but composition is gravitational, not flat.
- Colour: deep near-black centre (`#050202`), `--apex-gold` (#d4af37) ring at low luminance. Do NOT deliver full-saturation gold — the ring must read as *ember gold on void*, not decorative bling.
- Metaphor: *depth so severe it curves gravitationally — the specimen has mass now*

### D3 — Unique 6★ (**white + black hole**, *impossible*)
- Subject: the same near-black gravitational field as D2, but the centre carries a small white singularity — a bright core (~8px radial spike) that fades outward through faint gold to void. The `◉` glyph is inverted: pure white on the void.
- Style: hairline atlas-plate linework at the edges, but the core is a genuine bright singular point (rendered, not stylised). The illustration must read as *"this shouldn't be possible."*
- Colour: near-black field (`#050202`), white core (`#ffffff` at full luminance), faint gold intermediate glow. High contrast between core and field.
- Metaphor: *Apex without fusion. A non-suite skill that reached Grade S. The impossible object.*

**Failure conditions:**
- The three glyphs read as three separate visual languages rather than the same class deepening
- D2's accretion ring reads as decorative bling rather than gravitational depth
- D3's white core reads as sci-fi optical bloom rather than as *the impossible point*
- Any of the three lose the `◉` glyph reference — that mark is the class's identity anchor

**Estimated budget:** $700–1800 for the three-piece coherent series. If the same illustrator delivers Asset A and Asset C, they can typically hold the linework family across D as well; commission as one contract.
**Turnaround:** 3 weeks; commission alongside A and C.

---

## Asset E — Optional motion loops for Unique 5★ and 6★ (Tier 3, polish)

**Purpose:** subtle looping motion on Assets D2 and D3 to sell the "gravitational" reading. The static illustrations work; motion elevates them from *illustrated depth* to *felt depth*.

**Deliverables (optional; commission only if D2 and D3 already delivered and read cleanly):**

### E1 — Unique 5★ accretion ring rotation loop
- Subject: D2's gold accretion ring rotates once every 8–12 seconds, one full revolution. Rotation is uniform; no easing.
- Format: WebM (VP9) + MP4 (H.264) pair, 640×640, ≤300KB combined, seamless loop
- Alpha channel: WebM with alpha; MP4 with matte fallback
- Frame rate: 30fps (24fps acceptable for size reduction)

### E2 — Unique 6★ white core breathe loop
- Subject: D3's white singularity core "breathes" — subtle luminance modulation between full white and 85% white over ~4-second cycle, ease-in-out sine
- Format: WebM (VP9) + MP4 (H.264) pair, 640×640, ≤250KB combined, seamless loop
- Alpha channel: as E1
- Frame rate: 30fps

**Playback discipline (implementation-side, not vendor):**
- Both loops autoplay muted, `loop`, `playsinline`
- Both wrapped in `@media (prefers-reduced-motion: no-preference)` guard; reduced-motion falls back to the static PNGs from Asset D
- Both pause when off-screen via IntersectionObserver; resume when in-viewport

**Failure conditions:**
- Loop seam visible (any frame-to-frame discontinuity at the join)
- Motion reads as busy rather than gravitational
- File size exceeds spec — this is a signature section, not a video wall

**Estimated budget:** $400–1000 for both loops delivered by a motion designer with credentials in editorial + scientific-illustration adjacent motion. Motion Society, Cartoon Brew–adjacent illustrator/motion-designer collaboratives; not stock motion-graphics vendors.
**Turnaround:** 2 weeks after Asset D delivery.

---

## Summary table

| Asset | Purpose | Priority | Budget | Turnaround |
|---|---|---|---|---|
| A — Apex Gate arch | Signature backdrop | **Tier 1 (must)** | $600–1400 | 2–3 wk |
| B — Ledger paper texture | Section base | **Tier 1 (must)** | $0–400 | days–1 wk |
| C — Five rank stamps | Per-rank atlas marks | Tier 2 (recommended) | $600–1500 | 2–3 wk |
| D — Three Unique glyphs (violet / gold-hole / white-hole) | Signature evolution | **Tier 2 (recommended — highest ROI)** | $700–1800 | 3 wk |
| E — Unique motion loops (5★ / 6★) | Optional polish | Tier 3 (if D reads clean) | $400–1000 | 2 wk after D |

**Recommended commission bundle for full signature ship:** A + B + D. That's ~$1300–3600 depending on illustrator tier, and it lands the two most distinctive visual arguments (the Apex Gate arch + the Unique evolution) plus the ledger substrate that makes everything else feel plate-consistent. Asset C is a nice-to-have that elevates the middle-rank stages from "chip on a card" to "specimen in a plate"; skip if budget is tight.

**Recommended commission bundle for maximum impact:** A + B + C + D + E. ~$1700–4600. This is the full atlas-plate treatment with motion polish. Would justify the "extravagant" instruction from the operator.

---

## Illustrator vendor guidance

Prefer illustrators with **editorial + scientific-illustration** credentials. Portfolios that include:

- Scientific / natural-history plate illustration (botanical, zoological, geological)
- Editorial illustration for magazines like *Nautilus*, *Scientific American*, *Aeon*, *The New York Review of Books*
- Book cover work for university presses or small independent literary publishers
- Any published scientific plate work post-2010 that reads as *contemporary hand* interpreting a period language

Avoid illustrators whose portfolios are primarily:
- Character illustration / concept art / game art
- Vector-stock or Fiverr-tier commercial work
- AI-composited or hybrid AI-assisted styles
- Fantasy game art or portal/gate imagery specifically

Named illustrators as style pegs (not necessarily commission-available, but examples of the register):
- Kate Baylay
- Emily Carroll
- Nate Kitch (editorial abstract)
- Klaas Verplancke (editorial plate style)
- Elenia Beretta (natural history editorial)
- Marta Monteiro (linework-driven editorial)

For **motion (Asset E)**, prefer motion designers who have worked on:
- Editorial explainer motion for *The Pudding*, *The New York Times*, *Bloomberg*
- Scientific-illustration adjacent motion (data visualisation with restraint)
- Not: motion-graphics agencies whose reel is dominated by SaaS explainer video work

---

## Handover format

When commissioning, send illustrators:

1. This document
2. `founder/handovers/design-v6.1.1-ascension-overdrive-shape.md`
3. Access to Gaia's `PRODUCT.md` and `DESIGN.md` (public — link to the GitHub repo)
4. The public site at `gaiaskilltree.com/` so they can see the tonal context

Do NOT send:
- Screenshots of AI-generated versions "for reference"
- Fantasy-game gate references
- Sci-fi space visualisation references

If the illustrator asks for tighter mood-board input, the natural-history atlas anchors listed at the top of this document are the answer.

---

## Delivery + ratification checklist

Upon delivery of each asset, verify:

- [ ] Format spec met (dimensions, file size, transparency, format list)
- [ ] Displays cleanly at 10% opacity over `--bg` (Asset A) or blended `multiply` at 12% (Asset B)
- [ ] Renders correctly with CSS filter tinting (Assets A, C, D1)
- [ ] Assets D2 and D3 hold their gravitational reading at final display size
- [ ] Motion loops (E1, E2) are seamless — no visible loop seam
- [ ] All asset filenames follow the pattern `ascension-overdrive-<asset-id>-<version>.<format>` (e.g. `ascension-overdrive-apex-arch-v1.svg`)
- [ ] Sources delivered alongside rendered outputs (Illustrator, Figma, or comparable)
- [ ] Licensing terms captured in `evidence/asset-licenses/ascension-overdrive.md` on delivery

**Storage location on delivery:** `docs/assets/ascension-overdrive/` for shipped optimised outputs; `founder/handovers/design-v6.1.1-assets/` for source files.
