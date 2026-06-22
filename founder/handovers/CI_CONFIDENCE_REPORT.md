# CI Confidence + Windows-First Dev — Before/After Report

**Issue:** #795
**PR:** https://github.com/mbtiongson1/gaia-skill-tree/pull/796
**Drafted:** 2026-06-22
**Author:** Sub-agent A (Sonnet) under orchestrator session 18

## Context

PR #793 -> #794 hit CI red twice on a single bug-fix patch. Documented in `founder/MEMORY.md` session 18 (L1, L2, L3).

## Before

| Metric | Value |
|---|---|
| Windows agent: tests runnable without flags | No — every invocation needed `-p no:timeout` to skip SIGALRM crash (pytest-timeout v2.4.0, `timeout_method = "signal"`, Windows has no `signal.SIGALRM`) |
| Windows agent: CLI runnable with glyphs | No — every invocation needed `PYTHONIOENCODING=utf-8` env prefix to avoid UnicodeEncodeError on star glyphs and arrows |
| Pre-push feedback loop | None — agent commits → pushes → waits 2 min → reads `gh run view --log-failed` → guesses |
| Smoke test selection | None — agent either runs full 1,200-test suite or runs nothing |
| Local CI dryrun | None — `gaia validate` covers a fraction; no docs-cohesion or smoke gate |
| Wave 1 (#793 -> #794) CI rounds | 2 (1 unrelated meta-sync drift + 1 from PR's own regressions) |
| Wave 1 wall-clock | ~3 hr (orchestrator + sub-agent + 2x CI wait) |
| Wave 1 cost (orchestrator + sub-agent) | ~$3.35 (logged in MEMORY.md session 18) |

## After

| Metric | Value |
|---|---|
| Windows agent: tests runnable | Yes — `python -m pytest -x` works out of the box (thread mode, no INTERNALERROR) |
| Windows agent: CLI runnable | Yes — `gaia tree` prints glyphs natively without PYTHONIOENCODING |
| Pre-push feedback loop | `task release:dryrun` — runs all 4 gates |
| Smoke test selection | `pytest -m smoke` — 17 tests, runs in 4.49s on Windows |
| Local CI dryrun | `task release:dryrun` runs all 4 gates sequentially (fail-fast) |
| Projected Wave 2-6 CI rounds | Goal: <= 1 round per PR. Tracked in MEMORY.md session 19. |

## Hypothesis: cost reduction

Wave 1 burned ~$3.35 across two CI rounds and ~3 hours wall-clock. If `release:dryrun` had caught the regressions before push, each round saves:
- ~2 min CI wait (free, but blocks the loop)
- ~15k orchestrator tokens reading `gh run view --log-failed` and reasoning about the failure (~$0.30)
- ~5 min agent wall-clock re-edit cycle

**Projected savings for Waves 2-6 (4 PRs):** ~$1.20 in token spend, ~80 min wall-clock, 4 CI rounds avoided. Conservative estimate; real number tracked in MEMORY.md after the consolidated Wave 2-6 PR lands.

## What was actually shipped

| Step | Commit | Verification |
|---|---|---|
| 1 — pytest-timeout thread mode | 7ee8821b | `pytest -x` runs on Windows without `-p no:timeout`; SIGALRM INTERNALERROR gone |
| 2 — UTF-8 console reconfigure | 4554e125 | `python -c "import gaia_cli; print('ok: ✅ ⭐ →')"` works without PYTHONIOENCODING |
| 3 — `@pytest.mark.smoke` selection | dbf4db99 | 17 tests marked, runs in 4.49s on Windows; testpaths=["tests"] added to prevent root-level test_mcp.py INTERNALERROR during collection |
| 4 — `task release:dryrun` | 24c2cc63 | 4 gates defined; validate.py passes, check_nav_mounts.py passes on clean tree |
| 5 — This report | (this commit) | You are reading it |

## Smoke test selection rationale

The 17 smoke tests were chosen to cover the exact failure modes from #787 + #794:

| Test | Failure mode it catches |
|---|---|
| `test_help_exits_zero` | Argparse regression — CLI won't start |
| `test_parser_registers_all_public_commands` | New command added but not wired to subparser |
| `test_scan_repo_skips_*` | Scanner breakage from CLI refactor |
| `test_scan_repo_detailed_reports_*` | Scanner output contract |
| `test_top_level_help_shows_all_public_commands_with_usage` | Help output drift |
| `test_gaia_cli_package_imports` | Import error from broken __init__ |
| `test_python_module_help_runs_with_gaia_prog_name` | Module entry point |
| `test_console_script_points_to_canonical_package` | pyproject.toml script entry |
| `test_gaia_cli_main_remains_importable` | main.py import chain |
| `test_bundled_registry_is_used_*` | Bundled snapshot path (#793 regression) |
| `test_write_commands_require_explicit_registry` | Registry resolution contract |
| `test_parse_frontmatter_nested_links` | YAML frontmatter parser |
| `test_registry_paths_use_new_layout` | Registry path layout contract |
| `test_tree_manager_reads_and_writes_skill_trees` | Tree I/O contract |
| `test_cycle` | DAG validation catches schema drift |
| `test_bump_version` | Version bumping logic |
| `test_verify_lockstep` | Version lockstep across pyproject + npm + mcp + registry |

Tests excluded from smoke that were initially considered:
- `test_init_writes_local_registry_path` — fails due to live 404 fetch in test env (pre-existing, not safe for smoke)
- `test_clean_graph` — requires `registry/gaia.json` which is absent in worktree environments
- `test_seed_skills_have_valid_levels` — same, requires registry/gaia.json

## Recommended follow-ups (NOT in this PR)

- **Pre-commit hook** wiring `task release:dryrun` — gated behind opt-in env var so it does not break legacy contributor flows.
- **`gaia release dryrun` CLI verb** as a thin wrapper over `task release:dryrun` — discoverable in `gaia --help`.
- **Test-contract classification audit** (L1) — separate "release artifact" tests from "working-tree state" tests so the latter can move out of PR-gating CI.
- **Fix `test_init_*` network dependency** — the `gaia init` flow calls `fetch_command` unconditionally; a `--no-fetch` flag or mock would make these tests reliable for smoke.
