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


def test_report_tables_remain_semantic_and_are_keyboard_scrollable():
    rendered = _load_add_post().md_to_html(
        "| Case | Challenger | Compared against | Runner outcome | Meta verification | Admitted |\n"
        "|---|---|---|---|---|---|\n"
        "| C1 | Graphify | graft caller lookup | Contradicted (a tie) | Upheld | No |"
    )

    assert '<div class="report-table-scroll" role="region"' in rendered
    assert 'aria-label="Scrollable report table" tabindex="0">' in rendered
    assert "<table><thead><tr><th>Case</th>" in rendered
    assert "<tbody><tr><td>C1</td>" in rendered
    assert rendered.index('<div class="report-table-scroll"') < rendered.index("<table>")
    assert rendered.endswith("</table></div>")


def test_report_html_has_no_trailing_whitespace_without_chart():
    rendered = _load_add_post().render_report_html(
        title="Test report",
        author="Gaia Research",
        display_date="September 25, 2026",
        abstract="A short abstract.",
        body_html="<p>Body.</p>",
        download_name="test-report.html",
    )

    assert ".paper-journal-header {" in rendered
    assert ".paper-journal-header {{" not in rendered
    assert ".report-table-scroll { max-width: 100%; overflow-x: auto;" in rendered
    assert ".report-table-scroll:focus-visible" in rendered
    assert "table { width: max-content; min-width: 100%;" in rendered
    assert all(line == line.rstrip() for line in rendered.splitlines())
