# GEMINI.md

Agent guidance for the gaia-skill-tree repository. See CLAUDE.md for full details.

## Curation & CI Quick Reference

### 1. Stale docs crash CI

Changes to `registry/named/` or `registry/nodes/` make generated docs stale.

**Primary Fix:** Trigger the **Auto-Sync Registry Artifacts** GitHub Action manually (`workflow_dispatch`) for your branch. This is the safest way to regenerate artifacts.

**Alternative Fix (Local):** Run `gaia docs build` and commit the updated files with `[skip-gen]` tag before pushing to avoid CI failure.

**Local dependencies:** `gaia docs build` requires `numpy` + `scipy` (used by `scripts/build_layouts_3d.py` for the 3D layout solve during `tree.md` regen). Install via `pip install -e ".[dev]"` (full kit) or `pip install -e ".[docs]"` (slim — just numpy + scipy). If you skip these, the build fails with `ModuleNotFoundError: No module named 'numpy'` / `'scipy'`, `tree.md` won't regenerate, and `gaia docs build --check` will trip in CI.

### 2. `links.github` URL must use `blob/` not `tree/`

GitHub directory URLs use `tree/` but the installer only recognizes `blob/branch/subpath`. Convert manually to ensure skills are discoverable.

### 3. Only `links.github` is read by the installer

Wrong keys like `links.repo`, `links.docs`, or `origin` won't work. Always use `links.github` and strip any `#fragment` from docs URLs.

### 4. Suites never need `links.github` — do not flag them as uninstallable

Suite skills (with `suiteComponents`) install via components and have no directory of their own. Mark non-suite individual skills at 2★ or below with no public repo as `installable: false`.

### 5. Suite component links need subpaths

Each component in a suite must have a `blob/branch/subpath` URL, not a bare repo root, or symlinks will point incorrectly.

### 6. Pre-existing test failures (not regressions)

`test_tui_tokens.py`, `test_meta_merge`, and `test_docs_build_can_run_from_registry_clone_without_registry_flag` fail due to missing optional dependencies, not recent changes. Do not attempt to fix them in unrelated PRs.

### 7. Version lockstep — four files must match

`pyproject.toml`, `packages/cli-npm/package.json`, `packages/mcp/package.json`, and `registry/gaia.json` must always have the same version. Use `gaia release patch|minor|major` to bump all at once; the pre-commit hook enforces this.

### 8. Safe Merging & Conflict Resolution (Lessons from PR 416-438 Incident)

**Isolate Generated Artifacts:** Feature/Logic PRs should **never** commit `registry/gaia.json` or `docs/graph/gaia.json`. These files change on every build and cause constant merge noise. Let the `Auto-Sync Registry Artifacts` CI handle them.

**Atomic Refactors:** When moving code (e.g., extracting functions from `main.py` to a new module), do it in a standalone "Move-Only" PR. Do not combine structural refactors with logic changes in the same PR; this causes semantic merge conflicts that Git cannot resolve automatically.

**Verify after Merge:** Always run a simple smoke test (e.g., `gaia --version`) after resolving merge conflicts to ensure no Git merge markers (`<<<<<<< HEAD`) were accidentally committed.

## Meta Strategy (Source of Truth)

The registry's taxonomy, evidence methodology, and ranking strategy are defined in [META.md](./META.md). This is the single source of truth for all "Meta" rules.

### Meta Audit Implementation Rules

1. **Generic Skills**: Generic skills are completely starless/rankless. Only named skills have ranks. When auditing, do not run "level overshoot" checks against generic nodes.
2. **Origin Claims**: Origin mapping is not strictly chronological ("earliest"). It represents the highest-rated or most attributed skill in a generic bucket. There can only be one origin per bucket. Setting `origin: true` on one named skill requires stripping it from any others in the same bucket (now automated via `gaia dev update-named --origin`).
3. **Raw Repo Links**: Ecosystem suites (like `obra/superpowers`, `ruvnet/ruflo`, or `mattpocock`) are exempt from strict `SKILL.md` file link checks and should intentionally point to their raw repo URL.

### Tooling Strategy

1. **Close the Gap**: Always prioritize programmatic CLI use over manual registry edits. If a required registry mutation is missing from the CLI (e.g., changing origins, unsetting starless demerits, or standalone timeline events), **update the CLI to fit the gap** first. 
2. **Atomic Registry Commit**: Features adding CLI registry mutations should include the corresponding registry data changes in the same atomic commit.
3. **No Hand-Editing**: Manual YAML frontmatter or timeline edits are forbidden. All registry state changes must be verifiable and logged via CLI command execution.


