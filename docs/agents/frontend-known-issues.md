# Known Frontend Issues — Badges, Graph, Skill Explorer, Nav/Footer

Core user-facing frontend surfaces with load-bearing invariants. Each fix here was codified after a production regression; read the relevant section before editing the named file.

## Known Badges Issues (Core Implementation)

`docs/badges/index.html` is a **core** page — badge generation is user-facing and must work at all times. Key invariants to maintain:

**`renderRows()` currentState destructuring** (fixed in PR #675, issue #674): `renderRows()` (line ~1378) reads several fields from `currentState` via destructuring. Any new field used inside `renderRows()` **must** be added to that destructuring — or defined with `const <field> = currentState.<field> || <default>` — before use. Silent `ReferenceError`s from missing variables blank the entire badge output with no visible error. Pattern to follow: every other function (`updatePickerActions`, `buildSkillOptions`, `addSkillRow`, button handlers) defines `const namedSkills = currentState.namedSkills || []` at the top. Match this pattern whenever extending `renderRows()`.

**Rule:** after any edit to `docs/badges/index.html`, manually verify `https://gaiaskilltree.com/badges/?u=mattpocock&s=grill-me` renders badge markdown before merging.

**Redaction invariant — 1★ skills exist, 1★ badges do not** (lesson from PR #803/2026-06-22): a contributor whose every named skill is ≤1★ (Awakened / pre-named / demoted) is a legitimate registry citizen — their markdown files in `registry/named/<handle>/` are real, they appear in tree views, they accumulate evidence toward promotion. What they **do not** get is a public reward artifact: no `docs/badges/_assets/<handle>/` directory, no OG card, no entry in `docs/badges/registry.json`. The cutover is 2★ ("named"). `scripts/validate_redaction.py` proves this invariant across every static surface; `scripts/generateBadges.py` enforces it at generation time via `is_redacted()` from `src/gaia_cli/redaction.py` (single source of truth).

When auditing a "stale dir" complaint, first ask: are the underlying skills actually stale, or are they legitimately 1★ entries whose **badge directory** is the only thing that shouldn't be on disk? Removing the directory does not remove the skill — they're orthogonal.

**Generator semantics** (`scripts/generateBadges.py`): writes only — never deletes contributor directories already on disk. The outer caller `scripts/build_docs.py::build_badges()` does the `shutil.rmtree(committed) + shutil.copytree(out_dir, committed)` cycle, which is what actually removes stale dirs. If `build_docs.py` errors out mid-run (e.g. a profiles regen failure on the auto-sync runner), the badges step may not run, and the prior on-disk state survives. Treat `gaia dev docs` warnings as load-bearing.

**Auto-sync NEVER touches `docs/badges/`** (codified 2026-06-24 after the 17:34 UTC wipe outage): the `Auto-Sync Registry Artifacts` workflow runs `git checkout HEAD -- docs/badges/_assets/ docs/badges/registry.json` after `gaia dev docs`, so any badge regen the runner produced is discarded before commit. Badges may ONLY be refreshed via human-reviewed `infra/badge-*` PRs where the operator ran `gaia pull` against a known-good snapshot locally. Root cause of the ban: the runner's `gaia pull` step can hydrate from a stale GitHub Release (older than committed `named-skills.json`), and `gaia dev docs` then regenerates a near-empty badge tree against that stale snapshot — wiping live contributor SVGs that the CDN serves. See `founder/MEMORY.md` session 22 retro.

**Badge drift in `gaia dev docs --check` is warn-only** (codified 2026-06-24): the `badges_changed` signal is printed as a `::warning::` but does NOT count toward the `--check` exit code in `scripts/build_docs.py::main`. Unrelated PRs no longer trip the wire when named-skills.json on the CI runner happens to disagree with the committed badge tree. The opt-in escape `[skip-badge-check]` in the HEAD commit message skips the badges step entirely (quieter CI log; no behavior change since badges are already warn-only).

## Known Graph Issues

**`docs/js/skill-graph.js` bootstrap guard** (fixed in PR #365 `9fa66b8`): Any `querySelector(...).addEventListener(...)` call at module bootstrap level will silently abort the entire IIFE if the selector returns null, causing the canvas to fall back to the embedded `FALLBACK_SKILLS` (~18 legacy nodes) instead of fetching `docs/graph/gaia.json`. Always null-check overlay button selectors before wiring events. Grep for `_graphCloseOverlay.querySelector` if the 3D graph regresses to fallback mode.

**Stale `skills/` root directory** (removed in PR #365 `96c44df`): a pre-merge snapshot (`gaia.json v2.1.4`, 2026-04-30) that carried the legacy id `autonomous-research-agent` at `[VI · Transcendent ★]` with double-misencoded star glyphs. Do not recreate it; canonical data lives under `registry/` and `docs/graph/gaia.json`.

## Known Skill Explorer Issues

`docs/js/skill-explorer.js` is split into **two IIFEs** (lines 1–1862 and 1864–end). They do **not** share lexical scope — bindings in IIFE #2 are invisible to IIFE #1 and vice versa. Anything that needs to be shared has to be re-declared in each IIFE or hung off `window`.

**The cross-IIFE bugs caught in PR #714 (2026-06-17):**

| Bug | Symptom | Fix |
|---|---|---|
| `renderDocs` (IIFE #1, line ~619) called `getRootPath()` defined only in IIFE #2 (line ~1982) | "Docs section unavailable" when the modal opened, or — worse — entire render chain dead because the throw cascaded into `renderFlowchart` and `renderTimeline` | Duplicated `function getRootPath()` inside IIFE #1 (right after `findGeneric`). Comment links back to this CLAUDE.md note. |
| `openTreeDialog` (IIFE #2, line ~1949) referenced an **undeclared** `version` identifier | Skill Tree dialog opened blank or never opened (silent ReferenceError from the click handler) | Added `var version = window.GAIA_VERSION ? '?v=' + window.GAIA_VERSION : '';` mirroring the helper at `docs/js/named-skills.js:468` |
| Snapshot `_seBodyOriginalHTML` lazy-captured the live `.se-body` markup once, then restored it on every subsequent open | Subsequent modal opens missing `#se-docs` / `#se-upgrade` / `#se-changelog` mounts when the captured snapshot was already mid-mutation | Replaced with a constant `SE_BODY_SKELETON` template literal at IIFE #1 top |
| Render call chain at `openExplorer:1601-1607` had no try/catch | One render throwing (e.g. ReferenceError above) silently aborted every subsequent section so only Hero + Install showed | Wrapped each call in `_safeRender(name, mountId, fn)`. On throw, the affected section shows a 1-line "Section unavailable" notice and DevTools console gets the underlying error. Sibling sections continue to render. |

**Rules going forward:**

1. **Before referencing a top-level function from inside `skill-explorer.js`, confirm it's in the same IIFE.** Grep for the function name and check it's declared above the use in the *same* `(function(){ … })()` block. If it isn't, either duplicate it or expose via `window`.
2. **No undeclared identifiers — even on the right-hand side of fetch URLs.** A `version` or `prefix` typo throws ReferenceError at click time; the user sees an unresponsive button with no console hint unless they have DevTools open. Lint can't catch this when the file is two IIFEs in one script.
3. **Render functions in `openExplorer` must remain wrapped in `_safeRender`.** A throw in any of `renderInstall` / `renderDocs` / `renderFlowchart` / `renderTimeline` must not cascade. If you add a sixth section, wrap it.
4. **Don't snapshot live DOM into a module-level cache and assume it's the original.** Either rebuild from a constant template (preferred) or re-capture every modal open.

**Verification rule:** after any edit to `docs/js/skill-explorer.js` or `docs/named/index.html`, manually open `https://gaiaskilltree.com/named/` (or local equivalent), click any 2★+ skill, and confirm all five sections render: **Hero, Installation, Documentation, Upgrade Path, Evolution Changelog**. Click the topbar **Skill.md**, **Repo**, **Report**, and **Skill Tree** (in nav) buttons — each must open. Watch the DevTools console for `[skill-explorer]` warnings.

## Nav / Footer — Adding a New Section

Site nav (`docs/js/site-nav.js`) and site footer (`docs/js/site-footer.js`) both detect URL depth by scanning for a known mount segment. The canonical list lives in **one place only**:

```
docs/js/mounts.js  →  window.GAIA_MOUNTS = [ ... ]
```

Both scripts fall back to an inline copy if `mounts.js` hasn't loaded yet, but the source of truth is `mounts.js`.

**When you add a new `docs/<section>/` directory that uses site-nav or site-footer:**

1. Add the directory name to `window.GAIA_MOUNTS` in `docs/js/mounts.js`.
2. Load `mounts.js` before `site-nav.js` on every HTML page in that directory:
   ```html
   <script src="../js/mounts.js?v=X.Y.Z"></script>
   <script src="../js/site-nav.js?v=X.Y.Z"></script>
   ```
   Adjust the `../` prefix for the page's depth (depth 1 → `../`, depth 2 → `../../`, root → `js/`).
3. If the pages are generated by a Python script (e.g. `scripts/generateProfilePages.py`), update the NAV_HTML / NAV_DIR_HTML template strings there too.

**CI guard:** `scripts/check_nav_mounts.py` (Guard D in `.github/workflows/docs-cohesion.yml`) fails the PR if any HTML file uses `site-nav.js` without loading `mounts.js` first, or if an active `docs/` subdirectory is missing from `window.GAIA_MOUNTS`.

Run locally to verify: `python scripts/check_nav_mounts.py`
