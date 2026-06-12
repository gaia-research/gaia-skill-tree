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

### Test-suite conventions

**a. Default timeouts (never use `--timeout-method=thread`)**
`pyproject.toml` sets `timeout = 60` and `timeout_method = "signal"` as pytest defaults.
Do not pass `--timeout-method=thread` on the command line — it kills the entire pytest
process on the first timeout instead of just the offending test, masking every subsequent
failure.  Use `@pytest.mark.timeout(N)` on individual slow tests to raise the cap.

**b. `os.execvp` / `os.execv` are blocked by an autouse fixture**
`tests/conftest.py` installs a session-scoped autouse fixture `_block_process_replacement`
that monkeypatches `os.execvp` and `os.execv` to raise `RuntimeError`.  Any test that
legitimately needs to assert exec behavior must explicitly monkeypatch those functions
(e.g. with a recorder lambda) before calling the code under test.

**c. Tests must never write outside `tmp_path`**
Commands like `gaia docs build`, `gaia scan`, and `gaia graph` write render artifacts to
the registry root they resolve.  Run such commands with `cwd` pointing to a directory
inside `tmp_path` (or a full clone of the needed dirs inside `tmp_path`) so writes stay
isolated.  After adding or modifying any test that invokes a write command, verify
isolation with `git status --porcelain` and confirm no files under `docs/`, `registry/`,
`skill-trees/`, or `README.md` are modified.

**d. `tests/_archive/` — quarantine policy (archive, never delete)**
Obsolete tests or tests that target removed functionality are moved (never deleted) to
`tests/_archive/<original-filename>` with a header comment
`# ARCHIVED YYYY-MM-DD: <reason>` and an entry added to `tests/_archive/README.md`.
The directory is excluded from collection via `norecursedirs` in `pyproject.toml`, so
archived tests do not run.  Two failed repair attempts are the threshold for archiving.

**e. `helpers.strip_ansi` for asserting colored CLI output**
The CLI emits ANSI color codes.  Import `strip_ansi` from `tests/helpers.py` to normalize
output before asserting on text content:
```python
from helpers import strip_ansi
assert "Getting started" in strip_ansi(result.stdout)
```

**f. Network and clock are injected, never hit (auth tests)**
`gaia_cli/auth.py` (GitHub sign-in, PRD #155) routes *all* network through a
single `auth.http_request` function — monkeypatch it to go fully offline (see
`FakeHTTP` in `tests/test_auth.py`).  `poll_for_token` takes `sleep=`/`now=`
callables; pass fakes to drive GitHub's device-flow backoff in zero time (these
are parameters, not module attrs — patching `auth.time.sleep` won't reach the
bound default).  Token storage degrades gracefully: `keyring` is the optional
`[auth]` extra; without it the chmod-600 `GAIA_HOME/hosts.json` fallback is used,
so the suite is green with no keyring installed.  Full design + coverage map:
`tests/AUTH_TEST_SUITE_HANDOVER.md`.

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

### B. Missing `numpy`/`scipy` / `cairosvg` during Docs Build
* **Symptom:** `ModuleNotFoundError: No module named 'numpy'` or `scipy.linalg` when running `gaia docs build`.
* **Fix:** `scripts/build_layouts_3d.py` requires these libraries for 3D layout solving. Install them using the virtualenv:
  ```bash
  pip install -e ".[docs]"
  ```
* **Symptom:** Docs build runs but mysteriously deletes PNG images under `docs/og/`.
* **Fix:** This is caused by `cairosvg` not being installed in the environment where the documentation is built. Run `pip install cairosvg` or restore the PNGs using git before committing:
  ```bash
  git checkout HEAD -- docs/og/
  ```

### C. Pre-Existing Test Failures (Not Regressions)
* **Symptom:** Certain tests fail even on clean branches.
* **Explanation:**
  - `test_tui_tokens.py`, `test_meta_merge`, and `test_docs_build_can_run_from_registry_clone_without_registry_flag` fail in environments missing optional dependencies or due to CLI packaging constraints. Do not attempt to fix them in unrelated PRs.
  - `test_built_wheel_contains_only_python_package_data` and `test_wheel_install_smoke_tests_console_script` fail if your system has `setuptools<77` installed. Run `pip install "setuptools>=77"` to resolve this.

### D. Version Lockstep Violation
* **Symptom:** Pre-commit hook fails complaining about version mismatches.
* **Fix:** The version strings in `pyproject.toml`, `packages/cli-npm/package.json`, `packages/mcp/package.json`, and `registry/gaia.json` must be identical. Align them automatically:
  ```bash
  gaia release <patch|minor|major>
  ```

## 5. Safe Merging & Conflict Resolution

* **Isolate Generated Artifacts:** Feature/Logic PRs should **never** commit `registry/gaia.json` or `docs/graph/gaia.json`. These files change on every build and cause constant merge noise. Let the Auto-Sync Registry Artifacts CI handle them.
* **Atomic Refactors:** When moving code (e.g., extracting functions from `main.py` to a new module), do it in a standalone "Move-Only" PR. Do not combine structural refactors with logic changes in the same PR; this causes semantic merge conflicts that Git cannot resolve automatically.
* **Verify after Merge:** Always run a simple smoke test (e.g., `gaia --version`) after resolving merge conflicts to ensure no Git merge markers (`<<<<<<< HEAD`) were accidentally committed.

