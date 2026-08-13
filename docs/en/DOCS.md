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

| # | File | Title | Status | Routine |
|---|------|--------|--------|---------|
| 1 | `index.html` | Docs Home | ✅ Done (tier-card blurbs fixed 027) | 001, 017, 018, 025, 027 |
| 2 | `getting-started.html` | Getting Started | ✅ Done (updated 025) | 001, 017, 018, 025 |
| 3 | `cli-reference.html` | CLI Reference | ✅ Done (updated 025) | 002, 017, 018, 025 |
| 4 | `skill-hierarchy.html` | Skill Hierarchy | ⚠ Rank names fixed (025); Type/Branch tier-card diagram fixed (028); Fusion section diagram still pre-Yggdrasil-II — see #1479 | 002, 018, 025, 028 |
| 5 | `contributing.html` | Contributing | ✅ Done (updated 025) | 003, 017, 018, 025 |
| 6 | `named-skills.html` | Named Skills & Origin | ✅ Done (updated 025) | 003, 017, 018, 025 |
| 7 | `evidence-classes.html` | Evidence & Trust | ✅ Done (updated 025) | 004, 017, 018, 025 |
| 8 | `fusion.html` | Skill Fusion | ⚠ Version-synced only (025); tier framing still pre-Yggdrasil-II — see #1479 | 004, 017, 018, 025 |
| 9 | `mcp-server.html` | MCP Server | ⚠ Disclosure banner added (025); tool list documents a deleted prototype — see #1478 | 005, 017, 018, 025 |
| 10 | `faq.html` | FAQ | ✅ Done (tier/branch FAQ fixed 026) | 005, 017, 018, 025, 026 |
| 11 | `share-bundles.html` | Share Bundles | ✅ Done (updated 025) | 006, 018, 025 |
| 12 | `timeline-audit.html` | Timeline Audit & Repair | ✅ Done (updated 025) | 008, 018, 025 |
| 13 | `manual-curation-pipeline.html` | Manual Curation Pipeline | ✅ Done | — |

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

Fonts: EB Garamond (display headings), Bricolage Grotesque (body), JetBrains Mono (code).
Background: `#030712` (`--bg`). Surface: `#0f172a` (`--surface`). Border: `#1e293b`.
Text colors: Main content headings, introductions (`.page-lead`), section descriptions (`.section-desc`), command summaries (`.cmd-desc`), and callout text must use a high-contrast white font (`#ffffff`) for maximum accessibility.

Color vocabulary:
- Basic tier: `--tier-basic` `#38bdf8`
- Unique tier: `--tier-unique` `#7c3aed`
- 4★ rank: `--rank-4` `#e879f9`
- 5★ rank: `--rank-5` `#fbbf24`

Rank colors (0★ → 6★): slate → sky-blue → teal → violet → fuchsia → amber → amber-bright.

Callouts & Notes Branding:
- Keep note styles simple using two brand categories:
  - **Non-critical (`.callout.info`)**: Colored **Blue** (using `#38bdf8` accent) with white text. Used for normal notes and background context.
  - **Critical (`.callout.warn`, `.callout.danger`)**: Colored **Red** (using `#ef4444` accent) with white text, and prefixed automatically with a warning icon (`⚠️ `). Used for breaking behaviors, strict requirements, or crucial gaps.
- Callout placement: Always locate notes/callouts directly below the command body description, preceding tables and examples.

Interactive & Copy UI:
- **Flag Tables**: Flag columns (`td:first-child`) stack the flag label and an interactive terminal copy window vertically using a column flexbox.
- **Auto-sizing**: Let the flag column width auto-size naturally based on the content (flag label and mini-terminal length) without unnecessary blank padding.
- **Description Column constraint**: Limit flag description cells (`td:nth-child(2)`) to `max-width: 420px;` to prevent overly long line lengths on widescreen monitors.
- **Mini-Terminal Copy Windows**: Render a miniature macOS-style terminal window (`.mini-terminal-copy`) for every flag in command reference tables. On hover, the window dots light up, and clicking the window copies the full command invocation (prefix + flag) to the clipboard, switching the icon in the top right to a green checkmark as success feedback.
- **Copy Buttons**: Embed floating copy buttons in the upper-right corner of code example blocks (`.copy-btn`) to copy raw command snippets.

---

## Vocabulary Rules (from CONTEXT.md)

- **Yggdrasil II (ratified 2026-07-07) is current** — see `CONTEXT.md` § Taxonomy v6 before writing tier/rank copy. The legacy Yggdrasil I four-tier taxonomy (Basic ○ / Extra ◇ / Unique ◉ / Ultimate ◆ as *structural* categories) is retired, replaced by a Type axis (`basic`/`fusion`, starless only) + Branch axis (`standard`/`unique`/`suite`, named only, computed from `suiteComponents`). `docs/en/skill-hierarchy.html` and `fusion.html` still teach the retired model in full — tracked in issue #1479; don't copy their tier framing into new pages until that lands.
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
4. Table of Contents: For longer or reference-style documents, insert a visual Table of Contents grid immediately after the introduction/lead section.
5. Footer: version number + link back to registry

---

## Writing Voice & Readability

- **Tone**: Half-Merged tone with precise primary labels and minimal ceremony. No marketing fluff or complex buzzwords.
- **Readability**: Target a **Grade 7 English level**. Use short, direct sentences that are easy to read and understand.
- **Commanding Style**: Address the developer directly with commanding directives (e.g., "Use commands correctly", "Check your permissions") rather than passive descriptions.
- **Precision**: One clear sentence per concept. Provide code examples for everything.
