# Developer Guide (DEV.md)

This document provides a quick reference for setting up the local development environment, running common `gaia` commands, and executing/troubleshooting `pytest` suites to resolve CI failures.

---

## 0. Hosting Architecture (Read This First — Agents Often Get This Wrong)

Understanding how the site is hosted prevents wrong assumptions about CORS, headers, and deploys.

### Production: GitHub Pages + Cloudflare CDN

```
Browser → Cloudflare (DNS proxy + CDN) → GitHub Pages → docs/ on main branch
```

- **GitHub Pages** is the origin host. When `main` gets a new commit, GitHub automatically serves the updated `docs/` folder at `gaiaskilltree.com`. This is configured via `docs/CNAME`.
- **Cloudflare** sits in front as a CDN/DNS proxy (`Server: cloudflare` in response headers). It caches and accelerates pages but does NOT host them.
- **`_headers` files do NOT work here.** That is a Cloudflare Pages-only feature. This site is GitHub Pages — a `_headers` file in `docs/` would be served as a plain text download.
- **CORS** (`Access-Control-Allow-Origin: *`) is already applied site-wide by Cloudflare — verified by checking response headers. All `docs/api/v1/` JSON files inherit this automatically.
- **To deploy to production:** merge to `main`. GitHub Pages does the rest. There is no manual deploy step.

### PR Previews: Cloudflare Worker with Static Assets

- The `.github/workflows/cf-pr-preview.yml` workflow (`workflow_dispatch` only) deploys the branch as a Cloudflare Worker with Static Assets to a `gaia-skill-tree.<account>.workers.dev` preview URL.
- The Worker (`worker/index.js`) handles badge `?repo=` validation. This is the *only* thing the Worker does.
- `wrangler.toml` configures this preview Worker — it is **not** used by the production site.
- Despite the `run_worker_first = true` setting in `wrangler.toml`, this only affects the Worker preview environment. Production has no Worker in the request path.

### What this means for new features

| Feature | Where it lives | Deploy path |
|---|---|---|
| New HTML/JS/CSS page | `docs/<section>/` | Merge to `main` → auto-served |
| New static JSON (e.g. API) | `docs/api/v1/` | Merge to `main` → auto-served |
| CORS headers | Already on all responses (Cloudflare) | No action needed |
| `_headers` file | ❌ Not supported (GitHub Pages) | Use Cloudflare Dashboard Transform Rules instead |
| Badge validation logic | `worker/index.js` | `cf-pr-preview.yml` dispatch |

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
.venv/bin/gaia dev validate
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
| `gaia dev validate` | Validate schema, identifiers, DAG cycles, and timelines (`gaia validate` is a deprecated shim) |
| `gaia dev docs` | Regenerate documentation and assets locally (`gaia docs build` is a deprecated shim) |
| `gaia dev docs --check` | Regenerate + compare generated docs; fails (exit 1) on drift. NOT read-only — rewrites Class P/S artifacts locally (runs in CI) |
| `gaia init --user <username>` | Initialize your local Gaia user profile |
| `gaia scan` | Scan configured paths for skill evidence and generate promotion candidates |
| `gaia promote <skillId>` | Promote a skill in your tree after a scan |
| `gaia tree` | View your local-first user skill tree |
| `gaia dev list --generic --named` | List generic and named skills |
| `gaia dev evidence <skillId> <url> --class <S\|A\|B\|C\|D> --type <type>` | Add an evidence row to a skill (use the typed numeric flags below to drive Trust Magnitude correctly) |
| `gaia dev evidence ... --stars N` | GitHub star count (for `github-stars-own` / `github-stars-proxy`) |
| `gaia dev evidence ... --views N` | View count (for `social-signal`) |
| `gaia dev evidence ... --citations N` | Citation count (for `arxiv` / `peer-review`) |
| `gaia dev evidence ... --reviewers N` | Peer reviewer count (for `peer-review`; highest-impact type for science skills) |
| `gaia dev evidence ... --commits N` | Commit count (for `repo` / `repo-own`) |
| `gaia dev evidence ... --contributors N` | Contributor count (for `repo` / `repo-own`) |
| `gaia dev evidence ... --skill-count-in-repo N` | Mothership discount divisor for `github-stars-own` (per-skill star contribution) |
| `gaia dev evidence ... --source-started-at YYYY-MM-DD` | ISO date the source content first existed; populates `evidence[].sourceStartedAt` for the apex tenure predicate (RFC §11.12.7) |
| `gaia dev evidence ... --index N` | Patch an existing evidence row in place (combine with any of the numeric flags above or `--source-started-at` to amend without re-adding) |

> Numeric payload flags above (added during Phase 1.5) close the long-standing CLI gap that previously forced direct YAML edits for fields like `magnitude`, `reviewers`, and `views`. Always prefer the CLI so the timeline records the change.

---

## 2A. `gaia dev` → `python -m gaia_cli dev` (Blocked-Environment Fallback)

**Use this when the `gaia` shim is unavailable** — e.g. enterprise Windows that blocks unknown executables on `PATH`, sandboxes that strip `~/.local/bin`, or a worktree where `gaia` resolves to the wrong (system-installed) copy.

### The universal rule (1:1, mechanical)

The console script `gaia` is defined in `pyproject.toml` as `gaia = "gaia_cli.main:main"`. The module entry `python -m gaia_cli` runs `src/gaia_cli/__main__.py`, which calls the **same** `gaia_cli.main:main`. They share one argv/dispatch path, so:

```
gaia <anything>   ≡   python -m gaia_cli <anything>
```

There is nothing to memorize per command — **prefix any `gaia …` invocation with `python -m gaia_cli` instead of `gaia`.** This holds for every top-level command (`scan`, `tree`, `promote`, `skills …`) and every `gaia dev` subcommand. Global flags (`--registry`, `--global/-g`, `--canon`, `--version/-v`) work identically because they live on the root parser.

```bash
# Blocked:            gaia dev validate
python -m gaia_cli dev validate

# Blocked:            gaia dev list --generic --named
python -m gaia_cli dev list --generic --named
```

### Three environment knobs for enterprise/worktree runs

| Situation | Knob | Why |
|---|---|---|
| Running inside a `.claude/worktrees/<branch>/` checkout, or testing branch-new flags | `PYTHONPATH="$(pwd)/src" python -m gaia_cli …` | Forces import from the branch source instead of the installed wheel (same fix as §4.D). Or `pip install -e .` from the worktree. |
| Any **mutating** `dev` verb outside a Verifier context (CI, bots, non-4★ actors) | `GAIA_OPERATOR_OVERRIDE=1 python -m gaia_cli dev …` | Satisfies `authz.require_operator`. Not needed on a bootstrap (zero-verifier) registry, nor if the config user holds a 4★ named skill. **Exception:** `dev verify` has a second in-command `_is_verifier()` gate that *ignores* the override — it still requires a real 4★ verifier even in CI. |
| Any command that triggers a **docs rebuild**, or running `build_docs.py` directly, on Windows | `PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python -m gaia_cli dev …` | `main()` reconfigures the parent process's stdout/stderr to UTF-8 on win32, but the spawned `scripts/build_docs.py` subprocess does **not** inherit that and prints non-ASCII glyphs (`— • ★`). The CLI's own registry writes are already `encoding="utf-8"`, so this knob is about the child process's console output, not file integrity. |

### Per-command mapping

Every row's universal fallback is `python -m gaia_cli dev <cmd> …`. The **Direct script** column lists a `python scripts/*.py` alternative *only where one truly reproduces the effect* — most mutating registry verbs have **no** script equivalent and **must** route through the CLI (that's the Programmatic-First guarantee: they append timeline events the CLI owns). "Mut?" = mutates registry/timeline/git state → needs authorization.

| `gaia dev` command | Mut? | Direct `scripts/*.py` alternative | Notes |
|---|---|---|---|
| `list` | – | — | Read-only, ungated. Default (no `--generic`/`--named`) lists generic only. |
| `audit` | – | — | Read-only linter over `registry/nodes/`. Optional `--level N` threshold. |
| `diff [ref]` | – | — | Read-only; shells out to **git** (needs git on PATH). `git fetch origin` first; bare `diff` on `main`/HEAD errors — pass a branch ref. |
| `validate` | – | `python scripts/validate_intake.py` (for `--intake` only) | Default chains `validate.py` + `validate_redaction.py` + `validate_timelines.py` and OR's their exit codes — **prefer the CLI** to preserve the combined exit code; no single-script equivalent. |
| `test <meta\|all>` | – | `meta`→`python -m pytest tests/test_meta_ops.py tests/test_authz.py` · `all`→`python -m pytest tests/` | Thin pytest wrapper (cwd = repo root). Needs a source checkout with `tests/` (absent from wheels). |
| `docs [--check]` | – | `python scripts/build_docs.py [--check]` | Not authz-gated. On Windows set the UTF-8 knob for **both** paths (the `build_docs.py` child never inherits the parent's UTF-8 reconfigure). |
| `hook [--event T]` | – | — | Internal Claude Code editor hook; fully in-process, not for manual runs. |
| `mcp {start\|stop\|status}` | – | — | Shells out to **node** (`packages/mcp/dist/…`) — needs Node + a built MCP server (`npm run build` in `packages/mcp`). Not authz-gated. |
| `build` | ✓ | `python scripts/build_docs.py` | Thin wrapper (`→ python -m gaia_cli docs build → build_docs.py`). The **direct script bypasses authz**. Regenerates Class P + Class S; no git commit/push (only a read-only `git log`). No `--no-build` flag. |
| `add <name> …` | ✓ | — | Writes `registry/nodes/…` or `registry/named/…` + `add` timeline event, then rebuilds docs unless `--no-build`. `--description` ≥10 chars. |
| `rm <id> [--yes]` | ✓ | — | Deletes node + strips it from all prereqs/derivatives. Non-TTY must pass `--yes`. Rebuilds unless `--no-build`. |
| `merge <target> <src…>` | ✓ | — | Named-vs-generic chosen by whether target id contains `/` (the `--named` flag is a **no-op**). Prompts unless `--yes`. Always rebuilds docs (no `--no-build`). |
| `split <src> <t1> <t2…>` | ✓ | — | Clones source into each target (evidence/timeline cleared); refs + `split` event go to the **first** target only. Prompts unless `--yes`. Always rebuilds docs. |
| `rename <old> <new>` | ✓ | — | Renames node file + rewrites all refs and named `genericSkillRef` + `rename` event. Always rebuilds docs (no `--no-build`). |
| `reclassify <id> <type>` | ✓ | — | Rewrites node into `nodes/<new_type>/`, `type_change` event. `type ∈ basic\|extra\|ultimate\|unique`. Rebuilds unless `--no-build`. |
| `link <target> <a,b,c>` | ✓ | — | Merges (or `--reset` overwrites) prereqs. Rebuilds unless `--no-build`. |
| `calibrate <id> <N★>` | ✓ | — | Named skills only (generics rejected); enforces a **3★+ `links.github` blob-URL** preflight; `rank_up`/`demote` event. Rebuilds unless `--no-build`. |
| `calibrate-evidence-grades` | ✓ | — | Backfills per-row `grade` fields. `--dry-run` is read-only; prompts unless `--dry-run`/`--yes`. Rebuilds unless `--no-build`. |
| `evidence <id> <url> …` | ✓ | — | Adds an evidence row + `evidence_added`/`evidence_graded` event. `--type benchmark-result` requires all 8 fingerprint flags (preflight-enforced). Rebuilds unless `--no-build`. |
| `rm-evidence <id>` | ✓ | — | Requires `--index N` **or** `--source URL` (`--source` removes **all** rows at that exact URL). Prompts unless `--yes`. Rebuilds unless `--no-build`. |
| `verify <id> --index N` | ✓ | — | `--index` **required**; `[--dispute]`. **Double-gated** — the in-command `_is_verifier()` check ignores `GAIA_OPERATOR_OVERRIDE` and requires a real 4★ verifier. Rebuilds unless `--no-build`. |
| `verify-tier <id>` | ✓ | — | Recomputes + persists `verification.tier`. Positional only; no docs rebuild, no timeline event, no subprocess. Honors `GAIA_OPERATOR_OVERRIDE` (no extra verifier gate). |
| `update-named <id> …` | ✓ | — | Rewrites named `.md` frontmatter + timeline. Preflights reject `status=named` without `--title`/`--catalog-ref`, and reject github links not in `/blob/` form. Rebuilds unless `--no-build`. |
| `timeline <id> …` | ✓ | — | No `--user` → registry node timeline; `--user <name>` → `skill-trees/<name>/skill-tree.json`; `--timestamp` valid only with `--user`. Rebuilds unless `--no-build`. |
| `fuse <generic_id> …` | ✓ | — | Upserts a generic fusion node + optional suite manifest (`registry/nodes\|named\|suites`) + timeline. No git. Rebuilds unless `--no-build`. |
| `sync-upstream <id> --tag …` | ✓ | — | In-process frontmatter+timeline writer; **no** docs/git side effects. Flag is `--tag` (the module docstring's `--version` is stale). `--dry-run` needs `pyyaml`. |
| `freeze <id> --reason …` | ✓ | — | Sets `installable:false` + `upstream_deprecated` event. `--reason` required, ≤500 chars; refuses if already frozen; **no** docs/git side effects. |
| `release <patch\|minor\|major>` | ✓ | — | Bumps version in-process, then **git add/commit/tag** and (unless `--no-push`) **git push**. `[--sync]` aligns manifests first. Shells out to git. |

> **Rule of thumb:** if a command has no Direct-script cell, its effect (registry mutation + owned timeline event) is only reproducible through `python -m gaia_cli dev <cmd>`. Do **not** hand-edit `registry/` frontmatter to work around a blocked `gaia` binary — use the module invocation, which is the identical code path.

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
Commands like `gaia dev docs`, `gaia scan`, and `gaia graph` write render artifacts to
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

### A. Stale Documentation Crash (`gaia dev docs --check` fails)
* **Symptom:** Modifying `registry/named/` or `registry/nodes/` triggers a CI failure on the docs check.
* **Heads-up — `--check` is not read-only:** despite the name, it *regenerates* the Class P (gitignored `registry/gaia.json`) and Class S (tracked `docs/graph/*`) artifacts, then fails if the committed Class S output drifts. So running it locally will leave modified files in your working tree — that is expected. Commit the Class S changes; leave Class P (gitignored) alone. See CLAUDE.md § "Class P vs Class S".
* **Fix (Local):** Run the documentation build locally and commit the regenerated assets with a `[skip-gen]` commit tag so the auto-sync workflow does not double-regenerate:
  ```bash
  gaia dev docs
  git add docs/                     # Class S site artifacts (tracked)
  # registry/gaia.json is Class P — gitignored on main, do NOT git add it
  git commit -m "chore(docs): regenerate artifacts [skip-gen]"
  ```

  Optional: --auto-clean (local-only)

  If you prefer a local convenience to remove stale left-only generated files in certain bundles (e.g. the okf bundle), run the generator in write mode with --auto-clean. This will remove left-only committed files that are no longer produced by the generator and rewrite generated artifacts:

  ```bash
  python3 scripts/build_docs.py --auto-clean
  ```

  Notes:
  - --auto-clean is opt-in and OFF by default; do NOT enable it in CI. It is intended for local maintainer use only.
  - Always inspect git changes (git status && git diff) before committing; this tool only removes left-only files in targeted bundles.
  - If unsure, prefer the manual regenerate + review workflow above.

  Additional notes:
  - build_docs.py now normalizes the ledger "version" field (and generatedAt) when run with --check to reduce spurious failures caused by routine version bumps. This should make local --check results more consistent with CI; still follow the regenerate+commit flow for intentional version changes.

  Reproduce CI merge snapshot locally (replace <PR_NUMBER>):
  ```bash
  git fetch origin pull/<PR_NUMBER>/merge:refs/tmp/pr-<PR_NUMBER>-merge
  git checkout refs/tmp/pr-<PR_NUMBER>-merge
  gaia dev docs
  git add docs/
  git commit -m "chore(docs): regenerate artifacts [skip-gen]"
  ```
  Notes:
  - Run these commands from the repository root.
  - If your branch introduces new CLI flags, run via the worktree source: `PYTHONPATH=$(pwd)/src gaia dev docs` or install editable (`pip install -e .`) first.
  - Inspect all changes before pushing; prefer small, reviewable commits.

* **Fix (CI):** Manually trigger the **Auto-Sync Registry Artifacts** GitHub Action on your branch.
* **Encoding note (Windows):** `gaia dev docs` invokes subprocess scripts (`generateBadges.py`, `generateOgCards.py`, `renderGraphSvg.py`) that read UTF-8 JSON. On Windows, the default `cp1252` codec will choke on non-ASCII contributor handles or skill descriptions. Always export UTF-8 env before running:
  ```bash
  PYTHONIOENCODING=utf-8 PYTHONUTF8=1 gaia dev docs
  ```

### B. Missing `numpy`/`scipy` / `cairosvg` during Docs Build
* **Symptom:** `ModuleNotFoundError: No module named 'numpy'` or `scipy.linalg` when running `gaia dev docs`.
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

### D. Worktree CLI Resolves to Installed Version, Not Branch Source
* **Symptom:** Running `python3 -m gaia_cli ...` (or the `gaia` shim) inside a `.claude/worktrees/<branch>/` checkout uses the system-installed CLI rather than the worktree source. New flags introduced on the branch (e.g. `--source-started-at`, `--reviewers`) are reported as unrecognized arguments.
* **Fix:** Force the interpreter to import from the worktree source by setting `PYTHONPATH`:
  ```bash
  PYTHONPATH=/path/to/worktree/src python3 -m gaia_cli dev evidence ...
  ```
  Alternatively, run `pip install -e .` from inside the worktree to rebind the editable install to that checkout.

### E. Version Lockstep Violation
* **Symptom:** Pre-commit hook fails complaining about version mismatches.
* **Fix:** The version strings in `pyproject.toml`, `packages/cli-npm/package.json`, `packages/mcp/package.json`, and `registry/gaia.json` must be identical. Align them automatically:
  ```bash
  gaia dev release <patch|minor|major>
  ```

### F. Windows symlink failures during `gaia skills install` or tests
* **Symptom:** `OSError: [WinError 1314] A required privilege is not held by the client` when installing a named skill, or `test_install` / `test_share` / `test_suite_install` failing with permission errors.
* **Background:** `gaia skills install` symlinks the cached skill into `.agents/skills/<name>/` so the file at the link target is also visible to local agents. On Windows, `os.symlink()` requires Developer Mode (Settings → Privacy & security → For developers) OR the `SeCreateSymbolicLinkPrivilege` token. Many Python builds and nested-process contexts don't inherit the privilege even with Dev Mode on.
* **Fix (since PR #804, v5.0.10+):** the CLI now falls back to NTFS junctions (`mklink /J`) for directories and hardlinks for files via `src/gaia_cli/windowsLinks.py::makeLink`. **No action needed** — the failure should never surface.
* **If you DO see it on a newer Windows runner**: the helper raised `OSError` because all three mechanisms (symlink, junction, hardlink) failed. Check the surrounding message for `mklink` stderr; common causes are an antivirus blocking `cmd.exe` invocation or the target being on a network mount that doesn't support junctions. Workaround: install to a local NTFS path, then sync.
* **Caveat:** `os.readlink()` does **not** work on NTFS junctions. If your code introspects the link target, use `os.path.realpath()` or the project helper `windowsLinks.readLinkTarget()`. The two tests that hit this were updated in PR #804.

## 5. Safe Merging & Conflict Resolution

* **Class P vs Class S generated artifacts** (codified in PR #800): two distinct classes of generated files live in this repo, and confusing them caused a 12-hour site outage in June 2026 (see `founder/handovers/EPIC780_OPTION_A_DECISION.md`).
  - **Class P (pipeline-internal)** — `registry/gaia.json`, `registry/named-skills.json`, `registry/gaia.gexf`, `registry/gaia.svg`, `registry/layouts_3d.json`, `base_gaia.json`, `src/gaia_cli/data/registry/*`. **Gitignored.** Regenerated by `gaia dev docs`; bundled into PyPI wheels at vX.Y.0 minor releases. **NEVER commit these on a feature branch.**
  - **Class S (site-served)** — `docs/graph/gaia.json`, `docs/graph/named/index.json`, `docs/graph/gaia.gexf`, `docs/graph/gaia.svg`. **Tracked in git.** GitHub Pages publishes `main:/docs` as-is; untracking these takes the live site dark. Marked `linguist-generated=true` in `.gitattributes` so PR diff view collapses them.
* **When you change `registry/nodes/` or `registry/named/`**, run `gaia dev docs` and commit the Class S artifacts (`docs/graph/*`) alongside the source change in the same PR. CI Guard E in `docs-cohesion.yml` enforces this.
* **Atomic Refactors:** When moving code (e.g., extracting functions from `main.py` to a new module), do it in a standalone "Move-Only" PR. Do not combine structural refactors with logic changes in the same PR; this causes semantic merge conflicts that Git cannot resolve automatically.
* **Verify after Merge:** Always run a simple smoke test (e.g., `gaia --version`) after resolving merge conflicts to ensure no Git merge markers (`<<<<<<< HEAD`) were accidentally committed.

