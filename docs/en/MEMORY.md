# MEMORY.md — Documentation Agent Diary

---

## 2026-06-10 — Routine 001

**Branch:** `docs/routines/001`
**Task chosen:** Getting Started (Task 1 — maintain core pages; Task 2 — CLI feature)

### What I did

Bootstrapped the entire `docs/en/` documentation layer from scratch. No prior docs existed.

1. **Read** `DESIGN.md`, `CONTEXT.md`, `PRODUCT.md`, `DEV.md` to internalize vocabulary,
   color tokens, and design principles.

2. **Reviewed open issues** (#624, #637, #638, #642) to identify user pain points.
   Primary friction: CLI onboarding confusion — especially `gaia init` / `gaia scan`
   behavior outside a Git repo, and the local-first design being non-obvious to new users.

3. **Created `DOCS.md`** — information architecture, page map (10 planned pages), design
   system reference, vocabulary rules, per-page structure contract.

4. **Created `docs/en/index.html`** — documentation hub/landing page. Card grid of all
   planned pages, quickstart code block, consistent nav with the Atlas.

5. **Created `docs/en/getting-started.html`** — full Getting Started guide covering:
   - Prerequisites (Python, Git repo requirement)
   - Three install options (pip, pipx, source)
   - `gaia init --user` with notes on the `whoami` / authorization check
   - `gaia scan` — what the scanner looks for, the 24h stale-candidate caveat
   - `gaia promote` — slash-prefixed skill IDs, timeline entries
   - `gaia tree` and `gaia graph` — local-first design explained
   - `gaia push --dry-run` — always dry-run first warning
   - Core concepts table: four tiers (Basic/Extra/Unique/Ultimate), stars axis (0★–6★),
     local-first design, Named Skills
   - Non-repo environments section (directly addressing issue #624)

### Design decisions

- Inherited `--bg`, `--surface`, `--border` variables from `tokens.css` + `styles.css`.
- Used EB Garamond for h1/h2, Bricolage Grotesque for body, JetBrains Mono for code.
- Sidebar with scroll-spy active link highlighting on `getting-started.html`.
- Tier pills use exact token hex values (not hardcoded) to respect the design spec.
- All vocabulary follows `CONTEXT.md` strictly: "stars" not "rank", "fusion" not "merge",
  no rarity references anywhere.

### Issues noted

- Issue #624 (`gaia init` outside a repo gives false hope) — addressed directly in the
  "Non-repo environments" section with a clear callout.
- Issue #637 (local-first defaults not obvious) — the "Core concepts — Local-first design"
  section explains the `--canon` flag pattern.

### Files created

- `docs/en/DOCS.md`
- `docs/en/MEMORY.md` (this file)
- `docs/en/index.html`
- `docs/en/getting-started.html`

### Planned next (Routine 002)

- `docs/en/cli-reference.html` — full command reference table
- `docs/en/skill-hierarchy.html` — tier / fusion / stars explainer with diagrams

---

## 2026-06-10 — Routine 002

**Branch:** `docs/routines/002`
**Task chosen:** Task 2 — Write about a feature (CLI Reference) + Task 1 companion (Skill Hierarchy)

### What I did

Routine 001 was confirmed merged (PR #643). Created `docs/routines/002` from `origin/main`.

Reviewed open issues to identify writing priorities:
- Issue #644 — docs/en/ is new, needs discoverability (website nav / footer / README)
- Issue #637 — local-first design is non-obvious to users; `--canon` flag pattern underdocumented
- Issue #254 — Named vs. unnamed skill lifecycle not clearly documented

Both pages directly address #637 and #254.

1. **Created `docs/en/cli-reference.html`** — complete reference for all 20+ `gaia` commands
   organized into five groups: Player workflow, Discovery, Named skills, System, Registry dev.
   Every command gets: synopsis, description, flag table with defaults, and shell examples.
   Verifier-gated commands are clearly badged (◇ verifier). Known CLI gap (timeline --user)
   called out inline. `--canon` toggle documented on every applicable command.

2. **Created `docs/en/skill-hierarchy.html`** — full explainer of the two-axis model
   (tier × stars), covering:
   - Four-tier overview with visual cards (Basic ○ / Extra ◇ / Unique ◉ / Ultimate ◆)
   - Stars axis 0★–6★ with rank name table and color chips matching DESIGN.md tokens
   - Evidence classes (C/B/A) with CLI examples
   - Fusion diagram showing Basic→Extra and Extra→Ultimate paths, and Basic→Unique promotion
   - Named Skill lifecycle as a five-step numbered explainer
   - Generic/Starless distinction with visual before/after
   - Local-first design explained with --canon toggle code examples

3. **Updated `docs/en/index.html`** — promoted CLI Reference and Skill Hierarchy cards
   from "Coming soon" to "● New" state; removed opacity:0.7 dim.

4. **Updated `docs/en/DOCS.md`** — marked pages 3 and 4 as ✅ Done / Routine 002.

### Design decisions

- Both pages follow the exact same layout contract as `getting-started.html`:
  sticky nav, sidebar scroll-spy, main content, footer. CSS is self-contained per page.
- Tier card glyphs (○ ◇ ◉ ◆) and rank colors use token hex values from DOCS.md design system.
- Fusion diagram uses colored skill pills (blue/purple/violet/amber) to make tier
  immediately scannable without tooltips.
- Verifier gate badge (◇ verifier) vs open badge (● open) distinguishes mutating commands
  from read-only ones at a glance.
- Named CLI gaps documented inline (timeline --user caveat) rather than buried in a footnote.

### Issues addressed

- Issue #637 (local-first defaults) — `--canon` flag documented on every applicable command;
  Local-first design section in skill-hierarchy.html explains the design intent.
- Issue #254 (Named vs Unnamed lifecycle) — Named Skill section in skill-hierarchy.html
  traces the full five-step lifecycle from `gaia scan` to 4★ Verifier threshold.

### Files created / modified

- `docs/en/cli-reference.html` ← new
- `docs/en/skill-hierarchy.html` ← new
- `docs/en/index.html` ← updated (CLI Reference + Skill Hierarchy cards now live)
- `docs/en/DOCS.md` ← updated (pages 3–4 marked done)
- `docs/en/MEMORY.md` ← this entry

### Planned next (Routine 003)

- `docs/en/contributing.html` — CONTRIBUTING.md distilled for the web
- `docs/en/named-skills.html` — deep dive into claiming origin, evidence submission, and the naming PR flow
