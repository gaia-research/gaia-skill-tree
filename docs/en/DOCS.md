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
| 2 | `getting-started.html` | Getting Started | ✅ Done | 001 |
| 3 | `cli-reference.html` | CLI Reference | Planned | 002 |
| 4 | `skill-hierarchy.html` | Skill Hierarchy | Planned | 002 |
| 5 | `contributing.html` | Contributing | Planned | 003 |
| 6 | `named-skills.html` | Named Skills & Origin | Planned | 003 |
| 7 | `evidence-classes.html` | Evidence Classes | Planned | 004 |
| 8 | `fusion.html` | Skill Fusion | Planned | 004 |
| 9 | `mcp-server.html` | MCP Server | Planned | 005 |
| 10 | `faq.html` | FAQ | Planned | 005 |

---

## Design System

Inherits from `docs/css/tokens.css` and `docs/css/styles.css`.
All pages link `../css/tokens.css`, `../css/styles.css`.

Fonts: EB Garamond (display headings), Bricolage Grotesque (body), JetBrains Mono (code).
Background: `#030712` (`--bg`). Surface: `#0f172a` (`--surface`). Border: `#1e293b`.

Color vocabulary:
- Basic tier: `--tier-basic` `#38bdf8`
- Extra tier: `--tier-extra` `#c084fc`
- Unique tier: `--tier-unique` `#7c3aed`
- Ultimate tier: `--tier-ultimate` `#f59e0b`

Rank colors (0★ → 6★): slate → sky-blue → teal → violet → fuchsia → amber → amber-bright.

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
4. Footer: version number + link back to registry

---

## Writing Voice

Half-Merged tone: precise primary labels, minimal ceremony.
Documentation voice — never pure marketing voice, never "SaaS hero-metric dashboard" prose.
One clear sentence per concept. Code examples for everything.
