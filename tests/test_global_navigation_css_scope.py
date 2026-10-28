from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
STYLES = (ROOT / "docs/css/styles.css").read_text(encoding="utf-8")


def test_fixed_site_navigation_is_scoped_to_site_header():
    assert re.search(r"(?m)^#site-nav\s*\{[^}]*position:\s*fixed", STYLES)
    assert "nav:not(.footer-cols):not(.footer-rail)" not in STYLES


def test_mobile_navigation_layout_selectors_are_scoped_to_site_header():
    assert re.search(r"(?m)^\s*#site-nav\s*\{", STYLES)
    assert re.search(r"(?m)^\s*#site-nav ul\s*\{", STYLES)
    assert ".home-page #site-nav {" in STYLES
    assert re.search(r"(?m)^\s*nav\s*\{", STYLES) is None
    assert re.search(r"(?m)^\s*nav ul\s*\{", STYLES) is None
    assert ".home-page nav {" not in STYLES


def test_report_navigation_remains_in_normal_flow():
    assert re.search(r"(?m)^\.report-navlinks\s*\{\s*position:\s*static;", STYLES)
    assert ".report-navlinks" in (
        ROOT / "scripts/contentEngine/templates/report.html.j2"
    ).read_text(encoding="utf-8")
