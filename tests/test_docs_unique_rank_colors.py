"""Regression guard for the Unique-branch color ladder.

The Unique branch forks its own three rungs above 3★ exactly the way the Suite
branch does: 4★ Unique (deep violet, --rank-4-unique) → 5★ Unique Ultimate
(burnished copper, --rank-5-unique) → 6★ Unique Impossible (ember copper,
--rank-6-unique). Several surfaces used to hard-code the 4★ violet for every
Unique rank, so a 5★ Unique Ultimate skill rendered violet instead of copper on
its plaque and in the skill explorer. These tests pin the fork in place.

Widened 2026-09-08 (Issue #1763) to cover every other rendering surface the
same symptom class reached: the badge generator (Python), the rank-badge
element itself (both emitters), the profile-page rank chip, the profile
timeline, and page-ia.js's latent color map.
"""
from pathlib import Path
import importlib.util
import sys

import pytest

pytestmark = [pytest.mark.integration]

ROOT = Path(__file__).resolve().parents[1]

UNIQUE_LADDER = ("--rank-4-unique", "--rank-5-unique", "--rank-6-unique")


def _tokens():
    return (ROOT / "docs" / "css" / "tokens.css").read_text(encoding="utf-8")


def _plaque_css():
    return (ROOT / "docs" / "css" / "plaque.css").read_text(encoding="utf-8")


def _styles_css():
    return (ROOT / "docs" / "css" / "styles.css").read_text(encoding="utf-8")


def _explorer_js():
    return (ROOT / "docs" / "js" / "skill-explorer.js").read_text(encoding="utf-8")


def _profile_timeline_js():
    return (ROOT / "docs" / "js" / "profile-timeline.js").read_text(encoding="utf-8")


def _page_ia_js():
    return (ROOT / "docs" / "js" / "page-ia.js").read_text(encoding="utf-8")


def _rank_badge_js():
    return (ROOT / "docs" / "js" / "rank-badge.js").read_text(encoding="utf-8")


def _generate_profile_pages_source():
    return (ROOT / "scripts" / "generateProfilePages.py").read_text(encoding="utf-8")


def _generate_badges_source():
    return (ROOT / "scripts" / "generateBadges.py").read_text(encoding="utf-8")


def _load_generate_badges():
    """Import ``generateBadges`` by path (the script is not in a package)."""
    sys.path.insert(0, str(ROOT / "scripts"))
    sys.path.insert(0, str(ROOT / "src"))
    spec = importlib.util.spec_from_file_location("generateBadges", ROOT / "scripts" / "generateBadges.py")
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


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


# ── Issue #1763 widening: rank-badge.js / generateProfilePages.py ───────────

def test_rank_badge_js_emits_data_branch_when_known():
    js = _rank_badge_js()
    assert "opts.branch" in js
    assert 'data-branch="' in js
    # Never emitted empty — the attribute must be conditional on opts.branch.
    assert "opts.branch ? ' data-branch=\"'" in js


def test_generate_profile_pages_rank_badge_html_emits_data_branch_when_known():
    src = _generate_profile_pages_source()
    fn = src.split("def rank_badge_html(", 1)[1].split("\ndef ", 1)[0]
    assert "branch" in fn.split("(", 1)[0] or "branch: str | None = None" in fn
    assert 'data-branch="' in fn
    assert "if branch else" in fn, "data-branch must be omitted, never emitted empty"


def test_generate_profile_pages_field_rank_passes_the_derived_branch():
    src = _generate_profile_pages_source()
    fn = src.split("def _field_rank(", 1)[1].split("\ndef ", 1)[0]
    assert "skill_branch(ns)" in fn
    assert "branch=branch" in fn


def test_plaque_js_field_rank_passes_the_derived_branch():
    js = (ROOT / "docs" / "js" / "plaque.js").read_text(encoding="utf-8")
    fn = js.split("function _fieldRank(ns, variant)", 1)[1].split("\n  }", 1)[0]
    assert "branch: branch" in fn


# ── Issue #1763 widening: docs/css/styles.css rank-badge chip ───────────────

def test_styles_css_rank_badge_chip_drops_the_dead_data_tier_selector():
    css = _styles_css()
    assert '.rank-badge[data-tier="unique"]' not in css


def test_styles_css_rank_badge_chip_forks_the_unique_ladder_by_level():
    css = _styles_css()
    base_rule = '.rank-badge[data-branch="unique"] {'
    assert base_rule in css, "base (4★) Unique rung missing from styles.css"
    for level, stem in (("5", "--rank-5-unique"), ("6", "--rank-6-unique")):
        rule = f'.rank-badge[data-branch="unique"][data-level="{level}"]'
        assert rule in css, f"{rule} missing — Unique {level}★ falls back to apex gold"
        block = css.split(rule, 1)[1].split("}", 1)[0]
        assert f"--unique-accent: var({stem})" in block
    chip_selector = '.rank-badge[data-branch="unique"] .rank-badge__chip'
    assert chip_selector in css
    chip_block = css.split(chip_selector, 1)[1].split("}", 1)[0]
    assert "var(--unique-accent" in chip_block, "chip still hard-codes a rung"


# ── Issue #1763 widening: docs/js/profile-timeline.js ───────────────────────

def test_profile_timeline_branch_resolution_reads_the_emitted_field_on_fallback():
    js = _profile_timeline_js()
    fn = js.split("function _branchOf(skill)", 1)[1].split("\n  }", 1)[0]
    # The old code degraded straight to 'standard' with no read of the emitted
    # field, which is exactly why a Unique skill rendered ptl2__dot--standard
    # on a page (the profile page) that never loads skill-semantics.js.
    assert "return 'standard';" not in fn
    assert "skill.branch" in fn


def test_profile_timeline_tier_color_forks_unique_by_rank_and_drops_type_tokens():
    js = _profile_timeline_js()
    color_block = js.split("var TIER_COLOR = {", 1)[1].split("};", 1)[0]
    hex_block = js.split("var TIER_HEX = (function () {", 1)[1].split("}());", 1)[0]
    for block in (color_block, hex_block):
        # suite must read its branch-native apex-gold register, never the
        # fusion TYPE token (--tier-fusion is basic|fusion, not a branch).
        assert "--tier-fusion" not in block
        assert "--apex-gold" in block
        for stem in UNIQUE_LADDER:
            assert stem in block


def test_profile_timeline_dot_css_forks_unique_by_rank():
    js = _profile_timeline_js()
    assert "ptl2__dot--unique-5" in js
    assert "ptl2__dot--unique-6" in js
    assert "--rank-5-unique" in js
    assert "--rank-6-unique" in js


# ── Issue #1763 widening: docs/js/page-ia.js ────────────────────────────────

def test_page_ia_type_color_var_forks_unique_by_rank():
    js = _page_ia_js()
    block = js.split("var TYPE_COLOR_VAR = {", 1)[1].split("};", 1)[0]
    for stem in UNIQUE_LADDER:
        assert stem in block


# ── Issue #1763 widening: scripts/generateBadges.py ─────────────────────────

def test_badge_handle_routes_through_unique_hex():
    src = _generate_badges_source()
    fn = src.split("def badge_handle(", 1)[1].split("\ndef ", 1)[0]
    assert "unique_hex(rank) if is_unique" in fn
    assert "_UNIQUE_COLOR if is_unique" not in fn


def test_write_user_badges_passes_is_unique_to_every_badge_simple_call():
    src = _generate_badges_source()
    fn = src.split("def write_user_badges(", 1)[1].split("\ndef ", 1)[0]
    calls = fn.split("badge_simple(")[1:]
    assert len(calls) == 4, f"expected 4 badge_simple() calls, found {len(calls)}"
    for call in calls:
        head = call.split(")", 1)[0]
        assert "is_unique=is_unique" in head, f"badge_simple call missing is_unique: {call[:80]!r}"


def test_write_user_badges_is_unique_reflects_the_top_skill_branch():
    mod = _load_generate_badges()
    unique_skill = {"level": "5★", "type": "fusion", "branch": "unique", "suiteComponents": []}
    assert mod.skill_branch(unique_skill) == "unique"


# ── Issue #1763 gap A: the contributor DIRECTORY page card chip ────────────

def test_directory_page_rank_badge_call_passes_a_branch():
    """build_directory_page()'s card-chip call site was a fourth instance of
    the missing-branch defect: no `branch=` argument, so a Unique
    contributor's card on /u/ carried no data-branch and fell through to
    apex gold. Pin that the call site derives and passes one, and that it
    guards against skill_branch()'s ValueError on a missing/invalid emitted
    branch rather than letting one bad record break the whole directory build."""
    src = _generate_profile_pages_source()
    fn = src.split("def build_directory_page(", 1)[1].split("\ndef ", 1)[0]
    assert "rank_badge_dir_html = rank_badge_html(" in fn
    call_site = fn.split("rank_badge_dir_html = rank_badge_html(", 1)[1].split(")", 1)[0]
    assert "branch=" in call_site, "directory card chip call site is missing branch="
    assert "skill_branch(" in fn
    assert "except ValueError" in fn, "one bad record must not abort the whole directory build"
