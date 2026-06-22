# Epic #780 — Midpoint Handover Document

This document tracks the integration progress of Epic #780 (Architectural Modernization) and guides the incoming agent session to finalize the remaining sub-issues on the `dev/improve-codebase-architecture` branch.

## Current Status (Session 16 Close)

All dynamic dispatch, artifact isolation, and skill quality gates are completed and successfully merged:
- **Sub-Issue 1 (Artifact Isolation)**: Generated files (`gaia.json`, indices) are untracked and excluded; CI pulls and uploads tarball artifacts. **Issue #781 CLOSED.**
- **Sub-Issue 2 (CLI Dynamic Discovery)**: Shrunk `main.py` to 130 lines. Commands are in `src/gaia_cli/commands/` dynamic protocol modules. Mirroring of monkeypatched mocks to `gaia_cli.impl` is handled via a `MainModule` subclass wrapper. **Issue #782 CLOSED.**
- **Sub-Issue 2b (Dev Commands Migration)**: Dev-only commands moved under `gaia dev`.
- **Sub-Issue 4 (Skill Quality Gates)**: Pre-commit hook and `validate.yml` block pull requests with schema violations, orphans, or skills >800 lines. **Issue #784 CLOSED.**
- **Verification**: `python3 -m pytest` is 100% green (all 1,191 tests pass). Direct command executions function perfectly.

---

## Critical Architecture Notes (READ BEFORE EDITING)

### The `impl.py` Layer

The refactor did **not** delete the old `main.py` — it was renamed to `impl.py` (4,157 lines). All command modules import their implementation functions from `gaia_cli.main`, which re-exports everything from `impl.py` via `globals()[_name] = getattr(_impl, _name)` at import time. A `MainModule.__setattr__` class swap (lines 7–18 of `main.py`) mirrors attribute writes back to `impl` to keep test monkeypatches working.

**What this means for you:**
- `from gaia_cli.main import some_function` works because of the namespace injection from `impl.py`.
- If you add a new function to `impl.py`, it is automatically available as `gaia_cli.main.some_function`.
- If tests monkeypatch `gaia_cli.main.X`, the `MainModule.__setattr__` ensures `gaia_cli.impl.X` is also patched.
- Do NOT break the import order: `main.py` must import `impl` before re-exporting.

### `commands/dev.py` is 2,977 lines — Sub-Issue 2c will fix this

This is the new "fat module" — it contains all `gaia dev *` subcommand implementations inline (41 functions). **Sub-Issue 2c (#786)** is scoped within this epic to decompose it into domain sub-modules (e.g., `commands/dev/evidence.py`, `commands/dev/verify.py`, etc.).

---

## Remaining Work Items

The next agent should check out `dev/improve-codebase-architecture` and execute the following sub-issues:

### 1. Sub-Issue 2c: Decompose commands/dev.py (#786)
- **Goal**: Break the 2,977-line `commands/dev.py` into a `commands/dev/` package with domain sub-modules.
- **Branch**: `dev/780-dev-decompose`
- **Tasks**:
  1. Convert `commands/dev.py` into `commands/dev/__init__.py` + domain files (`evidence.py`, `verify.py`, `merge.py`, `rename.py`, `calibrate.py`, `list.py`, `build.py`, `audit.py`, `timeline.py`, `named.py`, `helpers.py`).
  2. Extract shared helpers (`_parse_md`, `_write_md`, `_find_named_file`, `_confirm_destructive`, `_is_verifier`, `_get_contributor`, `_run_docs_build`) into `helpers.py`.
  3. Keep the `DevCommand` class and its `configure()`/`execute()` dispatch in `__init__.py`.
  4. No individual file exceeds ~400 lines.
  5. All 1,191+ tests pass without modification.
  6. `gaia dev --help` output identical to pre-decomposition.

### 2. Sub-Issue 3: Polyglot Monorepo Versioning (#783)
- **Goal**: Maintain version alignment across manifests without complex package structures.
- **Tasks**:
  1. **Rename `ensure_versions_in_sync()` → `verify_lockstep()`** in [versioning.py](file:///Users/marcotiongson/Documents/gaia-skill-tree/src/gaia_cli/versioning.py). This function already reads all 4 manifests and raises on mismatch. Before renaming, check if any version-bearing files have been added since the function was written and are not yet covered. Add a CI entry point script that calls `verify_lockstep()` and exits non-zero on failure.
  2. Implement `Taskfile.yml` at the project root for unified developer shortcuts (`task validate`, `task test`, `task build`).
  3. Close the Changesets portion of #783 by **posting a comment on issue #783** explaining that the Changesets approach was rejected in favor of the existing `versioning.py` lockstep validation (it was originally a Changesets plan, but the custom solution is simpler and already tested for this monorepo's 2-npm-package scale).

### 3. Sub-Issue 5: Abstract MCP Management (#785)
- **Goal**: Minimal abstraction of MCP server management. This will be overhauled in a future dedicated round — invest minimal effort here.
- **Scope**: Ship a working `gaia dev mcp start/stop/status` and basic config merge. Don't over-engineer the daemon or config merger — the MCP server isn't fully PRD'd yet.
- **Tasks**:
  1. Inspect `packages/mcp/src/config/` to understand existing configuration patterns before creating new files.
  2. Build a simple multi-path configuration merger in `packages/mcp/src/config/merger.ts` (merging global user configuration with repo-level `.mcp.json`).
  3. Implement a lightweight process manager daemon in `packages/mcp/src/daemon.ts` that writes/removes a PID file.
  4. Wire the daemon process control as `gaia dev mcp start/stop/status` commands in `src/gaia_cli/commands/mcp_cmd.py` (**NOT** `dev.py`).

### 4. Final Closeout
- Tag `pre-epic-780` on `main` before merging the integration branch.
- Create rollback script `scripts/rollback-epic-780.sh` (documented in [EPIC780_REVERT.md](file:///Users/marcotiongson/Documents/gaia-skill-tree/founder/handovers/EPIC780_REVERT.md) but not yet created as an actual file).
- Update `CONTEXT.md` with the new architecture documentation section.

---

## Reference Documents

| Document | Path |
|---|---|
| Implementation Plan | [implementation_plan.md](file:///Users/marcotiongson/.gemini/antigravity-ide/brain/8634f4ce-4000-4565-b150-81fc921ae0ae/implementation_plan.md) |
| Task Tracker | [task.md](file:///Users/marcotiongson/.gemini/antigravity-ide/brain/8634f4ce-4000-4565-b150-81fc921ae0ae/task.md) |
| Interactive HTML Report | [EPIC780.html](file:///Users/marcotiongson/Documents/gaia-skill-tree/founder/reports/EPIC780.html) |
| Revert Playbook | [EPIC780_REVERT.md](file:///Users/marcotiongson/Documents/gaia-skill-tree/founder/handovers/EPIC780_REVERT.md) |
| Agent Testing Guide | [EPIC780_AGENT_TESTING.md](file:///Users/marcotiongson/Documents/gaia-skill-tree/founder/handovers/EPIC780_AGENT_TESTING.md) |
| Deprecation Cleanup | [EPIC780_DEPRECATION_CLEANUP.md](file:///Users/marcotiongson/Documents/gaia-skill-tree/founder/handovers/EPIC780_DEPRECATION_CLEANUP.md) |
| Midpoint Review | [EPIC780_midpoint_review.md](file:///Users/marcotiongson/.gemini/antigravity-ide/brain/f094bbd1-6234-4fc8-97ef-eb41072fba1e/EPIC780_midpoint_review.md) |
