# Handoff: image assets for the Skill Tree redesign (Codex, Sol)

**Issue:** [#2482](https://github.com/gaia-research/gaia-skill-tree/issues/2482), under epic [#2481](https://github.com/gaia-research/gaia-skill-tree/issues/2481).
**Team:** Sol at Xhigh, working solo in Codex. Terra reviews independently.
**Date:** 20 Nov 2026.

## Before you start

1. **Read the canonical skill end to end:** `gaia-research/.agents/skills/gaia-image-production/SKILL.md`. It governs the model rule, the free-first toolbelt, the workbench, the ledger and the strict check.
   - The copy in this repo (`gaia-skill-tree/.agents/skills/gaia-image-production/SKILL.md`) has a superseded model rule ([#2485](https://github.com/gaia-research/gaia-skill-tree/issues/2485)). Use it only for its Skill Tree storage rules: masters stay outside Skill Tree's Git, only WebP derivatives ever enter `docs/assets`, and no raster carries text.
2. **Model.** Codex image generation defaults to `gpt-image-2.6`, per the founder's attestation of 20 Nov 2026.
   - There is no model preflight.
   - Record `credit` as `Sol (Codex), gpt-image-2.6: Codex default, founder attestation 2026-11-20`.
   - If Codex ever reports a different model for a call, stop and say so; do not ledger that output as `gpt-image-2.6`.
3. **Free path first.** As the canonical skill says, generate only when no deterministic tool can make the content. A5 in particular is geometry, not generation.
4. **Read the references for each packet** (listed below), plus `DESIGN.md`, `founder/ARBOR-DESIGN.md` §3–4, and `founder/GAIA_MULTI_TREE_WEB_ENDGAME_2026-11-14.md` §2 and §4.
5. **Prototype.** Look at the boards in `prototype/project/` (`Handoff.dc.html`, `Home.dc.html`, `Heroes.dc.html`, `Observatory.dc.html`, `Scene.dc.html`). If the founder has shared the canvas, it is at https://claude.ai/artifact/8LmXZkYNH2HggishnaDwow.

## Where the work lives

All production happens in **gaia-research**, because the canonical harness and ledger live there:

| What | Where |
|---|---|
| Drafts and variants | `assets/workbench/skill-tree-redesign/` (gitignored) |
| Delivered masters and WebP derivatives | `assets/generated/skill-tree-redesign/<asset-id>/` |
| Ledger entries | `content/assets/asset-ledger.json`, one per master, derivatives listed in `derivatives` |
| Blender `.blend` and glTF (A1 only) | Outside Git, in the local master archive. A separate 3D art repo is preferred but not yet approved (ENDGAME §4). Record their SHA-256 in the A1 ledger `notes`. |
| Contact sheet for review | `scripts/assets/generate-contact-sheet.ts`, attached to the PR |

**Nothing enters `gaia-skill-tree` in this workstream.** Wiring is on hold until the founder has seen the final product.

**Asset ids:** `st-redesign-a1-arbor-plate`, `st-redesign-a1-arbor-plate-hell`, `st-redesign-a2-hall-stage`, `st-redesign-a3-observatory-floor`, `st-redesign-a5-keystone-ygg`, `st-redesign-a5-keystone-arbor`.

## Delivery

1. Open **one PR in gaia-research** titled `assets(skill-tree-redesign): A1–A5 candidates`, with `Refs gaia-research/gaia-skill-tree#2482` in the body.
   - Follow gaia-research's commit rule: commits are authored by `mbtiongson1`, with no AI attribution trailers.
   - Push after each asset, not at the end.
2. Every ledger entry lands with `status: "candidate"`.
3. Run `sync-asset-ledger.ts`, then `check-asset-ledger.ts --strict`. Both must pass.
4. In the PR body, list for each asset: its id, master path and SHA-256, every derivative with path, size, dimensions and SHA-256, the prompt you used (verbatim), and every deterministic step (crop, grade, composite) in order.
5. Mark the PR ready. **Do not merge it.**

## Review and stamp

1. **Terra verifies** each asset on the PR. Terra comments per asset id with the SHA-256s it checked and the result of every check in the asset's Terra list. A fail goes back to Sol with the specific check that failed; Sol corrects and Terra re-checks.
2. **Claude stamps** each verified asset. Claude sets the ledger entry to `status: "approved"` and appends to `notes`: `Stamped by Claude (redesign design lead) on <date>; Terra verification <PR comment link>`.
3. **The founder may veto** any stamp. A vetoed entry goes to `status: "deprecated"` with the reason in `notes`, and the packet returns to Sol.
4. Claude then places the stamped derivatives in the prototype for the founder's final review.

## Rules for every packet

- **No text** in any raster: no letters, numerals, labels or UI.
- **No lore.** No story symbols, characters, clues or chronology. Characters appear only under A4's rules.
- **Do not recolour semantic materials.** Evidence Platinum, Gold, Silver and Bronze, the gold Origin wreath and rank medallions keep their meaning. Arbor green identifies the lens and never means "good". Ultra gold is weather, not rank.
- **No stars, medallions or rank colour in Arbor assets.**
- **Compression.** WebP derivatives as small as the acceptance allows. Opaque unless the packet says transparent.

---

## A1 · Arbor reference plate (and Blender canon)

**Status:** required for parity with Yggdrasil.

**Destination.** The still behind the Arbor hero, and the Tree Explorer in Arbor. The live canvas stays the only semantic layer: this plate never carries meaning.

**Objective.** The tree the prototype sketches:

- a bundled trunk of parallel traces that turns only at 45°
- main branches peeling off on five separated depth planes
- thin secondary traces with small circle, square and diamond terminals
- ringed terminals at branch ends
- roots spreading as traces across a ground plane

Keep the front silhouette of the founder's Arbor I concept; the depth is what the concept does not show.

**Prompt (default plate):**

> A tree built from circuit traces, seen from slightly above and in front, standing on a dark ground plane. The trunk is a bundle of six to eight thin parallel traces that turns only at 45 degrees. Branches leave the trunk on several separated depth planes, like sheets of glass stacked front to back: each runs diagonally up at 45 degrees, then horizontally, and ends in a small ring terminal. Thin secondary traces split off with tiny circle, square and diamond pads. Roots spread across the ground plane as traces with 45-degree turns, receding into depth. Washed charcoal ground (#1b1d1b), traces in muted green (#61c674) with bone-white (#eeeae2) highlights at terminals, faint corner brackets marking each depth plane. Crisp, technical, calm. No curves, no leaves, no bark, no glow blobs, no neon, no stars, no medallions, no text, no UI.

**Hell variant.** The same composition, inverted to paper (#efece7) with black traces:

- a single red filament (#c2181d) up the trunk
- red glow rings at the terminals
- black triangular shards around the base
- faint red ground-plane lines

Hell's colours are approved as they stand; do not shift them.

**Blender canon.** ENDGAME §4 calls for a Blender-authored reference world.

- If Blender is available in your environment, build the model with each depth plane as a separate collection, render the plates from it, and export a glTF of the trace geometry.
- If Blender is not available, deliver the generated plates and report the Blender part as blocked. Do not substitute a fake 3D source.
- Gold-canon status for a Blender reference world stays with the founder (ENDGAME §4). A stamp here clears the plate for the prototype only.

**References.**

- The founder's Arbor I concept art on issue [#1736](https://github.com/gaia-research/gaia-skill-tree/issues/1736): the green sheet, the Hell sheet, the Yggdrasil III vs Arbor I lens sheet, and the red ground-plane study.
- `founder/ARBOR-DESIGN.md` §3–4.
- `prototype/project/Scene.dc.html` for plane spacing.

**Format.**

- Master: 3200 × 2400 PNG.
- Derivatives: 1600 × 1200 and 900 × 1200 (phone) WebP, opaque.
- glTF only from Blender.

**Phone crop.** Keep the trunk centred; the phone crop loses the outer third on each side.

**Acceptance.**

- Reads as a tree at thumbnail size and as circuitry up close.
- Never reads as a rail line or a fence: no long, evenly spaced parallels outside the trunk.
- At 35% opacity under the live graph, bone text in the copy column keeps 7:1 contrast.

**Terra checks.**

- Only 45° and 90° turns.
- The front silhouette matches the concept.
- At least three depth planes are visible when the camera orbits 20° (Blender) or are legible as overlapping planes (plate).
- No stars and no rank colour; green is used for traces only.

## A2 · Hall of Heroes stage

**Status:** required. It replaces placeholders ([#1326](https://github.com/gaia-research/gaia-skill-tree/issues/1326)).

**Destination.** Behind the contributor photo and medallion on every Hall of Heroes stage: one image for the whole page, not one per stage. Reusable as the badges page backdrop.

**Objective.** A ceremonial vitrine for one person at a time: weight and permanence without spectacle. The photo is the subject; the plinth only holds it.

**Prompt:**

> An empty museum vitrine at night: a low dark umber stone plinth (#14120f) under a single soft gold top light, the light pooling in a tight ellipse on the plinth surface. Very dark warm background falling to black at the edges. Faint engraved concentric rings on the plinth face like an astrolabe. Nothing on the plinth. Quiet, monumental, precise. No text, no people, no medallion, no gold glitter, no smoke.

**References.**

- `docs/assets/ascension-overdrive/aov4-astrolabe-substrate.webp` for ground colour and engraving.
- The Ascension Overdrive commissions doc for the warm Suite register.

**Format.**

- Master: 3840 × 2160.
- Derivatives: 2560 × 1440 and 900 × 1200 WebP, opaque.

**Phone crop.** Plinth centred, light pool in the upper half.

**Acceptance.**

- A 240 px circular photo with its gold wreath, placed at 32% from the left, reads as standing on the plinth.
- The ground matches the Yggdrasil ground token within ΔE 3.
- Under 180 KB at 2560 px.

**Terra checks.**

- No Apex-reserved gold intensity.
- No ornament that competes with the medallion.
- The engraving stays sub-legible.

## A3 · Observatory interior

**Status:** optional. The founder says yes or waives it before any spend; the PR asks the question.

**Destination.** The Observatory page, behind the SVG dome plan.

**Objective.** Turn the dome diagram into a place: a quiet observatory floor with three apertures throwing their rooms' light.

**Prompt:**

> Looking straight down into the floor of a circular observatory at night, a dark polished stone floor with a fine engraved compass ring. Three long slit apertures in the dome above cast three beams onto the floor at 120 degree intervals: one warm gold, one cool sky blue with a magenta edge, one split prismatic light (violet, blue, cyan, rose). The centre is dark and empty. Architectural, still, scientific. No people, no telescope, no stars painted on surfaces, no text.

**References.**

- Skill Heaven site `DESIGN.md` §05 (one beam, three names).
- Gaia Research brand colours #38bdf8 and #ec4899.
- Skill Heaven prism hues.

**Format.**

- Square master: 3000 × 3000.
- Derivative: 1600 × 1600 WebP.
- The beams sit at 0°, 120° and 240° from the top, so they align with the SVG apertures.

**Acceptance.**

- Beam colours match the room accents.
- The centre stays clear for the keystone.
- Works under a 50% dark overlay.

**Terra checks.**

- No figure or silhouette.
- No lore symbols.
- Alignment within 2° of the SVG apertures.

## A4 · Observatory character cameos

**Status:** conditional. **Generate nothing without the owner's approval.**

**Default.** Reuse approved art. The prototype already uses approved masters at small scale:

- the poster of the approved `milim.riv` (gaia-research `public/milim`)
- Lucy v5 Zero (the gaia-skill-heaven delivery)

Both sit inside their room's light at about 96 px tall, behind a Quiet or Off presence control. If the owner does not ask for bespoke cameos, A4 closes as "reuse approved art".

**Only if bespoke cameos are approved.**

- **Milim:** follow `marketing-tasks/MILIM.md` exactly, including the face settei test against the gold master. Approved expression only.
- **Lucy:** follow `LUCY_CANONICAL_CHARACTER_SHEET.md`. The Zero state is seated, eyes closed, no wings, one katana. Never horns, armour, boots or eye flare.

**Not allowed.** New costumes, new poses that imply story, lore clues, or either character presented as a Skill Tree ambassador.

## A5 · Rendered Diamond Seal keystone

**Status:** required. It replaces the CSS/SVG stand-in at the centre of The Observatory dome.

**Destination.**

- The keystone at the centre of The Observatory dome, about 90 to 160 px wide.
- Possibly the 28 px nav seal later; that is not requested now.

**Geometry to keep exactly.**

- The canonical Diamond Seal, `docs/assets/marks/diamond-seal.svg`: one diamond (`M 32 4 L 60 32 L 32 60 L 4 32 Z` on a 64-unit grid) with an EB Garamond SemiBold "G" centred in it.
- The prototype's extra inner square is not part of the brand mark. Do not add it.
- Front view, at most 8° of tilt.

**Method.** This is geometry, so take the free path:

- extrude and bevel the SVG in Blender, or
- build the layers in SVG and HTML and render them.

Generation may be used only for a material texture, composited back onto the exact geometry. Never let a model draw the "G": letterforms from an image model will not pass the overlay test.

**Material and light.**

- Key light from the upper left, soft fill from the lower right.
- A bevelled metal frame with a centre ridge, the "G" raised.
- **Yggdrasil:** warm gold with parchment highlights (accent `oklch(0.80 0.115 82)`, highlight near `oklch(0.95 0.05 88)`) and a dark umber recess.
- **Arbor:** cooler green-teal metal (accent `oklch(0.745 0.15 148)`) with a slate recess.

**Format.**

- Transparent WebP at 2× for 160, 96 and 56 px display sizes, per world.
- A flat two-tone SVG fallback using the same geometry.
- No baked background, glow or wordmark.

**Acceptance.**

- Overlays `diamond-seal.svg` within 1 px at 160 px.
- The diamond and the "G" stay distinct at 28 px.
- Reads on both world grounds.
- Under 60 KB a file.

**Terra checks.**

- The geometry overlay passes.
- No second square, no added ornament.
- Arbor's version uses no gold; Yggdrasil's gold does not reach Apex intensity.

## Not requested

- **The Hell-Heaven stamp artwork.** The founder approved the placement, but the artwork is not ratified. It stays a labelled placeholder.
- **Medallions, the Origin wreath, the Yggdrasil backdrop and the Ascension Overdrive art.** They are approved and unchanged.

## Done when

- A1, A2 and A5 are stamped and not vetoed.
- A3 and A4 are each either stamped or waived by the founder.
- `check-asset-ledger.ts --strict` passes on the PR head.
- The PR is ready, unmerged, for Claude's final audit.
