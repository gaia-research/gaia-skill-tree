# MEMORY.md — Documentation Agent Diary

---

## 2026-07-28 through 2026-07-31 — Routine 018 (consolidated)

**Branch:** `docs/routines/018` (single unified branch)
**PR:** #1334 (draft) — consolidated all routine 018 work including follow-up syncs
**Task:** SYNC trigger — version bump and content audit across full routine span.

### Overall Trigger
Routine documentation agent triggered; repository version jumped from v6.8.16 (routine 017) through v7.1.4 → v7.1.31 → v7.3.1. Routine 017 editor pass verified all 12 pages were locked at v6.8.16. Multiple version releases required staggered SYNC and content audit work across one unified branch per documentation workflow discipline.

### Day 1: 2026-07-28 — Initial version sync v6.8.16 → v7.1.4

**Task chosen:** Version bump to v7.1.4 (SYNC trigger).

**What I did:**
1. Created `docs/routines/018` branch from main
2. Updated all 12 English documentation HTML files from v6.8.16 to v7.1.4
3. Synchronized nav version chips, footer strings, script cache-bust query parameters across all pages

**Files modified:** All 12 pages in `docs/en/`

### Day 2: 2026-07-30 — Additional version sync v7.1.4 → v7.1.31

**Task continuation:** PR #1334 still open. Repository released additional versions from v7.1.4 through v7.1.31. Updated all 12 documentation pages to v7.1.31.

**What I did:**
1. Synchronized all 12 pages from v7.1.4 to v7.1.31
2. Verified nav chips, footer versions, script query parameters aligned across full suite

**Files modified:** All 12 pages in `docs/en/`

### Day 3: 2026-07-31 — Content audit & final version sync v7.1.31 → v7.3.1

**Task continuation:** Repository has advanced to v7.3.1 on main. Performed ROTATE audit of skill-hierarchy.html (least-recently-touched page, last substantive edit routine 002, June 2026).

**What I did:**
1. Audited skill-hierarchy.html for clarity, links, and callouts
   - Confirmed tier/stars explanation accurate
   - Verified fusion section and examples current
   - Confirmed Named Skills lifecycle comprehensive
   - Validated local-first design explanation
   - Checked sidebar scroll-spy and all navigation
   - No missing links or broken callouts detected
2. Updated skill-hierarchy.html from v7.1.31 to v7.3.1 (current main version)
3. Updated DOCS.md page map to record routine 018 update
4. Consolidated all work under single branch per workflow discipline

**Files modified:**
- All 12 pages in `docs/en/` (final version: v7.3.1)
- `docs/en/DOCS.md` (page map updated)
- `docs/en/MEMORY.md` (this entry, consolidated)

### Design decisions
- Updated uniformly across all HTML files to maintain consistency
- No content changes — version maintenance only
- Consolidated routines 020/021 work back into single routine 018 branch to maintain "one docs/routines branch at a time" discipline
- Closed PRs #1413 and #1414 to consolidate into single PR #1334

### Verification
- All 12 pages synchronized to v7.3.1
- HTML tag-balance check clean
- No vocabulary drift (merge/combine/compose/rarity correctly used only in warnings)
- Script query parameters match across suite
- No broken links or navigation issues

### Planned next (Routine 019+)
- ROTATE: audit next least-recently-touched page for content improvements
- SYNC: monitor for new CLI features/flags between v7.1.31 and v7.3.1
- Maintain: continue version synchronization on single unified branch per workflow discipline

---

## 2026-07-25 — Routine 017 — Editor pass (ship gate, PR #1249)

**Role:** Weekly editor. Reviewed the week's accreted commits on `docs/routines/017`, verified claims against the actual product, fixed what didn't hold up, and shipped.

### What I verified and fixed
1. **`gaia scan` flag table had a fictional flag.** The 2026-07-24 session added `--dir` correctly but left `--auto-promote` in the signature/table/example — that flag does not exist on `gaia scan` (confirmed via `python -m gaia_cli.main scan --help` and `commands/scan.py`). The real, undocumented flag was `--all` ("scan globally installed skills in addition to the local repository"). Replaced `--auto-promote` with `--all` in `cli-reference.html` (signature, table row, example).
2. **MCP server package name was wrong across two pages.** The 2026-07-22 session changed `mcp-server.html` and `index.html` to `@gaia-research/mcp@0.1.0`, citing `AGENTS.md` and commit `6ed72921d`. That commit itself was bad — `packages/mcp/package.json` (and its own README, and the root README's install table) has always published as `@gaia-registry/mcp-server`. Reverted both pages to the real package name and dropped the stale `-y`/version-pin flourishes to match the canonical README's install commands exactly.
3. **Self-contradiction in `faq.html`.** This week's own `evidence-classes.html` fix added an explicit "do not call it 'trust score'" pitfall — but `faq.html` still said "trust score tier" two lines away in spirit. Changed to "quality tier."
4. **Verified the big one held up.** The Trust Number threshold rewrite (S≥250/A≥100/B≥50/C≥20, replacing stale S≥90/A≥80/B≥60/C≥40) and the 10-row Evidence Type table were checked against `registry/schema/meta.json` and live `--help` output for `gaia dev evidence` / `gaia dev verify` — all accurate. Good work, kept as-is.
5. **Two small pre-existing vocabulary nits caught in the same files while verifying:** "feed the same review queue" → "feed the same intake" (`contributing.html`; CONTEXT.md: Intake, avoid "queue"), and a TOC entry "Combine skills" → "Fuse skills" (`cli-reference.html`; CONTEXT.md: Fusion, avoid "combine"). Left the rest of the site's vocabulary alone — didn't do a full 12-page nomenclature sweep this round.

### What I checked and left alone
- Hex colors added this week (`#34d399` checkmarks, `#f59e0b` deprecated tag, `var(--muted, #64748b)` fallbacks) all match long-established, pervasive site-wide convention (same raw values already used in `styles.css` and sibling pages) — not new drift, not touched.
- Version chips: all 12 pages consistently at `v6.8.16`, matching the latest tag and `pyproject.toml`. No stragglers.
- Links/anchors added this week (`evidence-classes.html#pitfalls`, etc.) all resolve.
- Rendered all 5 touched pages via Playwright — no console errors, nav clearance and TOC intact.

### Verification
`git status` scoped to `docs/en/**` only. HTML tag-balance check clean on all touched files. CI on PR #1249 all green (CodeQL, branch-scope, commit-attribution, design-system lint, docs-cohesion) before this pass; re-verified after.

### Files modified this pass
`docs/en/cli-reference.html`, `docs/en/contributing.html`, `docs/en/faq.html`, `docs/en/index.html`, `docs/en/mcp-server.html`.

### Shipped
Squash-merged PR #1249 into `main`. `docs/routines/017` closes; `docs/routines/018` opens next.

---

## 2026-07-24 — Routine 017 (continued, PR #1249 still open)

**Branch:** `docs/routines/017`
**Task chosen:** Rotate least-recently-touched page — `cli-reference.html` — for ongoing audit and sync with new CLI features.

### Trigger
PR #1249 (`docs/routines/017`) still open/unmerged; per branch discipline, continue on the same routine branch. DOCS.md page map shows `cli-reference.html` last touched in routine 012; the planned next from routine 017's 2026-07-23 session flagged this page as needing systematic audit for CLI-shape drift.

### What I did
1. **Added `gaia scan --dir` flag documentation** — CLI feature from commit `3cee7a4cc` (feat(scan): add repeatable --dir flag for nonstandard skill roots #1159) was live but not yet documented. Updated `cli-reference.html` scan command card: updated signature to `[--quiet] [--auto-promote] [--json] [--dir DIR]...`; added table row for `--dir DIR` with description "Scan an extra skill root beyond configured paths (repeatable). Accepts home-relative, absolute, or relative paths. Equivalent to adding to .gaia/config.toml skillDirs=[...]"; added a new example demonstrating repeatable `--dir ~/my-skills --dir ./local-agents`.

### Design decisions
- Kept the `--dir` description terse, avoiding implementation details (path normalization, realpath-dedup, warning on missing paths) — users needing those specifics can read `src/gaia_cli/scanner.py` docstring or the reference in `CLAUDE.md`. The docs page level stays at "what it does, when to use it."
- Description matches the phrasing in `src/gaia_cli/commands/scan.py` (line 24) which calls it "Sticky equivalent" to `.gaia/config.toml skillDirs=[...]" — both docs and code reference the same affordance.

### Issues informed
- Closes no filed issues; this is preventive: documented a live feature before the gap was reported.

### Files created / modified
- `docs/en/MEMORY.md` (modified)
- `docs/en/cli-reference.html` (modified)

### Planned next (Routine 018 or continuation)
- Continue systematic audit of `cli-reference.html` for other undocumented recent flags (scan has more, other commands may too).
- Audit `mcp-server.html` for package/version drift (similar to the class→grade migration already done).

---

## 2026-07-23 — Routine 017 (continued, PR #1249 still open)

**Branch:** `docs/routines/017`
**Task chosen:** Task 5 (edit outdated literature) — closed out issue #1254, filed by this same
routine yesterday, and found the same drift had spread further than the issue described.

### Trigger
PR #1249 (`docs/routines/017`) was still open/unmerged when this session started, so per branch
discipline this continues on the same branch rather than cutting `018`. Checked open `documentation`-
labeled issues for the next task; issue #1254 (filed 2026-07-22, end of yesterday's session) was the
clear next step — it's this routine's own flagged remainder, not someone else's backlog item.

### What I did
1. **Fixed `evidence-classes.html` Trust Number thresholds** — trust meter, grade table, and the
   pitfalls-table Grade S row all said `S≥90/A≥80/B≥60/C≥40`. Real thresholds from
   `registry/schema/meta.json` → `evidence.gradeThresholds` (confirmed against the CLI's own
   `--trust` help text in `impl.py`) are `S≥250/A≥100/B≥50/C≥20`. Fixed all instances.
2. **Rewrote the Evidence Type table** — was 3 rows (`arxiv`, `repo`, `github-stars`), two of which
   used IDs that don't exist. Replaced with all 10 real IDs from `evidence.types`
   (`repo-own`, `github-stars-own`, `arxiv`, `peer-review`, `verifier-attestation`,
   `benchmark-result`, `fusion-recipe`, `proxy-containment`, `social-signal`, `self-attestation`),
   each with what it represents and its real CLI flags, sourced from the `impl.py` `dev_evidence`
   argparse block and each type's `meta.json` description/magnitude formula.
3. **Fixed the `gaia dev evidence` CLI examples** — `--grade` is not a real flag (Grade is
   auto-derived from `--trust`; confirmed no such argument in `impl.py`); `--dry-run` does not
   exist for this subcommand either. Rewrote both example blocks to `--type` + `--trust`, with
   `--commits`/`--contributors`/`--citations` on the relevant rows.
4. **Found and fixed a CLI-shape error beyond the filed issue, in the same section**: the page's
   "verify"/"dispute" examples showed them as flags on `gaia dev evidence` — they're actually a
   separate subcommand, `gaia dev verify <skill_id> --index N [--dispute]` (confirmed in
   `impl.py`, `dev_verify` parser). Fixed both examples; this wasn't in issue #1254 but is the
   same accuracy problem in the same paragraph I was already rewriting, not separate scope.
5. **Migration guide + pitfalls sections**: updated `repo`/`github-stars` type-pills to
   `repo-own`/`github-stars-own`, and the Grade S callout's `≥ 90` to `≥ 250`. Replaced the
   "Skipping `--dry-run`" pitfall (wrong — no such flag) with "Passing `--grade` instead of
   `--trust`", the actually-real mistake.
6. **Checked whether the same drift had spread to other pages** — issue #1254 only flagged
   `evidence-classes.html`, but grepping `docs/en/` for the same numbers found it had:
   - `faq.html` — Class-vs-Grade comparison item used `≥90/≥80/≥60/≥40` and `--grade S|A|B|C`
     (nonexistent flag), plus `repo`/`github-stars` as example type IDs. Fixed all three.
   - `named-skills.html` — Evidence Grade table had the same stale thresholds (type IDs there
     were already correct from routine 017's earlier continuation). Also found and fixed
     `gaia dev verify skill-id 0` missing the required `--index` flag (bare positional isn't
     valid argparse for that subcommand). Fixed all four.
7. Verified no HTML structural breakage: tag-balance check (table/tr/td/th/tbody/thead/div/ul/h2/h3)
   and `html.parser` parse-error check on all three touched files — clean. Rendered
   `evidence-classes.html` locally via Playwright/Chromium and screenshotted the Evidence Type
   table, Trust Number meter/grade table, and CLI code block to confirm the new content displays
   correctly with no layout breakage.
8. Updated `DOCS.md` page map: `evidence-classes.html`, `named-skills.html`, `faq.html` rows all
   now note "updated 017" with 017 added to their routine list (still the same open branch/PR,
   not a new routine number).

### Design decisions
- Kept the Evidence Type table's "URL format / flags" column terse — full magnitude formulas
  live in `meta.json` and don't belong on a docs page; the callout below the table points there
  instead of duplicating it.
- Fixed the `gaia dev verify` shape bug inline rather than filing a new issue for it — it's the
  same CLI-accuracy sweep on the same page section already being rewritten for #1254, not
  distinct scope. Filing a follow-up for something already open in the editor would just be
  spreading the same fix across two PRs for no reason.
- Did not touch the legacy `--class` example (`gaia dev evidence ... --class B`) — that flag is
  real and still accepted for back-compat, confirmed in `impl.py`; only the *new*-form examples
  needed fixing.

### Issues informed
- Closes #1254 (evidence-classes.html Trust Number / Evidence Type / CLI-flag drift) — all three
  points in the issue fixed, plus the `gaia dev verify` shape bug found while doing so.

### Files created / modified
- `docs/en/DOCS.md` (modified)
- `docs/en/MEMORY.md` (modified)
- `docs/en/evidence-classes.html` (modified)
- `docs/en/faq.html` (modified)
- `docs/en/named-skills.html` (modified)

### Planned next
- Audit `mcp-server.html` and `cli-reference.html` for the same class of drift (flags/thresholds
  documented from memory rather than re-derived from `impl.py`/`meta.json`) — this routine found
  three pages with the same failure mode in one afternoon; worth a systematic pass rather than
  waiting for the next issue report.
- Once PR #1249 merges: next routine can move to a genuinely new page/feature rather than more
  accuracy cleanup — the Class→Grade wording and numbers should now be consistent repo-wide.

---

## 2026-07-22 — Routine 017

**Branch:** `docs/routines/017`
**Task chosen:** Version bump to v6.8.16, sync MCP server package name to `@gaia-research/mcp@0.1.0`, document root `AGENTS.md` intake surface, and perform full docs suite synchronization.

### Trigger
Routine documentation agent triggered; observed repository version bump to `6.8.16` / `v6.8.16` from `origin/main` (via `git describe --tags`).

### What I did
1. **Synchronized version numbers**: Updated all 12 English documentation HTML files under `docs/en/` from `v6.4.12` to `v6.8.16`. Mapped navigation tags, version chips, footer scripts (`?v=6.8.16`), and version labels across all files.
2. **Updated MCP server package namespace**: Updated all occurrences in `mcp-server.html` and `index.html` to reference `@gaia-research/mcp@0.1.0` (with `-y` flag in npx commands), aligning with `AGENTS.md` and commit `6ed72921d`.
3. **Documented root `AGENTS.md` discovery surface**: Added agent intake references in `contributing.html` and `index.html` pointing to `AGENTS.md` as the canonical entry point for visiting AI agents.
4. **Updated page map in `DOCS.md`**: Updated Routine 017 entries in `DOCS.md` page map table.

### Design decisions
- Replaced outdated `@gaia-registry/mcp-server` references with the authoritative `@gaia-research/mcp@0.1.0` package identifier and explicit `-y` flags for zero-prompt npx execution.
- Kept all HTML changes strictly within `docs/en/` adhering to `docs-en-shell.css` layout boundaries.

### Issues informed
- Resolves #1124 (Add `AGENTS.md` discovery reference to documentation)
- Partially addressed #917 (Deprecated Evidence Classes) — see continuation below, which actually closes it out.

### Files created / modified
- `docs/en/MEMORY.md` (modified)
- `docs/en/DOCS.md` (modified)
- `docs/en/index.html` (modified)
- `docs/en/mcp-server.html` (modified)
- `docs/en/contributing.html` (modified)
- `docs/en/cli-reference.html` (modified)
- `docs/en/evidence-classes.html` (modified)
- `docs/en/faq.html` (modified)
- `docs/en/fusion.html` (modified)
- `docs/en/getting-started.html` (modified)
- `docs/en/named-skills.html` (modified)
- `docs/en/share-bundles.html` (modified)
- `docs/en/skill-hierarchy.html` (modified)
- `docs/en/timeline-audit.html` (modified)

### Continued (same day) — Evidence Class residue cleanup, PR #1249 still open

**Task chosen:** Task 5 (edit outdated literature). PR #1249 (`docs/routines/017`) was still open/unmerged
when this session started, so per branch discipline this continues on the same branch rather than opening 018.

**Trigger:** Checked issue #917 (marked "Resolves" above, prematurely) — its own triage comment
(nova-gaia, 2026-07-09) flagged a residual "Class C evidence" wording at what was then L880 of
`skill-hierarchy.html`, asking for a reword to Trust Magnitude / Evidence Grade terms. That specific
file was already clean (an earlier routine had fixed it), but grepping `docs/en/` for `Class [ABC]`
turned up the same deprecated phrasing still live in six other places.

**What I did:**
1. Reworded every residual `Class A/B/C evidence` reference to the current `Grade A/B/C (Gold/Silver/Bronze)`
   terminology, matching the migration already established in `evidence-classes.html`:
   `named-skills.html` (7 spots: definition, compare panel, lifecycle steps 3–5, "what you need" list,
   evidence-types paragraph, CLI example, commit message example), `getting-started.html`,
   `fusion.html`, `faq.html` (star-tier table, 3 rows), `cli-reference.html` (`gaia propose` description),
   `contributing.html` (PR title example).
2. **Found a deeper, separate gap while doing so**: `cli-reference.html`'s `gaia dev evidence` card
   documented ONLY the deprecated `--class A|B|C` flag — it had never been migrated to the CLI's actual
   canonical interface (`--type` + `--trust`, confirmed against `src/gaia_cli/impl.py` argparse
   definitions). Rewrote the whole command card: new flag table rows for `--type`, `--trust`,
   `--stars/--commits/--contributors`, `--no-build`; kept `--class` documented but marked
   `[DEPRECATED]`; added a warning callout cross-linking to the Evidence & Trust pitfalls section;
   updated both shell examples to `--type repo-own --trust 20` / `--type arxiv --trust 100`.
3. Updated `named-skills.html`'s evidence-types paragraph and CLI walkthrough example to use real
   type IDs (`repo-own`, `github-stars-own`) instead of the shortened/incorrect `repo`, `github-stars`.
4. Verified with `grep -rn "Class [ABC]" docs/en/` — zero unintentional matches remain; the two
   surviving hits are the deliberate Class-vs-Grade contrast sentence in `faq.html` and my own
   vocabulary note in `DOCS.md`.
5. Updated `DOCS.md` vocabulary rules (Named Skill definition, evidence axis note) and page map
   (routine 017 now also touches `getting-started.html`, `cli-reference.html`, `named-skills.html`,
   `fusion.html`, `faq.html`).

**Design decisions:**
- Trust numbers used in rewritten CLI examples (20, 50, 100) are chosen to land exactly on the
  Grade C/B/A boundaries per the real `meta.json` `evidence.gradeThresholds` (S≥250, A≥100, B≥50,
  C≥20) — confirmed by reading `registry/schema/meta.json` directly, not assumed from the page's
  own (as it turns out, wrong) numbers.
- Kept `--class` in the flag table rather than deleting it — the CLI itself still accepts it for
  back-compat, so hiding it would leave readers of old PRs confused about a flag they'll still see.

**New gap discovered, deliberately NOT fixed here (separate, larger issue filed):**
`evidence-classes.html` — the canonical Evidence & Trust page — has its own accuracy problems
unrelated to the Class-wording residue: (a) its Trust Number thresholds table says S≥90/A≥80/B≥60/C≥40,
but the real `registry/schema/meta.json` → `evidence.gradeThresholds` is S≥250/A≥100/B≥50/C≥20;
(b) its Evidence Type examples use `repo`/`github-stars`, but the real `evidence.types` list in the
same schema file is `fusion-recipe`, `github-stars-own`, `proxy-containment`, `verifier-attestation`,
`benchmark-result`, `arxiv`, `peer-review`, `repo-own`, `self-attestation`, `social-signal` — five
types aren't mentioned on the page at all; (c) one CLI example uses `--grade A` and `--dry-run`,
neither of which exist as `gaia dev evidence` flags in `impl.py`. Fixing this properly means
re-deriving every number and type reference against the schema across a 700+ line file — a distinct,
larger task from tonight's wording cleanup, so it's filed as its own issue rather than rushed here.

### Issues informed (continuation)
- Closes #917 (deprecated Evidence Classes) — the residual wording it flagged is gone repo-wide in `docs/en/`.
- Filed a new issue for the `evidence-classes.html` Trust Number / Evidence Type / CLI-flag accuracy gap (see PR/issue links).

### Files created / modified (continuation)
- `docs/en/DOCS.md` (modified)
- `docs/en/MEMORY.md` (modified)
- `docs/en/named-skills.html` (modified)
- `docs/en/getting-started.html` (modified)
- `docs/en/fusion.html` (modified)
- `docs/en/faq.html` (modified)
- `docs/en/cli-reference.html` (modified)
- `docs/en/contributing.html` (modified)

### Planned next (Routine 018)
- Fix the `evidence-classes.html` Trust Number threshold / Evidence Type / CLI-flag drift filed above.
- Audit upcoming CLI commands for `v6.9.0` release features.
- Maintain and sync documentation for newly curated named skills.

---

## 2026-07-11 — Routine 016

**Branch:** `docs/routines/016`
**Task chosen:** Version bump to v6.4.12, document upstream tracking commands (`sync-upstream`, `freeze`), and add python fallback execution notes.

### Trigger
Routine documentation agent triggered; observed new git tag `v6.4.12` / repository version bump to `6.4.12` from origin/main.

### What I did
1. **Synchronized version numbers**: Updated all 12 English documentation HTML files under `docs/en/` from `v6.1.8` to `v6.4.12`. This covers navigation chips, footer versions, script query parameters, and What's New tags.
2. **Documented upstream tracking subcommands**: Added detailed command cards for <code>gaia dev sync-upstream</code> and <code>gaia dev freeze</code> in `docs/en/cli-reference.html`.
3. **Python execution fallback note**: Added the <code>python -m gaia_cli &lt;command&gt;</code> fallback execution note in the "Verify the install" section of `docs/en/getting-started.html` for blocked environments.
4. **Updated homepage banner**: Updated the "What's New" banner in `docs/en/index.html` to highlight upstream tracking (`gaia dev sync-upstream`/`freeze`), fallback map execution (`python -m gaia_cli`), and the `AGENTS.md` root-level discovery flow.

### Design decisions
- Mapped operator commands to <code>verifier</code> gate badges in command headers, matching style constraints in `DOCS.md`.
- Maintained simple high-contrast callouts with clear accents for operator/deprecation checking requirements.

### Issues informed
- Resolves #1124

### Files created / modified
- `docs/en/MEMORY.md` (modified)
- `docs/en/cli-reference.html` (modified)
- `docs/en/getting-started.html` (modified)
- `docs/en/index.html` (modified)
- `docs/en/contributing.html` (modified)
- `docs/en/evidence-classes.html` (modified)
- `docs/en/faq.html` (modified)
- `docs/en/fusion.html` (modified)
- `docs/en/mcp-server.html` (modified)
- `docs/en/named-skills.html` (modified)
- `docs/en/share-bundles.html` (modified)
- `docs/en/skill-hierarchy.html` (modified)
- `docs/en/timeline-audit.html` (modified)

### Planned next (Routine 017)
- Research: Audit changes in upcoming Sprint F CLI commands.
- Maintain: Sync documentation for any newly added named skill features or templates.

---

## 2026-07-08 — Routine 015

**Branch:** `docs/routines/015`
**Task chosen:** Version bump to v6.1.8, address Issue #917, and perform link/structural validation.

### Trigger
Routine documentation agent triggered; observed recent version bump to v6.1.8 (Sprint D release) from repository tags.

### What I did
1. **Synchronized version numbers**: Updated all 12 English documentation HTML files under `docs/en/` to increment `v5.9.1` and `5.9.1` strings to `v6.1.8`. This covers navigation chips, footer versions, script query parameters, and What's New tags.
2. **Sprint D Content Update**: Rewrote the "What's New" banner in `docs/en/index.html` to properly advertise the Sprint D / v6.1.8 features (automated Content Engine, Benchmark Engine with HumanEval & MMLU leaderboards, SEO discoverability).
3. **Addressed Issue #917 (Deprecated Evidence Classes)**:
   - Removed the legacy `#evidence` section from the bottom of `docs/en/skill-hierarchy.html` which showed deprecated `--class A/B/C` CLI usage.
   - Removed the `Evidence classes` sidebar link from `docs/en/skill-hierarchy.html`.
   - Updated the "Stars axis — how mature" box and "Rank names" table in `docs/en/skill-hierarchy.html` to refer to Evidence Grades (Bronze, Silver, Gold, Platinum / Grade C, B, A, S) instead of Classes.
   - Updated the star progression descriptions in `docs/en/getting-started.html` to use the new Evidence Grade terminology.
4. **Link / Structural Validation**:
   - Wrote and executed a link/anchor validation script across all HTML files.
   - Identified and fixed a broken link in `docs/en/timeline-audit.html` which referenced `cli-reference.html#dev` instead of the correct `cli-reference.html#dev-timeline`.

### Design decisions
- Swapped deprecated `Class A/B/C` mentions for the new `Grade C (Bronze) / B (Silver) / A (Gold) / S (Platinum)` terminology to align with the current Trust Magnitude model.
- Fixed structural links to keep the documentation consistent and error-free.

### Issues informed
- Resolves #917

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

### Planned next (Routine 016)
- Research: Audit new features from upcoming Sprint E.
- Maintain: Audit and expand documentation for any new CLI commands added in Sprint D.

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
