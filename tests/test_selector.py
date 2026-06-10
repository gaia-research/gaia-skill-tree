"""Wave 3 / Agent 3B — tests for gaia_cli.selector.

Covers:
  - _build_catalogue(): structure, public-command presence, dev-only read-only content
  - MenuItem.effective_argv(): with and without toggled flags
  - run_selector(): non-interactive fallback (prints help, returns None, no exec)
  - _rank_hex() / _shimmer_color(): return "#rrggbb" strings (smoke)
"""

from __future__ import annotations

import sys
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# helpers (tests/ is on sys.path via conftest)
# ---------------------------------------------------------------------------
from helpers import strip_ansi

from gaia_cli.selector import (
    MenuItem,
    _build_catalogue,
    _rank_hex,
    _shimmer_color,
    run_selector,
)


# ---------------------------------------------------------------------------
# _build_catalogue()
# ---------------------------------------------------------------------------

class TestBuildCatalogue:
    """_build_catalogue() returns a well-formed list of (group, items)."""

    def _all_leaves(self) -> list[MenuItem]:
        """Walk every leaf argv in the catalogue (children + root items that are leaves)."""
        leaves: list[MenuItem] = []
        for _, items in _build_catalogue():
            for item in items:
                if item.children:
                    for child in item.children:
                        leaves.append(child)
                else:
                    leaves.append(item)
        return leaves

    def _all_leaf_argv_flat(self) -> list[list[str]]:
        return [leaf.argv for leaf in self._all_leaves() if leaf.argv is not None]

    # --- group structure ---

    def test_returns_list_of_2_tuples(self):
        cat = _build_catalogue()
        assert isinstance(cat, list)
        for entry in cat:
            assert isinstance(entry, tuple) and len(entry) == 2

    def test_expected_group_names(self):
        group_names = [title for title, _ in _build_catalogue()]
        assert "Getting started" in group_names
        assert "Daily" in group_names
        assert "Skills" in group_names
        assert "Utilities" in group_names

    # --- required public commands present ---

    def test_init_present(self):
        argvs = self._all_leaf_argv_flat()
        assert ["init"] in argvs

    def test_scan_present(self):
        argvs = self._all_leaf_argv_flat()
        assert ["scan"] in argvs

    def test_push_present(self):
        argvs = self._all_leaf_argv_flat()
        assert ["push"] in argvs

    def test_tree_present(self):
        argvs = self._all_leaf_argv_flat()
        assert ["tree"] in argvs

    def test_fuse_present(self):
        argvs = self._all_leaf_argv_flat()
        assert ["fuse"] in argvs

    def test_graph_present(self):
        argvs = self._all_leaf_argv_flat()
        assert ["graph"] in argvs

    # --- dev entries: only read-only subcommands, no mutating commands ---

    def _all_argvs_starting_with_dev(self) -> list[list[str]]:
        """Collect all leaf argvs whose first element is 'dev'."""
        result = []
        for _, items in _build_catalogue():
            for item in items:
                if item.argv and item.argv[0] == "dev":
                    if item.children:
                        for child in item.children:
                            if child.argv:
                                result.append(child.argv)
                    else:
                        result.append(item.argv)
        return result

    def test_dev_children_are_readonly_only(self):
        """'dev' children must only be the read-only subcommands (list/audit/diff).

        Mutating subcommands (add, merge, split, evidence, timeline, …) must NOT appear
        in the catalogue — they are gated by the Verifier guardrail and require explicit
        CLI invocation.
        """
        MUTATING = {
            "add", "merge", "split", "rename", "calibrate", "evidence",
            "rm-evidence", "link", "reclassify", "update-named", "timeline",
            "rm", "verify", "build",
        }
        dev_argvs = self._all_argvs_starting_with_dev()
        # At least one dev entry should be present (list/audit/diff)
        assert len(dev_argvs) > 0, "Expected dev sub-commands in catalogue"
        for argv in dev_argvs:
            if len(argv) >= 2:
                subcommand = argv[1]
                assert subcommand not in MUTATING, (
                    f"Mutating dev subcommand '{subcommand}' must not appear in the selector catalogue"
                )

    def test_dev_read_only_commands_present(self):
        """list/audit/diff should all appear as dev children."""
        dev_argvs = self._all_argvs_starting_with_dev()
        subcommands = {argv[1] for argv in dev_argvs if len(argv) >= 2}
        assert "list" in subcommands
        assert "audit" in subcommands
        assert "diff" in subcommands

    # --- items are MenuItem instances ---

    def test_all_top_level_items_are_menuitem(self):
        for _, items in _build_catalogue():
            for item in items:
                assert isinstance(item, MenuItem)

    def test_children_are_menuitem_instances(self):
        for _, items in _build_catalogue():
            for item in items:
                if item.children:
                    for child in item.children:
                        assert isinstance(child, MenuItem)


# ---------------------------------------------------------------------------
# MenuItem.effective_argv()
# ---------------------------------------------------------------------------

class TestMenuItemEffectiveArgv:
    """effective_argv() returns base argv plus any toggled flags."""

    def _make_item(self, argv: list[str], flags: list[tuple[str, str]]) -> MenuItem:
        return MenuItem(
            label="test", rank="2★", desc="test item",
            argv=argv,
            flags=flags,
        )

    def test_no_flags_returns_base_argv(self):
        item = self._make_item(["scan"], [("--all", "All"), ("--json", "JSON")])
        assert item.effective_argv() == ["scan"]

    def test_toggled_flag_appended(self):
        item = self._make_item(["scan"], [("--all", "All"), ("--json", "JSON")])
        item._toggled.add("--all")
        result = item.effective_argv()
        assert result == ["scan", "--all"]

    def test_multiple_toggled_flags_appended(self):
        item = self._make_item(["scan"], [("--all", "All"), ("--json", "JSON")])
        item._toggled.add("--all")
        item._toggled.add("--json")
        result = item.effective_argv()
        assert "--all" in result
        assert "--json" in result
        assert result[0] == "scan"
        assert len(result) == 3

    def test_untoggled_flag_not_present(self):
        item = self._make_item(["tree"], [("--named", "Named"), ("--canon", "Canon")])
        item._toggled.add("--named")
        result = item.effective_argv()
        assert "--canon" not in result
        assert "--named" in result

    def test_no_flags_attribute_returns_base(self):
        """Leaf item with no flags: effective_argv() == argv."""
        item = MenuItem(label="fuse", rank="5★", desc="fuse", argv=["fuse"])
        assert item.effective_argv() == ["fuse"]

    def test_leaf_item_with_argv_returns_argv(self):
        item = MenuItem(label="init", rank="1★", desc="init", argv=["init"])
        assert item.effective_argv() == ["init"]

    def test_flags_order_follows_flags_definition_order(self):
        """Toggled flags must appear in the order they are defined in flags, not toggle order."""
        item = self._make_item(["push"], [("--dry-run", "Dry"), ("--no-issue", "No issue"), ("--yes", "Yes")])
        # Toggle in reverse order
        item._toggled.add("--yes")
        item._toggled.add("--dry-run")
        result = item.effective_argv()
        # --dry-run must come before --yes (follows flags definition order)
        assert result.index("--dry-run") < result.index("--yes")


# ---------------------------------------------------------------------------
# run_selector() non-interactive fallback
# ---------------------------------------------------------------------------

class TestRunSelectorNonInteractive:
    """run_selector falls back to parser.print_help() when non-interactive."""

    def _run_non_interactive(self, capsys):
        """Patch _has_interactive → False, run run_selector, return (result, stdout)."""
        from gaia_cli.main import get_parser

        with patch("gaia_cli.selector._has_interactive", return_value=False):
            parser, _ = get_parser()
            result = run_selector(parser)

        captured = capsys.readouterr()
        return result, captured.out

    def test_returns_none(self, capsys):
        result, _ = self._run_non_interactive(capsys)
        assert result is None

    def test_prints_help_with_getting_started(self, capsys):
        """Help output must contain 'Getting started' from COMMAND_USAGE epilog."""
        _, out = self._run_non_interactive(capsys)
        assert "Getting started" in strip_ansi(out)

    def test_no_exec_called(self, capsys, monkeypatch):
        """os.execvp must not be called; conftest already blocks it, so any exec attempt
        would raise RuntimeError — this test verifies the block was never reached."""
        from gaia_cli.main import get_parser

        exec_calls = []

        def recording_blocked(*args, **kwargs):
            exec_calls.append(args)
            raise RuntimeError("os.exec* blocked in tests — monkeypatch explicitly to assert exec behavior")

        monkeypatch.setattr("os.execvp", recording_blocked)

        with patch("gaia_cli.selector._has_interactive", return_value=False):
            parser, _ = get_parser()
            run_selector(parser)

        assert exec_calls == [], "os.execvp must not be called in non-interactive mode"

    def test_output_not_empty(self, capsys):
        """Fallback must produce some output (not silent)."""
        _, out = self._run_non_interactive(capsys)
        assert out.strip() != ""


# ---------------------------------------------------------------------------
# _rank_hex() — smoke tests
# ---------------------------------------------------------------------------

class TestRankHex:
    """_rank_hex returns '#rrggbb' format strings."""

    def test_returns_hash_prefixed_hex(self):
        for rank in ("0★", "1★", "2★", "3★", "4★", "5★", "6★"):
            result = _rank_hex(rank)
            assert result.startswith("#"), f"_rank_hex({rank!r}) should start with '#'"
            assert len(result) == 7, f"_rank_hex({rank!r}) should be 7 chars, got {result!r}"

    def test_hex_chars_valid(self):
        import re
        pattern = re.compile(r"^#[0-9a-f]{6}$", re.IGNORECASE)
        for rank in ("1★", "3★", "6★"):
            result = _rank_hex(rank)
            assert pattern.match(result), f"_rank_hex({rank!r}) is not valid hex: {result!r}"

    def test_unknown_rank_still_returns_hex(self):
        result = _rank_hex("99★")
        assert result.startswith("#") and len(result) == 7


# ---------------------------------------------------------------------------
# _shimmer_color() — smoke tests
# ---------------------------------------------------------------------------

class TestShimmerColor:
    """_shimmer_color returns '#rrggbb' format strings."""

    def test_returns_hash_prefixed_hex(self):
        import re
        pattern = re.compile(r"^#[0-9a-f]{6}$", re.IGNORECASE)
        for phase, col, total in [(0.0, 0, 10), (0.5, 5, 10), (1.0, 9, 10), (0.25, 3, 8)]:
            result = _shimmer_color(phase, col, total)
            assert pattern.match(result), (
                f"_shimmer_color({phase}, {col}, {total}) is not valid hex: {result!r}"
            )

    def test_total_cols_zero_no_crash(self):
        """Edge case: total_cols=0 or 1 must not raise ZeroDivisionError."""
        result = _shimmer_color(0.0, 0, 0)
        assert result.startswith("#") and len(result) == 7

    def test_total_cols_one_no_crash(self):
        result = _shimmer_color(0.0, 0, 1)
        assert result.startswith("#") and len(result) == 7
