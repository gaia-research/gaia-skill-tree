# Handoff: design-intent documentation for the Skill Tree redesign (Agy)

**Issue:** [#2484](https://github.com/gaia-research/gaia-skill-tree/issues/2484), under epic [#2481](https://github.com/gaia-research/gaia-skill-tree/issues/2481).
**Team:** Agy (Antigravity). Neon orchestrates; Hydrogen implements.
**Date:** 20 Nov 2026.

## The job

The founder approved a redesign prototype of gaiaskilltree.com. Write new Markdown docs that state what the prototype intends, aligned with the endgame, so that the later wiring work starts from a written spec instead of reverse-engineering HTML.

These docs **describe and align. They do not decide.** Where the prototype leaves something open, the doc lists it as open. Nothing here changes `docs/` (the site) or any code.

## Read first (in this order)

1. This packet's `README.md`: the teams, the stamp rule and the decisions recorded on 20 Nov 2026.
2. `founder/GAIA_MULTI_TREE_WEB_ENDGAME_2026-11-14.md`. It is the owner of adaptive website composition: three visual-authority layers, section dispositions, the hero and Blender contract, scene travel, and the Website Experience Manifest.
3. `founder/ENDGAME.md` §11 and `founder/ENDGAME - SCHEMA.md` (projection manifest, multi-index separation).
4. `DESIGN.md` (tokens and components), `founder/ARBOR-DESIGN.md` (Arbor law), `PRODUCT.md`, and `CONTEXT.md` (vocabulary, banned words).
5. `docs/agents/design-entrypoints.md`, `docs/agents/deferred-surface-convention.md`, `docs/agents/fixed-nav-clearance.md` and `docs/agents/frontend-known-issues.md`. Each surface doc must say how it meets these.
6. The prototype source in `prototype/project/`. Start with `Brief.dc.html`: its "Coverage matrix", "Yggdrasil in 3D" and "Round three" sections are the design brief. Then read the board for each surface. If the founder has shared the canvas, it is at https://claude.ai/artifact/8LmXZkYNH2HggishnaDwow.

## Roles

**Neon (orchestrator)**

- Reads everything above.
- Fixes the outline of every file before assigning it.
- Assigns one file, or one group of surface files, per Hydrogen.
- Reviews every file against the rules below and checks consistency across files.
- Runs the gates and opens the PR.
- Writes no surface file itself unless a Hydrogen is blocked.

**Hydrogen (implementers)**

- Each writes its assigned files from the prototype board, the live route's current code, and the canon.
- Each reports anything it could not resolve back to Neon rather than deciding it.

## Deliverables

Create `founder/website-design/` with these files. Keep each surface file between 120 and 300 lines.

| File | What it must contain |
|---|---|
| `README.md` | Index. Precedence, restated from the endgame and not reinvented: META.md and GOVERNANCE.md, then ENDGAME - SCHEMA.md, then DESIGN.md, then ARBOR-DESIGN.md, then the web endgame. These docs sit below all of them and describe the approved prototype. Also: how to read the prototype, and the glossary pointer to CONTEXT.md. |
| `EXPERIENCE-MANIFESTS.md` | **Draft** Website Experience Manifests for Yggdrasil IV and Arbor I, in the illustrative YAML shape of web endgame §6. Mark the schema as illustrative and not ratified. Add a table of every homepage and site section with its disposition per Tree (`shared`, `tree-owned`, `replaced`, `reordered` or `omitted`), exactly as the prototype composes it, and a fallback per Tree. |
| `DESIGN-SYSTEM.md` | The prototype's token layers (`prototype/project/atlas.css`, `System.dc.html`) mapped onto the endgame's three authority layers: the Gaia shell, Tree experience and semantic materials. Plus the world layer and the Arbor weather layer, typography (EB Garamond, Bricolage Grotesque, Departure Mono), and the component catalogue. The catalogue covers plate, section head, tabs, segmented controls, lens control, wreathed avatar, medallion, metal grade, ledger table, leaderboard bar, inspector, dock, sheet, toast, empty and unknown states. Per component: anatomy, states, both worlds, phone, accessibility. |
| `surfaces/<family>.md` | One file per surface family, listed below, using the surface template. |
| `EXPLORER-3D.md` | The 3D explorer as approved. See the section below. |
| `ARBOR-WEATHER.md` | Arbor runtime weather. See the section below. |
| `MOTION-AND-ACCESS.md` | Motion rules, reduced motion, flash safety, focus order, keyboard paths, touch targets, contrast, screen-reader labels and the live-region messages the prototype uses. |
| `ASSET-REGISTER.md` | Every image and Rive asset the redesign uses or requests: A1 to A5, R1 to R3, plus the reused approved art. Columns: id, role, surface, source, stamp state (pending until Claude stamps), fallback. Link the image and Rive handoffs; never mark an asset as stamped yourself. |

Also add **one short section to `DESIGN.md`**, titled "Website redesign: founder rulings of 20 Nov 2026". It records the rulings below and points to `founder/website-design/`. Edit nothing else in `DESIGN.md`. In particular, amend the "Glyph = structural class" section by one sentence only: tree renderers draw every node round, and the glyphs remain text marks.

### Founder rulings to record (20 Nov 2026)

- **Tree nodes are round** in tree renderers. A Fusion node carries a fine inner ring instead of a diamond. The text glyphs ○ ◇ ◆ ◉ stay in chips, legends and plaques.
- **The 3D explorer keeps the live layout's positions and colours** and grows its links as curved wood, the way the hero shape does.
- **A Unique hangs as fruit from a skill it needs**, at most three to a bough.
- **The Origin wreath frames the avatar exactly as the live plaque does:** the photo is 82% of the frame and the wreath 112%, so the wreath is 1.366 times the photo, centred.
- **The vertical-bar Leaderboard** is a homepage section and a page, and Leaderboard is in the primary nav. **The Trust Ledger** sits beside the Evidence Library, under the Yggdrasil lens only.
- **Arbor weather changes cut the whole screen** with an impact frame and a glitch, and Ultra is golder and bolder. The safety rules in `ARBOR-WEATHER.md` apply.
- **The Hell-Heaven stamp artwork is a placeholder.** The placement is approved; the artwork is not ratified.

## Surface files

| File | Prototype board | Live route today | Related issues |
|---|---|---|---|
| `surfaces/home.md` | `Home.dc.html`, `Main.dc.html` | `/` | #2462, #2464 |
| `surfaces/ascension-overdrive.md` | `Home.dc.html` (capture) | `/#ascension` | #975. **Locked:** the doc records that it is unchanged and framed. |
| `surfaces/tree-explorer.md` | `Atlas.dc.html`, `Scene.dc.html` | `/?tree=1`, `/?field=1` | #1736, #2463, #652 |
| `surfaces/skills.md` (Ledger, Specimens, By capability, Flow) | `Skills.dc.html` | `/named/` | #1231 |
| `surfaces/skill-dossier.md` | `Dossier.dc.html` | `/named/report.html` | #2063, #1194 |
| `surfaces/leaderboard.md` | `Leaderboard.dc.html`, `Home.dc.html` | `/` (leaderboard section) | none |
| `surfaces/evidence-and-trust.md` (Library, Ledger, Methodology, Challenges) | `Evidence.dc.html` | `/evidence/`, `/trust/ledger/`, `/codex/` | #1466, #1001 |
| `surfaces/benchmarks-and-stamps.md` | `Benchmarks.dc.html` | `/benchmarks/` | #2462, #2464, #1508 |
| `surfaces/contributors.md` | `Contributors.dc.html` | `/u/<handle>/` | #1194, #2046 |
| `surfaces/hall-of-heroes.md` | `Heroes.dc.html` | `/heroes/` | #1821, #1326 |
| `surfaces/share-plaque.md` | `Share.dc.html` | modal on every plaque | none |
| `surfaces/docs.md` | `Docs.dc.html` | `/en/*.html` | #952, #775, #2042 |
| `surfaces/observatory.md` | `Observatory.dc.html` | `/#ecosystem` | none |
| `surfaces/reports-and-changelog.md` | `Reports.dc.html`, `Changelog.dc.html` | `/meta.html`, `/reports/`, `/trending/`, homepage changelog sidebar | #973, #2265, #1309 |
| `surfaces/about.md` | `About.dc.html` | `/about.html` | none |
| `surfaces/badges.md` (states only) | `States.dc.html` | `/badges/` | #1326, #1817. **Core page; see frontend-known-issues.md.** |
| `surfaces/utility-states.md` | `States.dc.html` | various | none |
| `surfaces/navigation-and-footer.md` | `Main.dc.html`, `NavCompare.dc.html` | `site-nav.js`, `site-footer.js`, `mounts.js` | Guard D. The footer stays substantially unchanged. |

### Surface template

Every surface file uses these headings, in this order:

1. **Purpose.** Who comes here and what they leave with, in two or three sentences.
2. **Today.** The live route and the files that render it (paths), and what is dated.
3. **Approved design.** Composition top to bottom, with each component named from `DESIGN-SYSTEM.md`. Note which parts are shared and which are Tree-owned.
4. **Data.** Every figure's source file in the repo (for example `docs/api/v1/leaderboard.json`, `docs/graph/gaia.json`, `docs/graph/named/index.json`), and what is shown when a source is missing. Never a number without a source.
5. **Yggdrasil and Arbor.** What changes when the lens changes, and what is absent in Arbor and why. Follow web endgame §3: never a green clone of a Yggdrasil surface.
6. **Phone.** What reflows, collapses or moves to a sheet at 390 px.
7. **Accessibility and motion.** Specific to this surface. Point to `MOTION-AND-ACCESS.md` for the shared rules.
8. **Entrypoints.** Per `docs/agents/design-entrypoints.md`: nav, footer, homepage, `window.GAIA_MOUNTS`, cross-links and cache-busting. Say which are touched and which are waived.
9. **Bridge and deferred states.** Anything that would ship as a bridge state needs a `.wip-banner` and a tracking issue, per `docs/agents/deferred-surface-convention.md`. List them; do not create issues.
10. **Assets.** Ids from `ASSET-REGISTER.md`.
11. **Open questions.** Anything the prototype does not settle.
12. **Acceptance.** Checks that a later wiring PR can be tested against, at 1440 and 390 and in both worlds.

## `EXPLORER-3D.md` must cover

The source for all of this is `prototype/project/Explorer3D.dc.html` and the "Yggdrasil in 3D" section of `Brief.dc.html`.

- **The live layout**, from `docs/js/world-tree-layout.js` field pose, with the approved wood:
  - a twisted trunk spanning the layout's axis waypoints, stopping at bough height
  - a root fibre from the trunk base to every Basic
  - each fusion grown from its structural parent, or from the trunk where its route meets it
  - every other prerequisite drawn as a quiet strand that bows through the heartwood
  - the dashed lineage on selection draws every true prerequisite link
- **Nodes:** round, sized by rank with no Unique floor; Fusion with an inner ring; the 4★ Extra dwarf, 5★ sun and 6★ pulsar treatments.
- **Uniques as fruit:** hung from a prerequisite in the crown, then from a crown skill that builds on it, then from a proven bough in the same cluster; at most three per bough. Black holes are toned down; the 5★ Unique is copper (`--rank-5-unique`). Close-approach detail (level of detail at 18 px and above). Relationship to [#2480](https://github.com/gaia-research/gaia-skill-tree/issues/2480).
- **Navigation:** Orbit and Fly, keys, the altitude gauge, search with @people, the Lens panel, the inspector with the Origin holder and wreath, collection tray, off-screen chevron, phone sheets.
- **Performance budget and technique:**
  - sprites painted once
  - wood projected once per frame and batched by kind, colour and depth band
  - adaptive resolution
  - pause when hidden
  - render on input only under reduced motion
  - the measured figures from the Brief, with their caveat: headless software rendering, a comparison and not a target
- **The debug frame meter:** hidden, and opened with the backtick key or `?debug=frames`.
- **The hero shape:** a review alternative, not the production direction.

## `ARBOR-WEATHER.md` must cover

The source is `prototype/project/Weather.dc.html`, the weather code in `Home.dc.html` and `Atlas.dc.html`, and `atlas.css` layer 3.

- **The states:** Clear, Heaven, Hell, Ultra, and what each does to the instrument. Hell's colours are as approved.
- **The full-screen transition per state:** impact frame, glitch and resolve, with the prototype's timing table.
  - Heaven: 520 ms
  - Hell: 480 ms
  - Ultra: 640 ms, with the stamped ULTRA frame, gold burst and speed lines
  - Clear: 450 ms
- **Ultra at rest:** gold field, gold corner brackets, heavy gold labels, a solid gold pressed control. Ultra gold is a temporary signal, never a rank or Origin material (DESIGN.md, Multi-Tree scope).
- **Safety:**
  - no more than three flashes in any one second (WCAG 2.3.1)
  - no full-screen red
  - light sheets at 55% opacity or less
  - one overlay at a time; rapid changes restart it rather than stacking
  - reduced motion: a single 150 ms fade
  - compositor-only animation
- **Accessibility:** `aria-pressed` on the control and an `aria-live` announcement of the new weather.
- **Performance note:** the 1440 Ultra entry measured 39 to 50 fps in software rendering; idle Ultra is 60. Real-GPU measurement is still owed.

## Rules for every file

- **Describe the approved prototype; never invent a feature, number, quote or decision.** Cite file paths. State every count with its snapshot date (17 Nov 2026) and its source.
- **Open questions stay open.** Carry these, at least:
  - the Leaderboard's Yggdrasil IV contested marks, which the endgame keeps and the prototype does not yet show
  - the Hell-Heaven stamp artwork
  - optional A3
  - R2's glance state
  - R3's owner approval
  - the 28 px nav use of the A5 keystone
  - Real-GPU performance figures for Ultra
- **Vocabulary from `CONTEXT.md`.** Never use "Atlas" as a product or page name in any copy a visitor could see: it is an internal name. Do not touch `scripts/lexicon/` or `CONTEXT.md` unless a founder ruling requires it; the lexicon serves the work.
- **Nothing private.** No unpublished lore, story beats, chronology or character plans.
- **No wiring instructions disguised as decisions.** Wiring gets its own handoff after the founder sees the final product. A surface's "Acceptance" section is written so that handoff can reuse it.

## Gates before the PR

```bash
npx -y tsx scripts/lexicon/check-lexicon.ts      # must exit 0
python scripts/check_nav_mounts.py               # unchanged, sanity only
```

Also check that every relative link in `founder/website-design/` resolves.

## Delivery

1. **Branch.** Create `docs/website-design-intent` off `main`. The `docs/` prefix may touch any `*.md`.
2. **Push** after each file or small group, not at the end.
3. **PR.** Open one PR into `main` titled `docs(founder): website design intent for the approved redesign`, with `Refs #2484` in the body. The body lists every file, with one line on what it covers.
4. Mark the PR ready. **Do not merge it.** Claude audits it for fidelity to the prototype and to the endgame; the founder may veto.

## Done when

- Every file in the deliverables table exists and follows the template.
- The `DESIGN.md` section and the one-sentence glyph amendment are in, and nothing else in `DESIGN.md` has changed.
- The gates pass.
- The PR is ready and unmerged, for Claude's final audit.
