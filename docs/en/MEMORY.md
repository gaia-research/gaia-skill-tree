# MEMORY.md — Documentation Agent Diary

---

## 2026-06-12 — Consolidation (routines 003–005)

**Branch:** `docs/routines/005` (single converging PR)

PR #668 (routines 003–004) had forked from `v4.7.0` *before* the same routines
independently landed on `main` (commits `d608b7b`, `ca08170`) and before the
v4.7.1→v4.7.6 bumps, so it had drifted: its `contributing.html`,
`named-skills.html`, and `getting-started.html` were byte-identical to main
(no-ops), it would have **deleted** `fusion.html`, and it downgraded version
strings to v4.7.0.

The only substantive contribution of #668 was the **`evidence-classes.html`
rewrite** — recast as *Evidence & Trust*, with the Evidence Class deprecation
banner, the Type + Grade two-axis model, the trust meter, and the Class→Type+Grade
migration guide. Trust is the accurate forward model (Class is being deprecated),
so that rewrite was adopted here on top of #671's clean routine-005 base:

- Adopted `docs/en/evidence-classes.html` from #668; bumped its nav version
  v4.7.0 → v4.7.6.
- Renamed the Docs Home card and footer link "Evidence Classes" → "Evidence & Trust".
- `DOCS.md` page 7 retitled to "Evidence & Trust".
- **Kept** `fusion.html` and all v4.7.6 version strings (no drift, no feature loss).

PR #668 superseded by this branch and closed.

---

## 2026-06-12 — Routine 005

**Branch:** `docs/routines/005`
**Task chosen:** Task 2 (write about a feature — MCP Server) + Task 1 (maintain existing pages — FAQ) + Task 4 (recent PR update — PR #670 scanner optimization)

### Trigger

PR #670 (`feat/bolt-optimize-skill-matching`) merged at 13:19 UTC. The PR caches `_word_set`
computation per canonical skill in an external function attribute (`match_skill_to_canonical._word_cache`)
instead of mutating the data dict in-place (which would cause JSON serialization errors). Matching
200 custom skills against 2 000 canonical skills dropped from ~3.5 s to ~0.6 s (~6×).

Routine 004 confirmed merged (PR #665). Created `docs/routines/005` from `origin/main`.

### What I did

1. **Created `docs/en/mcp-server.html`** — comprehensive MCP server integration guide:
   - Overview: what the server does, stateless+read-heavy design, ETag-cached registry fetch
   - One-liner quickstart callout for Claude Code
   - Platform-tab installation UI (Claude Code, Claude Desktop, Cursor, VS Code, Gemini, Other)
     — all configs with annotated JSON; each tab shows the platform-specific file path
   - GAIA_USER-in-env warning callout (cross-links to known-issues section)
   - Tools section: five tool cards (gaia_lookup, gaia_suggest, gaia_scan_context, gaia_my_tree,
     gaia_propose) with full parameter tables, required/optional badges
   - Resources section: gaia://registry and gaia://tree/{username} with format notes
   - Configuration priority table: GAIA_USER env → project config → global config
   - Example prompts: seven copy-paste prompt strings for common agent tasks
   - Architecture diagram: annotated src/ tree with highlighted entry points per tool
   - Known issues: issue #212 (CWD-based identity resolution) with workaround and fix

2. **Created `docs/en/faq.html`** — accordion FAQ across five categories:
   - CLI & Setup (4 items): gaia init outside a repo (#624), gaia tree shows canonical not local (#637),
     checking authorization via `gaia whoami`, duplicate push proposals (#611)
   - Skills & Hierarchy (4 items): tier differences (Basic/Extra/Unique/Ultimate with colored pills),
     rank name table (0★–6★), Named vs generic skills, Evidence Class vs Evidence Grade warning
   - Scan & Promote (3 items): how gaia scan works (includes PR #670 word-set cache note),
     candidate expiry and fix, gaia push vs gaia promote distinction
   - MCP Server (3 items): identity resolution CWD issue (#212), whether CLI is required,
     GITHUB_TOKEN scope
   - Contributing (4 items): claiming a Named Skill step-by-step, CLI-only policy for registry edits,
     installing a Named Skill from another contributor, branch naming table

3. **Updated `docs/en/index.html`**:
   - What's New banner: v4.7.1 → v4.7.6, content updated to PR #670 scanner speedup (6×)
   - MCP Server card: removed `opacity:0.7`, changed badge from "○ Coming soon" to "● New"
   - FAQ card: same treatment
   - Nav version chip: v4.7.1 → v4.7.6
   - Footer version: v4.7.1 → v4.7.6

4. **Updated `docs/en/DOCS.md`** — marked pages 9 and 10 as ✅ Done / Routine 005.

### Design decisions

- `mcp-server.html` introduces: platform-tab component (JS-driven, no JS framework), tool-card
  component (dark surface with per-param rows), architecture diagram (monospace block with colored spans).
- `faq.html` introduces: accordion FAQ (CSS max-height transition + aria-expanded), category header
  labels, and inline tier pills inside answer text for quick visual scanning.
- PR #670 surfaced in two places: the What's New banner (index.html) and the FAQ answer for
  "How does gaia scan decide what skills I have?" — both reference the 6× improvement figure
  and the JSON serialization safety rationale.
- All vocabulary cross-checked: "fusion" not "merge", no rarity references, "stars" not "rank".

### Issues referenced

- Issue #624 (gaia init outside repo) — documented in FAQ with workaround and upstream fix note
- Issue #637 (local-first defaults) — FAQ explains --custom flag, links to planned --canon flip
- Issue #611 (duplicate push proposals) — FAQ documents workaround, links to planned --update flag
- Issue #212 (MCP identity CWD) — documented in mcp-server.html known-issues + FAQ MCP section
- PR #670 (scanner word-set cache) — What's New banner + FAQ scan mechanics section

### Files created / modified

- `docs/en/mcp-server.html` ← new
- `docs/en/faq.html` ← new
- `docs/en/index.html` ← updated (What's New banner, two cards promoted, version bumped)
- `docs/en/DOCS.md` ← updated (pages 9–10 marked done)
- `docs/en/MEMORY.md` ← this entry

### Planned next (Routine 006)

- Research new page ideas from trends (Task 3): possible candidates —
  Share Bundles guide (`gaia share` / `gaia install <bundle>`), Timeline audit guide, Agent workflows integration
- Maintain existing pages (Task 1): update cli-reference.html to add any new commands since v4.4.0 audit

---

## 2026-06-11 — Routine 004

**Branch:** `docs/routines/004`
**Task chosen:** Task 2 (write about a feature — Evidence Classes + Skill Fusion) + Task 4 (write about recent PR updates — PR #663 semantic search speedup)

### Trigger

PR #663 (`cli/bolt-semantic-search`) merged at 17:27 UTC. The PR optimised
`search_precomputed` in `src/gaia_cli/semantic_search.py` by batching cosine-similarity
calculations into a single NumPy matrix operation, dropping 1 000-item search time
from ~0.63 s to ~0.26 s (~2.5×). A pure-Python fallback (query-norm extracted outside
the loop) was retained for environments without NumPy. Version bumped 4.3.12 → 4.7.1.

Routine 003 confirmed merged (PR #662). Created `docs/routines/004` from `origin/main`.

### What I did

1. **Created `docs/en/evidence-classes.html`** — full evidence system deep-dive:
   - Overview callout: Class letters ≠ Grade letters warning (from CONTEXT.md)
   - Legacy Class system: C (first sighting), B (reproducible), A (battle-tested)
   - Migration path callout: when to use legacy `--class` vs new `--type` + `--grade`
   - Evidence Type: provenance axis (arxiv / repo / github-stars), kebab-case, list-driven
   - Evidence Grade: S / A / B / C × Platinum / Gold / Silver / Bronze
   - Grade cards with trust-number thresholds (S ≥ 90, A ≥ 80, B ≥ 60, C ≥ 40)
   - Trust Numbers section: internal 0–100 score, gradeThresholds meta.json snippet
   - Overall Trust Grade: aggregate, computed at build time, never stored on nodes
   - Verification States: Unverified / Verified (4★+ Verifier) / Disputed — with pill UI
   - Orthogonality callout: verification ≠ grading
   - CLI usage: legacy `--class` and new `--type --grade` examples, `rm-evidence`, `dev list`
   - Stars gate table: 0★–6★ with evidence requirements per level
   - Starless references info callout: effective rank = top named variant

2. **Created `docs/en/fusion.html`** — comprehensive fusion mechanics:
   - Overview: two-axis model (tier vs stars), fusion moves along the tier axis
   - Player-level fusion (`gaia fuse`) vs Registry-level fusion (`gaia dev merge`) distinction upfront
   - Ascension Cycle diagram: Register → Scan → Rank up → Name → **Fuse** → Apex (Fuse step highlighted)
   - Fusion Paths diagram: three canonical paths with colored tier pills
     - Path 1: Basic + Basic → Extra
     - Path 2: Extra + Extra → Extra (complex)
     - Path 3: Extra + Extra → Ultimate
   - Unique Skills callout: depth-only, no fusion path (◉)
   - Prerequisites table: unlocked inputs, recipe existence, fresh scan
   - 24-hour candidate expiry warning
   - `gaia fuse` walkthrough with under-the-hood explanation
   - skill-tree.json output example with fused entry and timeline event
   - Proposing a new fusion: requirements, push workflow, YAML batch snippet
   - Always-dry-run-first callout
   - Registry-level fusion: `gaia dev merge` command, Programmatic-first policy callout
   - Player vs Registry comparison table: 6 dimensions

3. **Updated `docs/en/index.html`**:
   - Added "What's New" banner (v4.7.1) about the semantic search speedup with link to CLI reference
   - Promoted Evidence Classes card: removed `opacity:0.7`, changed badge from "○ Coming soon" to "● New"
   - Promoted Skill Fusion card: same treatment
   - Updated nav version chip: v4.4.0 → v4.7.1
   - Updated footer version: v4.6.0 → v4.7.1
   - Expanded footer Docs column: added CLI Reference, Skill Hierarchy, Contributing, Evidence Classes, Skill Fusion

4. **Updated `docs/en/DOCS.md`** — marked pages 7 and 8 as ✅ Done / Routine 004.

### Design decisions

- Both new pages follow the identical layout contract (sticky nav, sidebar scroll-spy, main content, footer).
- evidence-classes.html introduces: grade cards (4-column grid with per-grade border colors), state pills row, gate table (7 rows 0★–6★).
- fusion.html introduces: fusion diagram with colored tier pills, Ascension Cycle journey bar, prerequisites/comparison tables.
- "What's New" banner on index.html uses a subtle sky-blue tint matching `--tier-basic` — reads as a system notice, not a marketing callout.
- All vocabulary cross-checked against CONTEXT.md: "Evidence Type" (never bare "type"), "Overall Trust Grade" (never stored on node), "Unique Skill" (never "fuses further"), "fusion" (never "merge" or "combine" in user copy).

### Issues addressed

- PR #663 semantic search speedup — documented in index.html "What's New" banner, referencing `gaia skills search` in CLI reference.
- Routine 004 planned pages (DOCS.md pages 7–8) — delivered on schedule.

### Files created / modified

- `docs/en/evidence-classes.html` ← new
- `docs/en/fusion.html` ← new
- `docs/en/index.html` ← updated (What's New banner, two cards promoted, version bumped, footer expanded)
- `docs/en/DOCS.md` ← updated (pages 7–8 marked done)
- `docs/en/MEMORY.md` ← this entry

### Planned next (Routine 005)

- `docs/en/mcp-server.html` — `@gaia-registry/mcp-server` integration guide
- `docs/en/faq.html` — FAQ consolidating the most common user questions from open issues

---

## 2026-06-11 — Routine 003

**Branch:** `docs/routines/003`
**Task chosen:** Task 1 (maintain existing pages — index.html) + Task 2 (write about features — Contributing workflow and Named Skills lifecycle)

### What I did

Routine 002 confirmed merged (PR #660). Created `docs/routines/003` from `origin/main`.

Reviewed open issues for writing priorities:
- Issue #254 — Named vs Unnamed lifecycle not documented (directly addressed by named-skills.html)
- Issue #644 — docs/en/ still needs discoverability (noted; nav integration is a design-scope task for a future routine)
- Issue #71 — Origin vs variant bucket not well explained (addressed in named-skills.html origin bucket section)

1. **Created `docs/en/contributing.html`** — three-path contributor guide:
   - Path A (gaia push): scanner workflow, dry-run warning, push variants
   - Path B (/gaia-curate-chain): six-link pipeline overview with step list
   - Path C (direct CLI meta shifts): all gaia dev commands with --no-build tip
   - Authorization paths table (verifier / override / bootstrap / denied)
   - Source of truth table (what to edit vs what never to touch)
   - Branch naming cheat sheet with copy-paste template
   - PR checklist (8 items including the links.github blob/ format rule)
   - PR title examples
   - Automated maintenance: Auto-Sync, Validation, Transparency Gate, Meta Guard, Monthly Meta Sweep
   - FAQ: four common questions

2. **Created `docs/en/named-skills.html`** — deep dive into Named Skills:
   - Clear distinction between generic (starless) references and Named Skills — directly addresses issue #254
   - Side-by-side compare cards (generic vs named)
   - Origin bucket diagram with role labels (★ origin / variant) — addresses the conceptual gap flagged in issue #71
   - Full five-step lifecycle: 0★ Unawakened → 1★ Awakened → 2★ Named → 3★ Evolved → 4★ Verifier
   - Evidence system: legacy Class (deprecated) vs new Type + Grade (S/A/B/C Platinum/Gold/Silver/Bronze)
   - Claiming walkthrough: step-by-step bash script including naming PR flow
   - Verifier threshold section with gaia whoami example
   - Installability policy: stars determine fate table, URL format pitfalls, wrong key name fixes, suite exemption

3. **Updated `docs/en/index.html`** — Contribute section:
   - Added Contributing card (new, ● New badge)
   - Promoted Named Skills card from "Coming soon" to "● New" state

4. **Updated `docs/en/DOCS.md`** — marked pages 5 and 6 as ✅ Done / Routine 003.

### Design decisions

- Both pages follow the identical layout contract (sticky nav, sidebar scroll-spy, main content, footer).
- contributing.html introduces a three-column path-card component for the workflow picker.
- named-skills.html introduces: compare-panel (generic vs named side-by-side), lifecycle step list with rank badges, evidence grade badge rows, origin bucket diagram (the bucket concept needed its own visual).
- All color tokens use the same hex values as DOCS.md design system — no new colors introduced.
- Deprecated Evidence Class (A/B/C) documented honestly alongside the new Grade (S/A/B/C) system, with an explicit warning box that the letter sets are not equivalent.

### Issues addressed

- Issue #254 (Named vs Unnamed lifecycle) — named-skills.html has a dedicated "Generic references vs Named Skills" section with a side-by-side compare panel.
- Issue #71 (origin vs variant display) — origin bucket diagram explains the bucket model and links to the issue for the upcoming CLI/UI implementation.

### Files created / modified

- `docs/en/contributing.html` ← new
- `docs/en/named-skills.html` ← new
- `docs/en/index.html` ← updated (Contributing card added; Named Skills card promoted to ● New)
- `docs/en/DOCS.md` ← updated (pages 5–6 marked done)
- `docs/en/MEMORY.md` ← this entry

### Planned next (Routine 004)

- `docs/en/evidence-classes.html` — full evidence system explainer (Class → Type + Grade transition, trust numbers, verification states)
- `docs/en/fusion.html` — skill fusion mechanics, gaia fuse workflow, when fusion applies

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
