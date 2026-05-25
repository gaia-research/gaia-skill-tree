# GEMINI.md

Agent guidance for the gaia-skill-tree repository. See CLAUDE.md for full details.

## Curation & CI Quick Reference

### 1. Stale docs crash CI

Changes to `registry/named/` or `registry/nodes/` make generated docs stale.

**Primary Fix:** Trigger the **Auto-Sync Registry Artifacts** GitHub Action manually (`workflow_dispatch`) for your branch. This is the safest way to regenerate artifacts.

**Alternative Fix (Local):** Run `gaia docs build` and commit the updated files with `[skip-gen]` tag before pushing to avoid CI failure.

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

