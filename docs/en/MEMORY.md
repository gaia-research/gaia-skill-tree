# MEMORY.md — Documentation Agent Diary

---

## 2026-07-02 — Routine 014

**Branch:** `docs/routines/014`
**Task chosen:** Release/Changelog Sync (Version bump to v5.9.1)

### Trigger
Routine documentation agent triggered; observed recent version bump to v5.9.1 from repository tags.

### What I did
1. **Synchronized version numbers**: Updated all 12 English documentation HTML files under `docs/en/` to increment `v5.8.2` and `5.8.2` strings to `v5.9.1`. This covers navigation chips, footer versions, script query parameters, and What's New tags.
2. **Sprint B Content Update**: Rewrote the "What's New" banner in `docs/en/index.html` to properly advertise the massive Sprint B Closure features (API Client SDKs, Trending Engine, Hall of Heroes, CLI Preflights).

### Design decisions
- Updated uniformly across all HTML files to ensure consistency.

### Issues informed
- No new open issues with `documentation` label.

### Files created / modified
- `docs/en/MEMORY.md` (modified)
- `docs/en/cli-reference.html` (modified)
- `docs/en/contributing.html` (modified)
- `docs/en/evidence-classes.html` (modified)
- `docs/en/faq.html` (modified)
- `docs/en/fusion.html` (modified)
- `docs/en/getting-started.html` (modified)
- `docs/en/index.html` (modified)
- `docs/en/mcp-server.html` (modified)
- `docs/en/named-skills.html` (modified)
- `docs/en/share-bundles.html` (modified)
- `docs/en/skill-hierarchy.html` (modified)
- `docs/en/timeline-audit.html` (modified)

### Planned next (Routine 015)
- Research: Search for any broken links or HTML structural validation issues across the entire `docs/en/` space.
- Maintain: Audit the newly added CLI/dev features and document in Getting Started.

---

## 2026-07-01 — Routine 013

**Branch:** `docs/routines/013`
**Task chosen:** Version bump to v5.8.2 and document MCP Advisor interfaces and telemetry options.

### Trigger

Audit of the MCP Advisor interfaces and request to document any telemetry options. Repo version bumped to v5.8.2.

### What I did

1. **Documented MCP Advisor Architecture**: Added the "Advisor Architecture" section to `docs/en/mcp-server.html` detailing the unified advisor system and its three concrete modules: `SkillDetector`, `FusionEngine`, and `NoveltyScorer`, all inheriting from `AbstractAdvisor<TResult>`.
2. **Documented Telemetry Policy**: Documented the "Telemetry & Privacy" zero-telemetry policy of the Gaia MCP Server, ensuring users are informed that no usage metrics, analytics, or tracking are collected, and that operations run entirely locally.
3. **Synchronized version numbers**: Updated all 12 English documentation HTML files under `docs/en/` from `v5.6.2` to `v5.8.2` and script query parameters from `?v=5.6.2` to `?v=5.8.2`.
4. **Audited Custom Theme Mobile Layouts**: Performed a layout audit on mobile viewports for `.sidebar` (hidden gracefully via display:none), `.nav-mobile-drawer` and `.docs-nav-mobile-drawer` (open/close handled gracefully), and `.profile-sidebar` (hidden offscreen and animated).

### Design decisions

- Added Jaccard similarity threshold details (0.3) for the `NoveltyScorer` and mapped advisor functionality to the specific taxonomy symbols (Basic Skill ○, Extra Skill ◇, Unique Skill ◉, Ultimate Skill ◆).
- Maintained consistent section and spacing structures in `mcp-server.html` matching existing CSS tokens.

### Issues informed

- Resolves #222

### Files created / modified

- `docs/en/MEMORY.md` (modified)
- `docs/en/mcp-server.html` (modified)
- `docs/en/cli-reference.html` (modified)
- `docs/en/contributing.html` (modified)
- `docs/en/evidence-classes.html` (modified)
- `docs/en/faq.html` (modified)
- `docs/en/fusion.html` (modified)
- `docs/en/getting-started.html` (modified)
- `docs/en/index.html` (modified)
- `docs/en/named-skills.html` (modified)
- `docs/en/share-bundles.html` (modified)
- `docs/en/skill-hierarchy.html` (modified)
- `docs/en/timeline-audit.html` (modified)

### Planned next (Routine 014)

- Research: Search for any broken links or HTML structural validation issues across the entire `docs/en/` space.
- Maintain: Audit the newly added CLI/dev features and document in Getting Started.

---

## 2026-06-27 — Routine 012

**Branch:** `docs/routines/012`
**Task chosen:** Version bump to v5.6.2 and formalize Workspace Mode documentation.

### Trigger

Recent release version bump to v5.6.2 and formalization of Workspace Mode under PR #861.

### What I did

1. **Documented Workspace Mode**: Updated `docs/en/getting-started.html` to document Workspace Mode. Replaced the stale "Non-repo environments" section to explain Workspace Mode fallback behavior, explicit `--workspace` initialisation, local scan/tree/graph availability, and remote push restriction.
2. **Updated CLI command specifications**: Updated `docs/en/cli-reference.html` to document the new `--workspace` flag for `gaia init`, updated warning boxes for `gaia init` and `gaia push`, and updated the `gaia whoami` example output showing `Mode: Repository Mode (or Workspace Mode)`.
3. **Synchronized version numbers**: Updated all 12 English documentation HTML files under `docs/en/` from `v5.1.3` to `v5.6.2` and script query parameters from `?v=5.0.7` to `?v=5.6.2`.
4. **Updated "What's New" Banner**: Highlighted Workspace Mode in the `index.html` What's New banner.
5. **Logged in MEMORY.md & DOCS.md**: Recorded Routine 012 logs.

### Design decisions

- Renamed `#non-repo` section in Getting Started guide to `#workspace-mode` and updated all navigation anchors/links to point to it correctly.
- Maintained consistent macOS-style console mockup syntax and Flexbox layouts in `cli-reference.html` when adding the workspace configuration options.

### Issues informed

- Resolves #624

### Files created / modified

- `docs/en/MEMORY.md` (modified)
- `docs/en/DOCS.md` (modified)
- `docs/en/getting-started.html` (modified)
- `docs/en/cli-reference.html` (modified)
- `docs/en/index.html` (modified)
- `docs/en/share-bundles.html` (modified)
- `docs/en/evidence-classes.html` (modified)
- `docs/en/skill-hierarchy.html` (modified)
- `docs/en/named-skills.html` (modified)
- `docs/en/mcp-server.html` (modified)
- `docs/en/fusion.html` (modified)
- `docs/en/contributing.html` (modified)
- `docs/en/timeline-audit.html` (modified)
- `docs/en/faq.html` (modified)

### Planned next (Routine 013)

- Research: Audit custom theme layouts on mobile screens to ensure the Sidebar active state is hidden gracefully.
- Maintain: Audit the MCP Advisor interfaces and document any telemetry options.

---

## 2026-06-25 — Routine 011

**Branch:** `docs/routines/011`
**Task chosen:** Version bump to v5.1.3, dev command namespace migration in docs, and GitHub issue curation.

### Trigger

Recent release version bump to v5.1.3 and modernization under Epic #780.

### What I did

1. **Updated version references**: Bumped version strings from `v5.0.3` / `v5.0.7` to `v5.1.3` across all 12 English documentation HTML files.
2. **Migrated CLI namespaces**: Updated stale command references in the English docs (`docs/en/`) from deprecated forms (like `gaia validate` and `gaia docs build`) to modern `gaia dev` forms (like `gaia dev validate` and `gaia dev docs`).
3. **Closed Issue #141**: Verified that JSON configurations had already been removed from `README.md` and root `index.html` to keep only the one-liner install command.
4. **Updated MEMORY.md**: Added this diary entry for Routine 011.

### Design decisions

- Standardized mount script versions (`?v=5.1.3`) along with structural document versions to guarantee consistent asset loading across pages.

### Issues informed

- Resolves #141

### Files created / modified

- `docs/en/MEMORY.md` (modified)
- `docs/en/cli-reference.html` (modified)
- `docs/en/contributing.html` (modified)
- `docs/en/evidence-classes.html` (modified)
- `docs/en/faq.html` (modified)
- `docs/en/fusion.html` (modified)
- `docs/en/getting-started.html` (modified)
- `docs/en/index.html` (modified)
- `docs/en/mcp-server.html` (modified)
- `docs/en/named-skills.html` (modified)
- `docs/en/share-bundles.html` (modified)
- `docs/en/skill-hierarchy.html` (modified)
- `docs/en/timeline-audit.html` (modified)
- `docs/en/MISSION.md` (modified)
- `docs/en/NOTES.md` (modified)
- `docs/en/RESOURCES.md` (modified)

### Planned next (Routine 012)

- Research: Search for any remaining undocumented `gaia dev` commands or deprecated CLI options.
- Maintain: Audit the documentation structure for mobile layouts and verify asset load times.

---

## 2026-06-20 — Routine 010

**Branch:** `documentation`
**Task chosen:** Routine version audit and update for English documentation folder (`docs/en/`).

### Trigger

User request / maintainer request to update version numbers to align with the release of v5.1.3.

### What I did

1. **Updated 12 HTML files in `docs/en/`**:
   - Replaced old version references (e.g., `v4.7.12`, `v4.7.7`, `v4.7.6`, `v4.7.1`, `v4.7.0`, `v4.6.0`) with `v5.1.3` / `5.1.3`.
   - Updated files: `cli-reference.html`, `contributing.html`, `evidence-classes.html`, `faq.html`, `fusion.html`, `getting-started.html`, `index.html`, `mcp-server.html`, `named-skills.html`, `share-bundles.html`, `skill-hierarchy.html`, and `timeline-audit.html`.
2. **Updated `docs/en/MEMORY.md`**:
   - Logged this entry as Routine 010.

### Design decisions

- Explicitly performed manual updates to version strings in `docs/en/` files because `scripts/patch_nav_footer.py` and `scripts/build_docs.py` do not process the English docs due to their custom navigation structure.

### Files created / modified

- `docs/en/MEMORY.md` (modified)
- All 12 HTML files in `docs/en/` (modified)

---

## 2026-06-20 — Routine 009

**Branch:** `documentation`
**Task chosen:** Implement terminal copy window UI per flag in every section, update note typography colors, and refine table column widths.

### Trigger

User request to add terminal-style copy window UI for all section flags in `cli-reference.html` and improve text color contrast.

### What I did

1. **Updated `docs/en/cli-reference.html`**:
   - Replaced simple flag text copying with a dynamic generator script that wraps flag text, parses command names, and constructs macOS-style terminal copy mockups (`.mini-terminal-copy`) inside flag cells.
   - Designed interactive mini-terminals: traffic light control dots that light up on hover, custom clipboard copying, and success icon swap states (using inline SVGs for copy and checkmark icons).
   - Configured `.mini-terminal-screen` with flex-wrap and responsive word-wrapping (`white-space: pre-wrap; word-break: break-all`) to keep commands fully visible at a glance.
   - Refined tables by setting `max-width: 420px;` on the flag descriptions to improve widescreen line-length readability.
   - Set all body text, introductions, page lead elements, and callout blocks to high-contrast white font (`#ffffff`) to ensure WCAG compliance.
2. **Updated `docs/en/DOCS.md`**:
   - Incorporated layout positioning constraints, white font accessibility rules, and interactive terminal-copy requirements into the Information Architecture & Design System guidelines.
3. **Updated `docs/en/MEMORY.md`**:
   - Logged this entry as Routine 009.

### Design decisions

- Decided to wrap flags in a `.flag-text` container to allow copying just the flag name when clicking the text itself, while clicking the mini-terminal copies the complete command invocation.
- Allowed tables to size columns automatically to fit contents organically, avoiding awkward blank space on widescreen displays.
- Integrated SVGs natively within the copy widgets instead of external webfonts to reduce layout shifts and guarantee cross-device compatibility.

### Files created / modified

- `docs/en/cli-reference.html` ← updated (mini-terminals, SVGs, style updates, layout overrides)
- `docs/en/DOCS.md` ← updated (design rules, column widths, white text rules)
- `docs/en/MEMORY.md` ← updated (this entry)

---

## 2026-06-14 — Routine 008

**Branch:** `docs/routines/008`
**Task chosen:** Task 2 (write about a feature — Timeline Audit & Repair) + Task 1 (maintain — version string audit)

### Trigger

All docs/routines branches merged. Created `docs/routines/008` from `origin/main` (v4.7.12).
Planned task from Routine 007: research open issues with `documentation` label; identify a new
page topic. Three open documentation issues found (#644 discoverability, #141 MCP copy-paste,
#71 bucket variants). Selected Timeline Audit & Repair guide as the highest-value new page —
explicitly flagged in Routine 007 planned next, and the `/gaia-trace-timeline` skill confirms
this is a common contributor pain point.

### What I did

1. **Created `docs/en/timeline-audit.html`** — comprehensive Timeline Audit & Repair guide:
   - Overview: two-file model (registry node vs user tree), Hero's Journey chart, why drift is silent
   - Drift problem: side-by-side diagram (authoritative registry node vs profile user tree),
     what each file stores, silent-failure callout
   - Detect (step 1): `validate_timelines.py` usage, output format (violations + clean),
     two invariants the gate checks (stale level + missing timeline event)
   - Trace (step 2): `trace_timeline.py <handle>/<slug>` dry-run, example output,
     `(from registry node)` vs `(reconciled)` event labels, git log cross-reference tip
   - Apply (step 3): `--apply` flag, `GAIA_OPERATOR_OVERRIDE=1`, three operations the script
     performs (append events, set level, rebuild levelHistory)
   - Manual CLI path: `gaia dev timeline --user` syntax, warning that it omits
     `previousValue`/`newValue` so rank chart stays flat — prefer `trace_timeline.py`
   - Known CLI gaps: four-row table (missing --user default, no previousValue/newValue,
     no gaia demote, no gaia remove-skill), gap logging etiquette callout
   - After backfill: full shell sequence (docs build → validate → checkout artifact churn →
     stage only skill-tree → commit), "never commit generated artifact churn" danger callout
   - Common drift causes: three cause cards (Star-Bar reset, reclassification, evidence rot)
     with git grep hints per cause
   - CI enforcement: Transparency Gate in release CI, `gaia dev validate` three-check suite,
     bot actor allowlist in meta-guard.yml, `GAIA_OPERATOR_OVERRIDE=1` automation tip

2. **Updated `docs/en/index.html`**:
   - Nav version chip: v4.7.7 → v4.7.12
   - Footer version: v4.7.7 → v4.7.12
   - What's New banner: v4.7.7 → v4.7.12, content updated to PR #680 (gaia tree username fix)
     and new Timeline Audit guide; link updated to `timeline-audit.html`
   - Added Timeline Audit card (📋) in Integrations section
   - Added Timeline Audit link to footer Docs column

3. **Updated `docs/en/getting-started.html`**:
   - Nav version chip: v4.4.0 → v4.7.12

4. **Updated `docs/en/DOCS.md`** — page 12 (timeline-audit.html) added as ✅ Done / Routine 008.

### Design decisions

- `timeline-audit.html` introduces: drift-diagram (two-column authoritative vs profile-source),
  step-list (numbered circles for the three-step fix flow), cause-cards (label + detail rows
  for the three drift causes), gap-note row class for the CLI gaps table.
- Callout colors signal severity: warning (amber) for silent failure and prefer-trace_timeline,
  danger (red) for never-commit-generated-artifacts, info (sky-blue) for tips, success (green)
  for the automation/CI tip.
- `gaia dev timeline` is documented alongside `trace_timeline.py` rather than hidden —
  the manual path is valid for non-level events (register, fuse, notes). The rank-chart
  limitation is called out explicitly so developers don't use the wrong tool for demotions.
- Version strings: updated only where they were clearly stale (nav chip on index.html and
  getting-started.html). Individual page footers are left at their creation-time versions —
  they record when content was last substantively updated, not the current CLI version.

### Issues informed

- Issue #644 ([docs] discoverability) — not closed; this routine adds a new content page, not
  a nav integration. The nav/footer wiring is a design-scope task deferred to a future routine.
- Issue #141 (MCP copy-paste) — the existing mcp-server.html platform-tab page covers this;
  left open pending a possible standalone "agent quickstart" one-pager.

### Files created / modified

- `docs/en/timeline-audit.html` ← new
- `docs/en/index.html` ← What's New banner + version bump + Timeline Audit card + footer link
- `docs/en/getting-started.html` ← nav version chip updated
- `docs/en/DOCS.md` ← page 12 added
- `docs/en/MEMORY.md` ← this entry

### Planned next (Routine 009)

- Research (Task 3): audit which pages are hardest to find; consider a lightweight
  "Agent Quickstart" page addressing issue #141 (one-liner MCP setup for Claude Code,
  Codex, Cursor) as a pure copy-paste reference separate from the full MCP guide.
- Maintain (Task 1): add `timeline-audit.html` cross-link to `cli-reference.html` in the
  dev commands section (`gaia dev timeline`), and add it to the sidebar nav on contributing.html.

---

## 2026-06-13 — Routine 007

**Branch:** `docs/routines/006`
**Task chosen:** Task 1 (maintain existing pages — cli-reference.html)

### Trigger

PR #671 confirmed merged (routines 005–006). Created `docs/routines/006` from `origin/main`.
Planned task from Routine 006 session: audit cli-reference.html against current CLI shape —
`gaia share`, `gaia install <bundle>`, and `gaia dev validate` were all missing from the page,
and the version string was stale (v4.6.0, current is v4.7.7).

### What I did

1. **Updated `docs/en/cli-reference.html`**:
   - Bumped nav version chip and footer: v4.6.0 → v4.7.7.
   - Added new **Sharing** sidebar group with `share` and `install` links.
   - Added `validate` link to the System sidebar group.
   - Added `gaia dev validate` command card (System section): three-check validation suite —
     canonical graph validator, redaction gate, Transparency Gate. Flags: `--intake`, `--meta-sync`.
     Includes a "Used in release CI" callout.
   - Added new **Sharing** section (between System and Registry dev) with:
     - `gaia share` card — bundle anatomy, producer flags (`--user`, `-o/--output`, `--stdout`),
       examples including pipe-to-jq and hosting workflow.
     - `gaia install` card — dual-mode detection (bundle ref vs named skill), full flag table,
       non-TTY default callout, suite install (`--suite`), and examples for each mode.
   - Removed stale "As of v4.6.0" qualifier from the `gaia dev timeline` known-gap callout.
   - Updated the `gaia version` example output comment (4.6.0 → 4.7.7).
   - Added `<a href="share-bundles.html">Share Bundles</a>` cross-link in Sharing section desc.

2. **Updated `docs/en/index.html`**:
   - What's New banner: v4.7.6 → v4.7.7, content updated to document the three new CLI reference
     additions (`gaia share`, `gaia install <bundle>`, `gaia dev validate`). Link updated to
     `cli-reference.html#sharing`.
   - Nav version chip and footer: v4.7.6 → v4.7.7.

3. **Updated `docs/en/DOCS.md`** — cli-reference.html row marked "updated 007".

### Design decisions

- The `gaia install` dual-mode design (bundle ref vs named skill slug detection) is documented
  as a first-class citizen — the detection logic (`_looks_like_bundle_ref`) is not mentioned
  by name, but the user-visible rule is spelled out (`.json` file path or `https://` URL =
  bundle mode; everything else = named skill mode). Avoids surprising users who try
  `gaia install karpathy/web-search` and expect the bundle flow.
- `gaia dev validate` is categorized under System (read-safe, open-gated) even though it touches
  registry files on read — it mutates nothing and exits non-zero if checks fail, which is
  exactly the CI contract.
- Sharing section placed between System and Registry dev to signal that sharing is a
  player-facing workflow (open-gated, no Verifier required), not a dev operation.
- Non-TTY default callout on `gaia install <bundle>` preempts the most likely CI surprise.

### Issues informed

- Routine 007 planned maintenance task (cli-reference.html audit) — delivered.
- Addresses the ongoing documentation gap around `gaia share` / `gaia install` noted since
  the Share Bundles guide was written in Routine 006.

### Files created / modified

- `docs/en/cli-reference.html` ← updated (share + install + validate commands; v4.7.7)
- `docs/en/index.html` ← What's New banner + version bump
- `docs/en/DOCS.md` ← cli-reference row updated
- `docs/en/MEMORY.md` ← this entry

### Planned next (Routine 008)

- Research (Task 3): Browse open issues with `documentation` label; identify a new page
  or deep-dive topic not yet covered (candidates: Timeline Audit guide, Agent Integration
  patterns page, or Programmatic-First policy explainer for bot authors).
- Maintain (Task 1): Audit `getting-started.html` — check whether the install command
  is still accurate for v4.7.7 (`pip install gaia-cli`) and whether any new flags
  on `gaia init` need documenting.

---

## 2026-06-12 — Routine 006

**Branch:** `docs/routines/005` (continued — PR #671 still open)

**Task chosen:** Task 2 (write about a feature — Share Bundles)

### Trigger

Resumed from a context-compacted session. PR #671 is open but the Cloudflare Workers
build has been failing since commit `dd96681` (another agent's consolidation commit).
The failure is instant (started_at == completed_at) suggesting a Cloudflare-side
pre-build issue, not a code error. Commits `56e7e4a` (my original routine-005 push)
deployed successfully; subsequent commits failed. Possible causes: rate limiting,
Cloudflare transient issue, or interaction between the `docs/js/site-nav.js` token
change (`'#38bdf8'` → `'var(--tier-basic)'`) and Cloudflare's build pipeline.
Cannot access Cloudflare build logs directly (Cloudflare-native check, not GitHub Actions).
Pushing this commit to trigger a fresh build and test if the issue self-resolves.

### What I did

1. **Created `docs/en/share-bundles.html`** — comprehensive Share Bundles guide:
   - Overview: what a share bundle is, producer-heavy / consumer-light design
   - Bundle anatomy: three-card layout explaining the three payloads (tree snapshot,
     install manifest, skill metadata)
   - gaia share: command reference, two-pass build process (resolve metadata → translate
     prereqs → build manifest), `--stdout` flag for piping
   - Install flow: [A]ll / [P]ick / [V]iew only / [Q]uit table with example session
   - Non-TTY / automation: automatic view-only default explained
   - Resolution strategy: registry-first → direct source URL → unresolved table
   - Bundle format reference: full JSON field tables for top level, tree, skillMeta, install
   - Known issues: Issue #128 (static copy-link page deferred), private-repo unresolved,
     suite skills with no directory

2. **Updated `docs/en/index.html`**:
   - Added Share Bundles card (📦) in Integrations section
   - Added Share Bundles link to footer Docs column

3. **Updated `docs/en/DOCS.md`** — added page 11 (share-bundles.html) as ✅ Done / Routine 006.

### Files created / modified

- `docs/en/share-bundles.html` ← new
- `docs/en/index.html` ← Share Bundles card + footer link
- `docs/en/DOCS.md` ← page 11 added
- `docs/en/MEMORY.md` ← this entry

### Planned next (Routine 007)

- Maintain existing pages (Task 1): cli-reference.html — audit against current CLI shape
  (share command, gaia install bundle detection not documented yet)
- Research (Task 3): Timeline audit guide — gaia dev timeline, the gap around --user flag,
  validate_timelines.py output

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
