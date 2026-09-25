"""Regression tests for user-facing post report rendering."""

from __future__ import annotations

import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "add_post.py"


def _load_add_post():
    spec = importlib.util.spec_from_file_location("add_post", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_md_to_html_preserves_accessible_figure_as_block():
    """A report's SVG figure must not be wrapped in a paragraph."""
    figure = (
        '<figure id="decision-funnel">\n'
        '  <img src="assets/chart.svg" alt="Decision outcomes" />\n'
        '  <figcaption>Figure 1. Outcomes.</figcaption>\n'
        "</figure>"
    )

    rendered = _load_add_post().md_to_html(f"Before the figure.\n\n{figure}\n\nAfter it.")

    assert "<p>Before the figure.</p>" in rendered
    assert figure in rendered
    assert "<p><figure" not in rendered
    assert "<p>After it.</p>" in rendered


def test_report_html_has_no_trailing_whitespace_without_chart():
    rendered = _load_add_post().render_report_html(
        title="Test report",
        author="Gaia Research",
        display_date="September 25, 2026",
        abstract="A short abstract.",
        body_html="<p>Body.</p>",
        download_name="test-report.html",
    )

    assert all(line == line.rstrip() for line in rendered.splitlines())
