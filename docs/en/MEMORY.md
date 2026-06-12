# MEMORY.md — Documentation Agent Diary

---

## 2026-06-12 — Routine 004

**Branch:** `docs/routines/003` (continued — no PR existed when session started)
**Task chosen:** Task 2 — Write about a feature (the evidence and trust model)

### What I did

Checked `docs/routines/003`: 3 Claude commits, no open PR. The MEMORY.md "Merged" note from Routine 003 was premature. Continued on the same branch per the "unmerged → continue" rule.

Reviewed open issues for writing priorities:
- **#646** — Trust model shipped in schema: Evidence Type + Grade now live. Immediate developer need to document the new system.
- **#658** — Verification Workflow (Community Verified, Security Reviewed, Enterprise Ready) depends on the trust model — documenting evidence first unblocks clarity.
- **#654** — RFC on evidence types (beyond arxiv/repo/stars) in progress; acknowledged in the page as planned work.
- **#648** — Trust Score Explanations: frontend should show why a skill got its trust grade; documentation provides the vocabulary before the UI is built.

1. **Created `docs/en/evidence-classes.html`** — comprehensive page on the full evidence and trust model:
   - Intro: why evidence gates stars; the Class system problem
   - Deprecated Evidence Class (C/B/A) — documented with a clear deprecation banner
   - Evidence Type (provenance): `arxiv`, `repo`, `github-stars` — table with what each represents, URL format rules per type
   - Evidence Grade (quality): S/A/B/C = Platinum/Gold/Silver/Bronze — visual trust meter + full table with trust number thresholds
   - Trust Number — internal 0–100 score, not user-facing, canonical term
   - Overall Trust Grade — aggregate, computed at build time, never stored on a node
   - Verification states — `unverified` / `verified` / `disputed` — chip layout with flags and semantics
   - CLI: `gaia dev evidence` with legacy `--class` form and new `--type --grade` form; `--dry-run` best practice
   - Migration guide — Class → Type+Grade approximate mapping with explicit caveats
   - Common pitfalls: Class A ≠ Grade A (main table), `tree/` vs `blob/`, github-stars alone, skipping `--dry-run`

2. **Updated `docs/en/index.html`**:
   - Evidence & Trust card: removed `opacity:0.7` dim, changed badge to `● New`, updated title and description to reflect the full Type+Grade model
   - Footer Docs column: added CLI Reference and Evidence & Trust links
   - Nav version badge: v4.4.0 → v4.7.0
   - Footer version: v4.6.0 → v4.7.0

3. **Updated `docs/en/DOCS.md`** — page 7 marked ✅ Done / Routine 004; Grade color tokens added to the design system section.

### Design decisions

- **Trust meter**: five-segment color bar (S/A/B/C/Ungraded) makes thresholds immediately scannable without reading text.
- **Verification chips**: three-card row instead of a table — the flag + description side-by-side layout reads more naturally for a state model.
- **Deprecated banner**: distinct gray callout with a ⚠ icon — clearly deprecated without removing the content (still needed for migration).
- **Grade badge colors**: S=amber, A=amber-dim, B=purple-100, C=sky-100 — reuse token palette from DOCS.md; no new colors.
- **Common pitfalls as h3 anchors**: findable via sidebar + linkable in issue replies (e.g. linking to `#pitfalls` in #646 discussion).

### Issues informed by this page

- **#646** — evidence-classes.html documents the shipped schema; developers no longer need to reverse-engineer it from commit history.
- **#648** — trust number and overall trust grade sections provide vocabulary for the planned frontend explanation UI.
- **#654** — callout in the Evidence Type section links forward to the RFC so contributors know where to track discussion.
- **#658** — verification states section provides canonical definitions the verification workflow will consume.

### Fact-check sweep (standing habit)

- Nav version badge in index.html was stale at v4.4.0; updated to v4.7.0 (matches release commits in branch history).
- Footer version was at v4.6.0; updated to v4.7.0.
- No other stale content detected in existing pages (install commands, CLI flags, vocabulary still accurate).

### Files created / modified

- `docs/en/evidence-classes.html` ← new
- `docs/en/index.html` ← updated (card live; footer updated; versions corrected)
- `docs/en/DOCS.md` ← updated (page 7 done; grade color tokens added)
- `docs/en/MEMORY.md` ← this entry

### Planned next (Routine 005)

- `docs/en/fusion.html` — skill fusion mechanics: when to fuse, `gaia fuse` workflow, Basic→Extra→Ultimate paths, fusion PR anatomy
- `docs/en/mcp-server.html` — Bond your agent flow; `@gaia-registry/mcp-server` setup; MCP tool inventory

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

### Standing habit — fact-check on every routine

When spare capacity exists at the start or end of any routine, sweep existing pages for stale content:
- Package names and install commands (e.g. `gaia-registry` → `gaia-cli`)
- Version numbers hard-coded in code blocks
- CLI flag names and command signatures (compare against live `gaia --help` output or README)
- Links to sections that may have been renamed or removed
- Vocabulary drift vs CONTEXT.md (banned synonyms, deprecated axes like rarity)

Log every correction found, even minor ones, in the MEMORY.md entry for that routine.

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
