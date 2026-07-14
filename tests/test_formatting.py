"""Tests for the centralized skill display formatter."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

import gaia_cli.formatting as fmt_mod
from helpers import strip_ansi
from gaia_cli.formatting import (
    COLOR_CONTRIBUTOR,
    COLOR_FUSION,
    COLOR_GREY,
    COLOR_LOCAL_USER,
    HARNESS_COLORS,
    RANK_COLORS,
    TIER_COLORS,
    TYPE_SYMBOLS,
    format_level_colored,
    format_skill_colored,
    format_skill_plain,
    format_type_colored,
    format_type_label,
    fusion_equation,
    get_harness_color,
    rank_hex,
    _rainbow_text,
    _bg,
)


# ---------------------------------------------------------------------------
# format_skill_plain
# ---------------------------------------------------------------------------


class TestFormatSkillPlain:
    def test_canon_unnamed(self):
        assert format_skill_plain("python-basics") == "/python-basics"

    def test_named_contributor(self):
        result = format_skill_plain("web-scraping", named_contributor="alice")
        assert result == "alice/web-scraping"

    def test_local_user(self):
        result = format_skill_plain("my-tool", is_local=True, local_user="bob")
        assert result == "/my-tool"

    def test_local_without_user_falls_to_canon(self):
        # is_local=True but no local_user -> fallback to canon display
        result = format_skill_plain("orphan-skill", is_local=True)
        assert result == "/orphan-skill"

    def test_named_takes_precedence_over_local(self):
        # If both named_contributor and is_local are given, named wins
        result = format_skill_plain(
            "dual", named_contributor="alice", is_local=True, local_user="bob"
        )
        assert result == "alice/dual"


# ---------------------------------------------------------------------------
# format_skill_colored — with NO_COLOR
# ---------------------------------------------------------------------------


class TestFormatSkillColoredNoColor:
    """When NO_COLOR is set, output should be identical to plain."""

    def test_canon_no_color(self, monkeypatch):
        monkeypatch.setenv("NO_COLOR", "1")
        result = format_skill_colored("python-basics", "1★")
        assert result == "/python-basics"
        assert "\033" not in result

    def test_named_no_color(self, monkeypatch):
        monkeypatch.setenv("NO_COLOR", "1")
        result = format_skill_colored("web-scraping", "2★", named_contributor="alice")
        assert result == "alice/web-scraping"
        assert "\033" not in result

    def test_local_no_color(self, monkeypatch):
        monkeypatch.setenv("NO_COLOR", "1")
        result = format_skill_colored("my-tool", "3★", is_local=True, local_user="bob")
        assert result == "/my-tool"
        assert "\033" not in result


# ---------------------------------------------------------------------------
# format_skill_colored — with color enabled (truecolor)
# ---------------------------------------------------------------------------


class TestFormatSkillColoredTruecolor:
    """Force truecolor output and verify ANSI sequences."""

    @pytest.fixture(autouse=True)
    def _enable_color(self, monkeypatch):
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setenv("COLORTERM", "truecolor")
        # Patch _use_color to always return True (avoids pytest stdout capture issues)
        monkeypatch.setattr(fmt_mod, "_use_color", lambda: True)

    def test_canon_has_rank_color(self):
        result = format_skill_colored("python-basics", "1★")
        r, g, b = RANK_COLORS["1★"]
        assert f"\033[38;2;{r};{g};{b}m" in result
        assert "/python-basics" in result
        assert "\033[0m" in result

    def test_named_has_red_contributor(self):
        result = format_skill_colored("web-scraping", "2★", named_contributor="alice")
        r, g, b = COLOR_CONTRIBUTOR
        assert f"\033[38;2;{r};{g};{b}m" in result
        assert "alice" in result
        # Skill name has rank color
        sr, sg, sb = RANK_COLORS["2★"]
        assert f"\033[38;2;{sr};{sg};{sb}m" in result
        assert "web-scraping" in result

    def test_local_has_green_user(self):
        result = format_skill_colored("my-tool", "3★", is_local=True, local_user="bob")
        r, g, b = COLOR_LOCAL_USER
        assert f"\033[38;2;{r};{g};{b}m" in result
        assert "/my-tool" in result

    def test_unknown_level_falls_to_zero(self):
        result = format_skill_colored("foo", "IX")
        r, g, b = RANK_COLORS["0★"]
        assert f"\033[38;2;{r};{g};{b}m" in result

    def test_default_level_is_zero(self):
        result = format_skill_colored("bar")
        r, g, b = RANK_COLORS["0★"]
        assert f"\033[38;2;{r};{g};{b}m" in result


# ---------------------------------------------------------------------------
# format_skill_colored — 256-color fallback
# ---------------------------------------------------------------------------


class TestFormatSkillColored256:
    """When COLORTERM is not truecolor, should emit 256-color sequences."""

    @pytest.fixture(autouse=True)
    def _enable_256(self, monkeypatch):
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setenv("COLORTERM", "")
        # Patch _use_color to always return True (avoids pytest stdout capture issues)
        monkeypatch.setattr(fmt_mod, "_use_color", lambda: True)

    def test_256_color_format(self):
        result = format_skill_colored("test-skill", "1★")
        assert "\033[38;5;" in result
        assert "\033[38;2;" not in result


# ---------------------------------------------------------------------------
# format_type_label
# ---------------------------------------------------------------------------


class TestFormatTypeLabel:
    def test_basic(self):
        assert format_type_label("basic") == "○ Basic"

    def test_fusion(self):
        assert format_type_label("fusion") == "◆ Fusion"

    def test_legacy_type_fallback(self):
        # Yggdrasil II retired extra/ultimate/unique; they degrade to the
        # unknown-glyph + capitalized label until data migration (#997).
        assert format_type_label("ultimate") == "? Ultimate"

    def test_unknown_type(self):
        result = format_type_label("legendary")
        assert result == "? Legendary"


# ---------------------------------------------------------------------------
# format_type_colored
# ---------------------------------------------------------------------------


class TestFormatTypeColored:
    def test_no_color_matches_plain(self, monkeypatch):
        monkeypatch.setenv("NO_COLOR", "1")
        assert format_type_colored("basic") == format_type_label("basic")

    def test_with_color(self, monkeypatch):
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setenv("COLORTERM", "truecolor")
        monkeypatch.setattr(fmt_mod, "_use_color", lambda: True)

        result = format_type_colored("basic")
        r, g, b = TIER_COLORS["basic"]
        assert f"\033[38;2;{r};{g};{b}m" in result
        assert "○ Basic" in result
        assert "\033[0m" in result


# ---------------------------------------------------------------------------
# format_level_colored
# ---------------------------------------------------------------------------


class TestFormatLevelColored:
    def test_no_color(self, monkeypatch):
        monkeypatch.setenv("NO_COLOR", "1")
        assert format_level_colored("3★") == "3★"

    def test_with_color(self, monkeypatch):
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setenv("COLORTERM", "truecolor")
        monkeypatch.setattr(fmt_mod, "_use_color", lambda: True)

        result = format_level_colored("5★")
        r, g, b = RANK_COLORS["5★"]
        assert f"\033[38;2;{r};{g};{b}m" in result
        assert "5★" in result
        assert "\033[0m" in result


# ---------------------------------------------------------------------------
# fusion_equation
# ---------------------------------------------------------------------------


class TestFusionEquation:
    def test_basic_fusion(self):
        result = fusion_equation(["a", "b"], "c")
        assert result == "/a + /b → /c ◇"

    def test_single_prereq(self):
        result = fusion_equation(["x"], "y")
        assert result == "/x → /y ◇"

    def test_custom_glyph(self):
        result = fusion_equation(["alpha", "beta"], "gamma", result_glyph="◆")
        assert result == "/alpha + /beta → /gamma ◆"

    def test_three_prereqs(self):
        result = fusion_equation(["a", "b", "c"], "d")
        assert result == "/a + /b + /c → /d ◇"

    def test_empty_prereqs(self):
        result = fusion_equation([], "lonely")
        assert result == " → /lonely ◇"


# ---------------------------------------------------------------------------
# Constants integrity
# ---------------------------------------------------------------------------


class TestConstants:
    def test_tier_colors_keys(self):
        assert set(TIER_COLORS.keys()) == {"basic", "extra", "unique", "ultimate"}

    def test_rank_colors_keys(self):
        assert set(RANK_COLORS.keys()) == {"0★", "1★", "2★", "3★", "4★", "5★", "6★"}

    def test_type_symbols_keys(self):
        assert set(TYPE_SYMBOLS.keys()) == {"basic", "fusion"}

    def test_all_colors_are_rgb_tuples(self):
        for name, color in RANK_COLORS.items():
            assert len(color) == 3, f"RANK_COLORS[{name}] not a 3-tuple"
            assert all(0 <= c <= 255 for c in color)
        for name, color in TIER_COLORS.items():
            assert len(color) == 3, f"TIER_COLORS[{name}] not a 3-tuple"
            assert all(0 <= c <= 255 for c in color)
        assert len(COLOR_CONTRIBUTOR) == 3
        assert len(COLOR_LOCAL_USER) == 3


# ---------------------------------------------------------------------------
# Pure helpers — rainbox, harness colors, bg, hex
# ---------------------------------------------------------------------------


class TestRainbowText:
    """_rainbow_text outputs ANSI color codes; strip_ansi recovers original text."""

    def test_strips_to_original(self, monkeypatch):
        """strip_ansi(_rainbow_text(text)) must equal text."""
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setenv("COLORTERM", "truecolor")
        monkeypatch.setattr(fmt_mod, "_use_color", lambda: True)

        text = "Gaia Skill Tree"
        colored = _rainbow_text(text)
        assert strip_ansi(colored) == text

    def test_empty_string_safe(self, monkeypatch):
        """_rainbow_text("") must be safe (empty or unchanged)."""
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setenv("COLORTERM", "truecolor")
        monkeypatch.setattr(fmt_mod, "_use_color", lambda: True)

        result = _rainbow_text("")
        assert result == ""

    def test_single_char_safe(self, monkeypatch):
        """_rainbow_text with single char must work."""
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setenv("COLORTERM", "truecolor")
        monkeypatch.setattr(fmt_mod, "_use_color", lambda: True)

        result = _rainbow_text("X")
        assert strip_ansi(result) == "X"

    def test_contains_multiple_color_escapes(self, monkeypatch):
        """_rainbow_text output must contain multiple distinct \\033[ color escapes."""
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setenv("COLORTERM", "truecolor")
        monkeypatch.setattr(fmt_mod, "_use_color", lambda: True)

        result = _rainbow_text("Hello World")
        # Count the escape sequences
        assert result.count("\033[") >= 2, "Expected multiple color escapes for longer text"

    def test_no_color_returns_plain_text(self, monkeypatch):
        """With NO_COLOR set, _rainbow_text must return plain text."""
        monkeypatch.setenv("NO_COLOR", "1")
        text = "colored text"
        result = _rainbow_text(text)
        assert result == text
        assert "\033" not in result


class TestRankHex:
    """rank_hex returns '#rrggbb' strings keyed from RANK_COLORS."""

    def test_six_star_maps_to_gold(self):
        """6★ must map to the value in RANK_COLORS['6★']."""
        expected_rgb = RANK_COLORS["6★"]
        expected_hex = f"#{expected_rgb[0]:02x}{expected_rgb[1]:02x}{expected_rgb[2]:02x}"
        result = rank_hex("6★")
        assert result == expected_hex

    def test_all_ranks_return_valid_hex(self):
        """All ranks must return valid #rrggbb format."""
        for rank in RANK_COLORS.keys():
            result = rank_hex(rank)
            assert result.startswith("#")
            assert len(result) == 7, f"{rank} returned {result} (not 7 chars)"
            # Verify it's valid hex
            int(result[1:], 16)  # Will raise if invalid

    def test_unknown_rank_falls_to_zero(self):
        """Unknown rank must map to 0★."""
        expected_rgb = RANK_COLORS["0★"]
        expected_hex = f"#{expected_rgb[0]:02x}{expected_rgb[1]:02x}{expected_rgb[2]:02x}"
        result = rank_hex("UNKNOWN")
        assert result == expected_hex


class TestGetHarnessColor:
    """get_harness_color detects harness from path and returns tuple."""

    def test_claude_path(self):
        """Path containing '.claude' must return HARNESS_COLORS['claude']."""
        result = get_harness_color("/home/user/.claude/skills")
        assert result == HARNESS_COLORS["claude"]

    def test_cursor_path(self):
        """Path containing '.cursor' must return HARNESS_COLORS['cursor']."""
        result = get_harness_color("/home/user/.cursor/rules")
        assert result == HARNESS_COLORS["cursor"]

    def test_windsurf_path(self):
        """Path containing '.windsurf' must return HARNESS_COLORS['windsurf']."""
        result = get_harness_color("/home/user/.windsurf/config")
        assert result == HARNESS_COLORS["windsurf"]

    def test_agents_path(self):
        """Path containing '.agents' or 'agents' must return HARNESS_COLORS['agents']."""
        assert get_harness_color("/project/.agents/skills") == HARNESS_COLORS["agents"]
        assert get_harness_color("/project/agents") == HARNESS_COLORS["agents"]

    def test_plain_path_returns_default(self):
        """Plain path with no harness indicators must return COLOR_GREY (default)."""
        result = get_harness_color("/home/user/skills")
        assert result == COLOR_GREY

    def test_case_insensitive(self):
        """Path detection must be case-insensitive."""
        result = get_harness_color("/HOME/USER/.CLAUDE/SKILLS")
        assert result == HARNESS_COLORS["claude"]


class TestBackgroundColor:
    """_bg with truecolor and 256-color fallback."""

    def test_truecolor_format(self, monkeypatch):
        """With COLORTERM=truecolor, _bg must return \\033[48;2;r;g;bm format."""
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setenv("COLORTERM", "truecolor")
        monkeypatch.setattr(fmt_mod, "_use_color", lambda: True)

        result = _bg(100, 150, 200)
        assert result == "\033[48;2;100;150;200m"

    def test_256_color_fallback(self, monkeypatch):
        """With COLORTERM unset/empty, _bg must use 256-color \\033[48;5;Nm format."""
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setenv("COLORTERM", "")
        monkeypatch.setattr(fmt_mod, "_use_color", lambda: True)

        result = _bg(100, 150, 200)
        assert result.startswith("\033[48;5;")
        assert result.endswith("m")

    def test_no_color_returns_empty(self, monkeypatch):
        """With NO_COLOR or _use_color()=False, _bg must return empty string."""
        monkeypatch.setenv("NO_COLOR", "1")
        result = _bg(100, 150, 200)
        assert result == ""


class TestColorConstantsShape:
    """Verify COLOR_FUSION, COLOR_GREY, and HARNESS_COLORS are 3-tuples of ints."""

    def test_color_fusion_is_purple_3tuple(self):
        """COLOR_FUSION must be a 3-tuple."""
        assert isinstance(COLOR_FUSION, tuple)
        assert len(COLOR_FUSION) == 3
        assert all(isinstance(c, int) and 0 <= c <= 255 for c in COLOR_FUSION)
        # Verify expected value (192, 132, 252) — fuse purple
        assert COLOR_FUSION == (192, 132, 252)

    def test_color_grey_is_slate_3tuple(self):
        """COLOR_GREY must be a 3-tuple."""
        assert isinstance(COLOR_GREY, tuple)
        assert len(COLOR_GREY) == 3
        assert all(isinstance(c, int) and 0 <= c <= 255 for c in COLOR_GREY)
        # Verify expected value (148, 163, 184) — slate grey
        assert COLOR_GREY == (148, 163, 184)

    def test_harness_colors_all_3tuples(self):
        """Each HARNESS_COLORS value must be a 3-tuple of ints 0-255."""
        for name, color in HARNESS_COLORS.items():
            assert isinstance(color, tuple), f"HARNESS_COLORS[{name}] not a tuple"
            assert len(color) == 3, f"HARNESS_COLORS[{name}] not a 3-tuple"
            assert all(isinstance(c, int) and 0 <= c <= 255 for c in color), \
                f"HARNESS_COLORS[{name}] contains non-byte values"


# ═══════════════════════════════════════════════════════════════════════════
# Relocated from test_pr540_review.py — force-color env handling
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.integration
def test_force_color_formatting():
    from gaia_cli.formatting import _use_color

    # Test FORCE_COLOR
    with patch.dict(os.environ, {"FORCE_COLOR": "1"}):
        with patch.dict(os.environ, {"NO_COLOR": ""}):
            assert _use_color() is True

    # Test CLICOLOR_FORCE
    with patch.dict(os.environ, {"CLICOLOR_FORCE": "1", "NO_COLOR": ""}):
        assert _use_color() is True

    # Test NO_COLOR (should take precedence)
    with patch.dict(os.environ, {"NO_COLOR": "1", "FORCE_COLOR": "1"}):
        assert _use_color() is False
