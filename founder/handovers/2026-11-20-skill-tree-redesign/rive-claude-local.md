# Handoff: Rive requests for the Skill Tree redesign (local Claude team)

**Issue:** [#2483](https://github.com/gaia-research/gaia-skill-tree/issues/2483), under epic [#2481](https://github.com/gaia-research/gaia-skill-tree/issues/2481).
**Team:** local Claude with the Rive MCP. Opus (medium) leads; Sonnet and Opus implement.
**Date:** 20 Nov 2026.

The cloud design session has no Rive capability, so the prototype uses static stand-ins. This handoff asks for three pieces, and two of them reuse approved files.

**No wiring.** Deliver files into this handover folder; nothing goes into `docs/` and no page loads them yet. The founder decides on wiring after seeing the final product.

## Before you start

- **Read** `founder/ARBOR-DESIGN.md`, the Typography and Motion sections of `DESIGN.md`, and `founder/GAIA_MULTI_TREE_WEB_ENDGAME_2026-11-14.md` §2 and §5.
- **Read the boards** in `prototype/project/`: `Main.dc.html` (the lens buttons and their two SVG glyphs), `Observatory.dc.html` (the apertures and the presence control) and `Handoff.dc.html`.
- **Characters** follow their canon exactly:
  - Milim: `marketing-tasks/MILIM.md`.
  - Lucy: `LUCY_CANONICAL_CHARACTER_SHEET.md`; Zero state, eyes closed, no eye flare (owner ruling).
  - No new costume, pose, effect or text on either.

## Who does what

| Role | Model | Owns |
|---|---|---|
| Lead | Opus (medium) | Splits the work, checks each piece against its acceptance list, opens the PR, writes the receipt |
| Implementer | Sonnet | R1's state machine, artboards and exports; poster and recording exports for R2 and R3 |
| Implementer | Opus | R1's motion feel (timing, easing, stroke morph); checking R2 and R3 against canon |

## R1 · Lens glyph morph

**Status:** required. It is the signature micro-interaction of the Tree lens.

**Purpose.** When the lens switches, the Yggdrasil glyph's curved branches straighten into Arbor's angular branches, and back.

**Source.** New file `lens-glyph.riv`. Its two idle states must match the prototype's SVG glyphs (`Main.dc.html`: `.ln-ygg` and `.ln-arbor`).

**Machine.**

- States: `ygg_idle`, `arbor_idle`, `to_arbor`, `to_ygg`.
- Input: Boolean `isArbor`, set when a lens button is pressed.

**Motion.**

- 600 ms, expo-out.
- Strokes only.
- Two colour slots, bound at runtime to the accent tokens. No baked colour.

**Sizes.** 18, 24 and 48 px artboards, crisp at 1× and 2×.

**Reduced motion.** The page swaps glyphs instantly. The static SVGs in the prototype are the fallback, so the file needs no reduced-motion state.

**Acceptance.**

- Legible in monochrome at 18 px.
- Endpoints never overshoot.
- Both idles overlay the prototype SVGs within 0.5 px at 48 px.

## R2 · Milim field-note idle

**Status:** reuse; no new art.

**Purpose.** When The Observatory faces the Research room, Milim glances up once, then idles.

**Source.** The approved `milim.riv` in gaia-research (`public/milim`) and its existing state machine.

**Machine.**

- States: `idle`, then `look_up` (one shot when the aperture gets focus), then back to `idle`.
- If the existing machine has no glance, report that. **Do not draw one.** Adding art to `milim.riv` needs its own approval.

**Size.** 96 px tall inside the aperture window, with the poster WebP as fallback.

**Reduced motion.** Poster only.

**Acceptance.**

- Passes MILIM.md's face test at 96 px.
- No added effects or text.

## R3 · Lucy at rest

**Status:** reuse. **Get the owner's approval before starting.**

**Purpose.** A barely moving Zero-state Lucy in the Skill Heaven aperture: hair and ribbon breathing, eyes closed.

**Source.**

- The gaia-research `lucy` Rive source.
- `packages/site/public/lucy-live` in gaia-skill-heaven is the consumer copy; do not edit the consumer copy.

**Machine.** `zero_idle` only, with no trigger.

**Size.** 96 px tall, with the v5 Zero delivery WebP as fallback.

**Reduced motion.** Static image.

**Acceptance.**

- Matches the character sheet's Zero state.
- No eye flare.
- The reflection is never mirrored.

## Delivery

1. **Branch.** Create `design/skill-tree-redesign-rive` off `main`. The `design/` prefix may touch `founder/handovers/`.
2. **Files.** Add them under `founder/handovers/2026-11-20-skill-tree-redesign/deliverables/rive/`:
   - `lens-glyph.riv`
   - poster WebPs for every idle state at 2×
   - one short WebM recording per transition or one-shot, under 2 MB each, for review without a Rive runtime
   - for R2 and R3: a receipt of which existing states were used. Do not copy `milim.riv` or `lucy.riv` here unless a state was added with approval.
3. **Receipt.** Write `deliverables/rive/RECEIPT.md` with, for each request:
   - the file, its SHA-256, artboards, state machine name, states and inputs
   - the acceptance checks with their results
   - anything blocked, and why
4. **PR.** Open one PR into `main` titled `design(redesign): Rive deliverables R1–R3`, with `Refs #2483` in the body.
   - Push after each request, not at the end.
   - Mark it ready. **Do not merge it.**

## Review and stamp

The same gate as images (see `README.md`):

1. **Terra verifies** each deliverable against its acceptance list, using the recordings and posters (and the `.riv` where Terra's harness can play it). Terra comments on the PR with the SHA-256s it checked.
2. **Claude stamps** each verified deliverable by adding a stamp line to `RECEIPT.md`: `Stamped by Claude (redesign design lead) on <date>; Terra verification <link>`.
3. **The founder may veto.** A vetoed piece goes back to the team.

## Done when

- R1 is stamped and not vetoed.
- R2 is stamped, or reported as blocked because the glance state does not exist.
- R3 is stamped, or not started because the owner declined.
- The PR is ready and unmerged, for Claude's final audit.
