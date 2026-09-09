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
import json
import shutil
import subprocess
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


def _load_generate_profile_pages():
    """Import ``generateProfilePages`` by path (the script is not in a package)."""
    sys.path.insert(0, str(ROOT / "scripts"))
    sys.path.insert(0, str(ROOT / "src"))
    spec = importlib.util.spec_from_file_location(
        "generateProfilePages", ROOT / "scripts" / "generateProfilePages.py")
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


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


def test_profile_timeline_carries_no_unreferenced_branch_color_map():
    """TIER_COLOR / TIER_HEX were branch->color maps with zero consumers.

    Sandbox review on PR #1764 established both were already dead on main.
    Forking their Unique entry by rank made a fictional ladder look
    maintained; a future caller wiring one up would inherit whatever drift
    it had accumulated. The live surface is the ptl2__dot-- CSS below, which
    the next test pins. Keep them deleted rather than kept in lockstep.
    """
    js = _profile_timeline_js()
    assert "var TIER_COLOR" not in js
    assert "var TIER_HEX" not in js
    # resolveVar() must survive the deletion: RANK_HEX and RANK_LINE call it.
    assert "function resolveVar(" in js
    assert js.count("resolveVar(s, expr)") >= 2


def test_profile_timeline_dot_css_forks_unique_by_rank():
    js = _profile_timeline_js()
    assert "ptl2__dot--unique-5" in js
    assert "ptl2__dot--unique-6" in js
    assert "--rank-5-unique" in js
    assert "--rank-6-unique" in js


# ── Issue #1763 widening: docs/js/page-ia.js ────────────────────────────────

def test_page_ia_carries_no_unreferenced_type_color_map():
    """TYPE_COLOR_VAR had zero consumers repo-wide — see the note on
    test_profile_timeline_carries_no_unreferenced_branch_color_map."""
    js = _page_ia_js()
    # the declaration, not the word — a comment may still name it in
    # explaining why it is gone.
    assert "var TYPE_COLOR_VAR" not in js


def test_page_ia_chip_surface_passes_a_branch():
    """chipBadge() passed no branch, so the chip could never match the
    Unique rules.

    Scope, stated honestly: its only caller renders into #ultimatesList,
    an id that appears in no html file in the repo, so this block is
    unmounted today. The PR #1764 review called it "the actual page-ia
    surface the ladder misses"; a live probe of every page that loads
    page-ia.js found the element absent. Fixed so a future mount is correct
    by construction — not because a visitor sees anything wrong now.
    """
    js = _page_ia_js()
    fn = js.split("function chipBadge(", 1)[1].split("\n  }", 1)[0]
    assert "branch:" in fn, "chipBadge() still drops the branch on the floor"
    assert "chipBadge(uLevel, u.branch)" in js, "call site passes no branch"


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


def test_write_user_badges_writes_the_unique_rung_not_the_standard_ladder(tmp_path):
    """Execute the emitter. The previous version of this test asserted
    skill_branch({"branch": "unique"}) == "unique", which tests the fixture,
    not the code under test (flagged in the PR #1764 sandbox review)."""
    mod = _load_generate_badges()
    mod._RANK_COLORS.clear()
    mod._RANK_COLORS.update(mod.load_rank_colors())
    mod._UNIQUE_COLOR = mod.load_tier_color("unique")

    info = {
        "top_skill": {"id": "u/s", "level": "5★", "type": "fusion", "branch": "unique",
                      "rankWord": "Unique Ultimate"},
        "top_rank": 5,
        "count": 1,
        "named_skills": [{"id": "u/s", "level": "5★", "type": "fusion",
                          "branch": "unique", "rankWord": "Unique Ultimate"}],
    }
    mod.write_user_badges("u", info, dict(mod._RANK_COLORS), tmp_path)

    copper = mod.unique_hex(5).lower()
    apex_gold = "#fbbf24"
    violet = "#7c3aed"
    for name in ("rank.svg", "skills.svg", "handle.svg"):
        svg = (tmp_path / "_assets" / "u" / name).read_text(encoding="utf-8").lower()
        assert copper in svg, f"{name}: 5-star Unique lost the copper rung"
        assert violet not in svg, f"{name}: 5-star Unique pinned to the 4-star violet stem"
    # rank/skills carry no gold at all; handle keeps ORIGIN_GOLD by design
    # (rubric E4 gold handle), so only assert the accent is not gold there.
    for name in ("rank.svg", "skills.svg"):
        svg = (tmp_path / "_assets" / "u" / name).read_text(encoding="utf-8").lower()
        assert apex_gold not in svg, f"{name}: Unique Ultimate rendered as a Suite Apex"


# ── Issue #1763 gap A: the contributor DIRECTORY page card chip ────────────

def test_directory_page_rank_badge_call_passes_a_branch():
    """build_directory_page()'s card-chip call site was a fourth instance of
    the missing-branch defect: no `branch=` argument, so a Unique
    contributor's card on /u/ carried no data-branch and fell through to
    apex gold. Pin that the call site derives and passes one, and that it
    resolves the branch the same fail-fast way every other call site in the
    module does.

    The original version of this guard swallowed skill_branch()'s ValueError
    "so one bad record can't break the directory build". Sandbox review on
    PR #1764 disproved that: generate_pages() builds the per-user pages
    first, and _field_orb calls skill_branch() unguarded, so a bad record
    aborts long before the directory is reached. The except bought a quieter
    failure, not a survivable one — and a silently uncoloured rank chip is
    the exact defect class this file exists to catch."""
    src = _generate_profile_pages_source()
    fn = src.split("def build_directory_page(", 1)[1].split("\ndef ", 1)[0]
    assert "rank_badge_dir_html = rank_badge_html(" in fn
    call_site = fn.split("rank_badge_dir_html = rank_badge_html(", 1)[1].split(")", 1)[0]
    assert "branch=" in call_site, "directory card chip call site is missing branch="
    assert "skill_branch(" in fn
    assert "except ValueError" not in fn, (
        "directory build must fail fast on a stale/invalid emitted branch, "
        "matching _field_orb / _field_rank / _shell"
    )


# ── PR #1764 review follow-up: execute BOTH emitters and compare bytes ──────

def test_rank_badge_emitters_agree_byte_for_byte():
    """The one test the grep-only suite could not provide.

    Every other guard here `.split()`s a source file and asserts on
    substrings, so none of them executes an emitter — a drift in attribute
    ORDER or attribute SET between docs/js/rank-badge.js and its Python
    sibling in scripts/generateProfilePages.py would sail straight past.
    The two emit the markup that the CSS ladder keys on, on the client and
    the server respectively; if they disagree, one surface silently loses
    its branch and falls back to the standard ladder.

    Runs the real JS under node against the real Python function.
    """
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not available")

    src = _load_generate_profile_pages()

    cases = [
        ("5★", "chip", "md", "unique"),
        ("4★", "stars", "sm", "unique"),
        ("6★", "full", "lg", "suite"),
        ("3★", "chip", "md", "standard"),
        ("5★", "chip", "md", None),
        ("5★", "chip", "md", ""),
    ]

    js_src = (ROOT / "docs" / "js" / "rank-badge.js").read_text(encoding="utf-8")
    payload = json.dumps([
        {"level": lv, "variant": v, "size": s, "branch": b} for lv, v, s, b in cases
    ])
    driver = (
        "var window = {};\n"
        + js_src
        + "\nvar cases = " + payload + ";\n"
        "console.log(JSON.stringify(cases.map(function (c) {\n"
        "  var o = { variant: c.variant, size: c.size, label: c.level };\n"
        "  if (c.branch) o.branch = c.branch;\n"
        "  return window.rankBadge(c.level, o);\n"
        "})));\n"
    )
    out = subprocess.run([node, "-e", driver], capture_output=True, text=True, check=True)
    js_out = json.loads(out.stdout)

    for (level, variant, size, branch), js_html in zip(cases, js_out):
        py_html = src.rank_badge_html(
            level, variant=variant, size=size, label=level, branch=branch
        )
        assert py_html == js_html, (
            f"emitter drift for level={level} variant={variant} size={size} "
            f"branch={branch!r}\n  js: {js_html}\n  py: {py_html}"
        )


def test_rank_badge_emitters_omit_an_unknown_branch_rather_than_emitting_it_empty():
    """data-branch="" would match no rule but still read as 'branch resolved'.
    Both emitters must leave the attribute off entirely instead."""
    src = _load_generate_profile_pages()
    for falsy in (None, ""):
        html_out = src.rank_badge_html("5★", variant="chip", label="5★", branch=falsy)
        assert "data-branch" not in html_out
