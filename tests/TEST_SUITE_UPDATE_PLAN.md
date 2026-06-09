# Test Suite Update Plan — PR #635 (MAJOR CLI OVERHAUL)

Status: triage complete (601 tests: ~37 fail, 1 hang, 1 exec-killer · 28/39 files green).
This plan is executed by implementation agents in waves. Each wave ends with a commit + push
to `cli/fix-gaia-scan-and-push-2`.

## Ground rules (read before touching anything)

1. **Run tests ONLY like this** (until Wave 0 lands the pyproject default):
   `.venv/bin/python -m pytest <target> -q -p no:cacheprovider --timeout=30 --timeout-method=signal`
   **Never** use `--timeout-method=thread` — it kills the whole pytest process on the first hang.
2. **Two known session-killers** (neutralized in Wave 0 — do not run these files before Wave 0 lands):
   - `test_dx.py::test_bare_skills_command_prints_skills_help` — `gaia skills` launches the real
     Textual TUI and blocks forever.
   - `test_pr540_review.py::test_tui_missing_textual_error` — `--tui` hits `os.execvp` and
     **replaces the pytest process**.
3. **Archive policy (backup strategy)**: a test that targets removed functionality, or resists
   2 honest repair attempts, is MOVED (never deleted) to `tests/_archive/<original-name>` with a
   header comment `# ARCHIVED 2026-06-10: <reason>` and a line added to `tests/_archive/README.md`.
   `tests/_archive` is excluded from collection via `norecursedirs` (already in pyproject).
4. **Slash convention (decided)**: `scan_skill_mds()` deliberately returns IDs with a single
   leading slash (`/my-skill`, scanner.py ~355). Tests adapt to this; do NOT revert the scanner.
   Where product code compares scan IDs to bare IDs it already `.lstrip("/")`s — tests must do
   the same in comparisons.
5. ANSI-colored CLI output: assert through the `strip_ansi()` helper (Wave 0).
6. No network in tests: `gaia fetch` / `pull` / anything touching GitHub must be monkeypatched.
7. Don't touch Hermes-owned files, `registry/` data, or `skill-trees/` (see CLAUDE.md).
8. Commit messages end with `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

## Triage verdict table (input data — from per-test investigation)

| Test | Verdict | Root cause |
|---|---|---|
| card_renderer::test_compact_card_shows_effective_arrow_when_demerited | stale | effective-arrow removed from compact cards |
| card_renderer::test_contains_level | stale | star now comes from `display_name(include_star=True)` |
| dx::test_bare_skills_command_prints_skills_help | HANG | `skills` launches real GaiaApp |
| graph::test_write_graph_artifact_defaults_to_standalone_html | stale | canvas id `gaiaGraphCanvas` → `canvas3d` |
| graph::test_graph_command_defaults_to_html_and_opens_it | mixed | `custom=True` default + no chdir → writes to real `./.gaia/` |
| pr540::test_tui_usage_mentions_gaia | stale | help text rewritten + ANSI codes |
| pr540::test_tui_missing_textual_error | KILLER | `--tui` now execvp's `gaia skills`; error path removed |
| pr635::TestRed_WriteGraphArtifactCustom (2) | stale | `write_graph_artifact` now returns `(path, graph)` tuple |
| pr635::TestGreen_ScanGlobalSearch::test_local_scan_finds_project_skills | stale | IDs now slash-prefixed |
| pr635::TestGreen_CustomGraphMatchesScan (2) | stale | tuple return + slash-prefixed scan IDs vs bare graph node IDs |
| scanner::TestScanSkillMds (5) | stale | IDs now slash-prefixed |
| scanner::TestSkillSearchDirs (6) | **product bug + stale** | slash prefix AND `PYTEST_CURRENT_TEST` guard drops symlink targets outside root (`startswith(root)` before resolving) |
| scanner::test_semantic_match_origin_threshold | stale | passes nonexistent `origin_threshold=` kwarg |
| packaging::test_scan_can_use_explicit_writable_registry | stale | "Matched N canonical skill(s)." string removed |
| packaging::test_local_registry_auto_resolves_for_write_command | stale fixture | push now requires `.gaia/custom_state.json` |
| packaging::test_docs_build_can_run_from_registry_clone_without_registry_flag | slow | legit but >30s (3D layout solve) — needs `@pytest.mark.timeout(300)` |
| push::TestGaiaPush (3) | stale fixture | `build_skill_batch` ignores raw_tokens, reads custom_state.json |
| redaction (2) | stale (mostly) | `display_name` adds leading `/` + star; redaction blocks still applied. **Check**: owner branch returns `/{contrib}/{nick}` for own skills — confirm intent vs `/{nick}` |
| local_context::test_load_with_scan, test_is_local_with_novel | stale fixture | paths.json fixture uses old `availablePaths[].ownedPrereqs`; loader now reads `detectedIds`/`nearUnlocks`/`oneAway` |
| local_context::TestLocalFirstMap (3) | stale | `_iter_manifest_refs` now also yields named-ID self-mapping (intentional local-first); display format changed |
| local_context — 4 `@skip`ped display tests | rewrite | "Own skills have a new setup" — un-skip with new expected formats |
| stats (2) | stale fixture | `_slot_levels()` derives levels from named skill `.md` `level:`; fixture md has none |
| treeManager::test_unowned_skill_formatting | AMBIGUOUS | test (new in this PR) expects `/???` in default `show_tree`; code only renders unowned when `known_only=False`. Check git intent; either render the ≤5-unowned teaser in default mode (product fix) or pass `known_only=False` in test |

## Wave 0 — Safety rails [haiku] — DO FIRST, single agent

1. `pyproject.toml`: add `pytest-timeout` to the dev extra; in `[tool.pytest.ini_options]` add
   `timeout = 60` and `timeout_method = "signal"`.
2. `tests/conftest.py`: autouse fixture `_block_process_replacement` that monkeypatches
   `os.execvp` (and `os.execv`) to raise `RuntimeError("os.exec* blocked in tests — monkeypatch explicitly to assert exec behavior")`.
3. `tests/conftest.py`: add `strip_ansi(text)` helper (regex `\x1b\[[0-9;]*m` → "") exposed as a
   plain importable function (`from tests.conftest import strip_ansi` won't work cross-rootdir —
   put it in a new `tests/helpers.py` and import via `from helpers import strip_ansi`; conftest
   already puts tests/ on sys.path — verify, else add).
4. Neutralize the killers NOW:
   - dx: monkeypatch `sys.modules["gaia_cli.tui"]` with a stub module whose `GaiaApp().run()`
     records the call; assert the launch attempt instead of letting it run.
   - pr540: replace `test_tui_missing_textual_error` with `test_tui_flag_execs_skills`:
     monkeypatch `os.execvp` with a recorder, call `main()` with `["--tui"]`, assert it was
     invoked with `"skills"` as the subcommand argv.
5. Verify: both files pass; full collect still clean. Commit + push.

## Wave 1 — Core CLI tests: new `tests/test_cli_core.py` [sonnet] — single agent

Shared fixture `make_project(tmp_path, monkeypatch)`: chdir to tmp, minimal registry
(copy the pattern used by `tests/test_pr635_review.py` fixtures), one
`.agents/skills/demo-skill/SKILL.md` with frontmatter (name/description/prerequisites).

Cover (one test class per command):
- **bare `gaia`** (non-TTY): `main()` with argv `["gaia"]`, stdin/stdout not a TTY → prints help;
  `strip_ansi` output contains "Getting started", "Daily commands", "Skills", "Utilities".
- **`gaia --help`**: contains every `PUBLIC_COMMANDS` entry incl. `fetch` and `reset`.
- **selector fallback**: `run_selector(parser)` when `_has_interactive()` is False → prints help,
  never raises, never execs (guard from Wave 0 proves it).
- **`gaia init --user x --yes`**: creates `.gaia/config.toml` + user tree; `fetch_command`
  monkeypatched — assert init invokes it.
- **`gaia scan`**: in fixture project → exit 0; writes `.gaia/custom_state.json` (keys
  `customSkills[].{id,name,mapped_to,match_type,prerequisites}`, `customFusions`) and
  scan-state (`scan_state_path()`: `skills[].{id,localId,level,type,matchType,namedRef}`);
  writes promotion candidates; `scan --all` parses (`args.all`).
- **`gaia push --dry-run`**: with a pre-seeded `custom_state.json` → batch contains
  `knownSkills[].{skillId,localId}` and `proposedCombinations`; `--no-pr` writes the batch file
  under `registry-for-review/skill-batches/`.
- **`gaia tree`**: smoke — exit 0, legend rendered, no crash with custom skills present.
- **`gaia graph --canon`**: chdir'd tmp → writes `registry/render/gaia.html` with `canvas3d` +
  embedded JSON; **custom default** → writes `.gaia/render/gaia.html`.
- **`gaia fetch`**: monkeypatch the URL opener → writes `.gaia/registry/gaia.json` +
  `named-skills.json`.
- **`gaia reset --yes`**: clears `.gaia` state but preserves `config.toml` / `.gitignore`.
- **`gaia pull`**: monkeypatch `fetch_command` + `scan_command` → both called, no git pull.
- **`--tui`**: execvp recorder → argv ends with `["skills"]`.
Commit + push.

## Wave 2 — Repair existing failures [3 parallel agents, disjoint files, NO commits — orchestrator commits]

**Agent 2A [haiku] — mechanical assertion updates**
- `test_card_renderer.py` (2): drop effective-arrow expectation (assert arrow ABSENT now);
  `test_contains_level` → assert star via new `display_name` format.
- `test_pr540_review.py::test_tui_usage_mentions_gaia`: `strip_ansi(COMMAND_USAGE)`, assert
  "Open command selector" (or current phrasing — read the source string first).
- `test_pr635_review.py`: tuple-unpack `write_graph_artifact` in C/D/F/G; slash-prefix
  expectations in E; `.lstrip("/")` when comparing scan IDs to graph node IDs in F.
- `test_stats.py` (2): add `level: 2★` to the fixture named-skill md; recompute expected
  `level_counts` / `named_eligible` per `_slot_levels()` semantics.

**Agent 2B [sonnet] — scanner + graph**
- `test_scanner.py`: update TestScanSkillMds (5) + slash-affected TestSkillSearchDirs cases to
  expect `/`-prefixed IDs. **Product fix (explain in report)**: in `_skill_search_dirs`, the
  `PYTEST_CURRENT_TEST` guard filters candidate dirs with `startswith(root)` BEFORE resolving
  symlinks, so symlinked skill dirs pointing outside root are dropped — resolve/realpath the
  comparison so `test_symlinked_skill_dir_followed` / `test_symlink_deduplication` pass against
  intended behavior. `test_semantic_match_origin_threshold`: align with the real
  `match_skill_to_canonical(..., threshold=)` signature and current priority semantics.
- `test_graph.py`: canvas id → `canvas3d`; `test_graph_command_defaults_to_html_and_opens_it` →
  `monkeypatch.chdir(tmp_path)` + explicit `canon=True` namespace attr; ADD test asserting custom
  default writes under `.gaia/render/`. NEVER let graph tests write to the repo's real `.gaia/`.

**Agent 2C [sonnet] — context/redaction/push/packaging/tree**
- `test_local_context.py`: paths.json fixtures → `detectedIds` format; install-map tests accept
  the named-ID self-mapping (assert as superset or full new dict); un-skip + rewrite the 4
  skipped display tests with the new `"/contrib/nick N★"` format and `include_star=False`
  variants. While here: confirm whether owner-branch `display_name` returning the full
  `/{contrib}/{nick}` for the user's own skill is intended (git log / src comments). If clearly
  unintended, minimal product fix + explanation; if plausible, test the current behavior and
  note it.
- `test_redaction.py` (2): new format (leading `/`, star) while still asserting the redaction
  blocks (`████████`) appear for other contributors below named rank and never for self.
- `test_push.py` (3): seed `.gaia/custom_state.json` in fixtures with `customSkills` matching the
  old raw-token intent; assert new batch shape.
- `test_packaging.py`: scan-output assertion → match current "Scanning installed custom skills"
  flow (read actual output first); push test → seed custom_state.json; docs-build test →
  `@pytest.mark.timeout(300)`.
- `test_treeManager.py::test_unowned_skill_formatting`: check `git log -p` intent for the
  unowned teaser. Default `show_tree` has a ≤5-unowned `/???` grouping path that is currently
  unreachable under `known_only=True` — if the teaser was meant for default mode, make the
  minimal product change to render it; otherwise call with `known_only=False`. Explain choice.

Orchestrator commits per agent batch, then pushes.

## Wave 3 — Coverage for new surface [2 parallel agents, disjoint files, NO commits]

**Agent 3A [haiku] — pure helpers**
- `test_formatting.py` additions: `_rainbow_text` (strip_ansi(out) == input; contains per-char
  color codes), `rank_hex` ("#rrggbb"), `get_harness_color` (claude/cursor/agents paths + default),
  `_bg` truecolor + 256 fallback, `COLOR_FUSION`/`COLOR_GREY`/`HARNESS_COLORS` shape.
- `tests/test_scan_state.py` (new): contract test for `.gaia/custom_state.json` +
  scan-state schema using the Wave 1 fixture (import it or duplicate minimal version).

**Agent 3B [sonnet] — selector + interactive + fuse**
- `tests/test_selector.py` (new): `_build_catalogue()` covers the public commands (incl.
  fetch/reset, no dev leakage); `MenuItem.effective_argv()` with toggled flags; `run_selector`
  non-interactive fallback prints help (capsys + strip_ansi); exec guard proves no exec.
- `test_interactive.py` additions: `FuseCancelled` is an Exception; `_format_id`
  (generic → `/id`; `a/b` stays bare; never `//`); `_fuse_sort_key` ordering
  custom<starless<named<origin; `_fusion_flowchart_frags` single- and multi-source text content
  (join fragment texts, assert arrows/box chars + target id); each `select_*` returns its
  non-interactive fallback when `_has_interactive()` is patched False.
- fuse: `fuse_command` with `--skills a,b` + tmp project → writes `customFusions` entry
  (`sources`, `type: extra`, level) to custom_state.json; Ctrl+C path: patch picker to raise
  `FuseCancelled`, assert clean exit (no traceback, no state mutation).

Orchestrator commits + pushes.

## Wave 4 — Green run + closeout [sonnet]

1. Full suite: `.venv/bin/python -m pytest tests/ -q -p no:cacheprovider` (timeouts now from
   pyproject). Target: 0 failed, 0 hung. Chunk the run if any single Bash call nears 10 min.
2. Stragglers: 2 repair attempts max, then archive per policy with reason.
3. Update `DEV.md` §3: timeout conventions, `tests/_archive` policy, the exec-guard note.
4. Final commit + push. Post-commit cleanup only (archive stays intact).

## Notes for the PR description (orchestrator collects)
- `--auto-promote` parsed but unconsumed (kept: selector menu references it) — wire or drop later.
- `validate.yml` intake validation + registry-for-review triggers commented out in this PR.
- Branch touches `pyproject.toml` / root files outside the `cli/` scope table — may need
  `skip-scope-check`.
