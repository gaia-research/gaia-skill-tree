# design-v6.1.1 — Ascension Cycle Overdrive Shape v3 (Y-Fork Edition)

> Sibling to `design-v6.1.1-ascension-overdrive-shape-v2.md`. v3 is the ratified evolution of v2: the section is rebuilt around Yggdrasil II's Type + Branch axis split so the Y-fork between the Suite branch and the Unique branch becomes the section's structuring narrative, not a tier-ordering afterthought. The Suite branch reads as ceremonial (warm cream ledger, brass tags, ordered architecture). The Unique branch reads as rule-breaking (dark, void, edgy, corrupted-tree sub-narrative). This is the only surface on the site where the design goes edgy, by design: Uniques are the exception, Suites are the norm, and the section teaches that dichotomy at viewport scale. All Yggdrasil II vocabulary is absorbed inline; "Hardened" is retired, "Ultimate" becomes a rank word, "Unique Impossible" becomes the 6★ Unique canonical name.

## The Meta Shift context

Ascension Overdrive v3 is the frontend expression of Yggdrasil II (EPIC #1002) and specifically the scope of sub-issue #998 (Frontend). Yggdrasil II collapses the starless `type` enum to `{basic, fusion}` and introduces a derived branch axis on named skills with values `{standard, unique, suite}`. The Ascension section is the site's only viewport-scale explainer of the rank ladder, so the branch split has to land here first or nowhere; every other surface (skill-explorer, badges, codex) inherits the vocabulary this section anchors. See `founder/handovers/YGGDRASIL_II_RATIFICATION_2026-07-07.md` for the full ratification. v3 ships on a new branch `design/yggdrasil-ii-aov-v3` off `dev/yggdrasil-ii-staging` and merges back into staging per the staging-branch protocol. PR #989 (v2 preview) is closed as absorbed — v2 milestone locked at staging fork; v3 begins clean.

---

## Failure tests (v3 must pass all 15, front-loaded)

The commissioner brief and the coding agent both key on this list. Nothing else in this doc overrides these; if any test fails at preview time, the shape brief is wrong or the execution is wrong, and one of the two is fixed before the section re-opens for review.

1. A first-time reader who scrolls the section top-to-bottom can, without any other page context, state in one sentence what a Suite is and what a Unique is, and why they are different branches rather than different ranks.
2. The word "Hardened" does not appear anywhere in the section. The 4★ Suite rank is named **Extra**, and the word "Hardened" as a rank label is retired site-wide by the Yggdrasil II implementation PRs.
3. The word "Ultimate" appears exactly as a rank word (Suite 5★ = **Ultimate**, Unique 5★ = **Unique Ultimate**). Neither instance reads as a taxonomy category. The gacha-anchor collision is intentional and legible in the copy.
4. The 6★ Unique tile carries the canonical rank name **Unique Impossible** with the `◇ Provisional` glyph. The legacy label "Unique Apex" does not appear on the surface.
5. No rank tag row on any scene contains "Grade C+", "Grade B+", or "Grade S" as a rank-floor claim. The Evidence Floor is removed per Yggdrasil II; tags describe evidence and gates, not thresholds pinned to ranks.
6. Act II fork lede reads "Basic or Fusion" (never "Basic or Extra"). The word Extra is reserved for the 4★ Suite rank label only.
7. The dichotomy is visually unmissable at a glance: pause on Act III's 5★ scene, cover the type, and the two rails still read as opposite design languages (palette hue, texture, geometry, motion). A screenshot without any text should still communicate the split.
8. The gold thread bifurcates at Act II. One SVG path enters Act II, two paths exit (the Suite lane and the Unique lane), and both draw independently as the reader scrolls through Act III. Reduced-motion renders both branches fully drawn on load.
9. Act III uses a dual-lane sticky layout with left rail (Suite, ceremonial) and right rail (Unique, void) held in view together for each of the three paired scenes. On mobile the two rails collapse to a stacked pair (Suite above, Unique below) per scene, with the Y-fork degrading to a vertical binary tree at the top of Act III.
10. The mobile-first parallax discipline from v2 is preserved. Sticky pins collapse on <900px; parallax rates hold at 1.0×; the two rails stack; no jank on iOS scroll rubberbanding.
11. The section still owns its horizontal viewport (`margin-inline: calc(50% - 50vw)`, `max-width: 100vw`) and the `#ascension` id + `scroll-margin-top: 5rem` are unchanged. Nav clearance from `CLAUDE.md §Fixed-nav clearance` is preserved.
12. No `sessionStorage` one-shot guard is added. Scroll-linked motion is designed to be re-experienced every visit; v2's discipline holds.
13. The Suite left rail carries new-generation rank stamps (freshly commissioned; not Asset C v2 recolored). Visually the left rail reads as the ordered mirror of the Unique right rail's void register. This is a commissions concern; the shape only requires the left rail to be a peer surface, not a duplicate of the Unique treatment.
14. Asset I (Unique Impossible terminal art, impossible-object register) anchors the 6★ Unique scene in Act III. It sits on the right rail, not on a separate bleed, and the paired left tile (6★ Apex, Suite branch) reads as its ceremonial counterpart across the same viewport.
15. The Act II fork paragraph links to `docs/codex/trust-methodology.html#branches` on the phrase "Suite or Unique branch". A reader who wants the full derivation walks from the section to the codex in one click.

Any subsequent design pass that adds a tile, changes a rank name, or moves a scene renumbers these tests; they do not shrink.

---

## Three-act structure

v2 was one long ladder over ~1000vh. v3 rebuilds the ladder as three acts because the story now has three beats: a trunk that every named skill walks (Act I), a decision point that only some skills reach (Act II), and a divergence that only 4★+ skills experience (Act III). Each act carries its own vocabulary, its own atmospheric palette, and its own motion mode. The gold thread stitches all three together and bifurcates at the Act II→III boundary.

### Scene table

| # | Act | Scene | Rank(s) | Pin duration | Purpose |
|---|-----|-------|---------|--------------|---------|
| 1 | I | Opening | none | ~100vh | Section title, subtitle, first Y-fork motif in the background (faint, foreshadowing) |
| 2 | I TRUNK | 1★ Awakened | 1 | ~100vh | Standard branch entry. Single column. Ceremonial register in warm cream. |
| 3 | I TRUNK | 2★ Named | 2 | ~100vh | Standard branch middle. Single column. Continues cream register. |
| 4 | I TRUNK | 3★ Evolved | 3 | ~100vh | Standard branch top. Single column. Trunk terminates here. |
| 5 | II FORK | Fork teaching scene | n/a | ~150vh | Sticky-pinned. Single tall column. The gold thread visibly splits into two. The reader learns the branch axis: at 4★, the tree forks, and every subsequent scene renders the split as two rails held together. |
| 6 | III DIVERGENCE | 4★ paired | Suite: **Extra** / Unique: **Unique** | ~120vh | Dual-lane sticky. Left rail (Suite, ceremonial). Right rail (Unique, void). |
| 7 | III DIVERGENCE | 5★ paired | Suite: **Ultimate** / Unique: **Unique Ultimate** | ~120vh | Dual-lane sticky. Both rails carry a caption that teaches the Q7 gacha-anchor: Ultimate is the 5★ rank name universally. |
| 8 | III DIVERGENCE | 6★ paired terminal | Suite: **Apex** / Unique: **Unique Impossible** (◇ Provisional) | ~250vh | Dual-lane sticky, long pin. Left rail illuminates the six Suite Apex Gate predicates. Right rail illuminates the five provisional Unique Impossible Gate predicates. Asset I anchors the right rail; the Suite Apex arch anchors the left rail. |

Total viewport-heights budget: **~1140vh unpinned**. Longer than v2 (~1000vh) because the paired 6★ scene carries two gate machines and the fork scene is a full teaching pause. Mobile collapse target: ~800–900vh (paired rails stack per scene, gate pin shortens to ~150vh).

### What's removed vs v2

- The "Unique branch as a middle scene between R4 and R5" beat is gone. Uniques do not sit above Suites in a linear ordering; they are a parallel branch. The 9-rung "Order" coda from v2 is also gone; it encoded the wrong mental model (single ladder with Unique tier one step above the normal at each rank) and Yggdrasil II retires that framing entirely.
- "Ascension without Fusion" as a tagline is retired. Post-Y-II, both branches carry `type=fusion` under the hood; the differentiator is `suiteComponents` presence on the generic parent, not the fusion property of the named skill. The Unique branch tagline is rewritten in the Copy blocks section below.
- The Evidence Floor tags on rank scenes ("Grade C+ evidence", "Grade B+ rank-floor") are removed from every scene. Trust Magnitude is the sole gate; rank scenes describe the state a skill is in, not the numeric floor.

---

## Dichotomy spec (design brief for the commissioner)

The two rails in Act III are the design payload of the whole redesign. If they read as siblings, v3 has failed. They must read as opposites held in the same viewport. This table is the brief.

| Axis | Suite rail (left, ceremonial) | Unique rail (right, void) |
|------|-------------------------------|---------------------------|
| Palette hue | Warm cream, aged parchment, brass, deep ink brown. Existing `--rank-N` warm family. Atmospheric anchor: `--evidence-gold` / `--apex-gold`. | Near-black, void purple, dead violet, ash gray. Existing `--tier-unique` extended. Atmospheric anchor: `--tier-unique` at low luminance. |
| Substrate | Astrolabe engraving (Asset B direction B.v3-b, ratified): faint constellation and star-chart engraving replacing v2's parchment ledger. Structured, orderly, celestial in the ordered-mechanism sense. | Dark void plate. No substrate texture; alpha voids and hairline crackle only. The absence of a ground is the ground. |
| Texture | Layered paper grain, brass rivet lines, engraved rules, letterpress emboss. Every element sits ON something. | Hairline cracks, alpha voids, negative space, subtle interference patterns. Elements float in nothing. |
| Motion mode | Slow ceremonial drift. Parallax rates 0.15 / 0.25 / 0.40 as in v2. Everything settles into place with a soft latching cadence. | Broken, jittered, uncanny. Micro-glitch on state changes (never on rest state, per reduced-motion). Motion feels like something is wrong in the frame in a controlled way. |
| Typography weight | EB Garamond regular and italic. Serif. Full stops. Star Bar tags in Departure Mono at brass-plate scale. | EB Garamond italic and light. Same family, thinner axis, more air. Tags in Departure Mono at void register with wider tracking (~0.06em). |
| Geometry | Arches, columns, pediments, ordered rectangles, staircase indents. Right angles hold. | Broken arches, inverted forms, Penrose / Escher references (Asset I terrain), non-Euclidean hints. Right angles do not hold. |
| Micro-copy voice | "The rank is earned. The seal is set." Declarative, ceremonial, past-perfect. | "The path bends. The rule does not apply." Declarative, edged, present. Same half-Merged voice, different register. |

The commissions doc names specific asset compositions. This shape does not. What the shape requires is the split reading: two languages, one section.

---

## Motion spec

### Parallax layers per act

**Act I TRUNK** carries a single column, so the parallax stack is v2's stack minus the Unique branch layers.

| Layer | Rate | Duration | Notes |
|-------|------|----------|-------|
| Astrolabe substrate (Asset B v3-b) | 0.15× | Full Act I + Act II | Replaces v2's ledger. Faint, ambient, always present. |
| Fog / haze (Asset G, v2 reused) | 0.25× | Full section | Sits between substrate and content. Warm sepia in Acts I / II; shifts hue-neutral in Act III. |
| Rank hero plate (Asset F: v2 reused for 1★–3★ trunk; Asset F v3 new commission for 4★–6★ Suite rail) | 1.0× | Per scene | Behind rank type. |
| Content column | 1.0× | Per scene | Rank name, tags, caption. |
| Gold thread | scroll progress | Full section | See § Gold thread bifurcation below. |

**Act II FORK** is a single sticky teaching scene. It carries:

| Layer | Rate | Duration | Notes |
|-------|------|----------|-------|
| Substrate | 0.15× | Continued | Fades at ~50% of Act II toward the Act III dichotomy palette. |
| Fork diagram | scroll progress | Full Act II | The literal Y-fork rendered in SVG, drawn on scroll. |
| Copy column | 1.0× | Full Act II | The teaching paragraph. |
| Gold thread | scroll progress | Full Act II | Splits mid-scene; second branch draws in during last third. |

**Act III DIVERGENCE** carries two parallel stacks per scene, one per rail.

| Layer | Rate | Rail | Notes |
|-------|------|------|-------|
| Suite substrate | 0.15× | Left | Astrolabe cream register. |
| Unique substrate | 0.15× | Right | Void black register. |
| Suite hero plate | 1.0× | Left | Asset F v3 (new) Suite rank plate 4★/5★/6★; Asset C v3 Suite stamp composited on top. |
| Unique hero plate | 1.0× | Right | Asset D v3 (new) Unique stamp for 4★/5★; Asset I for 6★ Unique Impossible terminal. |
| Unique motion loop | autoplay | Right | Asset E v3 (re-commission) MP4/WebM loops, per-scene, lazy-loaded on IO. |
| Gold thread, Suite branch | scroll progress | Left | Continues the Suite lane. |
| Gold thread, Unique branch | scroll progress | Right | Continues the Unique lane. Undraws on scroll-up (bidirectional). |
| Apex Gate predicates (6★ only) | per-predicate scroll | Left | Six locked → unlocked latches, v2 pattern. |
| Unique Impossible Gate predicates (6★ only) | per-predicate scroll | Right | Five locked → unlocked, provisional. Renders with `◇ Provisional` header glyph. |

### Gold thread bifurcation

The thread is one SVG element with two paths. Path A is the full trunk plus the Suite lane through Act III; path B branches off at the Act II fork point and traces the Unique lane through Act III. Both paths carry `stroke-dashoffset` linked to the section's normalized scroll progress, but path B's `pathLength` accounts for its shorter start (it begins drawing at Act II's midpoint, not at the section top). The bifurcation moment is visually reinforced by a subtle luminance shift on path A (staying warm gold) and path B (cooling to a pale silver-blue) as they diverge.

Reduced-motion (`prefers-reduced-motion: reduce`): both paths render fully drawn as static SVG on section entry. Parallax rates collapse to 1.0×. Sticky pins remain (they are layout, not motion). Asset E loops are replaced with the still-poster frame.

Mobile (`<900px`): sticky pins release (position:static). The two rails stack per scene, Suite above Unique. The gold thread renders as a vertical spine on desktop; on mobile it renders as **a single spine on the left with a `→ Unique` tag at each Act III scene entry**. This is ratified — do not render two parallel mobile spines; the Y-fork teaching has already happened in Act II at trunk scale, and the mobile Act III lane needs the compression.

---

## Copy blocks (verbatim strings, load-bearing)

### Section opening (Scene 1)

- Eyebrow: `The Ascension Cycle`
- Title: `Ascension`
- Subtitle: `Rank is earned. Branch is chosen.`

The subtitle is rewritten from v2's `Rank is earned. Apex is rare.` because branch selection is now the section's teaching moment, and Apex is one of two 6★ outcomes rather than the sole terminal.

### Act II fork lede (Scene 5, the teaching paragraph)

> At three stars, every named skill has walked the same trunk. Awakened, Named, Evolved. The fourth star is where the tree forks. A skill whose generic parent lists **suiteComponents** ascends the Suite branch. A skill whose generic parent is Basic or Fusion, without suiteComponents, ascends the Unique branch. The choice is not made at promotion time; it is derived from the structure the skill already has. Read the derivation in the [Suite or Unique branch](codex/trust-methodology.html#branches) reference in the Codex.

Rendering: EB Garamond italic body, `clamp(1.25rem, 2vw, 1.75rem)`, `--text` at 0.85 opacity. The `codex/trust-methodology.html#branches` link is inline, colored `--evidence-gold`, no underline until hover. The phrase "Basic or Fusion" is the Yggdrasil II vocabulary carrier; do not shorten to "Basic" alone.

### Act III 5★ paired caption (Scene 7)

Both rails carry captions that teach the Q7 gacha-anchor collision explicitly.

Left rail (Suite 5★):
- Rank name: `Ultimate`
- Caption: *"The Suite 5★ rank name. Ultimate is the ceiling of the standard promotion path when the branch is Suite."*

Right rail (Unique 5★):
- Rank name: `Unique Ultimate`
- Caption: *"The Unique 5★ rank name. Ultimate is the shared 5★ label across both branches; the Unique prefix marks the branch."*

Below both, a shared caption spans the two rails at the bottom of the scene:

> *Ultimate is a rank, not a class. Every 5★ skill is Ultimate; the branch prefix tells you which lane it rose through.*

Rendering: shared caption is EB Garamond italic, `clamp(1.1rem, 1.8vw, 1.5rem)`, centered across the two rails, `--muted`.

### Act III 6★ paired caption (Scene 8)

Left rail (Suite 6★):
- Rank name: `Apex`
- Caption: *"The Suite terminal. Six predicates, all required. The Suite Apex Gate is unchanged from Yggdrasil I."*

Right rail (Unique 6★):
- Rank name: `Unique Impossible` `◇ Provisional`
- Caption: *"The Unique terminal. Five predicates, provisional. The Unique Impossible Gate is the Suite Apex Gate minus the directNestedSuiteGte1 predicate. Formal ratification pending."*

The `◇ Provisional` glyph renders inline with the rank name, Departure Mono, `clamp(0.75rem, 0.9vw, 0.9rem)`, `--muted`. It is a semantic tag, not decoration; it tells the reader the gate itself is not yet ratified. On hover / tap, a tooltip renders the deferred-surface WIP language per `CLAUDE.md §Deferred-surface convention` and links to the Yggdrasil III tracking issue when it exists.

Below both, a shared coda spans the two rails at the bottom of the scene:

> *Two terminals. Two gates. Both are Apex-grade trust, earned through opposite structural paths.*

---

## What v3 does NOT change (preserved from v2)

- The section id remains `#ascension`. Nav highlights, footer refs, and deep links continue to work.
- `scroll-margin-top: 5rem` is unchanged. Fixed-nav clearance per `CLAUDE.md §Fixed-nav clearance` is preserved.
- The section owns its horizontal viewport via `margin-inline: calc(50% - 50vw)` and `max-width: 100vw`. The `.home-page #ascension.aov` bleed override in `docs/css/ascension-overdrive-v2.css` is preserved.
- Mobile-first parallax discipline: rAF loop reads `window.scrollY` normalized against the section's bounding rect; `will-change: transform` set during scroll and removed after leaving. iOS rubberbanding tested at commit time. The v2 JS pattern in `docs/js/ascension-overdrive-v2.js` is the base; v3 extends it for the two-lane thread and paired scenes but does not rewrite it.
- No `sessionStorage` one-shot guard. Scroll-linked motion is meant to be re-experienced every visit.
- Token discipline: no new CSS tokens introduced. v3 reuses `--rank-N`, `--tier-unique`, `--tier-*`, `--apex-gold`, `--evidence-gold`, `--font-display`, `--font-body`, `--font-mono`, `--bg`, `--surface`, `--border`, `--text`, `--muted`. Any darkening on the Unique rail resolves against these; no hex fallbacks.
- No em dashes in prose. Commas, colons, semicolons.
- No glassmorphism, no SaaS metrics, no `mix-blend-mode` PNG keying.
- No CTA at the bottom of the terminal scene. The section teaches; the earlier hero converts.
- No touching `docs/js/site-nav.js`, `docs/js/site-footer.js`, or any node_modules directories.
- Every rank name and tier name on the page traces back to `META.md` (as amended by the Yggdrasil II Docs PR) or to this shape brief.

---

## Deferred and commissions boundaries

This shape brief does not specify asset compositions. That is the commissions doc's scope; the sibling `design-v6.1.1-ascension-overdrive-commissions-v3.md` carries it. Where this brief names an asset, it names the role, not the illustration. Specifically:

- **Asset B v3-b (astrolabe substrate)**: ratified direction per operator, replaces v2's parchment. Full replacement, not overlay. Composition is the commissions doc's scope.
- **Asset C v3 — Suite rank stamps, full 1★–6★ set**: NEW commission covering the entire Suite ladder. Operator ratified full replacement of the v2 Asset C stamps because they were unused elsewhere on the site and because Asset C v3 doubles as the foundation for skill plaques (used later across the site outside Ascension). Naming preserves "Asset C" — v3 is the successor, not a sibling. Composition is the commissions doc's scope.
- **Asset D v3 — Unique rank stamps (4★ / 5★ / 6★)**: NEW commission. Void, broken, impossible-object register. Composition is the commissions doc's scope.
- **Asset E v3 (Unique motion loops)**: RE-COMMISSION with unlimited budget per operator. Better animations, longer loops, more variety.
- **Asset F reinstated**: NEW commission for 4★–6★ Suite rank hero backdrops. Reintroduced on operator ratification (was flagged deprecated in an earlier commissions draft). 1★–3★ Trunk plates: reused from v2 unchanged.
- **Asset G (parallax haze, v2)**: reused as color-graded variants for the two rails. A fresh Asset G commission stays ready as fallback if the color-grade approach fails legibility tests.
- **Asset I (Unique Impossible terminal art)**: NEW, iterated from the beloved v2 sketch. Impossible-object / Penrose / Escher register. Anchors the 6★ Unique tile in Scene 8.
- **Asset H — Y-Fork gold-thread illustration**: NEW commission, critical set-piece for Act II FORK. SVG-primary with named separable paths for scroll-driven `stroke-dashoffset` animation.

Operator has ratified unlimited asset budget; the commissions doc allocates.

---

## Refs

- **Ratification**: `founder/handovers/YGGDRASIL_II_RATIFICATION_2026-07-07.md`
- **v2 shape (inheritance base)**: `founder/handovers/design-v6.1.1-ascension-overdrive-shape-v2.md`
- **v2 commissions (v3 supersedes)**: `founder/handovers/design-v6.1.1-ascension-overdrive-commissions-v2.md`
- **v3 commissions (sibling agent, forthcoming)**: `founder/handovers/design-v6.1.1-ascension-overdrive-commissions-v3.md`
- **EPIC**: Yggdrasil II EPIC #1002
- **Sub-issue**: #998 Frontend (this shape's implementation home)
- **Codex reference (linked from Act II lede)**: `docs/codex/trust-methodology.html#branches`
- **v1 shape brief (deep reference)**: `founder/handovers/design-v6.1.1-ascension-overdrive-shape.md`
- **Site invariants**: `CLAUDE.md §Design Entrypoints`, `CLAUDE.md §Fixed-nav clearance`, `CLAUDE.md §Deferred-surface convention`

---

## Deliverable checklist for the v3 coding agent

1. Read this shape in full.
2. Read the Yggdrasil II ratification handover in full.
3. Read the v2 shape brief in full; note what is inherited unchanged.
4. Read the v3 commissions brief when it lands; do not begin markup until asset filenames are stable.
5. Verify branch: `design/yggdrasil-ii-aov-v3` — create off `dev/yggdrasil-ii-staging`. Do NOT continue on `design/v6.1.1-ascension-overdrive-v2` (that branch is retired; its PR #989 closed as absorbed).
6. Verify base: the branch targets `dev/yggdrasil-ii-staging`, never `main`.
7. **Fork to v3 files.** Create `docs/css/ascension-overdrive-v3.css` and `docs/js/ascension-overdrive-v3.js` as fresh files. Do NOT edit the v2 files in place — the v2 files stay on disk as archival reference; the v3 file swap happens in `docs/index.html` where the `<link>` and `<script>` tags point to the new files. Cache-busting via `?v=…` per `CLAUDE.md §Adding a new versioned HTML page`.
8. Implement three acts with sticky pins per scene table above.
9. Implement dual-lane sticky layout for Act III with the dichotomy spec.
10. Implement the gold thread as a single SVG with two paths and independent scroll-linked draw.
11. Implement the fork teaching scene with the SVG Y-fork and the exact Act II lede copy above.
12. Wire the `◇ Provisional` glyph and its tooltip on the 6★ Unique tile.
13. Confirm all 15 failure tests pass at preview time.
14. Verify mobile collapse at 375px and 768px widths.
15. Confirm reduced-motion path renders the fully-drawn thread and no parallax offsets.
16. Confirm `#ascension` anchor, mounts, nav highlight, footer refs are preserved.
17. Confirm `scroll-margin-top: 5rem` clearance holds against the fixed nav.
18. Ship as a draft PR on the existing branch; the operator previews before merge into staging.
19. Do not commit any asset that is not yet in `docs/assets/ascension-overdrive/`; wait for the commissions delivery.
20. Log token spend at session close per `CLAUDE.md §Token Spend Logging`.
