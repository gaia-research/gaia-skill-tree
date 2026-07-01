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
| 1 | `index.html` | Docs Home | ✅ Done | 001 |
| 2 | `getting-started.html` | Getting Started | ✅ Done (updated 012) | 001 |
| 3 | `cli-reference.html` | CLI Reference | ✅ Done (updated 012) | 002 |
| 4 | `skill-hierarchy.html` | Skill Hierarchy | ✅ Done | 002 |
| 5 | `contributing.html` | Contributing | ✅ Done | 003 |
| 6 | `named-skills.html` | Named Skills & Origin | ✅ Done | 003 |
| 7 | `evidence-classes.html` | Evidence & Trust | ✅ Done | 004 |
| 8 | `fusion.html` | Skill Fusion | ✅ Done | 004 |
| 9 | `mcp-server.html` | MCP Server | ✅ Done (updated 013) | 005 |
| 10 | `faq.html` | FAQ | ✅ Done | 005 |
| 11 | `share-bundles.html` | Share Bundles | ✅ Done | 006 |
| 12 | `timeline-audit.html` | Timeline Audit & Repair | ✅ Done | 008 |

---

## Design System

Inherits from `docs/css/tokens.css` and `docs/css/styles.css`.
All pages link `../css/tokens.css`, `../css/styles.css`.

Fonts: EB Garamond (display headings), Bricolage Grotesque (body), JetBrains Mono (code).
Background: `#030712` (`--bg`). Surface: `#0f172a` (`--surface`). Border: `#1e293b`.
Text colors: Main content headings, introductions (`.page-lead`), section descriptions (`.section-desc`), command summaries (`.cmd-desc`), and callout text must use a high-contrast white font (`#ffffff`) for maximum accessibility.

Color vocabulary:
- Basic tier: `--tier-basic` `#38bdf8`
- Extra tier: `--tier-extra` `#c084fc`
- Unique tier: `--tier-unique` `#7c3aed`
- Ultimate tier: `--tier-ultimate` `#f59e0b`

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

- Tier taxonomy: Basic Skill (○), Extra Skill (◇), Unique Skill (◉), Ultimate Skill (◆)
- Stars axis: 0★ → 6★. Never call it "rank" or "level" alone.
- Rank names: Unawakened, Awakened, Named, Evolved, Hardened, Transcendent, Transcendent ★
- Fusion: combining skills. Never "merge", "combine", "compose".
- Named Skill: a skill claimed by a real contributor with Class C evidence or better.
- Evidence Class: C (first sighting), B (reproducible), A (battle-tested, peer-reviewed).
- Do NOT mention rarity (deprecated axis).

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
