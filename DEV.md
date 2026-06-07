# Developer Guide (DEV.md)

This document provides a quick reference for setting up the local development environment, running common `gaia` commands, and executing/troubleshooting `pytest` suites to resolve CI failures.

---

## 1. Local Environment Setup

Since this repository contains a pre-configured Python virtual environment (`.venv`), you should run commands within it to avoid "externally managed environment" errors or missing executable errors (e.g., `command not found: pip` or `command not found: gaia`).

### Activating the Virtual Environment
Activate the environment in your shell:
```bash
source .venv/bin/activate
```

Once activated, your standard `pip`, `pytest`, and `gaia` commands will resolve to the virtual environment.

### Alternative (Direct Invocation)
If you prefer not to activate the shell environment, call the binaries directly:
```bash
.venv/bin/pip install -e ".[dev,embeddings]"
.venv/bin/gaia validate
.venv/bin/pytest
```

### Alternative (Using `pipx`)
If you want to install and run the `gaia` CLI tool globally (isolated in its own virtual environment) while still tracking local code changes:
```bash
pipx install --editable .
# Or to include optional dependencies like dev/docs:
pipx install --editable ".[dev,embeddings]"
```


### Installing Dependencies
To install the full suite of dev and docs dependencies (including `numpy` and `scipy` required for 3D layout solving during docs generation):
```bash
pip install -e ".[dev,embeddings]"
```
Or the slim alternative for docs/validation only:
```bash
pip install -e ".[docs]"
```

---

## 2. Common Gaia Commands

| Command | Purpose |
|---|---|
| `gaia validate` | Validate schema, identifiers, DAG cycles, and timelines |
| `gaia docs build` | Regenerate documentation and assets locally |
| `gaia docs build --check` | Verify if generated documentation is up to date (runs in CI) |
| `gaia init --user <username>` | Initialize your local Gaia user profile |
| `gaia scan` | Scan configured paths for skill evidence and generate promotion candidates |
| `gaia promote <skillId>` | Promote a skill in your tree after a scan |
| `gaia tree` | View your local-first user skill tree |
| `gaia dev list --generic --named` | List generic and named skills |

---

## 3. Running and Troubleshooting Tests

We use `pytest` for the Python codebase and `npm test` for npm/MCP packages.

### Run Python Tests
```bash
pytest                               # Run all tests
pytest tests/test_packaging.py       # Run a specific test file
pytest -k "test_docs_build"          # Run tests matching a name pattern
```

### Run Node/MCP Tests
```bash
cd packages/cli-npm && npm test
cd ../mcp && npm run build && npm test
```

---

## 4. Common CI Failures & Troubleshooting Reference

Refer to [CLAUDE.md](file:///Users/marcotiongson/Documents/gaia-skill-tree/CLAUDE.md) and [GEMINI.md](file:///Users/marcotiongson/Documents/gaia-skill-tree/GEMINI.md) for full context.

### A. Stale Documentation Crash (`gaia docs build --check` fails)
* **Symptom:** Modifying `registry/named/` or `registry/nodes/` triggers a CI failure on the docs check.
* **Fix (Local):** Run the documentation build locally and commit the regenerated assets with a `[skip-gen]` commit tag:
  ```bash
  gaia docs build
  git add docs/ registry/gaia.json
  git commit -m "chore(docs): regenerate artifacts [skip-gen]"
  ```
* **Fix (CI):** Manually trigger the **Auto-Sync Registry Artifacts** GitHub Action on your branch.

### B. Missing `numpy`/`scipy` during Docs Build
* **Symptom:** `ModuleNotFoundError: No module named 'numpy'` or `scipy.linalg` when running `gaia docs build`.
* **Fix:** `scripts/build_layouts_3d.py` requires these libraries for 3D layout solving. Install them using the virtualenv:
  ```bash
  pip install -e ".[docs]"
  ```

### C. Pre-Existing Test Failures (Not Regressions)
* **Symptom:** Certain tests fail even on clean branches.
* **Explanation:** `test_tui_tokens.py`, `test_meta_merge`, and `test_docs_build_can_run_from_registry_clone_without_registry_flag` fail in environments missing optional dependencies or due to CLI packaging constraints. Do not attempt to fix them in unrelated PRs.

### D. Version Lockstep Violation
* **Symptom:** Pre-commit hook fails complaining about version mismatches.
* **Fix:** The version strings in `pyproject.toml`, `packages/cli-npm/package.json`, `packages/mcp/package.json`, and `registry/gaia.json` must be identical. Align them automatically:
  ```bash
  gaia release <patch|minor|major>
  ```

### E. Avoid Committing Registry JSONs in Feature PRs
* **Rule:** Feature/Logic PRs should **never** commit `registry/gaia.json` or `docs/graph/gaia.json`. Let the Auto-Sync Registry Artifacts CI handle them to avoid constant merge conflict noise.
