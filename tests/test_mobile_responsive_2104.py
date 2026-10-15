from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).parent.parent


def test_leaderboard_css_mobile_rules():
    css = (REPO_ROOT / "docs/trust/leaderboard/leaderboard.css").read_text(encoding="utf-8")
    
    # Meta shift banner stacks cleanly
    assert ".lb-meta-shift-banner" in css
    assert "flex-direction: column" in css
    assert ".lb-meta-shift-text" in css

    # Controls wrap cleanly without clipping
    assert ".lb-panel-filters .lb-section-meta" in css
    assert "max-width: 100%" in css
    assert ".lb-skill-search" in css

    # Evidence type tabs scrollable rail
    assert ".lb-typetabs" in css
    assert "overflow-x: auto" in css
    assert "flex-wrap: nowrap" in css
    assert ".lb-panel-watermark" in css
    assert "display: none" in css

    # Scroll margins clear fixed nav
    assert "scroll-margin-top: 5rem" in css
    assert "#trust-preview" in css
    assert "#lbNamed" in css


def test_styles_css_mobile_rules():
    css = (REPO_ROOT / "docs/css/styles.css").read_text(encoding="utf-8")

    # HoH mini shift banner stacks cleanly
    assert ".hoh-mini-shift-banner" in css
    assert "flex-direction: column" in css
    assert "min-height: 44px" in css

    # Sticky controls clear fixed nav
    assert ".ns-controls--sticky" in css
    assert "top: 58px" in css


def test_world_tree_hero_mobile_clearance():
    css = (REPO_ROOT / "docs/css/world-tree-hero.css").read_text(encoding="utf-8")

    # Hero content clears utilities
    assert "padding-top: 5rem" in css
    # Hero copy background bed constrained
    assert "inset: -1.5rem -0.5rem -2.25rem" in css


def test_leaderboard_js_mobile_adaptations():
    js = (REPO_ROOT / "docs/trust/leaderboard/leaderboard.js").read_text(encoding="utf-8")

    # Total width adaptive to container width
    assert "Math.min(chartContainerW(), 320)" in js

    # Dense mobile bars omit unrotated overlapping sub-labels
    assert "if (!isMobileViewport())" in js
