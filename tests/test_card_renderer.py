"""Tests for gaia_cli.cardRenderer."""

import json
import os

import pytest

from gaia_cli.cardRenderer import (
    CARD_WIDTH,
    TIER_GLYPHS,
    LEVEL_LABELS,
    render_card,
    render_card_compact,
    render_cards,
    render_promotion_prompt,
    render_fusion_diagram,
    load_and_render,
    _pad,
    _wrap_lines,
    render_appraise_card,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def basic_skill():
    """A minimal basic-tier skill."""
    return {
        "id": "tokenize",
        "name": "Tokenize",
        "type": "basic",
        "level": "0★",
        "description": "Splits input text into discrete tokens suitable for downstream processing by language models.",
        "prerequisites": [],
        "derivatives": ["rag-pipeline"],
        "evidence": [
            {"class": "C", "source": "https://example.com", "evaluator": "tester", "date": "2026-01-01"}
        ],
        "status": "provisional",
    }


@pytest.fixture
def extra_skill():
    """An extra-tier skill with prerequisites."""
    return {
        "id": "rag-pipeline",
        "name": "RAG Pipeline",
        "type": "extra",
        "level": "2★",
        "demerits": ["experimental-feature"],
        "description": "Retrieval-augmented generation pipeline combining retrieval, ranking, and synthesis.",
        "prerequisites": ["tokenize", "retrieve", "rank"],
        "derivatives": ["autonomous-research-agent"],
        "evidence": [
            {"class": "B", "source": "https://example.com/a", "evaluator": "alice", "date": "2026-01-01"},
            {"class": "B", "source": "https://example.com/b", "evaluator": "bob", "date": "2026-01-01"},
        ],
        "status": "validated",
    }


@pytest.fixture
def ultimate_skill():
    """An ultimate-tier skill."""
    return {
        "id": "autonomous-research-agent",
        "name": "Autonomous Research Agent",
        "type": "ultimate",
        "level": "3★",
        "description": "Fully autonomous agent that formulates hypotheses, designs experiments, collects evidence, and synthesizes findings.",
        "prerequisites": ["rag-pipeline", "code-generation", "tool-use", "planning"],
        "derivatives": [],
        "evidence": [
            {"class": "A", "source": "https://example.com/a", "evaluator": "a", "date": "2026-01-01"},
            {"class": "B", "source": "https://example.com/b", "evaluator": "b", "date": "2026-01-01"},
            {"class": "B", "source": "https://example.com/c", "evaluator": "c", "date": "2026-01-01"},
        ],
        "status": "validated",
    }


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------


class TestPad:
    def test_left_pad_shorter(self):
        assert _pad("hi", 6) == "hi    "

    def test_left_pad_exact(self):
        assert _pad("hello", 5) == "hello"

    def test_truncates_long(self):
        result = _pad("a very long string", 10)
        assert len(result) == 10
        assert result.endswith("…")

    def test_center_alignment(self):
        result = _pad("hi", 6, "center")
        assert result == "  hi  "

    def test_right_alignment(self):
        result = _pad("hi", 6, "right")
        assert result == "    hi"


class TestWrapLines:
    def test_short_text_single_line(self):
        result = _wrap_lines("hello world", 20)
        assert result == ["hello world"]

    def test_long_text_wraps(self):
        text = "one two three four five six"
        result = _wrap_lines(text, 10)
        for line in result:
            assert len(line) <= 10

    def test_empty_string_returns_single_empty(self):
        result = _wrap_lines("", 20)
        assert result == [""]

    def test_single_long_word_not_broken(self):
        result = _wrap_lines("superlongword", 5)
        assert result == ["superlongword"]


# ---------------------------------------------------------------------------
# render_card tests
# ---------------------------------------------------------------------------


class TestRenderCard:
    def test_basic_skill_card_structure(self, basic_skill):
        card = render_card(basic_skill)
        lines = card.split("\n")

        # First line is top border (rounded or square)
        assert lines[0][0] in ("┌", "╭")
        assert lines[0][-1] in ("┐", "╮")
        # Last line is bottom border
        assert lines[-1][0] in ("└", "╰")
        assert lines[-1][-1] in ("┘", "╯")

    def test_contains_skill_name(self, basic_skill):
        card = render_card(basic_skill)
        assert "/tokenize" in card

    def test_contains_tier_glyph(self, basic_skill):
        card = render_card(basic_skill)
        assert TIER_GLYPHS["basic"] in card

    def test_contains_tier_label(self, basic_skill):
        card = render_card(basic_skill)
        assert "Basic Skill" in card

    def test_contains_level_label(self, basic_skill):
        card = render_card(basic_skill)
        assert "0★ Basic" in card

    def test_shows_claimed_and_effective_when_demerited(self, extra_skill):
        card = render_card(extra_skill)
        assert "Potential:" in card
        assert "claimed 2★" in card

    def test_contains_description(self, basic_skill):
        card = render_card(basic_skill)
        # At least the first word of the description
        assert "Splits" in card

    def test_contains_prereqs_none(self, basic_skill):
        card = render_card(basic_skill)
        assert "Prereqs: (none)" in card

    def test_contains_prereqs_listed(self, extra_skill):
        card = render_card(extra_skill)
        assert "tokenize" in card
        assert "retrieve" in card
        assert "rank" in card

    def test_contains_derivatives(self, basic_skill):
        card = render_card(basic_skill)
        assert "rag-pipeline" in card

    def test_contains_status_and_evidence(self, basic_skill):
        card = render_card(basic_skill)
        assert "provisional" in card
        assert "ev:1" in card

    def test_contains_skill_id_in_footer(self, basic_skill):
        card = render_card(basic_skill)
        assert "tokenize" in card

    def test_all_lines_same_width(self, basic_skill):
        card = render_card(basic_skill)
        lines = card.split("\n")
        for line in lines:
            assert len(line) == CARD_WIDTH, f"Line width {len(line)} != {CARD_WIDTH}: {repr(line)}"

    def test_custom_width(self, basic_skill):
        card = render_card(basic_skill, width=60)
        lines = card.split("\n")
        for line in lines:
            assert len(line) == 60

    def test_extra_skill_shows_diamond(self, extra_skill):
        card = render_card(extra_skill)
        assert TIER_GLYPHS["extra"] in card

    def test_ultimate_skill_shows_filled_diamond(self, ultimate_skill):
        card = render_card(ultimate_skill)
        assert TIER_GLYPHS["ultimate"] in card

    def test_ultimate_skill_shows_tier_label(self, ultimate_skill):
        card = render_card(ultimate_skill)
        assert "Ultimate Skill" in card

    def test_long_description_truncated(self):
        skill = {
            "id": "verbose-skill",
            "name": "Verbose",
            "type": "basic",
            "level": "0★",
            "description": " ".join(["word"] * 100),
            "prerequisites": [],
            "derivatives": [],
            "evidence": [],
            "status": "provisional",
        }
        card = render_card(skill)
        # Should have the "..." truncation indicator or at most 4 desc lines
        lines = card.split("\n")
        # Card should not be excessively long
        assert len(lines) <= 20

    def test_many_prerequisites_truncated(self):
        skill = {
            "id": "many-prereqs",
            "name": "Many Prereqs",
            "type": "ultimate",
            "level": "4★",
            "description": "A skill with many prerequisites.",
            "prerequisites": [f"skill-{i}" for i in range(8)],
            "derivatives": [],
            "evidence": [],
            "status": "validated",
        }
        card = render_card(skill)
        # Should show some items and then "+N more" for the remainder
        assert "+", "more" in card
        assert "/skill-0" in card

    def test_many_derivatives_truncated(self):
        skill = {
            "id": "many-derivs",
            "name": "Many Derivs",
            "type": "basic",
            "level": "0★",
            "description": "A skill with many derivatives.",
            "prerequisites": [],
            "derivatives": [f"skill-{i}" for i in range(6)],
            "evidence": [],
            "status": "provisional",
        }
        card = render_card(skill)
        # Should show some items and then "+N more" for the remainder
        assert "more" in card
        assert "/skill-0" in card

    def test_compact_card_omits_effective_arrow(self, extra_skill):
        compact = render_card_compact(extra_skill)
        assert "2★→1★" not in compact
        assert TIER_GLYPHS["extra"] in compact
        assert "/rag-pipeline" in compact
        assert " — " in compact
        assert "Retrieval-augmented generation" in compact

    def test_missing_optional_fields_defaults_gracefully(self):
        """Card should render even with minimal skill data."""
        skill = {"id": "bare-skill"}
        card = render_card(skill)
        assert "bare-skill" in card
        assert "○" in card  # defaults to basic glyph


# ---------------------------------------------------------------------------
# render_card_compact tests
# ---------------------------------------------------------------------------


class TestRenderCardCompact:
    def test_single_line(self, basic_skill):
        result = render_card_compact(basic_skill)
        assert "\n" not in result

    def test_contains_glyph(self, basic_skill):
        result = render_card_compact(basic_skill)
        assert "○" in result

    def test_contains_name(self, basic_skill):
        result = render_card_compact(basic_skill)
        assert "/tokenize" in result

    def test_contains_level(self, basic_skill):
        # Without ctx: no level/star in output
        result = render_card_compact(basic_skill)
        assert "★" not in result

        # With minimal stub ctx: level appears
        stub_ctx = type('StubCtx', (), {
            'display_name': lambda self, skill_id, canon=False, include_star=True: "/demo 2★"
        })()
        result_with_ctx = render_card_compact(basic_skill, ctx=stub_ctx)
        assert "2★" in result_with_ctx

    def test_contains_description(self, basic_skill):
        result = render_card_compact(basic_skill)
        assert "Splits" in result

    def test_long_description_truncated(self):
        skill = {
            "id": "x",
            "name": "X",
            "type": "basic",
            "level": "0★",
            "description": "A" * 100,
        }
        result = render_card_compact(skill)
        assert "…" in result


# ---------------------------------------------------------------------------
# render_cards tests
# ---------------------------------------------------------------------------


class TestRenderCards:
    def test_multiple_cards_separated(self, basic_skill, extra_skill):
        result = render_cards([basic_skill, extra_skill])
        # Full cards are separated by double newlines
        assert "\n\n" in result
        assert "/tokenize" in result
        assert "/rag-pipeline" in result

    def test_compact_mode(self, basic_skill, extra_skill):
        result = render_cards([basic_skill, extra_skill], compact=True)
        lines = result.split("\n")
        assert len(lines) == 2

    def test_empty_list(self):
        result = render_cards([])
        assert result == ""

    def test_compact_empty_list(self):
        result = render_cards([], compact=True)
        assert result == ""


class TestRenderPromotionPrompt:
    def test_shows_skill_id_with_slash(self):
        prompt = render_promotion_prompt(
            {"id": "plan-and-execute", "name": "Different Registry Name", "type": "extra", "prerequisites": ["a", "b"]},
            "4★",
        )
        assert "/plan-and-execute" in prompt
        assert "gaia promote plan-and-execute" in prompt

    def test_shows_level_and_rank_name(self):
        prompt = render_promotion_prompt({"id": "research-agent", "type": "extra", "prerequisites": ["x"]}, "3★")
        assert "3★" in prompt
        assert "gaia promote research-agent" in prompt

    def test_shows_fusion_diagram_when_prereqs_exist(self):
        prompt = render_promotion_prompt(
            {"id": "research", "type": "extra", "prerequisites": ["web-search", "summarize"]},
            "3★",
        )
        assert "──▶" in prompt


# ---------------------------------------------------------------------------
# load_and_render tests
# ---------------------------------------------------------------------------


class TestLoadAndRender:
    def test_load_existing_skill(self, tmp_path):
        """Should load and render a skill from gaia.json."""
        graph_dir = tmp_path / "registry"
        graph_dir.mkdir()
        graph_data = {
            "skills": [
                {
                    "id": "web-scrape",
                    "name": "Web Scrape",
                    "type": "basic",
                    "level": "0★",
                    "description": "Scrapes data from web pages.",
                    "prerequisites": [],
                    "derivatives": [],
                    "evidence": [],
                    "status": "provisional",
                }
            ]
        }
        (graph_dir / "gaia.json").write_text(json.dumps(graph_data))

        result = load_and_render("web-scrape", str(tmp_path))
        assert result is not None
        assert "/web-scrape" in result
        assert "┌" in result or "╭" in result

    def test_load_nonexistent_skill_returns_none(self, tmp_path):
        """Should return None for a skill not in the registry."""
        graph_dir = tmp_path / "registry"
        graph_dir.mkdir()
        (graph_dir / "gaia.json").write_text(json.dumps({"skills": []}))

        result = load_and_render("no-such-skill", str(tmp_path))
        assert result is None

    def test_load_missing_registry_returns_none(self, tmp_path):
        """Should return None when gaia.json does not exist."""
        result = load_and_render("anything", str(tmp_path / "no-such-dir"))
        assert result is None

    def test_load_compact_mode(self, tmp_path):
        """Should render in compact mode when requested."""
        graph_dir = tmp_path / "registry"
        graph_dir.mkdir()
        graph_data = {
            "skills": [
                {
                    "id": "classify",
                    "name": "Classify",
                    "type": "basic",
                    "level": "0★",
                    "description": "Assigns labels.",
                    "prerequisites": [],
                    "derivatives": [],
                    "evidence": [],
                    "status": "provisional",
                }
            ]
        }
        (graph_dir / "gaia.json").write_text(json.dumps(graph_data))

        result = load_and_render("classify", str(tmp_path), compact=True)
        assert result is not None
        assert "\n" not in result
        assert "/classify" in result


# ---------------------------------------------------------------------------
# render_fusion_diagram tests
# ---------------------------------------------------------------------------


class TestRenderFusionDiagram:
    def test_single_prereq_simple_arrow(self):
        """Single prereq renders a simple inline arrow."""
        output = render_fusion_diagram(["web-search"], "research")
        assert "────▶" in output
        assert "/web-search" in output
        assert "/research" in output
        assert "◇" in output  # default extra glyph

    def test_two_prereqs_bracket_and_connector(self):
        """Two prereqs render top bracket, connector row, bottom bracket."""
        output = render_fusion_diagram(["code-gen", "code-review"], "pair-program")
        lines = output.split("\n")
        assert len(lines) == 3
        assert "─┐" in lines[0]
        assert "├──▶" in lines[1]
        assert "─┘" in lines[2]
        assert "/pair-program" in output
        assert "◇" in output

    def test_three_prereqs_midpoint_arrow(self):
        """Three prereqs: first ─┐, middle ─┼──▶, last ─┘."""
        output = render_fusion_diagram(
            ["web-search", "summarize", "cite-sources"], "research"
        )
        lines = output.split("\n")
        assert len(lines) == 3
        assert "─┐" in lines[0]
        assert "─┼──▶" in lines[1]
        assert "─┘" in lines[2]
        assert "/research" in output
        assert "◇" in output

    def test_four_prereqs_structure(self):
        """Four prereqs: first ─┐, middle ─┤ and ─┼──▶, last ─┘."""
        output = render_fusion_diagram(
            ["web-search", "summarize", "cite-sources", "knowledge"],
            "autonomous-research",
            result_type="ultimate",
        )
        lines = output.split("\n")
        assert len(lines) == 4
        assert "─┐" in lines[0]
        assert "─┘" in lines[3]
        # Arrow is on the midpoint row (index 2 for 4 items)
        assert "──▶" in output
        assert "/autonomous-research" in output
        assert "◆" in output  # ultimate glyph

    def test_basic_tier_glyph(self):
        """Basic tier uses the circle glyph."""
        output = render_fusion_diagram(["a", "b", "c"], "result", result_type="basic")
        assert "○" in output

    def test_prereqs_padded_to_equal_width(self):
        """Shorter prereq names are padded so brackets align."""
        output = render_fusion_diagram(["ab", "longername"], "out")
        # Both prereq lines should have the bracket at the same column
        lines = output.split("\n")
        # First line (shorter name) should be padded
        assert "/ab" in lines[0]
        assert "/longername" in lines[2]


def test_render_appraise_card_truncation():
    skill_data = {
        "id": "test-skill",
        "name": "Test Skill",
        "type": "basic",
        "level": "0★",
        "description": "Short description.",
    }
    derivatives = [
        {"id": "d1", "name": "First Derivative Skill Name"},
        {"id": "d2", "name": "Second Derivative Skill Name"},
        {"id": "d3", "name": "Third Derivative Skill Name"},
    ]
    output = render_appraise_card(
        skill_data=skill_data,
        prereq_status={},
        derivatives=derivatives,
        actions=[],
    )
    assert "First Derivative Skill Name" in output
    assert "+2 more" in output
    assert "Second Derivative" not in output

