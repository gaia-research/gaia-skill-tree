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
