# DOCS.md — Gaia Documentation Information Architecture

Maintained by the technical documentation agent (docs/routines/).
All docs live under `docs/en/`. Never generate or modify files outside this directory.

---

## Audience

Primary: AI agent developers using Claude Code, Codex, Cursor, Devin, and similar
tool-calling frameworks. Technically fluent. Distrust hype. Respond to evidence.

Secondary: Open-source contributors wanting to claim a Named Skill.

---

## Page Map

Status reflects current truth only — the per-routine edit history lives in
`MEMORY.md`, not here; the Routine column is the pointer.

| # | File | Title | Status | Routine |
|---|------|--------|--------|---------|
| 1 | `index.html` | Docs Home | ✅ Current. Tier/MCP/Fusion cards accurate; nav version chip self-updates off `window.GAIA_VERSION`, build-stamped every release. | 001, 017, 018, 025, 027, 051, 057 |
| 2 | `getting-started.html` | Getting Started | ✅ Current. Yggdrasil II Type/Branch taxonomy throughout. | 001, 017, 018, 025, 042, editor-055wk |
| 3 | `cli-reference.html` | CLI Reference | ✅ Current. All mutating `gaia dev` verbs (incl. `dev timeline-resort`) + `gaia steward` suite documented, including the current `full run`, `record`, `abandon`, and `status` contracts; `dev add --named` row covers `--contributor`/`--generic-ref` and the lowercase-only contributor rule. | 002, 017, 018, 025, 034, 039, 040, 041, editor-047wk, editor-053wk, 053, 054, editor-055wk, 062, editor-063wk, 064 |
| 4 | `skill-hierarchy.html` | Skill Hierarchy | ✅ Current. Type/Branch model throughout (closes #1479). | 002, 018, 025, 028, editor-026wk, editor-055wk |
| 5 | `contributing.html` | Contributing | ✅ Current. `dev evidence`/`dev calibrate` examples match live CLI. | 003, 017, 018, 025, 036, 043, editor-055wk |
| 6 | `named-skills.html` | Named Skills & Origin | ✅ Current. Claiming walkthrough is CLI-only (`gaia dev add --named`) end to end — no hand-edited frontmatter, `calibrate`/`evidence` target the `contributor/slug` id. | 003, 017, 018, 025, 038, editor-055wk, editor-056wk |
| 7 | `evidence-classes.html` | Evidence & Trust | ✅ Current. Evidence Type/Grade axis distinct from deprecated Evidence Class; `npm-downloads`/`engagement` types documented. | 004, 017, 018, 025, 035, 043, 047, 050, 052, 058 |
| 8 | `fusion.html` | Skill Fusion | ✅ Current. Type/Branch model throughout; Fusion Score explainer present. | 004, 017, 018, 025, 029, editor-026wk, 048, 049, editor-055wk |
| 9 | `mcp-server.html` | MCP Server | ✅ Current. Documents the `skill-heaven` plugin's `summon` tool; standalone Gaia MCP noted as decommissioned. | 005, 017, 018, 025, 045, editor-055wk |
| 10 | `faq.html` | FAQ | ✅ Current. Tier/Branch and Evidence Type/Grade vocabulary match CONTEXT.md. | 005, 017, 018, 025, 026, 042, editor-055wk |
| 11 | `share-bundles.html` | Share Bundles | ✅ Current. `gaia share` Flags table complete (`-o/--output`); no fictional `--auto` flag; nav chip self-updates via `id="ver"`. | 006, 018, 025, 038, 056, 059, editor-056wk |
| 12 | `timeline-audit.html` | Timeline Audit & Repair | ✅ Current. `dev validate`'s Trust Magnitude Consistency Gate documented; `dev timeline --previous-value/--new-value` documented; Reclassification card correctly attributes `installable` to `dev update-named`, not `dev reclassify`. | 008, 018, 025, 044, editor-055wk, 060 |
| 13 | `manual-curation-pipeline.html` | Manual Curation Pipeline | ✅ Current. CTA table's named-implementation row is the real `gaia dev add --named --contributor ... --generic-ref ...` invocation (no fictional `gaia dev named`/`gaia dev discover`). | 030, 031, 032, 033, 037, 046, editor-055wk, 061 |

---

## Design System

Inherits from `docs/css/tokens.css` and `docs/css/styles.css`.
All pages link `../css/tokens.css`, `../css/styles.css`, then **`docs-en-shell.css`** (same directory).

### Fixed-nav clearance (`docs-en-shell.css`)

The site-wide nav is `position: fixed` (~58px). Global `styles.css` hides the legacy in-page `.docs-nav` when `#site-nav` is present but does not offset content, so titles would sit under the bar.

`docs-en-shell.css` is the modular fix for `/en` only (no edits outside this folder):

| Token | Default | Role |
|---|---|---|
| `--docs-en-site-nav-height` | `3.625rem` | Sticky sidebar / scroll-margin baseline |
| `--docs-en-nav-clearance` | `5rem` | Top clearance for content shells (fixed-nav ladder base) |

Rules target body-child shells: `.page-layout`, `.docs-layout`, and index `.docs-hero`. New pages under `docs/en/` must load this sheet after `styles.css`.

### Typography and color

Keep the existing display, body, and mono font families from the committed
tokens. Use the font and color tokens rather than overriding their values.
Do not add fonts, hardcoded color palettes, glass effects, or decorative
terminal chrome.

Use `--bg`, `--surface`, `--border`, and `--text` for reference components. Normal
text needs at least 4.5:1 contrast. Aim for 65 to 75 characters per prose line
where space permits. Keep code distinct from prose without shrinking either to
fit a narrow column.

Type colors are `--tier-basic` and `--tier-fusion`. Star colors use `--rank-N` and
`--rank-N-unique`. Do not use retired structural-tier tokens or repurpose rank
colors as arbitrary decoration.

### Progressive disclosure for command references

The default view is a compact index, not a wall of syntax:

- Keep a short command or flag name and one short purpose visible in each row.
- Keep safety limits visible in the summary or a note above the index. Existing
  critical warnings must not disappear into a tooltip or closed disclosure.
- Put complete syntax, defaults, and extended explanations behind native
  `details` / `summary` controls. Support click, tap, and keyboard activation.
  Several entries may stay open for comparison.
- On mobile, put the name and disclosure chevron on the first line and the
  purpose below. Hide the repeated Details label on compact screens instead
  of squeezing or fragmenting identifiers. Use one full-width explanation when expanded, not three narrow
  columns or repeated all-caps field labels. New breakpoints are mobile-first.
- Preserve every authored option, argument, default, link, explanation, and
  example. An ellipsis is acceptable in a short overview only when the complete
  text is available in the same disclosure. Never clip or line-clamp the detail.
- Use simple row dividers, visible focus rings, and targets at least 44px high.
  Avoid nested cards, hover-only information, and motion that delays reading.
- Do not shrink fonts or break identifiers into character fragments to make a
  layout pass. Syntax may wrap at spaces; unusually long tokens may scroll
  inside their code pane, never off the page.

`cli-reference.html` progressively enhances the authored `.flag-table` rows into
`.reference-entry` disclosures. The original tables remain the no-JavaScript
and print fallback. Keep table cells authoritative. Use `data-summary` on a row
when its first sentence is too long or misses an important safety boundary.

### Copy controls and notes

Reuse the shared `ui.js` copy utilities (`copyToClipboard`, `gaiaFlashCopied`)
for syntax references and example blocks. Keep the shared icon helper loaded
with the correct nested-page sprite path.

Reference entries and example blocks serve distinct copy needs:

- **Authored example blocks:**
  - Provide whole-block copy in the example block's label (`.example-label`),
    copying all authored commands, comments, and structure together.
  - Provide functional per-line Bash copy for independently runnable command
    lines. Each line-copy control copies the exact intended shell command
    without prompt glyphs (`$`, `>`), UI labels, formatting whitespace, or
    unrelated lines. Multi-line commands with line continuations (`\`) must
    preserve the continuation syntax intact. Inline comments are stripped
    from the runnable line copy.
- **Reference disclosures and syntax panes:**
  - Retain complete terminal flag semantics in reference entries: flag names,
    argument and value forms, positional context, defaults, and combinations
    must remain accurately represented.
  - Never manufacture a standalone runnable command by joining a command prefix
    to a flag cell: required subcommands and arguments can be lost or falsified.
  - The syntax copy control in a reference entry disclosure copies the exact
    descriptive syntax specification fragment (e.g. `--user <handle>` or
    `full run [--observe | --triage]`), clearly distinguished from runnable
    Bash lines.
  - Do not restore per-flag mini-terminal windows.
- **Accessibility and responsiveness:**
  - Copy controls must use native `<button type="button">` elements with
    explicit, contextual `aria-label` and `title` attributes (e.g.
    `Copy all examples`, `Copy command: gaia init`, `Copy syntax for full run`).
  - Support mouse click, tap, and keyboard activation (Tab focus, Enter/Space).
  - Provide visible copy feedback by flashing the checkmark icon and `.copied`
    class for 1600ms.
  - Ensure all controls meet minimum 44px touch targets without causing
    horizontal overflow across viewports from 320px to 1440px.

Keep existing non-critical notes in `.callout.info` and critical requirements in
`.callout.warn` / `.callout.danger`. Place them below the command description,
before the reference entries and examples. Tooltips may supplement brief,
non-essential explanations, but must not be the only way to obtain information.

---

## Vocabulary Rules (from CONTEXT.md)

- **Yggdrasil II (ratified 2026-07-07) is current** — see `CONTEXT.md` § Taxonomy v6 before writing tier/rank copy. The legacy Yggdrasil I four-tier taxonomy (Basic ○ / Extra ◇ / Unique ◉ / Ultimate ◆ as *structural* categories) is retired, replaced by a Type axis (`basic`/`fusion`, starless only) + Branch axis (`standard`/`unique`/`suite`, named only, computed from `suiteComponents`). Issue #1479 (migrate `skill-hierarchy.html` and `fusion.html` off the retired four-tier framing) closed 2026-08-15 — both pages now teach the Type/Branch model throughout (see Page Map rows 4, 8). No page still teaches the retired structural framing.
- Stars axis: 0★ → 6★. Never call it "rank" or "level" alone.
- Rank names (Yggdrasil II, current): Unawakened(0★), Awakened(1★), Named(2★), Evolved(3★), then branch-qualified — **Extra** (4★ Suite) / **Unique** (4★ Unique branch), **Ultimate** (5★ Suite) / **Unique Ultimate** (5★ Unique branch), **Apex** (6★ Suite) / **Unique Impossible** (6★ Unique branch). "Hardened" (4★), "Transcendent" (5★), and "Transcendent ★" (6★) are deprecated Yggdrasil I names — never use them.
- Fusion: the act of combining two or more skills into one. Never call it "merge" or "compose" in user-facing copy (`gaia dev merge` is a real CLI verb — fine in command examples, just not as the concept name).
- Named Skill: a skill claimed by a real contributor with Grade C (Bronze) evidence or better.
- Evidence Grade (current, S/A/B/C → Platinum/Gold/Silver/Bronze): the quality axis. Evidence Type (arxiv, repo-own, github-stars-own, etc.): the provenance axis. Evidence Class (deprecated, letters A/B/C): the legacy single axis these two replaced — never conflate Class A/B with Grade A/B.
- Do NOT mention rarity (deprecated axis).
- There is no `gaia promote` command (retired under Yggdrasil II — "No self-promote"). The player-facing flow is `gaia scan` → `gaia push` (proposes to canon; curation assigns rank) or `gaia propose <skillId>` (claims one specific skill as a Named Skill). Never document `gaia promote`, `--all`, `--unique`, or `--name` as real flags — they don't exist on any current command.

---

## Section Structure per Page

Every doc page includes:
1. Top nav: `← Back to Atlas` + page title breadcrumb
2. Left sidebar (on wide viewports): section outline with anchor links
3. Main content: section headers (h2/h3), code blocks, callout boxes
4. Table of Contents: For longer or reference-style documents, place a compact, scannable section outline after the introduction. Avoid a second grid of decorative cards.
5. Footer: version number + link back to registry

---

## Writing Voice & Readability

- **Tone**: Half-Merged tone with precise primary labels and minimal ceremony. No marketing fluff or complex buzzwords.
- **Readability**: Target a **Grade 7 English level**. Use short, direct sentences that are easy to read and understand.
- **Commanding Style**: Address the developer directly with commanding directives (e.g., "Use commands correctly", "Check your permissions") rather than passive descriptions.
- **Precision**: One clear sentence per concept. Provide code examples for everything.
