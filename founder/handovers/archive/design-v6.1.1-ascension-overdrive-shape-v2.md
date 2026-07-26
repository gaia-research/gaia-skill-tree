# design-v6.1.1 — Ascension Cycle Overdrive Shape v2 (Bold Direction)

> Sibling to `design-v6.1.1-ascension-overdrive-shape.md` (v1). v1 shipped as PR #988 draft preview. v2 keeps the same mechanic content and five-plane structure but re-executes at **viewport scale**: full-page bleed, real multi-layer parallax, and experimental typography that treats the section as the destination scene of the entire site.

## Terminology ratification (operator, 2026-07-06)

The Unique class is the non-suite prestige branch. It exists across three ranks:

| Card | Formal name | Prestige name | What it is |
|---|---|---|---|
| **4★ Unique** | Unique | Unique | The entry state. A Basic-or-Extra skill that reaches 4★ without becoming a Suite earns the Unique class. Structural. |
| **5★ Unique** | **Unique Ultimate** | Unique Ultimate | A Unique that reaches 5★. Ultimate is the standard 5★ tier name; when a Unique clears it, the card reads *Unique Ultimate*. |
| **6★ Unique** | **Unique Apex** | **Unique Impossible** | A Unique that reaches 6★. Apex normally requires suite fusion; a Unique cannot fuse (by definition). Therefore Unique-Apex is Apex-grade trust *without* the suite fusion predicate. Literally impossible under the standard promotion path. The prestige name is **Unique Impossible**; the formal name is **Unique Apex**. |

**Dropped terminology (v2 does NOT use):**
- ❌ "Gravitational" (was v1's 5★ Unique name; replaced by *Unique Ultimate*)
- ❌ "Structural" as a card title (it stays as an internal shorthand for the 4★ visual language; the card title is just *Unique*)

**Preserved terminology (v2 keeps):**
- ✅ *Impossible* as the prestige/visual name for 6★ Unique (the "impossible object" reads correctly and the operator ratified)
- ✅ All main-line rank names per `META.md §1.1`: Awakened / Named / Evolved / Hardened / Transcendent / Apex

**Formal ratification pending**: this terminology needs to land in `META.md` (§1.1 Unique subsection + Star Bar tag table §2.4) as a schema/ branch PR. Not gating v2 craft; the shape brief IS the operator's ratification of record until META.md catches up. Track under Issue #975 follow-up.

**Content-invariance rule**: every rank name and tier name on the page must trace back to META.md (or to this document until META.md ratifies). The v2 worker MUST use `Unique / Unique Ultimate / Unique Apex` as the formal card titles and MAY use `Unique Impossible` as the prestige tag on the 6★ Unique card.

---

## What changed from v1

v1 (PR #988) executed the mechanic beautifully at **card scale**: cream picture frames, tidy grid, IntersectionObserver reveals, six-card row. Reads as a *well-composed spread*.

v2 executes the same mechanic at **viewport scale**: full-page bleed, real scroll-linked parallax, and typography at display-hero scale. Reads as *the destination scene of the entire site*.

Concretely, v2 differs from v1 on these axes and only these axes. Mechanic content, terminology, plane taxonomy, motion philosophy, failure tests, and Star Bar / Apex Gate / Unique-branch structure all inherit from v1 unchanged unless explicitly re-specified below.

### Axis 1 — Full-page bleed (no gutter)

The section owns its horizontal viewport. No left/right margin, no page gutter, no card boundaries that respect the container width. Content edges align to `100vw`, not to the site's `--content-max-width` (~72rem).

Nav clearance stays at `scroll-margin-top: 5rem` per `CLAUDE.md`; the top of the section still respects fixed-nav. But the *left and right edges bleed to the browser viewport*.

Implication for CSS: the section uses a full-viewport CSS grid or `margin-inline: calc(50% - 50vw)` escape from the main content column. Inner content stays legible via inner max-widths on the *content columns*, not on the section itself.

### Axis 2 — Real multi-layer parallax

v1 used IntersectionObserver-driven one-shot reveals. v2 uses **scroll-linked parallax across the full duration of the section**. Multiple z-planes each transform at different rates in response to scroll position, not to time.

Implementation: `scroll-timeline` (native CSS scroll-linked animations) where supported, with a JS `rAF` fallback that reads `IntersectionObserverEntry.intersectionRatio` (or `window.scrollY` normalized against the section's bounding rect) and applies transforms per frame. Cache the section's rect, use `will-change: transform` on the parallax planes during scroll, remove after leaving.

Plane rates for v2 (relative to native scroll = 1.0×):
- Ledger paper base: 0.15× (nearly fixed; the scene *behind*)
- Ascending risers: 0.40× (drift up slower than content)
- Main-line rank cards: 1.0× (native scroll)
- Unique branch cards: 1.0× (native scroll, but on a sticky pin — see Axis 4)
- Apex Gate arch: 0.60× (arch descends toward the viewport as user scrolls into the panel)
- Gold thread: draws along scroll progress, not on time (v1 was time-based; v2 is scroll-driven)

**Reduced-motion**: all parallax rates collapse to 1.0× (no differential motion). Everything moves at native scroll speed, no offsets applied.

### Axis 3 — Experimental typography

v1 typography read as caption-scale (`clamp(1.2rem, 1.8vw, 1.5rem)`). v2 elevates typography to the primary visual anchor.

Type scale for v2:
- **Section title "Ascension"** — EB Garamond, `clamp(6rem, 22vw, 20rem)`, tight letter-spacing (`-0.03em`), rendered as the section's opening scene occupying its own ~90vh sub-panel. Optional: split into two lines (`As | cension`) or use variable-font weight axis for a stroke-weight climb.
- **Rank names per card** — EB Garamond, `clamp(3rem, 12vw, 10rem)`, one word per card, positioned as the card's dominant element. The rank stamp (Asset C PNG) sits *behind* or *beside* the type, not above it.
- **Star Bar tags** — Departure Mono, small (`clamp(0.75rem, 0.9vw, 0.9rem)`), rendered as inline grid rails beneath the rank name.
- **Apex predicate names** — Departure Mono, `clamp(0.9rem, 1.3vw, 1.4rem)`, brass-plate tags at staircase indent.
- **Apex Gate closing line** — EB Garamond italic, `clamp(1.5rem, 3vw, 3rem)`, gold-lit at animation terminus: *"Six predicates. All required. No exceptions."*

Line-height for large display: `0.9` on the rank names and section title (tight, columnar). Body/mono retain `1.4`.

**No lorem-ipsum, no filler.** Every string on the page must be load-bearing — a rank name, a Star Bar threshold, an Apex predicate, or a caption that adds mechanical clarity.

### Axis 4 — Sticky scene composition

v1 rendered all six rank cards + Unique branch + Apex Gate as one continuous scroll (~88vh section). v2 uses **sticky scenes**: each rank card occupies its own ~80vh sub-scene, and the whole section spans ~7–9 viewport heights.

Implementation pattern per rank:

```html
<div class="ao-scene" data-rank="1">
  <div class="ao-scene__stage">
    <!-- rank stamp, huge rank name, star bar, tags -->
  </div>
</div>
```

CSS:
```css
.ao-scene {
  min-height: 100vh;
  position: relative;
}
.ao-scene__stage {
  position: sticky;
  top: 0;
  height: 100vh;
  display: grid;
  place-items: center;
}
```

The stage pins to the viewport for the scene's ~100vh scroll distance, then releases as the next scene arrives. Inside the pinned stage, sub-elements transform based on scroll progress within the scene (rank stamp fades in first, then rank name, then Star Bar; Apex Gate scene has predicates illuminate as user scrolls the last ~50vh).

Unique branch: **one dedicated pinned scene** after the 4★ Hardened main-line scene, showing all three Unique cards on a shared plate (they don't get their own individual pins — the branch is a single "you can also go this way" beat).

Apex Gate: **the section's terminal scene**, pinned for ~150vh so the six predicates illuminate one by one as user scrolls through them.

Total section length: **~9 viewport heights** (title + 6 rank scenes + Unique branch scene + Apex Gate scene = 9). Users will scroll through the section as an experience, not glance at it as a diagram.

**Mobile (<900px):** sticky scenes collapse to standard flow (`position: static`, `min-height: auto`), because sticky-scroll on mobile is jank-prone. The scenes stack vertically at natural card height, ~80vh each, with the parallax layers replaced by static positions. Total mobile section length: ~5–6 viewport heights. Motion loops for Unique cards still lazy-load; gold thread becomes a vertical spine.

### Axis 5 — Scroll-driven gold thread

v1 drew the gold thread on time (SVG `stroke-dashoffset` animation, 1400ms). v2 draws it on **scroll progress**: the thread's `stroke-dashoffset` is a function of `window.scrollY` normalized against the section's scroll range.

Path: begins at the top-left of Scene 1 (Awakened), weaves through each rank scene's Star Bar as user scrolls, arcs through the Unique branch scene (a subtle detour off the main thread), and terminates at the apex of the Apex Gate arch in the terminal scene.

Because scroll progress is bidirectional, the thread draws forward on scroll-down and undraws on scroll-up — this creates the sensation of *composing the ascent as you scroll*. Reduced-motion: thread rendered fully drawn as static SVG, no scroll-linked update.

### Axis 6 — Cinematic transitions between scenes

Between adjacent scenes, a **cross-fade + parallax pass** on scroll. As Scene N exits the pin (user scrolls past its ~100vh), the stage's opacity fades from 1 → 0 over the last ~15vh, and the incoming Scene N+1's stage fades from 0 → 1 over the same distance. Simultaneously, the ledger and risers continue their parallax drift, so the *scene changes but the atmospheric context continues*.

CSS `animation-timeline: view()` if we can budget for it, else `IntersectionObserver` with `threshold: [0, 0.15, 0.85, 1.0]` on each scene stage and JS-driven opacity.

---

## Plane inventory for v2 (updated from v1's five planes)

Same taxonomy as v1, re-executed:

- **Plane −2** — Ledger paper: full-viewport bleed, `min-height: 100%` of section, `background-size: cover`, parallax 0.15×. Opacity as v1 (~0.28). Ledger has warm sepia tone which will bleed to page edges without gutters.
- **Plane −1** — Ascending risers: six SVG paths per rank, drawn as continuous horizontal lines spanning full viewport width at each rank's y-anchor. Colour per `--rank-N`. Parallax 0.40×. Scroll-driven `stroke-dashoffset` (not IO one-shot) — the risers draw across viewport as user scrolls each scene.
- **Plane 0** — Main-line rank scenes: **six sticky-scene stages**, one per rank, each `min-height: 100vh`, stamp + huge rank name + Star Bar composed at viewport scale. Card 6 (Apex) does NOT use Asset A here — the Apex Gate gets its own terminal scene (Plane +1). Card 6 in the main-line uses a placeholder rank stamp (Asset C's Transcendent visual might be reused as an inversion; verify with the transparent resend) OR is empty in the main line and reads as *"you're now in the Apex scene"*.
- **Plane 0b** — Unique branch scene: **one dedicated sticky scene** between the 4★ main-line scene and the 5★ main-line scene. All three Unique cards on a shared plate. Motion loops (Asset E MP4s) autoplay on entry with the same `preload="none"` + IO trigger discipline from v1.
- **Plane +1** — Apex Gate terminal scene: **sticky-pinned for ~150vh**. Asset A arch centered, six predicates illuminating one-by-one as scroll progresses through the pin. Closing line reveals at scroll terminus.
- **Plane +2** — Gold thread: single SVG path spanning all scenes, `stroke-dashoffset` scroll-linked. Drawn behind cards, above ledger.

---

## Copy voice (unchanged from v1 + terminology corrections)

Half-Merged voice. No SaaS metrics, no em-dashes in prose, no glassmorphism, no filler.

Section-level copy candidates:

- **Section title**: `Ascension`
- **Sub-caption (subtitle beneath title)**: `Rank is earned. Apex is rare.`
- **Main-line rank captions** (one per scene, brief; italic muted): see v1 shape brief for candidates
- **Unique branch header**: `The Unique branch — for skills that ascend without fusing.`
- **Unique card captions**:
  - 4★ Unique: *"A parallel prestige class. Not a rank step."*
  - 5★ Unique Ultimate: *"A Unique that reaches Ultimate. Depth without fusion."*
  - 6★ Unique Impossible: *"Apex without the suite fusion. Literally impossible under the standard rule."*
- **Apex Gate scene**:
  - Opening (fades in as scene enters pin): *"The Apex Gate."*
  - Six predicates illuminate as scroll progresses through the pin
  - Closing (revealed at scroll terminus): *"Six predicates. All required. No exceptions."*

---

## Asset needs for v2 (delta from v1)

v1 assets are ALL still in play. The following are additional or replacement needs:

**Priority 1 — Bleed-friendly hero plates (new commission)**
- **Asset F (six rank hero plates)**: one plate per rank, 2560×1440, WebP + PNG, ≤200KB WebP each. Each plate is a bleed-friendly composition with the rank stamp centered on a solid or subtly-textured background *in that rank's colour family*. Purpose: fill the ~100vh sticky-scene backdrop when card content is stripped of its picture frame. Background must be *easy to remove* (single-colour ground) so we can composite it against the ledger. Composition: rank stamp at 60% of frame height, centered, with generous negative space at all edges for typography to overlap.

**Priority 2 — Larger apex arch plate (replacement or supplement to Asset A)**
- **Asset A-v2 (bleed apex arch)**: 3840×2160, WebP + PNG, ≤400KB WebP. Same subject as Asset A (columns → arch → gate → stele) but composed for full-viewport bleed with the arch positioned in the upper third and generous negative space in the lower two-thirds where the predicate staircase will render. Solid or ultra-simple ground (removable). Vendor's Asset A composition was tight; v2 wants room to breathe.

**Priority 3 — Motion loops (already commissioned as Asset E, needs recompression)**
- unique-5-loop.mp4 to <500KB (currently 19MB)
- All three loops need WebM siblings at ≤500KB each

**Priority 4 — Optional but valuable: parallax layer masks**
- **Asset G (parallax fog / haze layer)**: 2000×1200 semitransparent PNG (alpha required) with faint atmospheric wisps in warm sepia. Purpose: sits between ledger and risers at parallax 0.25× to add depth on the bleed direction. ≤120KB.

---

## Tier ordering layout (post-ratification 2026-07-06)

Operator's design directive: the Unique-vs-normal ordering must be **legible on the page**, not implicit. Three treatments compose it:

### Treatment 1 — Per-Unique-card ordering pill

Each of the three Unique cards carries a compact ordering pill immediately below its title:

- 4★ Unique: `Unique tier · above 4★ Hardened`
- 5★ Unique Ultimate: `Unique tier · above 5★ Ultimate`
- 6★ Unique Apex: `Unique tier · above 6★ Apex`

Rendered as Departure Mono at `clamp(0.75rem, 0.9vw, 0.9rem)`, `--muted` colour, letter-spacing `0.02em`. Understated but explicit. The pill is a semantic statement, not decoration.

### Treatment 2 — Unique branch scene header line

The Unique branch scene opens with a one-line explanation before the three cards render:

> *The Unique tier sits one prestige level above the same-rank normal.*

EB Garamond italic, `clamp(1.25rem, 2vw, 1.75rem)`, `--muted` colour with slight warm tint. Fades in on scene entry (scroll-linked opacity 0→1 across first 20vh of the scene pin).

### Treatment 3 — The Order coda (new closing beat)

A final compact scene between the Apex Gate closing line and the section's end — a **9-rung prestige ladder** rendered as display typography, top-to-bottom in descending prestige order:

```
           Unique Apex (Impossible)
                    Apex
               Unique Ultimate
                   Ultimate
                    Unique
                  Hardened
                   Evolved
                    Named
                  Awakened
```

Rendering spec:
- EB Garamond, weight climbs top to bottom (lighter at bottom, heavier at top)
- Size: `clamp(1.5rem, 4vw, 3.5rem)` — display type but smaller than rank-scene names
- Line-height: 1.1 (readable stack, not crushed)
- Alignment: center on desktop; left-align on mobile
- Colour: top three rungs (Unique Apex, Apex, Unique Ultimate) in `--apex-gold` at descending opacity (1.0, 0.85, 0.7); remaining rungs interpolate from `--rank-N` colour toward `--muted`
- Interpolation: each rung fades in as scroll passes its scene-local threshold — the ladder assembles top-to-bottom as user scrolls through the coda pin
- Header line above the ladder: `The Order.` (EB Garamond, `clamp(2rem, 5vw, 4rem)`, `--apex-gold`)
- Optional footer line: `Unique sits one tier above the same-rank normal.` (mono small, muted, one line below the ladder)

Coda pin: `min-height: 100vh`; the ladder fully assembles by 50vh of scroll and then the scene releases. Total section length climbs from ~900vh to ~1000vh with this addition.

Reduced-motion: ladder rendered fully-composed on scene entry.

### Placement in the section

Revised sub-scene order for v2 with the new coda:

1. Title (`Ascension`)
2. Rank 1 Awakened
3. Rank 2 Named
4. Rank 3 Evolved
5. Rank 4 Hardened
6. Unique branch (three cards with per-card ordering pills)
7. Rank 5 **Ultimate** (renamed from Transcendent)
8. Rank 6 Apex + Apex Gate (consolidated terminal, 200vh pin)
9. **The Order** coda (new, 100vh pin)

Section total: ~1000vh.

---

## Vendor briefing note (for resend):
- Backgrounds must be a single flat colour (removable via CSS or alpha-key). No detailed background scenes (v1's assets had varied backgrounds which don't composite cleanly over ledger).
- All new assets 2560×1440 minimum (v1's 1254×1254 stamps read small at viewport scale).
- Alpha channel required on all resends of v1 primaries (A, C stamps, D stamps).
- Keep half-Merged voice: 19th-century natural-history-atlas anchor, not fantasy-game / sci-fi / SaaS.

---

## Motion budget for v2

Total section scroll length: ~9 viewport heights (`900vh` when unpinned).

Sticky pins per scene: ~100vh each (except Apex Gate at ~150vh).

Scroll-linked animations (all bidirectional, no time-based decay):
- Ledger parallax: continuous, 0.15× rate
- Risers parallax: continuous, 0.40× rate
- Rank stamp fade-in per scene: linear on first 30vh of scene pin (`intersectionRatio: 0 → 0.3`)
- Rank name reveal per scene: linear on next 20vh (`intersectionRatio: 0.3 → 0.5`)
- Star Bar tags illuminate per scene: linear on next 30vh (`intersectionRatio: 0.5 → 0.8`)
- Apex predicates: illuminate one at a time, each on ~25vh of the Apex Gate pin (150vh / 6 = 25vh per predicate)
- Gold thread: `stroke-dashoffset` linear on section-total scroll progress
- Apex Gate closing line: fades in on last 20vh of Apex Gate pin

IntersectionObserver on each scene stage (thresholds `[0, 0.1, 0.5, 0.9, 1]`) drives per-scene state class toggles (`is-entering`, `is-active`, `is-exiting`).

`requestAnimationFrame` used ONLY for scroll-linked transforms (parallax rates, gold thread offset). All other animations are CSS transitions triggered by state class toggles from IO.

**No sessionStorage guard**. Scroll-linked motion is meant to be experienced every visit — the user drives the animation with their scroll, not the page's timer. This is the shift from *presentation* (v1) to *scene* (v2).

Reduced-motion (`prefers-reduced-motion: reduce`):
- All parallax rates collapse to 1.0× (no differential motion)
- Sticky pins remain, but sub-scene animations pin to their fully-composed end state on scene entry
- Gold thread rendered fully drawn as static SVG
- No cross-fade between scenes; scenes appear at 1.0 opacity

---

## Failure tests for v2 (v1 tests all inherit; adding four)

v1's 8 failure tests still apply. v2 adds:

9. **Does the section bleed to the viewport edges on desktop?** If the ledger stops short of `100vw` or the rank scenes have visible page-gutter margin, that's v1 conservatism leaking through. Must bleed edge-to-edge.
10. **Is the parallax scroll-driven, not time-based?** If the user pauses scroll and the risers keep moving, that's animation on a timer. Must be locked to scroll position (or `scroll-timeline` where supported).
11. **Do the sticky scenes actually pin?** Pinned scenes are the sensation-making move of v2. If scrolling through the section just cross-fades cards without sticky pinning, we've built v1 with bigger type — not v2.
12. **Does the typography read as "viewport-scale" or as "big caption"?** Rank names at `clamp(3rem, 12vw, 10rem)` should feel like display posters at the rank's threshold, not like enlarged captions. If they read as captions, scale is too conservative — push to `clamp(4rem, 15vw, 12rem)`.

---

## What v2 explicitly does NOT do

- No em-dashes in prose (commas, semicolons, full stops; en-dashes for ranges only)
- No glassmorphism (backdrop blur + translucent cards)
- No SaaS metrics language
- No `mix-blend-mode` background keying (still — accept opaque assets until transparent resend arrives)
- No time-based motion for scroll-linked planes (parallax and gold thread must be scroll-driven)
- No sessionStorage one-shot guard on scroll-linked motion (that was v1's IO discipline; v2 wants the scene to *breathe* on every visit)
- No CTA at the bottom of the Apex Gate scene (the section teaches; the earlier hero converts)
- No introduction of new CSS tokens (use existing `--rank-N`, `--tier-*`, `--apex-gold`, `--evidence-gold`, `--tier-unique`, `--font-display`, `--font-body`, `--font-mono`, `--bg`, `--text`, `--muted`, `--border`)
- No touching of `docs/js/site-nav.js`, `docs/js/site-footer.js`, or `packages/api-client-ts/node_modules/`

---

## Deliverable checklist for v2 worker

- [ ] Read v1 shape brief in full (`design-v6.1.1-ascension-overdrive-shape.md`, 309 lines) — understand the mechanic content that v2 inherits unchanged
- [ ] Read this v2 brief in full — understand what execution changes
- [ ] Read `META.md` §1.1 and §2.4 for content invariance
- [ ] Read `founder/handovers/G7_TRUST_TAXONOMY_RFC.md` §11.12 for the six Apex predicates verbatim
- [ ] Read `docs/index.html` current state (post-v1 has PR #988 draft; v2 branches from main and starts fresh)
- [ ] Read `docs/css/styles.css` for available tokens
- [ ] Read `CLAUDE.md` (deferred-surface WIP banner convention, half-Merged voice, nav clearance)
- [ ] Branch off `main` as `design/v6.1.1-ascension-overdrive-v2` (do NOT branch off v1's branch)
- [ ] Copy assets from `docs/assets/ascension-overdrive/` (already committed on main via PR #988's parent commit; sanity check first)
- [ ] Implement six-scene sticky-pinned composition with real parallax
- [ ] Implement scroll-linked gold thread
- [ ] Implement viewport-scale typography per Axis 3
- [ ] Preserve `#ascension` anchor, mounts, nav highlight, footer refs
- [ ] Preserve entrypoints into/out of the section
- [ ] Ship as **draft PR** titled `design(ascension): overdrive v2 bold direction (#975)` — do NOT merge; operator preview
- [ ] Note in PR body: v1 (PR #988) is the reference; v2 is the sibling for operator comparison; formal ratification of Unique terminology tracked in META.md follow-up
- [ ] All 12 failure tests (v1's 8 + v2's 4) self-checked green before draft opens

---

## Where v2 lives

- **Shape brief (this doc)**: `founder/handovers/design-v6.1.1-ascension-overdrive-shape-v2.md`
- **v1 shape brief (reference)**: `founder/handovers/design-v6.1.1-ascension-overdrive-shape.md`
- **Commission brief (updated)**: `founder/handovers/design-v6.1.1-ascension-overdrive-commissions.md` (asset F, A-v2, G added)
- **v1 preview PR**: #988 (draft, on `design/v6.1.1-ascension-overdrive`)
- **v2 branch**: `design/v6.1.1-ascension-overdrive-v2` (off main, not off v1)
- **v2 preview PR**: to open on completion

When v2 preview lands, the operator picks a direction and the losing branch is archived (kept for reference but not merged).
