"""Tests for gaia_cli.interactive module.

Validates graceful degradation when questionary is not installed
or when running in a non-interactive context.
"""

import os
import sys
from unittest.mock import patch

import pytest

from gaia_cli.interactive import (
    FuseCancelled,
    _format_id,
    _fuse_sort_key,
    _fusion_flowchart_frags,
    _has_interactive,
    confirm,
    select_fusion_candidate,
    select_fusion_to_edit,
    select_multiple_skills,
    select_promotion_candidate,
    select_push_batch,
    select_skill,
)
pytestmark = [pytest.mark.integration]


class TestHasInteractive:
    """Tests for _has_interactive() detection logic."""

    def test_returns_false_when_stdin_not_tty(self, monkeypatch):
        monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
        monkeypatch.delenv("CI", raising=False)
        assert _has_interactive() is False

    def test_returns_false_when_ci_env_set(self, monkeypatch):
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        monkeypatch.setenv("CI", "true")
        assert _has_interactive() is False

    def test_returns_false_when_questionary_missing(self, monkeypatch):
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        monkeypatch.delenv("CI", raising=False)
        with patch.dict(sys.modules, {"questionary": None}):
            # Simulate ImportError by removing the module
            import importlib
            with patch("builtins.__import__", side_effect=_make_import_raiser("questionary")):
                assert _has_interactive() is False

    def test_returns_true_when_all_conditions_met(self, monkeypatch):
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        monkeypatch.delenv("CI", raising=False)
        # questionary may or may not be installed; mock it as available
        with patch("builtins.__import__", side_effect=_make_import_passer("questionary")):
            assert _has_interactive() is True


class TestSelectSkill:
    """Tests for select_skill() in non-interactive mode."""

    def test_returns_none_when_non_interactive(self, monkeypatch):
        monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
        skills = [{"id": "python-basics", "type": "basic", "level": "1"}]
        assert select_skill(skills) is None

    def test_returns_none_with_empty_skills(self, monkeypatch):
        monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
        assert select_skill([]) is None


class TestSelectFusionCandidate:
    """Tests for select_fusion_candidate() in non-interactive mode."""

    def test_returns_none_when_non_interactive(self, monkeypatch):
        monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
        candidates = [
            {"candidateResult": "advanced-python", "detectedSkills": ["python-basics", "oop"]}
        ]
        assert select_fusion_candidate(candidates) is None

    def test_returns_none_with_empty_candidates(self, monkeypatch):
        monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
        assert select_fusion_candidate([]) is None


class TestSelectPromotionCandidate:
    """Tests for select_promotion_candidate() in non-interactive mode."""

    def test_returns_none_when_non_interactive(self, monkeypatch):
        monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
        candidates = [
            {"skillId": "python-basics", "currentLevel": "1", "suggestedLevel": "2"}
        ]
        assert select_promotion_candidate(candidates) is None


class TestConfirm:
    """Tests for confirm() in non-interactive mode."""

    def test_returns_default_true_when_non_interactive(self, monkeypatch):
        monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
        assert confirm("Proceed?", default=True) is True

    def test_returns_default_false_when_non_interactive(self, monkeypatch):
        monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
        assert confirm("Proceed?", default=False) is False


# ===========================================================================
# Wave 3 / Agent 3B additions
# ===========================================================================

class TestFuseCancelled:
    """FuseCancelled is a proper Exception subclass."""

    def test_is_exception_subclass(self):
        assert issubclass(FuseCancelled, Exception)

    def test_can_be_raised_and_caught(self):
        with pytest.raises(FuseCancelled):
            raise FuseCancelled("cancelled by user")

    def test_can_be_raised_without_args(self):
        with pytest.raises(FuseCancelled):
            raise FuseCancelled()

    def test_isinstance_check(self):
        exc = FuseCancelled("test")
        assert isinstance(exc, Exception)
        assert isinstance(exc, FuseCancelled)


class TestFormatId:
    """_format_id normalises skill IDs for display."""

    def test_generic_id_gets_leading_slash(self):
        assert _format_id("code-review") == "/code-review"

    def test_already_slash_prefixed_unchanged(self):
        assert _format_id("/already") == "/already"

    def test_contributor_slash_id_stays_bare(self):
        # "alice/tool" contains an interior slash → returned as-is (no leading slash)
        result = _format_id("alice/tool")
        assert result == "alice/tool"

    def test_no_double_slash_generic(self):
        result = _format_id("code-review")
        assert "//" not in result

    def test_no_double_slash_already_slashed(self):
        result = _format_id("/already")
        assert "//" not in result

    def test_no_double_slash_contributor(self):
        result = _format_id("alice/tool")
        assert "//" not in result

    def test_leading_slash_stripped_before_check(self):
        # An ID that was previously slash-prefixed generics must not get double-slash
        result = _format_id("/my-skill")
        assert result == "/my-skill"
        assert "//" not in result


class TestFuseSortKey:
    """_fuse_sort_key orders skills: Custom (0) < Starless (1) < Named (2) < Origin (3)."""

    def _custom(self):
        return {"id": "custom-skill", "local": True, "origin": False}

    def _starless(self):
        return {"id": "code-review", "local": False, "origin": False}

    def _named(self):
        return {"id": "tool", "local": False, "origin": False, "named_ref": "alice/tool"}

    def _origin(self):
        return {"id": "origin-tool", "local": False, "origin": True, "named_ref": "bob/tool"}

    def test_custom_is_bucket_zero(self):
        key = _fuse_sort_key(self._custom())
        assert key[0] == 0

    def test_starless_is_bucket_one(self):
        key = _fuse_sort_key(self._starless())
        assert key[0] == 1

    def test_named_is_bucket_two(self):
        key = _fuse_sort_key(self._named())
        assert key[0] == 2

    def test_origin_is_bucket_three(self):
        key = _fuse_sort_key(self._origin())
        assert key[0] == 3

    def test_sorted_order_custom_first(self):
        items = [self._origin(), self._named(), self._starless(), self._custom()]
        result = sorted(items, key=_fuse_sort_key)
        ids = [s["id"] for s in result]
        assert ids[0] == "custom-skill"

    def test_sorted_order_origin_last(self):
        items = [self._origin(), self._named(), self._starless(), self._custom()]
        result = sorted(items, key=_fuse_sort_key)
        ids = [s["id"] for s in result]
        assert ids[-1] == "origin-tool"

    def test_full_sorted_order(self):
        items = [self._origin(), self._named(), self._starless(), self._custom()]
        result = sorted(items, key=_fuse_sort_key)
        assert [s["id"] for s in result] == [
            "custom-skill",   # 0 — custom
            "code-review",    # 1 — starless
            "tool",           # 2 — named
            "origin-tool",    # 3 — origin
        ]

    def test_tiebreak_is_id_alphabetical(self):
        """Within the same bucket, sort is alphabetical by id."""
        a = {"id": "aardvark", "local": False, "origin": False}
        b = {"id": "zebra", "local": False, "origin": False}
        assert _fuse_sort_key(a) < _fuse_sort_key(b)


class TestFusionFlowchartFrags:
    """_fusion_flowchart_frags renders fusion definitions as flowchart text."""

    def _text(self, frags: list) -> str:
        return "".join(t for _, t in frags)

    def test_single_source_contains_target_id(self):
        frags, _ = _fusion_flowchart_frags(
            target_id="my-fusion",
            sources=["source-skill"],
            fusion_level="3★",
            skill_meta={},
        )
        text = self._text(frags)
        assert "my-fusion" in text

    def test_single_source_contains_source_id(self):
        frags, _ = _fusion_flowchart_frags(
            target_id="my-fusion",
            sources=["source-skill"],
            fusion_level="3★",
            skill_meta={},
        )
        text = self._text(frags)
        assert "source-skill" in text

    def test_single_source_contains_arrow(self):
        frags, _ = _fusion_flowchart_frags(
            target_id="my-fusion",
            sources=["source-skill"],
            fusion_level="3★",
            skill_meta={},
        )
        text = self._text(frags)
        # Arrow character in single-source case: ──→
        assert "→" in text

    def test_single_source_line_count_is_one(self):
        _, line_count = _fusion_flowchart_frags(
            target_id="my-fusion",
            sources=["source-skill"],
            fusion_level="3★",
            skill_meta={},
        )
        assert line_count == 1

    def test_multi_source_contains_target_id(self):
        frags, _ = _fusion_flowchart_frags(
            target_id="mega-fusion",
            sources=["skill-a", "skill-b"],
            fusion_level="4★",
            skill_meta={},
        )
        text = self._text(frags)
        assert "mega-fusion" in text

    def test_multi_source_contains_all_sources(self):
        frags, _ = _fusion_flowchart_frags(
            target_id="mega-fusion",
            sources=["skill-a", "skill-b"],
            fusion_level="4★",
            skill_meta={},
        )
        text = self._text(frags)
        assert "skill-a" in text
        assert "skill-b" in text

    def test_multi_source_contains_box_drawing_chars(self):
        """Multi-source layout uses box-drawing characters (┌, └, ├)."""
        frags, _ = _fusion_flowchart_frags(
            target_id="mega-fusion",
            sources=["skill-a", "skill-b"],
            fusion_level="4★",
            skill_meta={},
        )
        text = self._text(frags)
        # At least one box-drawing character must appear
        box_chars = set("┌└├─")
        assert any(ch in text for ch in box_chars), (
            f"Expected box-drawing chars in multi-source flowchart, got: {text!r}"
        )

    def test_multi_source_contains_arrow(self):
        frags, _ = _fusion_flowchart_frags(
            target_id="mega-fusion",
            sources=["skill-a", "skill-b"],
            fusion_level="4★",
            skill_meta={},
        )
        text = self._text(frags)
        assert "→" in text

    def test_multi_source_line_count_equals_sources_plus_one(self):
        """line_count = len(sources) + 1 (one line per source + target line)."""
        _, line_count = _fusion_flowchart_frags(
            target_id="mega-fusion",
            sources=["skill-a", "skill-b"],
            fusion_level="4★",
            skill_meta={},
        )
        assert line_count == 3  # 2 sources + 1 target

    def test_three_source_line_count(self):
        _, line_count = _fusion_flowchart_frags(
            target_id="triple",
            sources=["a", "b", "c"],
            fusion_level="5★",
            skill_meta={},
        )
        assert line_count == 4  # 3 sources + 1 target

    def test_line_count_consistent_with_newlines(self):
        """line_count must equal the number of rendered newlines + 1 (for the last line)."""
        for n_sources in [1, 2, 3]:
            sources = [f"src-{i}" for i in range(n_sources)]
            frags, line_count = _fusion_flowchart_frags(
                target_id="target",
                sources=sources,
                fusion_level="2★",
                skill_meta={},
            )
            text = self._text(frags)
            newline_count = text.count("\n")
            # line_count == newlines + 1 for single-source (no trailing newline),
            # for multi-source it's len(sources)+1 lines total
            assert line_count == newline_count + 1, (
                f"n_sources={n_sources}: expected line_count={newline_count+1}, got {line_count}"
            )

    def test_no_source_returns_target_only(self):
        frags, line_count = _fusion_flowchart_frags(
            target_id="empty-fusion",
            sources=[],
            fusion_level="2★",
            skill_meta={},
        )
        text = self._text(frags)
        assert "empty-fusion" in text
        assert line_count == 1

    def test_returns_list_of_two_tuples(self):
        frags, _ = _fusion_flowchart_frags(
            target_id="f", sources=["s"], fusion_level="1★", skill_meta={}
        )
        assert isinstance(frags, list)
        for item in frags:
            assert isinstance(item, tuple) and len(item) == 2


class TestNonInteractiveFallbacks:
    """Each select_* function returns its documented fallback when _has_interactive() is False."""

    def _patch_non_interactive(self, monkeypatch):
        """Patch _has_interactive to return False in all relevant modules."""
        monkeypatch.setattr("gaia_cli.interactive._has_interactive", lambda: False)

    # select_skill → None

    def test_select_skill_returns_none(self, monkeypatch):
        self._patch_non_interactive(monkeypatch)
        result = select_skill([{"id": "python-basics", "type": "basic", "level": "1★"}])
        assert result is None

    def test_select_skill_returns_none_empty_list(self, monkeypatch):
        self._patch_non_interactive(monkeypatch)
        assert select_skill([]) is None

    # select_fusion_candidate → None

    def test_select_fusion_candidate_returns_none(self, monkeypatch):
        self._patch_non_interactive(monkeypatch)
        candidates = [{"candidateResult": "fusion-a", "detectedSkills": ["a", "b"]}]
        result = select_fusion_candidate(candidates)
        assert result is None

    def test_select_fusion_candidate_returns_none_empty(self, monkeypatch):
        self._patch_non_interactive(monkeypatch)
        assert select_fusion_candidate([]) is None

    # select_promotion_candidate → None

    def test_select_promotion_candidate_returns_none(self, monkeypatch):
        self._patch_non_interactive(monkeypatch)
        candidates = [{"skillId": "skill-a", "currentLevel": "1★", "suggestedLevel": "2★"}]
        result = select_promotion_candidate(candidates)
        assert result is None

    def test_select_promotion_candidate_returns_none_empty(self, monkeypatch):
        self._patch_non_interactive(monkeypatch)
        assert select_promotion_candidate([]) is None

    # select_multiple_skills → []

    def test_select_multiple_skills_returns_empty_list(self, monkeypatch):
        self._patch_non_interactive(monkeypatch)
        result = select_multiple_skills([{"id": "skill-a"}, {"id": "skill-b"}])
        assert result == []

    def test_select_multiple_skills_returns_empty_list_on_empty_input(self, monkeypatch):
        self._patch_non_interactive(monkeypatch)
        assert select_multiple_skills([]) == []

    # select_push_batch → []

    def test_select_push_batch_returns_empty_list(self, monkeypatch):
        self._patch_non_interactive(monkeypatch)
        batch = {
            "knownSkills": [{"skillId": "skill-a", "localId": "skill-a"}],
            "proposedCombinations": [],
        }
        result = select_push_batch(batch)
        assert result == []

    def test_select_push_batch_returns_empty_list_on_empty_batch(self, monkeypatch):
        self._patch_non_interactive(monkeypatch)
        assert select_push_batch({}) == []

    # select_fusion_to_edit → None

    def test_select_fusion_to_edit_returns_none(self, monkeypatch):
        self._patch_non_interactive(monkeypatch)
        fusions = {"my-fusion": {"sources": ["a", "b"], "level": "3★"}}
        result = select_fusion_to_edit(fusions)
        assert result is None

    def test_select_fusion_to_edit_returns_none_empty(self, monkeypatch):
        self._patch_non_interactive(monkeypatch)
        assert select_fusion_to_edit({}) is None


# -- Helpers --

def _make_import_raiser(blocked_module):
    """Create an __import__ side_effect that raises ImportError for a specific module."""
    real_import = __builtins__.__import__ if hasattr(__builtins__, "__import__") else __import__

    def _import(name, *args, **kwargs):
        if name == blocked_module:
            raise ImportError(f"No module named '{blocked_module}'")
        return real_import(name, *args, **kwargs)

    return _import


def _make_import_passer(allowed_module):
    """Create an __import__ side_effect that returns a mock for a specific module."""
    from unittest.mock import MagicMock
    real_import = __builtins__.__import__ if hasattr(__builtins__, "__import__") else __import__

    def _import(name, *args, **kwargs):
        if name == allowed_module:
            return MagicMock()
        return real_import(name, *args, **kwargs)

    return _import
