# Ascension Overdrive Commissions — v3 (Y-Fork Edition)

> Sibling to `design-v6.1.1-ascension-overdrive-commissions-v2.md`. v3 is the **Y-fork edition**: the Yggdrasil II ratification (2026-07-07) split the branch axis into two rails, and Act III of the Ascension section renders that split as a full visual dichotomy. The left rail (Suite) is ceremonial, warm, ordered, architectural. The right rail (Unique) is the only edgy zone on the entire site, intentionally so: deep void fill, white singularity, impossible geometry, broken arches, inverted colour. The design thesis of v3 is that dichotomy; the assets carry it. Asset budget is unlimited; commission for what the shape needs, not what the schedule can bear.

---

## Asset inventory

Statuses: **NEW** (v3 original), **RE-COMMISSION** (v2 asset that gets a fresh pass), **REUSED-V2** (ship v2 file unchanged). Format shorthand: `PNG+WebP` (raster with alpha), `SVG` (vector source), `MP4+WebM` (paired video codecs).

| ID | Name | Status | Format | Dimensions | Where it appears |
|---|---|---|---|---|---|
| A | Apex arch (Suite terminal) | REUSED-V2 | PNG+WebP | 3840×2160 | Act III · Scene 8 (Suite left rail, 6★ Apex terminal) |
| A-components | Individual arch components (arch, columns, stele, foliage) | REUSED-V2 | PNG+WebP | ~1500² each | Act III · Scene 8 predicate staircase (six brass-tagged rows) |
| B v3 | Astrolabe substrate (base parallax layer) | NEW | PNG+WebP | 3840×2160 | Full section, Plane −2 base texture |
| C v3 | **Suite rank stamps, full 1★–6★ set** (1★ Awakened, 2★ Named, 3★ Evolved, 4★ Extra, 5★ Ultimate, 6★ Apex) — full replacement of v2 Asset C; doubles as skill-plaque foundation for reuse elsewhere on the site | NEW | PNG+WebP | 2048² each (six stamps) | Act I Trunk (1★–3★) + Act III Suite left rail (4★–6★); also reused site-wide as skill plaques |
| D v3 | Unique rank stamps (4★ Unique, 5★ Unique Ultimate, 6★ Unique Impossible) | NEW | PNG+WebP + SVG source | 2048² | Act III · Unique right rail (three void scenes) |
| E v3 | Unique branch loops (motion) | RE-COMMISSION | MP4+WebM | 1920×1080 | Act III · Unique right rail, motion tiles per scene |
| F v3 | **Suite hero rank plates 4★–6★** (backdrops behind Suite stamps in Act III) | NEW | PNG+WebP | 2560×1440 | Act III Suite left rail, per-scene backdrop |
| F v2 | Suite hero rank plates 1★–3★ (`f-rank-1-hero` through `f-rank-3-hero`) | REUSED-V2 | WebP | 2560×1440 | Act I Trunk backdrops |
| G | Atmospheric haze (Suite-warm + Unique-cold color-graded variants) | REUSED-V2 (color-grade first, fresh illustration on standby) | PNG+WebP | 2560×1440 | Full section, Plane −1 |
| H | Y-Fork gold-thread illustration | NEW (critical) | SVG primary + PNG fallback | 3840×2160 or vector | Act II · FORK, single set-piece plate |
| I | Unique Impossible terminal | NEW (iterated from v2 sketch) | PNG+WebP + optional SVG accent | 3840×2160 | Act III · Scene 8 (Unique right rail, 6★ Unique Impossible terminal) |

Section total: 11 asset lines, 7 of which are NEW or RE-COMMISSION.

---

## Asset B v3 — Astrolabe substrate

**Purpose.** Replace the ledger-parchment base texture with a faint constellation and star-chart engraving; Yggdrasil is the world tree mapping the cosmos, and the substrate should read as celestial cartography rather than accounting ledger.

**Reference / mood.** 17th–18th century celestial atlases (Cellarius *Harmonia Macrocosmica*, Bode *Uranographia*, Hevelius plates), planispheric astrolabe engravings, azimuthal star charts. Faint hairline linework, tycho-graphic node marks, house divisions, ecliptic bands, tick-mark circumferences. The register is *engraved copper plate*, not *decorative fantasy map*. Failure modes to avoid: zodiac cartoons; anything resembling a modern space-nebula render; heraldic sunbursts; anything with visible authored text (astrolabes have engraved numerals; treat those as texture, not as legend the reader can parse).

**Dimensions / format.** 3840×2160 PNG+WebP. WebP ≤ 260KB. Full alpha not required (opaque ground preferred so the substrate anchors the parallax); the artist may deliver a transparent-line variant if the workflow is one PSD with a `Lines` layer separable, but the served asset is the composited opaque plate.

**Motion requirements.** Static base plate; the parallax layer above (haze) provides atmospheric drift. No stroke-dashoffset animation. If the artist chooses to author in vector, retain the SVG source in the deliverables archive for later 8K re-rasterisation.

**Palette hooks.** Substrate must sit legibly under both rails at Act III. Ground colour should read as warm-cool neutral, biased slightly warmer than the v2 ledger to preserve the Suite side without clashing with the Unique void when the two rails compose above it. Target OKLCH `oklch(0.22 0.015 85)` for the ground; linework at `oklch(0.55 0.03 75)` at 30–45% ink. Match `--aov-substrate-ground` and `--aov-substrate-ink` custom properties.

**Mobile constraint.** At 375px viewport width and 1× DPR, constellation nodes should not visually cluster into noise. Deliverable includes a `-mobile` variant at 1500×2000 with linework thickened 1.4× and 30% fewer node marks to preserve legibility when the plate is centre-cropped tall.

**Deliverables.**
- `aov3-astrolabe-substrate.png`
- `aov3-astrolabe-substrate.webp`
- `aov3-astrolabe-substrate-mobile.png`
- `aov3-astrolabe-substrate-mobile.webp`
- Source: PSD or AI retained in `founder/handovers/design-v6.1.1-assets/Asset B v3/`

---

## Asset C v3 — Suite rank stamps, full 1★–6★ set

**Purpose.** Give the Suite ladder a coherent visual identity from the first rank to the last. Operator ratified full replacement of v2's Asset C (v2 stamps are unused elsewhere on the site; the naming "Asset C" is preserved to keep the visual system's semantics stable). This is a **six-stamp ladder** (1★ Awakened, 2★ Named, 3★ Evolved, 4★ Extra, 5★ Ultimate, 6★ Apex) that reads as an ascending register: from botanical / natural-history plate at 1★ to ceremonial architecture at 6★. Note: 4★ Suite is formally called **Extra** per Yggdrasil II (deprecates "Hardened").

**Extended reuse mandate.** Asset C v3 doubles as the **foundation for skill plaques** used elsewhere on the site (skill-explorer plaques, badge OG cards, contributor-profile rank marks, potentially README badges). The commissioner should treat the six stamps as production visual identity for the site's rank system, not one-off illustration for a single section. Deliver each stamp with legibility at three usage scales: 2048² hero, 800² card, 240² badge / plaque. The tokens carry the same identity across surfaces; the stamp is that identity's visual anchor.

**Reference / mood.** An ascending register:
- **1★–3★ (Trunk register)** — engraved natural-history atlas plates (Hooker, Ehret, Bauer botanical drawings). Ink linework on cream ground, delicate specimen framing. Not fantasy foliage; scientific illustration.
- **4★–6★ (Ceremonial register)** — Beaux-Arts and neoclassical architectural marks: keystone medallions, embossed brass rank tags, columned niches, pediment carvings, laurel and volute ornament, incised stone stele glyphs. Order rising with rank: 4★ Extra reads as *reinforced*, 5★ Ultimate reads as *consecrated*, 6★ Apex reads as *enthroned*.

The transition from Trunk register to Ceremonial register happens at the 3★→4★ boundary and mirrors Act I→Act III in the section. Do not deliver six stamps in six wholly different aesthetics; deliver a *ladder* that ascends through the two registers with a legible transition at 4★. Failure modes to avoid: fantasy game class icons; military rank chevrons; corporate certification badges; anything with a glowing gradient rim; identical framing across all six (they need to feel like they escalate).

**Dimensions / format.** 2048×2048 PNG+WebP per stamp (six stamps total). WebP ≤ 180KB each. Alpha channel required so stamps composite over the astrolabe substrate. Retain per-stamp SVG or high-res vector source if authored digitally. Additional deliverables (per stamp): 800×800 card variant and 240×240 badge/plaque variant, hand-composed (do not just downscale — hairline linework needs re-authoring at each scale).

**Motion requirements.** Static rank marks. The stamp receives a scroll-linked opacity fade-in at scene entry via CSS transform on the wrapper; the asset itself does not animate.

**Palette hooks.** Suite rail palette — warm ordered brass. Bind to `--aov-suite-cream` (ground tint), `--aov-suite-gold` (relief highlight), `--aov-suite-ink` (incised line), `--aov-suite-brass` (metallic tag surface). Rank progression: Trunk ranks (1★–3★) bias toward `--aov-suite-cream` field with delicate `--aov-suite-ink`; Ceremonial ranks (4★–6★) escalate from brass-tag through `--aov-suite-gold` relief to `--aov-suite-brass` pediment at 6★ Apex.

**Mobile constraint.** Stamp must read as a single silhouette from 375px width. Interior filigree may soften below 400px display size; the medallion / keystone / specimen shape carries the identity at every scale. The 240² badge variant is the mobile-primary at 1× DPR (do not downscale the 2048² server-side).

**Deliverables (per rank, six ranks total).**
- `aov3-suite-stamp-1-awakened.png` / `.webp` (2048²)
- `aov3-suite-stamp-1-awakened-card.png` / `.webp` (800²)
- `aov3-suite-stamp-1-awakened-badge.png` / `.webp` (240²)
- Same triple for 2-named, 3-evolved, 4-extra, 5-ultimate, 6-apex
- Source: PSD / AI / Figma per stamp (six source files)
- Delivery folder: `founder/handovers/design-v6.1.1-assets/Asset C v3/`

**Dichotomy anchor.** C v3 is the deliberate mirror of D v3 at the 4★–6★ range. Where C v3 4★–6★ read as ordered, engraved, warm, and closed, D v3 stamps must read as broken, inverted, cold, and open. Ship the 4★–6★ Suite tier and the 4★–6★ Unique tier in one paired delivery pass so the artist holds the dichotomy in mind and calibrates contrast between the two rails.

---

## Asset D v3 — Unique rank stamps (4★ Unique, 5★ Unique Ultimate, 6★ Unique Impossible)

**Purpose.** Rank marks for the Unique right rail. These are the ONLY intentionally edgy visuals on the entire site. Read as *rule-breaking prestige*: the Suite side follows the rules and gets rewarded ceremonially; the Unique side breaks the rules and gets rewarded impossibly.

**Reference / mood.** Impossible-object geometry (Penrose triangle, Reutersvärd assemblies, Escher construction studies, tesseract projections, non-orientable surfaces). Void-fill compositional register: deep near-black or ink-void ground, single white or gold singularity mark against it, broken arches, inverted colour keys, glitched or off-register linework. Aesthetic pegs: brutalist gallery-catalogue plates, Jenny Holzer's black-ground text works for contrast palette, Vera Molnár's ordered-then-broken geometric studies. Failure modes to avoid: neon cyberpunk (edgy but wrong register); horror / occult iconography (edgy but wrong register); anything with a "corrupted glitch VHS" filter (dated, cliché); Suite motifs recoloured (the geometry itself must break, not just the palette).

**Dimensions / format.** 2048×2048 PNG+WebP per stamp (three stamps). WebP ≤ 200KB each. Alpha channel required. **SVG source strongly preferred** for D v3 so the impossible-object geometry can be authored precisely and animated (see motion requirements). If SVG is impractical for the artist's workflow, deliver a layered PSD with the primary linework on a separable vector-smart layer.

**Motion requirements.** The 5★ and 6★ stamps benefit from subtle iterative animation: an impossible edge that re-enters itself, a Penrose corner that never resolves, a singularity that pulses at low frequency. SVG stroke paths should be authored as separable segments so that later CSS can animate `stroke-dashoffset` on individual edges (the Y-fork thread trick, applied to broken geometry). The 4★ stamp is static. The 6★ Unique Impossible stamp is the terminal asset for the right rail and should have the strongest motion affordance, connecting compositionally to Asset I.

**Palette hooks.** Unique rail palette — cold void, singularity white. Bind to `--aov-unique-void` (ground fill, near-black with warm undertone to sit beside Suite cream without reading as pure #000), `--aov-unique-singularity` (single-point highlight, off-white with slight blue lift), `--aov-unique-glitch` (secondary accent for broken-edge marks, gold shifted toward magenta), `--aov-unique-fracture` (linework mid-tone). Rank progression: 4★ Unique biases toward `--aov-unique-void` ground with a single `--aov-unique-singularity` mark; 5★ Unique Ultimate introduces `--aov-unique-glitch` as broken accent; 6★ Unique Impossible reaches full impossible-object composition with `--aov-unique-fracture` linework carrying the geometry.

**Mobile constraint.** Impossible-object geometry MUST resolve as impossible at 375px width. If the reader has to zoom to see the trick, the asset failed. Design the geometry so the "wrong corner" of each stamp is visible in silhouette from mobile viewing distance. Deliver 800×800 primary-mobile variants.

**Deliverables.**
- `aov3-unique-stamp-4.png` / `.webp` / `.svg`
- `aov3-unique-stamp-5-ultimate.png` / `.webp` / `.svg`
- `aov3-unique-stamp-6-impossible.png` / `.webp` / `.svg`
- Mobile variants for all three
- Source: PSD / AI / Figma per stamp
- Delivery folder: `founder/handovers/design-v6.1.1-assets/Asset D v3/`

---

## Asset E v3 — Unique branch motion loops (RE-COMMISSION)

**Purpose.** Motion tiles that live inside the Unique right-rail scenes. v2's E loops were adequate but conservative: brief, low-variety, thin fidelity. Marcus asked for better animations with an unlimited budget: use this as a full re-commission and iterate the shape. Motion should read as *the Unique branch behaving in ways the Suite branch cannot*.

**Reference / mood.** Particle-void studies (points of light drifting through negative space), glitch loops in the Vera Molnár / Casey Reas generative register (not consumer VHS glitch), iterative regression sequences (a shape approaching a limit and never reaching it), impossible-object rotations (an object turning past its own topology), field-of-view breathing (parallax without translation). Aesthetic register consistent with D v3 stamps: cold, void, singular. Failure modes to avoid: stock After Effects presets; anything that reads as UI microinteraction; laser-cyberpunk; branded motion graphics.

**Dimensions / format.** 1920×1080 primary, MP4 (H.264 or H.265) + WebM (VP9) pair. Each loop ≤ 800KB per codec. Loop cleanly with no visible seam. Loop length 6–12 seconds per tile — longer than v2, so the loop doesn't announce itself. Deliver one loop per Unique rank scene (three total). Each loop should be visually distinct from its rank neighbours (do not deliver three colour-graded variants of one motion primitive).

**Motion requirements.** Frame rate 30fps or 24fps (do not deliver 60fps; the CPU cost on mobile is not worth the smoothness gain for these subtle loops). No audio. Poster frame extracted at first-frame parity for `poster=` attribute on the video element. Reduced-motion path: the poster frame is displayed as a static image; no loop plays. Deliver the poster frames as separate PNG+WebP files.

**Palette hooks.** Bound to Unique rail palette (`--aov-unique-void`, `--aov-unique-singularity`, `--aov-unique-glitch`). Loop should read as native to the D v3 stamp of its rank scene, not compete with it. Consider treating one loop per rank as *the D v3 stamp in motion* — but leave the artist room to compose the loop as a distinct piece if that reads stronger.

**Mobile constraint.** Loops autoplay on mobile only when the tile enters viewport under an IntersectionObserver trigger; `preload="none"` is authored on the element. Motion should read as motion at 375px width; if the loop needs a 720p viewport to read, downscale the composition. Deliver a mobile-specific 720×1280 vertical-crop variant per loop for the mobile scene layout (three additional files).

**Deliverables.**
- `aov3-unique-loop-4.mp4` / `.webm` / poster `.png`+`.webp`
- `aov3-unique-loop-5-ultimate.mp4` / `.webm` / poster
- `aov3-unique-loop-6-impossible.mp4` / `.webm` / poster
- Mobile variants: `aov3-unique-loop-4-mobile.mp4` / `.webm` (and matching for 5, 6)
- Source: After Effects / Blender / Processing / TouchDesigner project files retained
- Delivery folder: `founder/handovers/design-v6.1.1-assets/Asset E v3/`

---

## Asset F v3 — Suite hero rank plates 4★–6★ (REINSTATED)

**Purpose.** Backdrop plates for the Suite rail's 4★, 5★, and 6★ scenes in Act III. Sits behind the Asset C v3 rank stamp on each Suite scene; the stamp is the identity mark, the F v3 plate is the scene's atmospheric ground within the astrolabe substrate. Operator ratified reinstating F v3 (was flagged deprecated in an earlier draft): the ceremonial Suite rail needs a per-rank atmospheric backdrop escalation to sell the "ascending register" from 4★ Extra → 5★ Ultimate → 6★ Apex; the astrolabe substrate is a constant, and the haze is atmospheric filler, so F v3 carries the rank-specific ceremonial escalation.

**Reference / mood.** Neoclassical architectural interior plates rendered as backdrops: a niche at 4★ Extra (reinforced enclosure), a vaulted chamber at 5★ Ultimate (consecrated interior), a Grand Order interior with the Apex arch centered at 6★ Apex (enthroned terminus). Each plate is a *ground for the stamp*, not a competing subject; treat the plate as scenography, not illustration. Aesthetic register consistent with C v3 4★–6★ ceremonial marks. Failure modes to avoid: literal building photographs; game menu backdrop clichés (throne rooms with lens flare); anything that steals foreground from the stamp; any plate that requires the C v3 stamp to sit inside a specific alcove (the plate must be spatially neutral enough that the stamp reads as centered without pixel-perfect alignment).

**Dimensions / format.** 2560×1440 PNG+WebP per plate (three plates total). WebP ≤ 220KB each. Alpha channel optional (a fully opaque plate composites cleanly over the astrolabe substrate; alpha may be delivered if the artist wants to preserve substrate-through-plate visibility at the edges). Retain PSD / AI source.

**Motion requirements.** Static plate. Receives a scroll-linked parallax transform at 1.0× rate (moves with content, not the substrate). No internal animation.

**Palette hooks.** Bind to Suite palette: 4★ Extra biases toward `--aov-suite-cream` ground with `--aov-suite-ink` architectural detail; 5★ Ultimate biases toward `--aov-suite-gold` warmth with a hint of `--aov-suite-brass`; 6★ Apex reaches full `--aov-suite-brass` with the deepest `--aov-suite-ink` for enthroned shadow. The three plates should read as a warm-temperature ladder ascending with rank.

**Mobile constraint.** Plate must not compete with the stacked mobile layout. On mobile the plate crops center-vertical to a 1080×1080 square variant and sits at 60% opacity behind the stamp. Deliver mobile square variants explicitly (do not rely on browser-side crop).

**Deliverables.**
- `aov3-suite-plate-4-extra.png` / `.webp`
- `aov3-suite-plate-4-extra-mobile.png` / `.webp` (1080²)
- `aov3-suite-plate-5-ultimate.png` / `.webp`
- `aov3-suite-plate-5-ultimate-mobile.png` / `.webp`
- `aov3-suite-plate-6-apex.png` / `.webp`
- `aov3-suite-plate-6-apex-mobile.png` / `.webp`
- Source: PSD / AI per plate
- Delivery folder: `founder/handovers/design-v6.1.1-assets/Asset F v3/`

**Trunk plates note.** v2's Asset F 1★–3★ plates (`f-rank-1-hero.webp`, `f-rank-2-hero.webp`, `f-rank-3-hero.webp`) are reused as-is for Act I Trunk scenes; do not re-commission the Trunk range. If the operator later decides Trunk plates should escalate with the C v3 stamp register, F v3 can extend to a full 1★–6★ set as a follow-up commission.

---

## Asset G — Atmospheric haze (REUSED-V2 color-graded first; fresh commission ready on standby)

**Purpose.** v2's Asset G haze remains valid as the atmospheric parallax layer between substrate and content. v3 requires two colour-graded variants so the haze reads warm on the Suite left rail and cold-void on the Unique right rail. **Operator ratified color-grade first, fresh illustration on standby.** Attempt path 1 (color-grade v2 source composite into two variants); if legibility tests fail at preview time — the haze reads muddy on the Unique rail or overpowers the astrolabe substrate — escalate to path 2 (fresh Asset G v3 illustration, two rails, two source composites). Do not launch path 2 up-front; the color-grade is the cheaper and faster path and preserves budget for Assets H, I, C v3, D v3, E v3 where the illustration matters more.

**Reference / mood.** Path 1 (color-grade, primary): unchanged from v2 — lantern-lit dust motes, atmospheric wisps, low-contrast humidity. Suite variant biases warm sepia toward `--aov-suite-cream` at the highlights. Unique variant biases cold near-black with faint blue-white singularity glints toward `--aov-unique-void` at the highlights. Path 2 (fresh, standby): if launched, re-illustrate the haze as two register-native atmospheric plates: a warm ceremonial haze (incense-smoke, gilded dust) for Suite and a cold void haze (interstellar particulate, singularity mist) for Unique. Failure modes to avoid in path 2: nebula clichés on the Unique variant; anything reading as fog machine on the Suite variant.

**Dimensions / format.** 2560×1440 PNG+WebP, alpha required, per variant. WebP ≤ 140KB per variant.

**Motion requirements.** Static plate, driven by CSS parallax transform at 0.25× scroll rate. No internal animation.

**Palette hooks.** Suite variant matches `--aov-suite-cream` / `--aov-suite-gold` highlight. Unique variant matches `--aov-unique-void` / `--aov-unique-singularity` highlight.

**Mobile constraint.** Haze must not dominate; on mobile the parallax collapses to static and the haze should sit at 20–30% opacity via CSS.

**Deliverables (path 1, primary).**
- `aov3-haze-suite.png` / `.webp` (color-graded from v2 source)
- `aov3-haze-unique.png` / `.webp` (color-graded from v2 source)
- Grading LUT or PSD layer notes retained; v2 source composite preserved as the master for potential re-grade

**Deliverables (path 2, standby — DO NOT commission unless path 1 fails legibility test).**
- `aov3-haze-suite-fresh.png` / `.webp` (new illustration, ceremonial atmospheric)
- `aov3-haze-unique-fresh.png` / `.webp` (new illustration, void atmospheric)
- Source: PSD or AI retained in `founder/handovers/design-v6.1.1-assets/Asset G v3/`

**Escalation trigger.** Path 2 launches if any of these fail at preview time: (a) the Suite haze reads muddy against the astrolabe substrate; (b) the Unique haze reads too similar to the substrate ground and loses atmospheric depth; (c) the two variants read as flavor-tint of the same plate rather than as opposite atmospheric registers. The operator makes the escalation call at preview review.

---

## Asset H — Y-Fork gold-thread illustration (NEW, critical)

**Purpose.** The visual set-piece of Act II FORK. This asset carries the teaching moment of the entire section: at 3★ Evolved the tree forks, and every named skill either continues onto the Suite branch (if its generic parent carries `suiteComponents`) or onto the Unique branch (if it stands alone). The Y-fork is the single frame that makes the reader understand the branch axis without a paragraph of copy.

**Reference / mood.** Half-Merged voice, 19th-century natural-history-atlas anchor. A single gold thread (or engraved gold-leaf line, or filigreed brass path) that ascends the frame and splits once into two branches: one continuing straight, one branching sharply off at an angle. Compositional pegs: engraved cross-sections of tree trunks and root systems (Baylay, Ernst Haeckel *Kunstformen der Natur* trunk plates), goldsmith filigree tree-of-life motifs, alchemical branching diagrams. The negative space between and around the two branches must be preserved for card overlays. Failure modes to avoid: literal illustrated tree with leaves (too on-the-nose; Yggdrasil is metaphor, not botany); railway junction diagrams (too mechanical); DNA / helix imagery (wrong metaphor); anything with three or more branches (the fork is exactly binary, per Yggdrasil II).

**Dimensions / format.** **SVG source is primary and required.** The thread must animate cleanly via CSS `stroke-dashoffset` transitions on scroll progress, so the SVG must be authored with each branch as a separable path (main trunk → fork point → Suite branch, and main trunk → fork point → Unique branch, as at least two distinct paths sharing an endpoint at the fork). Deliver a 3840×2160 PNG+WebP rasterisation as fallback for browsers that fail SVG-fetch, but the served primary is the SVG. If the artist works raster, they must additionally trace the thread into a hand-authored SVG (or approve a vendor-side vector trace) as part of the deliverable.

**Motion requirements.**
- Primary SVG paths named `#aov3-fork-trunk`, `#aov3-fork-branch-suite`, `#aov3-fork-branch-unique`.
- Each path receives a `stroke-dasharray` equal to its computed path length and a `stroke-dashoffset` animated from that length to 0 on scroll progress.
- Fork sequence: trunk draws first (0–40% section scroll), then both branches draw in parallel (40–100% section scroll). The Suite branch draws on the left, the Unique branch on the right; on mobile the branches may draw top-to-bottom stacked, artist to advise.
- Stroke width authored at 6px at native SVG viewBox; CSS may scale.
- Ornamental engraving around the thread (if any) is a separate `<g>` element with its own `stroke-dashoffset` if animated; otherwise fills in at the trunk-draw phase.

**Palette hooks.** Trunk and both branches use `--aov-suite-gold` for the primary stroke (the thread is unified before it forks; both branches inherit gold). Suite branch endpoint fades toward `--aov-suite-brass` (warm resolve). Unique branch endpoint fades toward `--aov-unique-singularity` (cold resolve, the thread cools as it enters void territory). Compositional intent: the fork is a colour-grade departure, not a wholesale palette change — the reader sees one gold thread splitting into two temperatures.

**Mobile constraint.** At 375px width, the fork must remain visible as a fork. If the branches converge into a single line at mobile scale, the composition failed. Deliver a mobile-composed SVG variant if the desktop composition is width-biased; alternatively, deliver a portrait-orientation variant with the fork rotated so the split is vertical rather than horizontal.

**Deliverables.**
- `aov3-y-fork.svg` (primary, hand-authored, named paths)
- `aov3-y-fork.png` / `.webp` (raster fallback, 3840×2160)
- `aov3-y-fork-mobile.svg` (portrait or width-adjusted variant)
- `aov3-y-fork-mobile.png` / `.webp`
- Source: Illustrator or Figma vector file retained
- Delivery folder: `founder/handovers/design-v6.1.1-assets/Asset H/`

**Criticality note.** If any single asset in this commission drives whether the section reads as a *diagram* or as a *scene*, it is H. Under-invest here and the Y-fork becomes decoration; over-invest and it becomes the moment the reader understands the branch axis. Marcus's brief allows unlimited budget on this one specifically.

---

## Asset I — Unique Impossible terminal (NEW, iterated from v2 sketch)

**Purpose.** Terminal art for the 6★ Unique Impossible rail scene, the final beat of the Unique right rail. Marcus loved the v2 Asset I sketch; commission the final production version, iterate the shape but stay in the beloved silhouette.

**Reference / mood.** Impossible-object aesthetic maxed: Penrose staircase, Escher hands-drawing-hands, impossible cube in perspective, tesseract or 4-cube projection, void singularity as the object's centre. The object should read as *cannot exist yet does*. Compositional pegs: the v2 Asset I sketch (the operator will supply the exact reference; the artist should treat that sketch as the compositional starting point and refine, not replace). Aesthetic register consistent with D v3 stamps (this is the terminal piece of the same rail). Failure modes to avoid: departing from the v2 silhouette (the operator ratified it; iterate, do not rework); adding narrative subjects (human figures, hands, faces — the piece is geometric); anything that dilutes the void ground with decoration.

**Dimensions / format.** 3840×2160 PNG+WebP. WebP ≤ 300KB. Alpha channel required. Optional SVG accent layer for the singularity mark or key impossible edge, delivered separately so CSS can animate the singularity (subtle pulse or iterative offset) atop the raster ground.

**Motion requirements.** Terminal scene may pin for ~150vh matching the Suite Apex Gate opposite rail. The object itself is static raster; if an SVG accent layer is delivered, its stroke paths follow the same `stroke-dashoffset` discipline as Asset H. Motion is optional but valued.

**Palette hooks.** Full Unique rail palette. Ground on `--aov-unique-void`, primary geometry on `--aov-unique-fracture`, singularity mark on `--aov-unique-singularity`, accent breaks on `--aov-unique-glitch`. The piece should compositionally rhyme with the 6★ Apex arch on the opposite rail: same terminal weight, mirrored temperature.

**Mobile constraint.** At 375px width the impossible-object trick must still land. If the geometry only resolves as impossible at desktop scale, redesign. Deliver a 1500×2000 mobile-composed variant if the desktop composition is landscape-biased.

**Deliverables.**
- `aov3-unique-impossible-terminal.png` / `.webp`
- `aov3-unique-impossible-terminal-mobile.png` / `.webp`
- Optional: `aov3-unique-impossible-accent.svg` (singularity or key-edge overlay)
- Source: PSD / AI retained; reference the v2 sketch inline in the source metadata
- Delivery folder: `founder/handovers/design-v6.1.1-assets/Asset I/`

---

## Dichotomy palette split

Two rails, two colour families. Every v3 asset binds to one side or spans both (substrate, haze). CSS custom properties below are the source of truth for asset delivery and site-side implementation.

| Token | Rail | Purpose | OKLCH target |
|---|---|---|---|
| `--aov-suite-cream` | Suite | Cream ledger tint, stamp ground | `oklch(0.92 0.025 85)` |
| `--aov-suite-gold` | Suite | Primary gold relief, thread stroke | `oklch(0.78 0.14 82)` |
| `--aov-suite-brass` | Suite | Metallic tag surface, warm terminal | `oklch(0.65 0.10 72)` |
| `--aov-suite-ink` | Suite | Incised linework, engraved shadow | `oklch(0.25 0.02 75)` |
| `--aov-unique-void` | Unique | Ground fill, deep near-black | `oklch(0.13 0.015 260)` |
| `--aov-unique-singularity` | Unique | White-point, singularity highlight | `oklch(0.96 0.01 240)` |
| `--aov-unique-fracture` | Unique | Broken linework, mid-tone geometry | `oklch(0.55 0.03 245)` |
| `--aov-unique-glitch` | Unique | Broken accent, magenta-shifted gold | `oklch(0.72 0.16 12)` |
| `--aov-substrate-ground` | Both | Astrolabe substrate ground | `oklch(0.22 0.015 85)` |
| `--aov-substrate-ink` | Both | Astrolabe engraved linework | `oklch(0.55 0.03 75)` |

The two rails are not colour-inversions of each other; the Unique rail is not "Suite with a dark background". The Unique palette rotates the hue axis (yellow-gold toward blue-void), collapses the chroma near the ground, and reserves a single high-chroma accent (`--aov-unique-glitch`) for the broken-edge moments. Suite is warm-ordered; Unique is cold-broken.

---

## Naming convention

All v3 asset files use the prefix `aov3-` to prevent collisions with v2 assets already served from `docs/assets/ascension-overdrive/`.

```
aov3-<asset>-<rank>-<state>.<ext>
```

Slots:
- `<asset>`: `astrolabe-substrate`, `suite-stamp`, `suite-plate`, `unique-stamp`, `unique-loop`, `haze`, `y-fork`, `unique-impossible-terminal`
- `<rank>`: `1-awakened`, `2-named`, `3-evolved`, `4-extra`, `5-ultimate`, `6-apex`, `6-impossible` (rank omitted for section-scope assets like substrate and Y-fork)
- `<state>`: optional; `mobile`, `card`, `badge`, `poster`, `accent`, `fresh` (Asset G path 2 fallback marker)

Examples:
- `aov3-astrolabe-substrate.webp`
- `aov3-suite-stamp-1-awakened-badge.webp`
- `aov3-suite-stamp-4-extra.webp`
- `aov3-suite-stamp-6-apex-card.webp`
- `aov3-suite-plate-5-ultimate.webp`
- `aov3-unique-stamp-6-impossible.svg`
- `aov3-unique-loop-5-ultimate.mp4`
- `aov3-unique-loop-5-ultimate-poster.webp`
- `aov3-haze-suite.webp`
- `aov3-haze-suite-fresh.webp` (if Asset G path 2 launches)
- `aov3-y-fork.svg`
- `aov3-y-fork-mobile.png`
- `aov3-unique-impossible-terminal.webp`

v2 assets already in `docs/assets/ascension-overdrive/` retain their existing filenames (no `aov3-` prefix); v3 assets are added alongside them.

---

## What is REUSED without change from v2

- Asset A (`apex-arch.png` / `.webp`) — served as-is for the Suite 6★ Apex terminal scene.
- Asset A components (`apex-component-*.png` / `.webp`, seven files) — served as-is for the Suite Apex Gate predicate staircase.
- Asset F v2 Trunk plates: `f-rank-1-hero.webp`, `f-rank-2-hero.webp`, `f-rank-3-hero.webp` — reused as Act I Trunk backdrops. (F v3 covers 4★–6★ Suite; F v2 covers 1★–3★ Trunk.)
- Any v2 asset not superseded by a v3 rewrite and not listed in *DEPRECATED* below is presumed reused.

---

## What is DEPRECATED from v2

- **v2 Asset C rank stamps (full 1★–6★ set: `rank-1-awakened`, `rank-2-named`, `rank-3-evolved`, `rank-4-hardened`, `rank-5-ultimate`, `rank-6-*` if present).** Operator ratified full replacement by Asset C v3. Reasons: (a) v2 stamps are unused elsewhere on the site, so the sunk-cost concern is nil; (b) Asset C v3 doubles as skill-plaque foundation for site-wide reuse, requiring production-grade identity artwork the v2 stamps do not carry; (c) the rank rename from "Hardened" to "Extra" per Yggdrasil II obligates a fresh 4★ stamp regardless; (d) coherent 1★–6★ ladder identity beats mixing v2 Trunk stamps with v3 Suite stamps. The v2 files remain on disk for archival reference only.
- **Ledger-texture (`ledger-texture.png` / `.webp`, `ledger-texture-variant.png` / `.webp`).** Superseded by Asset B v3 astrolabe substrate. Files remain on disk; v3 shape does not reference them.
- **v2 Asset D stamps (`unique-4`, `unique-5-ultimate`, `unique-6-impossible`).** Superseded by Asset D v3. v2 stamps did not carry the impossible-object geometry the ratification calls for.
- **v2 Asset E loops** (if any were delivered under the v2 filenames): superseded by Asset E v3 re-commission.

**NOT deprecated (reinstated in v3):** Asset F Suite hero plates. The v2 Trunk plates (1★–3★) are reused as-is; Asset F v3 covers the new 4★–6★ Suite rail hero plates.

---

## Failure tests for the commission

The commission passes when all of these are demonstrably true against delivered assets:

1. Asset H animates from `stroke-dashoffset: <path-length>` to `0` via a single SVG stroke transition on scroll progress without frame drops on Chromium mobile at 375px width.
2. Asset D v3 Unique 6★ Impossible reads as an impossible object from ~15ft viewing distance on a 27-inch monitor; the "wrong corner" is visible in silhouette, not only on close inspection.
3. Asset B v3 astrolabe engraving remains legible at 375px viewport width without competing visually with rank-card foreground copy or with the haze plate above it.
4. Asset C v3 Suite stamps read as ceremonial architecture, and D v3 Unique stamps read as broken geometry, when the two sets are placed side-by-side at equal size; the dichotomy is legible without any accompanying label.
5. Asset E v3 loops are visually distinct from each other (no two loops read as recolours of the same motion primitive) and each loop reads as motion, not as still image with drift, at 720p mobile scale.
6. Asset G haze variants are colour-graded such that the Suite variant reads warm-cream and the Unique variant reads cold-void, without either overpowering the substrate or the rank content composited above them.
7. Asset I Unique Impossible terminal iterates from the v2 sketch silhouette; the operator recognises the shape as an evolution, not a departure.
8. Every v3 raster asset with a mobile variant delivers the mobile primary at the stated dimensions; no v3 file relies on browser-side downscaling of the desktop primary to serve mobile.
9. Every v3 asset with an alpha channel composites cleanly over both `--aov-substrate-ground` and `--aov-unique-void` without visible white halos or matte artefacts.
10. Zero v3 asset filenames collide with existing v2 filenames in `docs/assets/ascension-overdrive/`; the `aov3-` prefix is applied throughout.

---

## Delivery logistics

- Vendor drops → `founder/handovers/design-v6.1.1-assets/Asset [X] v3/`, mirroring existing v1/v2 folder convention.
- Served kebab-case primaries → `docs/assets/ascension-overdrive/`.
- Delivery cadence: Asset H (Y-fork) is the critical-path piece; if the artist can deliver one asset first, it is H. Astrolabe substrate (B v3) is second priority; the shape work cannot preview at intended fidelity without it. Stamps (C v3, D v3) as a paired delivery. Loops (E v3) and Impossible terminal (I) close the commission.
- Two-way iteration expected: as v3 shape preview ships and drafts arrive, the artist and Marcus refine composition against the rendered scenes, particularly for the Y-fork and the Unique 6★ terminal.

Budget: unlimited. Do not economise on any single line. If the shape needs a piece not enumerated here, ask.
