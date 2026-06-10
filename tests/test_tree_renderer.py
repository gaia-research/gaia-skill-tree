"""Tests for _tree_renderer.render_tree — focusing on sub-Ultimate deduplication."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from _tree_renderer import render_tree

# ---------------------------------------------------------------------------
# Minimal skill fixtures
# ---------------------------------------------------------------------------

_BASIC = {"id": "search", "name": "Search", "type": "basic", "level": "0★", "prerequisites": []}

_EXTRA = {
    "id": "deep-search",
    "name": "Deep Search",
    "type": "extra",
    "level": "0★",
    "prerequisites": ["search"],
}

# A 5★ Ultimate that is also a prerequisite of the 6★ below
_SUB_ULT = {
    "id": "engineering",
    "name": "Engineering",
    "type": "ultimate",
    "level": "0★",
    "prerequisites": ["deep-search"],
}

# A 6★ Ultimate whose prereq chain includes the sub-ultimate above
_PARENT_ULT = {
    "id": "skills",
    "name": "Skills",
    "type": "ultimate",
    "level": "0★",
    "prerequisites": ["engineering"],
}

# A standalone 5★ Ultimate with no overlap
_STANDALONE_ULT = {
    "id": "gstack",
    "name": "Gstack",
    "type": "ultimate",
    "level": "0★",
    "prerequisites": ["search"],
}

_ALL_SKILLS = [_BASIC, _EXTRA, _SUB_ULT, _PARENT_ULT, _STANDALONE_ULT]

# named_map: skill_id → display name (makes skills "claimed")
_NAMED_MAP = {
    "skills": "mattpocock/skills",
    "engineering": "mattpocock/engineering",
    "gstack": "garrytan/gstack",
}

_NAMED_LEVEL_MAP = {
    "skills": "6★",
    "engineering": "5★",
    "gstack": "5★",
}


def _render(skills=None, **kwargs):
    return render_tree(
        _ALL_SKILLS if skills is None else skills,
        mode="canonical",
        named_map=_NAMED_MAP,
        named_level_map=_NAMED_LEVEL_MAP,
        version="0.0.0",
        date_str="2026-01-01",
        **kwargs,
    )


def _top_ult_lines(out: str) -> list[str]:
    """Top-level ◆ lines that are actual skill entries, not the legend."""
    return [
        line for line in out.splitlines()
        if line.startswith("◆ ") and "Ultimate ·" not in line
    ]


# ---------------------------------------------------------------------------
# Sub-Ultimate deduplication
# ---------------------------------------------------------------------------

class TestSubUltimateExclusion:
    def test_parent_ultimate_appears_at_top_level(self):
        out = _render()
        assert any("skills" in line for line in _top_ult_lines(out))

    def test_sub_ultimate_not_at_top_level(self):
        out = _render()
        # engineering (5★) is nested inside skills — must NOT be a bare top-level ◆
        top_engineering = [l for l in _top_ult_lines(out) if "engineering" in l]
        assert top_engineering == [], (
            "engineering is a sub-ultimate of skills and should not be a top-level entry"
        )

    def test_standalone_ultimate_at_top_level(self):
        out = _render()
        assert any("gstack" in line for line in _top_ult_lines(out))

    def test_top_level_count_excludes_sub_ultimates(self):
        out = _render()
        # skills + gstack = 2 top-level; engineering is sub-component → excluded
        assert len(_top_ult_lines(out)) == 2

    def test_no_ultimates_produces_no_skill_entries(self):
        out = render_tree([], mode="canonical", version="0.0.0", date_str="2026-01-01")
        assert _top_ult_lines(out) == []

    def test_transitive_sub_ultimate_excluded(self):
        # engineering is a direct prereq of skills → sub-ultimate
        # Verify the sub-id detection works for a 2-hop chain too
        grandparent = {
            "id": "mastery",
            "name": "Mastery",
            "type": "ultimate",
            "level": "0★",
            "prerequisites": ["skills"],   # skills is itself an Ultimate
        }
        all_skills = _ALL_SKILLS + [grandparent]
        named_map = {**_NAMED_MAP, "mastery": "mattpocock/mastery"}
        named_level_map = {**_NAMED_LEVEL_MAP, "mastery": "6★"}
        out = render_tree(
            all_skills,
            mode="canonical",
            named_map=named_map,
            named_level_map=named_level_map,
            version="0.0.0",
            date_str="2026-01-01",
        )
        top = _top_ult_lines(out)
        names_shown = [l for l in top]
        # Only mastery and gstack should appear at top level
        assert len(top) == 2
        assert any("mastery" in l for l in top)
        assert any("gstack" in l for l in top)
        # skills and engineering are transitively nested
        assert not any("skills" in l for l in top)
        assert not any("engineering" in l for l in top)


# ---------------------------------------------------------------------------
# Ordering: higher-star Ultimates sort first (via internal _sorted_ults)
# ---------------------------------------------------------------------------

class TestUltimateOrdering:
    def test_higher_star_sorts_first(self):
        # skills [6★] should appear before gstack [5★] in the output
        out = _render()
        top = _top_ult_lines(out)
        assert len(top) >= 2
        assert "skills" in top[0]
        assert "gstack" in top[1]

    def test_unclaimed_ultimate_sorts_last(self):
        extra_unclaimed = {
            "id": "orphan",
            "name": "Orphan",
            "type": "ultimate",
            "level": "0★",
            "prerequisites": [],
        }
        all_skills = _ALL_SKILLS + [extra_unclaimed]
        out = render_tree(
            all_skills,
            mode="canonical",
            named_map=_NAMED_MAP,           # orphan intentionally absent → Unclaimed
            named_level_map=_NAMED_LEVEL_MAP,
            version="0.0.0",
            date_str="2026-01-01",
        )
        top = _top_ult_lines(out)
        # orphan has no star → must be last
        assert "orphan" in top[-1].lower() or "Orphan" in top[-1]
