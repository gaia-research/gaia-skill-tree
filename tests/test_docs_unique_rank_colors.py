"""Regression guard for the Unique-branch color ladder.

The Unique branch forks its own three rungs above 3★ exactly the way the Suite
branch does: 4★ Unique (deep violet, --rank-4-unique) → 5★ Unique Ultimate
(burnished copper, --rank-5-unique) → 6★ Unique Impossible (ember copper,
--rank-6-unique). Several surfaces used to hard-code the 4★ violet for every
Unique rank, so a 5★ Unique Ultimate skill rendered violet instead of copper on
its plaque and in the skill explorer. These tests pin the fork in place.
"""
from pathlib import Path
import pytest

pytestmark = [pytest.mark.integration]

ROOT = Path(__file__).resolve().parents[1]

UNIQUE_LADDER = ("--rank-4-unique", "--rank-5-unique", "--rank-6-unique")


def _tokens():
    return (ROOT / "docs" / "css" / "tokens.css").read_text(encoding="utf-8")


def _plaque_css():
    return (ROOT / "docs" / "css" / "plaque.css").read_text(encoding="utf-8")


def _explorer_js():
    return (ROOT / "docs" / "js" / "skill-explorer.js").read_text(encoding="utf-8")


def test_unique_ladder_tokens_are_all_defined():
    css = _tokens()
    for stem in UNIQUE_LADDER:
        assert f"{stem}:" in css, f"{stem} missing from tokens.css"
        assert f"{stem}-rgb:" in css, f"{stem}-rgb missing from tokens.css"


def test_plaque_accent_forks_the_unique_ladder_by_level():
    css = _plaque_css()
    for level, stem in (("5", "--rank-5-unique"), ("6", "--rank-6-unique")):
        rule = f'.plaque[data-branch="unique"][data-level="{level}"]'
        assert rule in css, f"{rule} missing — Unique {level}★ falls back to 4★ violet"
        block = css.split(rule, 1)[1].split("}", 1)[0]
        assert f"--plaque-accent: var({stem})" in block


def test_plaque_slug_and_stars_read_the_forked_unique_accent():
    css = _plaque_css()
    # The slug/star rules must read the resolved rung, never the 4★ stem direct.
    assert "--unique-accent: var(--rank-5-unique)" in css
    assert "--unique-accent: var(--rank-6-unique)" in css
    for selector in (
        '.plaque[data-branch="unique"] .plaque-skill-name.named-slug',
        '.plaque[data-branch="unique"] .rank-badge__star[data-on]',
    ):
        assert selector in css
        block = css.split(selector, 1)[1].split("}", 1)[0]
        assert "var(--unique-accent" in block, f"{selector} still hard-codes a rung"


def test_plaque_unique_hover_glow_tracks_the_resolved_accent():
    css = _plaque_css()
    block = css.split('.plaque[data-branch="unique"]:hover', 1)[1].split("}", 1)[0]
    assert "--rank-4-unique-rgb" not in block
    assert "var(--plaque-accent-rgb)" in block


def test_skill_explorer_resolves_the_unique_rung_by_rank():
    js = _explorer_js()
    assert "function _seUniqueStem(rank)" in js
    stem_fn = js.split("function _seUniqueStem(rank)", 1)[1].split("\n  }", 1)[0]
    for stem in UNIQUE_LADDER:
        assert f"'{stem}'" in stem_fn
    # _seBranchColor must route through the rung resolver, not a fixed token.
    branch_fn = js.split("function _seBranchColor(branch, isApex, level)", 1)[1].split("\n  }", 1)[0]
    assert "_seUniqueStem(level)" in branch_fn
    assert "'var(--rank-4-unique)'" not in branch_fn


def test_skill_explorer_breadcrumb_slug_is_not_pinned_to_the_4_star_violet():
    js = _explorer_js()
    # No live code path may emit the 4★ token as a literal color for the branch.
    for line in js.splitlines():
        code = line.split("//", 1)[0]
        if "var(--rank-4-unique)" in code:
            pytest.fail(f"hard-coded 4★ Unique color in live code: {line.strip()}")
