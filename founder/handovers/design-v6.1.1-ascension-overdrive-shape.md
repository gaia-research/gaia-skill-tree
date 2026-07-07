# design-v6.1.1 — Ascension Cycle Overdrive Shape

> `/impeccable overdrive` — the Ascension Cycle section (`#ascension` on `docs/index.html` L743–790) becomes the homepage's educational centerpiece: a single-page visual refresher on how ranks actually work, treated with the ceremonial gravity of the mechanic itself. No CTA burden — the section teaches, the earlier hero handles conversion.

## Framing correction from Direction B

The earlier Direction B shape treated the section as decorative ceremony with an "Apex Threshold" beat. That was too thin. Research surfaced three concrete mechanics that must all be legible in the section:

1. **Rank ladder** — six stages, ascending (existing intent)
2. **Star Bar** (per `META.md §2.4`) — the threshold ladder each rank must **actually clear**. Not a progress bar. Concrete gates: evidence grade floor, installability requirement, security review, enterprise-ready, Apex 6-predicate gate.
3. **Apex Gate** — the six named predicates that hard-gate 5★ → 6★ Apex promotion. Currently only documented on `docs/codex/trust-methodology.html §5`; on the homepage the 5★→6★ transition is a bare `→` arrow, which is dishonest to the mechanic.
4. **Unique class off-ramp** — per #935 ratification: Basic/Extra skills that reach 4★ without becoming a Suite earn `◉ Unique` as a parallel prestige class. This must appear in the section or the "here's how ranks work" refresher is incomplete.

Overdrive scope is therefore the coordinated visual assertion of **four mechanics simultaneously**, on one section, without collapsing into a spec dump. The ceremonial voice (guild ledger kept with obsessive care) is the tonal glue.

---

## The scene sentence

An initiate stands at the base of a six-step atlas plate. Each step is a threshold with the specific conditions carved into its riser. A gated arch spans the top step; six brass-tag predicates dangle from the gate's crossbar. To the right of the fourth step, a side door leads to a parallel plate marked `UNIQUE · ◉`. The whole plate is lit as if by lamp-oil, catching hairline gold on the riser edges and the gate's arch.

**Category-reflex check.** Guessing "evidence-backed registry → clean rank ladder with progress bars" is the first reflex. Guessing "editorial-typographic ledger" is the second. Neither predicts the mechanic-forward, brass-tag Apex Gate treatment — that's the composition's identity move. The ceremonial gate + brass-tag predicate motif is not visible in AI landing-page training data for skill registries; it's borrowed from admissions-hall and museum-annotation visual language, adjacent to Gaia's stated 19th-century natural-history-atlas anchor but distinct from anything on the site today.

---

## The composition, plane by plane

The section renders as **one full-viewport plate** (min-height `100vh` clamped, or `88vh` on ≤900px) with the following layered composition. Layer count ceiling: five planes total (parallax discipline permits three atmospheric; we're adding two content planes that are load-bearing).

### Plane −2 · Ledger paper base (atmospheric, static)

A commissioned or hand-composed **ledger-paper texture** covering the section background at 8–12% opacity, blended `multiply` over `--bg`. Warm-cool balance: faint umber warmth, not literal parchment beige (that lands on PRODUCT.md anti-references as "warm-neutral AI default"). This is the plate the whole composition sits on.

**Asset ask:** one high-res texture, ~1600×2400px, WebP + JPEG fallback, ≤80 KB. See § Asset commission menu below.

### Plane −1 · Ascending risers (atmospheric, parallax 0.10×)

Six horizontal riser strokes, each aligned under one rank, ascending in unequal heights so the composition physically climbs left-to-right. Riser under Apex is +80–120px above the riser under Awakened.

**Hairline colour ladder:** each riser inherits its rank's own `--rank-N` token at 20% alpha as a subtle chromatic hint (Awakened blue → Named teal → Evolved violet → Hardened pink → Transcendent gold-pink → Apex gold). Adjacent risers pass through connecting hairlines in `--border`. The gradient is signal, not decoration — it reads as the palette climbing.

Parallax drift: `translate3d(0, y * 0.10, 0)` on scroll. On section entry (IntersectionObserver, `unobserve` after fire): each riser draws in via `stroke-dashoffset` animation, staggered 80ms apart, ease-out-quart 900ms. Reduced-motion: all risers pre-drawn at rest position.

### Plane 0 · The six rank stages (load-bearing content)

Each stage is a **stepped card** riding its riser, containing top-to-bottom:

- **Rank name** — EB Garamond, `clamp(1.2rem, 1.8vw, 1.5rem)`, medium weight
- **`.rank-badge` chip** — existing component, unchanged (preserves screen-reader semantics)
- **Star Bar tag** — the concrete threshold this rank must clear, expressed as a compact mono line in an inline `<code>`-styled tag. Rendered as one or two short strings per rank. Examples:

  | Rank | Star Bar tag(s) |
  |---|---|
  | 1★ Awakened | `verified as real skill` |
  | 2★ Named | `RPG title assigned` · `Grade C+ evidence` |
  | 3★ Evolved | `Grade B+` · `verified blob link` |
  | 4★ Hardened | `Grade B+ rank-floor` · `security-reviewed` |
  | 5★ Transcendent | `Grade B+ rank-floor` · `enterprise-ready` |
  | 6★ Apex | `Grade S` · `6-predicate Apex Gate` *(links to Plane +2 panel below)* |

- **Optional per-rank micro-glyph** — a hand-drawn atlas-plate stamp specific to the rank's semantic (compass rose for Named, anvil for Hardened, laurel for Transcendent). If commissioned; see asset menu. Without commission: rank-appropriate Unicode glyph in muted mono is acceptable but weaker.

### Plane 0b · The Unique parallel branch (three cards, color evolves)

At the 4★ stage on the main line, a **branch exits to the right** and runs parallel to the main ascension from 4★ through 6★. **Three Unique cards** sit on the branch, one mirroring each of the three highest main-line stages (Hardened / Transcendent / Apex). Per #935 ratification: a Basic or Extra skill that is NOT a suite earns Unique class at 4★+; the class persists as the skill advances, so the branch runs the full length of the top half of the plate.

**The Unique branch's colour language evolves rank by rank** — this is the section's most distinctive visual argument. Unique's terminal form is gravitational; the palette climbs from *structural* (violet) through *gravitational* (black hole gold) to *impossible* (white/black hole):

| Card | Star Bar tag | Colour treatment |
|---|---|---|
| **4★ Unique ◉** | `Basic or Extra` · `not a Suite` · `4★+` | `--tier-unique` violet (`#7c3aed`). Standard token palette. Card border-hairline in `--tier-unique` at 40% alpha, `--tier-unique-bg` fill at 12%. The *structural* off-ramp. |
| **5★ Unique ◉** | `Transcendent Unique` · `enterprise-ready` · `non-Suite` | **Black hole + gold.** Card fill is a deep near-black radial gradient sinking toward `#050202` at centre, ringed by a hairline `--apex-gold` accretion ring at ~85% radius. The `◉` glyph sits in the centre in `--apex-gold` at low luminance. Optional: subtle rotation loop on the accretion ring (see asset menu). Reads as *the specimen has gravity now.* |
| **6★ Unique ◉** | `Apex Unique` · `Grade S` · `never fused` | **White + black hole.** Card fill is the same deep near-black but with a small white singularity at centre, rendered as a `--text`-white radial spike (~8px) that fades outward through faint gold to void. The `◉` glyph is inverted — white on the void. This is the *impossible object*: a non-suite skill that reached Apex-grade trust without ever fusing. Optional: subtle white-core breathe loop. |

Between the three Unique cards, the branch line remains a hairline `--tier-unique` violet at 40% alpha, terminating at each card boundary — the branch stays chromatically stable while the cards themselves *transform through the gates*. That colour contrast (stable violet branch vs. evolving card treatments) is deliberate: it argues that the **class is one thing** but its *state* deepens as it advances.

Each Unique card carries a one-line caption below it in `--muted` italic:

- 4★ Unique: *"A parallel prestige class. Not a rank step."*
- 5★ Unique: *"The Unique passes through Transcendent. Depth becomes gravity."*
- 6★ Unique: *"Apex without fusion. The rarest form."*

The visitor's eye follows both tracks: main-line ascension climbing through the Apex Gate, and the parallel Unique branch climbing through its own transformation. At Apex, the two tracks are visually siblings but chromatically opposite — gold arch/gate versus white/black hole. Two ways to be rare.

**Content plane, no parallax on these cards.** They are the load-bearing story.

### Plane +1 · The Apex Gate panel (load-bearing content, the crescendo)

Between the 5★ Transcendent stage and the 6★ Apex stage, spanning ~40–50% of section width, sits **THE APEX GATE** — the compositional crescendo the whole plate ascends toward.

Structure:

- Section eyebrow: `THE APEX GATE · 6 PREDICATES` in `--font-mono`, `--apex-gold`, uppercase, 0.72rem, letter-spacing 0.12em
- Beneath: a 2×3 grid (2×3 on desktop, 1×6 on ≤700px) of **brass-tag predicates**, each rendered as:
  - Predicate ID in `--font-mono` at 0.78rem, `--tier-extra` colour (matching the existing `docs/codex/trust-methodology.html §5` styling of `.tm-predicate-list .pred-id`)
  - One-line human-readable summary in body font, `--muted`
  - A left border-hairline in `--apex-gold` at 60% alpha (echoes the `border-left: 3px solid var(--tier-extra)` on `.pred-pass` but in gold to signal "all six must pass")
- Below the grid: a subtle mono caption `All six predicates must evaluate true. Partial satisfaction is logged, not promoted.`
- The whole panel sits behind a **commissioned or hand-composed gate/arch atlas plate illustration** at 6–10% opacity, tinted `--apex-gold`. Not a stock woodcut, not clip art — a genuine plate-style rendering. This is the signature move.

The six predicates rendered:

1. `aGradedOriginsGte5` — At least 5 fusion-origin components each hold Grade A or higher.
2. `directNestedSuiteGte1` — At least 1 directly-nested suite exists among the origins.
3. `depth2OnlyReachableGte1` — At least 1 origin is reachable only at depth-2.
4. `overallGradeS` — Trust Magnitude ≥ 250 with diversity gate satisfied.
5. `sourceTenureDaysGte180AorS` — At least 1 A/S evidence row has ≥ 180 days public tenure.
6. `apexPromotionPrSigned` — Maintainer-signed promotion PR.

### Plane +2 · The gold thread + brass-tag reveal (motion crescendo)

One continuous `--apex-gold` thread at 1px weight, `stroke-linecap: round`, drawn along the ascension geometry from Awakened's baseline through each stage's riser edge, up and around the Apex Gate panel's top arch, and terminating at the 6★ Apex chip. This is the visual argument that **the ascension is one line, drawn once, terminating only at Apex through the six-predicate gate**.

On section entry (staged after Plane −1 risers complete):

1. **T=0ms** — Risers begin draw-in cascade (Plane −1, 900ms total)
2. **T=1100ms** — Gold thread begins `stroke-dashoffset` animation, 1400ms ease-out-quart, following the ascending geometry
3. **T=1600ms** — As the thread crosses the Apex Gate panel's arch, the six brass-tag predicates illuminate one-by-one, 120ms stagger, each fading its left-border from `--muted` to `--apex-gold` and its predicate ID from `--tier-extra` to `--apex-gold` briefly (240ms) then settling back to `--tier-extra` — the transient gold flash reads as *"this condition just verified true."*
4. **T=2400ms** — Thread completes its stroke at the Apex chip. The chip's existing `.is-apex` state gets a one-shot `box-shadow` pulse: `0 0 0 rgba(var(--apex-gold-rgb), 0.6)` expanding to `0 0 60px rgba(var(--apex-gold-rgb), 0)` over 600ms, ease-out-expo. The Apex is *earned* at the end of the animation, not merely displayed.

Total choreographed motion length: ~3.0 seconds. Fires once per session (IntersectionObserver → `unobserve` on first fire, stored in `sessionStorage` to prevent re-fire on same-tab navigation).

**Reduced-motion collapse:** all planes render in composed final state. Risers full-drawn. Thread full-drawn. All brass-tag predicates gold-lit. Apex chip carries the standard `.is-apex` treatment without the pulse. The composition still reads as ceremonial and earned — the motion is the delivery, the composed state is the message.

---

## Signature moves (four, each with a specific role)

1. **The ascending riser palette** — riser hairlines carry each rank's own `--rank-N` colour at 20% alpha. The palette IS the ascension; you can identify what rank a strip belongs to from the colour alone. This is unique to Gaia's rank tokenization and readable at a glance.

2. **The Unique branch's evolving colour language** — violet (structural) at 4★, black hole + gold (gravitational) at 5★, white + black hole (impossible) at 6★. The class stays the same; its *state* deepens. This is the single most distinctive visual argument in the whole section and the strongest lure to commission real illustration or subtle motion loops (see asset menu C and E). The colour peg is operator-ratified.

3. **The main-line vs. Unique-branch chromatic opposition at Apex** — at the top of the plate, the two tracks are visually siblings but chromatically opposite: the main line terminates in the gold Apex Gate arch, the Unique branch terminates in the white/black hole. Two ways to be rare, presented side-by-side. A visitor's eye must be able to read this diptych in one glance.

4. **Brass-tag predicates with the transient gold flash** — the six Apex Gate conditions read as brass identification tags on a museum specimen, each verifying with a moment of gold. Solo-Leveling guild-ceremony energy borrowed from PRODUCT.md's anchor, delivered through 19th-century-atlas language, without any anime UI.

---

## Interaction contract

The section is **display + educational**, not transactional. What visitors must still be able to do:

- Read every rank name and star count at 3s glance
- Read every Star Bar tag (contrast-verified `--text` on `--bg`, no `--muted` on primary content)
- Read every Apex Gate predicate name and description
- Locate the Unique branch as a genuinely-visible off-ramp
- Follow a keyboard tab order that visits: each rank card in order (1★→6★), then the Unique card, then each of the six predicates. All are `role="listitem"` inside a labelled `role="list"`; no interactive controls beyond focus.
- One optional link on the Apex Gate eyebrow → `docs/codex/trust-methodology.html#apex-gate` for the full spec. This is the only navigation the section carries.

No hover-pop, no click-to-expand, no accordion. The whole section is legible without interaction. Motion enhances; motion is not required for comprehension.

---

## Reduced-motion fallback (the composed static state)

`@media (prefers-reduced-motion: reduce)` collapses:

- Plane −1 risers: pre-drawn full at rest position, no draw-in cascade
- Plane +2 gold thread: fully drawn at rest along the ascension path
- Brass-tag predicates: all six left-borders in `--apex-gold` at 60% alpha, all predicate IDs in `--tier-extra`
- Apex chip: `.is-apex` standard state, no pulse
- Parallax `translate3d` layers: transform removed, layers at their rest offset

The section is fully composed, fully readable, ceremonial in tone. A visitor with `prefers-reduced-motion` never sees the motion delivery but receives the whole message. This is the passing bar per `SKILL.md` Motion rules and `animate.md` reduced-motion policy.

---

## Failure test (what would let a reviewer say "wrong")

Any of these on landing:

1. A visitor reads the section for 15 seconds and cannot answer "what makes something Apex?" That means the Apex Gate panel didn't land.
2. A visitor reads the section for 15 seconds and doesn't notice the Unique branch exists. That means the branch geometry was too subtle or the caption was buried.
3. A visitor sees the three Unique cards but cannot articulate that they are the *same class deepening* rather than three separate classes. That means the branch's chromatic stability (violet hairline connecting all three) got out-shouted by the individual card treatments; rebalance.
4. A visitor says "row of six chips" instead of "a staircase to a gate." That means the ascending geometry didn't win.
5. The section reads as decorative rather than educational. If someone asks "why is this here on the landing page?", the answer *must* be "this is how ranks actually work"; if the answer is "atmosphere," we've built decoration.
6. The gold thread reads as decoration rather than as the section's spine. Cut it if it's not the argument.
7. The 6★ Unique white/black hole reads as sci-fi decoration rather than as *the impossible object*. If it doesn't carry the argument that a non-suite skill reaching Apex is genuinely rare, the treatment is wrong.
8. Motion fires more than once per session on reload. Nauseating.

## Fixed-nav clearance & positioning

The section is not the first below the nav (hero + hall-of-heroes + trust-preview precede it), so the 5rem/8rem clearance ladder does not apply to its own container. Standard `.reveal` section boundary + `.section-divider` above and below. Section minimum height 88vh at ≥900px viewports (composed as one full plate on desktop) and `auto` below with cards stacking vertically.

---

## Cross-section discipline

**Palette (permitted).**
- Section-wide: `--bg`, `--text`, `--muted`, `--border`, `--font-display`, `--font-body`, `--font-mono`
- Riser hairlines: each `--rank-N` at 20% alpha (canonical rank colours in their canonical roles — signal, not decoration)
- Star Bar tags: `--muted` background at 8% alpha, `--text` foreground
- Main-line rank cards: standard token palette, no cascade
- Unique branch hairline (connecting the three cards): `--tier-unique` violet at 40% alpha, stable through all three cards
- Unique 4★ card: `--tier-unique` palette, standard treatment
- Unique 5★ card: **black hole + gold** — near-black radial fill sinking to `#050202` at centre, `--apex-gold` hairline accretion ring at ~85% radius; the ◉ glyph in `--apex-gold` at low luminance
- Unique 6★ card: **white + black hole** — same near-black base, small white singularity core (`--text` at full luminance, ~8px radial spike fading through faint gold to void); the ◉ glyph inverted white
- Apex Gate: `--apex-gold` for eyebrow + brass-tag left-borders + thread + pulse; `--tier-extra` for predicate IDs (matching existing methodology page); `--muted` for descriptions

**Palette (refused everywhere in this section).**
- `--honor-red` — contributor identity token, never scenery
- Gradient text — banned per `SKILL.md` Absolute bans
- Glass / backdrop-blur — no glassmorphism as decoration
- Tier tokens (`--tier-basic`, `--tier-extra`, `--tier-ultimate`) outside their semantic roles above

**Typography.**
- Display: EB Garamond medium for rank names + Apex Gate title
- Body: Bricolage Grotesque for descriptions
- Mono: Departure Mono / JetBrains Mono for predicate IDs, Star Bar tags, section eyebrows

**Motion budget.**
- One choreographed sequence per section entry, ~3.0s total, fires once per session
- Parallax on scroll: two atmospheric planes at 0.10× / 0× drift
- Reduced-motion: full composed rest state

**Content invariance.**
- Rank names come from `META.md §1.1` — do not paraphrase
- Star Bar tags come from `META.md §1.1` and `META.md §2.4` — quote verbatim
- Apex predicates come from `founder/handovers/G7_TRUST_TAXONOMY_RFC.md §11.12` (active set post-2026-06-17 delta) — quote verbatim
- Unique class rule comes from #935 comment `IC_kwDOSNHq388AAAABIxE1PQ` — quote verbatim

---

## Asset commission menu

Operator budget confirmed available. Priority ordering by ROI-per-dollar:

### Tier 1 — Signature (highest impact, commission if only one)

**Apex Gate arch illustration.** One piece, ~1200×800px, transparent PNG + SVG source. Style: 19th-century natural-history atlas plate — think Ernst Haeckel's Kunstformen or Charles Darwin's Origin plates, adapted to a metaphorical gate/arch motif. Six columns or six arches (one per predicate). Etched hairline linework, restrained cross-hatching. Tintable via `filter` for `--apex-gold` overlay. Sits behind the Apex Gate predicate grid at 6–10% opacity.

Vendor guidance: illustrator with editorial + scientific-illustration credentials; not Fiverr, not generic vector-stock. Reference: Kate Baylay, Emily Carroll, or a scientific illustrator with plate-style credentials.

**Estimated cost:** $400–1200 depending on illustrator tier. Turnaround 1–3 weeks.

### Tier 2 — Foundation (elevates the whole section)

**Ledger paper base texture.** One high-res image, ~2000×3000px, WebP primary + JPEG fallback, target ≤80KB after optimization. NOT stock parchment texture, NOT AI-generated paper — a genuine scanned ledger page from a period source (British Library digital collection, MET Open Access, National Archives) or a hand-photographed piece of aged paper with hairline rulings. Warm-neutral but low-saturation (chroma near 0.02 in OKLCH). Blended `multiply` over `--bg` at 8–12% opacity.

**Estimated cost:** $0 if sourced from public-domain scans; $50–150 for licensed stock at appropriate quality; $200–400 for a commissioned scan of a period ledger.

### Tier 3 — Elaboration (ships nicely if budget permits)

**Six rank-glyph atlas stamps.** One coherent series of six small illustrations (~200×200px each), matching the Apex arch's linework style. One per rank:
- 1★ Awakened — a candle or ember (verified as real, not yet named)
- 2★ Named — a signet stamp or seal (RPG title assigned)
- 3★ Evolved — a verified compass (blob link verified)
- 4★ Hardened — an anvil or shield (security-reviewed)
- 5★ Transcendent — a laurel (enterprise-ready)
- 6★ Apex — reserved / rendered by the Apex Gate arch itself

Sits above each rank card at ~64×64px display size, tintable to `--rank-N`.

**Estimated cost:** $600–1500 for a six-piece coherent series.

**Ratification of series style:** if commissioned, all six must ship together from the same illustrator on the same brief so they read as siblings.

### Tier 4 — Distinctive but skippable

**Unique class glyph illustration.** Custom rendering of `◉` as a full illustration — a struck coin or medallion in the same atlas-plate style. Sits above the Unique branch card at ~80×80px.

**Estimated cost:** $150–300 for one piece if the same illustrator has already delivered Tier 1 or Tier 3.

### Total budget guidance

- **Signature-only ship** (Tier 1 + Tier 2 public-domain texture): ~$400–1350
- **Elevated ship** (Tier 1 + Tier 2 + Tier 3): ~$1000–3050
- **Full ship** (all tiers): ~$1150–3350

I recommend **Tier 1 + Tier 2 (public-domain sourced)** as the minimum for the overdrive treatment to land. Tier 3 elevates the section from "excellent" to "signature," but the composition works cleanly without it. Tier 4 is polish; skip unless the Unique branch is materially deprioritized as a marketing surface.

---

## Rollout

This is `/impeccable overdrive shape` output. Follow-on is `/impeccable overdrive craft` — a dedicated implementation delegation that:

1. Rewrites the `#ascension` section in `docs/index.html` per this brief
2. Adds a scoped CSS block (either inline `<style>` per the pattern used by `.bench-shell` / `.reports-shell`, or a new `docs/css/ascension-overdrive.css` if the block exceeds ~250 lines — call from the shape approval)
3. Writes the choreographed IntersectionObserver + `stroke-dashoffset` + brass-tag reveal sequence in JS (~120 lines target; module-scoped, tree-shakeable if we later migrate)
4. Integrates commissioned assets when they arrive from the operator (skeleton composition works with placeholder assets; live assets swap in without markup changes)
5. Validates against all six failure tests before shipping

**Delegation target:** `sonnet-worker` or `opus-worker` depending on final scope after craft handoff. Motion choreography favours opus for the polish pass.

**Estimated craft effort:** 6–10 hours of focused work if assets ship in parallel. 4 hours if we defer assets and ship the atlas-plate composition with tokens-only atmospheric planes as a stepping stone.

**Ship in same PR (#972) or separate:** *recommend separate.* This is a section-scale rewrite that deserves its own review surface, its own before/after screenshots, and its own commit history. PR #972 stays scoped to entrypoint polish + WIP-banner + Trending CTA + nav clearance codification.

---

## Confirmation gate

Operator confirms four things before craft:

1. **Composition acceptance.** The one-plate, five-plane composition with Unique branch, Apex Gate panel, and choreographed gold-thread crescendo is the direction — or override with specific corrections.

2. **Content invariance.** The Star Bar tags at each rank quoted from `META.md §1.1` + `§2.4` and the six Apex predicates quoted from the G7 RFC §11.12 are correct as summarized above — or supply corrections. (Verbatim strings will be pulled at craft time; this brief captures the semantic set.)

3. **Unique class positioning.** The Unique branch off 4★ per #935 ratification comment is the correct treatment — parallel prestige class visualized as a side path, not a rank step. Confirm or override the phrasing of the branch caption *"A parallel prestige class. Not a rank step."*

4. **Asset commission scope.** Which tier to commission:
   - Tier 1 only (Apex Gate arch): ~$400–1200
   - Tier 1 + Tier 2 (arch + ledger paper): ~$400–1350 (Tier 2 free if public-domain sourced)
   - Tier 1 + Tier 2 + Tier 3 (arch + paper + six rank stamps): ~$1000–3050
   - All tiers: ~$1150–3350
   - Or: ship tokens-only first, commission assets in a follow-up polish PR

On confirmation, hand this brief to `/impeccable overdrive craft` with `docs/index.html`, `docs/css/styles.css` (or a new `ascension-overdrive.css`), and the commissioned asset paths as the working files.
