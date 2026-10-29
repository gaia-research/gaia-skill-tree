"""Source-contract checks; rendered layout is verified separately in Chromium."""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).parent.parent
HTML_PATH = REPO_ROOT / "docs/en/cli-reference.html"


def steward_rows():
    html = HTML_PATH.read_text(encoding="utf-8")
    table = re.search(
        r'<div class="cmd-card" id="steward">.*?<table class="flag-table">(.*?)</table>',
        html,
        re.DOTALL,
    )
    assert table is not None
    body = re.search(r"<tbody>(.*?)</tbody>", table.group(1), re.DOTALL)
    assert body is not None
    return html, re.findall(r"<tr(?:\s[^>]*)?>.*?</tr>", body.group(1), re.DOTALL)


def test_steward_keeps_complete_reference_behind_short_overviews():
    _, rows = steward_rows()
    assert len(rows) == 12
    assert all(row.count("<td") == 3 for row in rows)
    summaries = [re.search(r'data-summary="([^"]+)"', row).group(1) for row in rows]
    assert len(set(summaries)) == 12
    assert all(len(summary) <= 65 for summary in summaries)
    for row, command in zip(rows[-4:], (
        "full run [--observe | --triage | --verify | --retro]",
        "full record RUN_ID STEP_ID --input FILE.json",
        "full abandon RUN_ID --reason TEXT",
        "full status [--ledger {auto,git,local}]",
    )):
        assert command in row
        assert "<td>—</td>" in row
    assert "[--no-agents] [--integration-branch B] [--push]" in rows[-4]
    assert "Actions needing a model or forge are emitted for a driver." in rows[-4]
    assert "Never merges or pushes to main." in summaries[-4]
    assert "Never merges or pushes to <code>main</code>." in rows[-4]
    assert "Record a driver's outcome for an action emitted by" in rows[-3]
    assert "unbuilt work stays adoptable by a later run." in rows[-2]
    assert "Read-only view of the ledger and active run." in rows[-1]


def test_disclosure_enhances_all_tables_without_inferred_commands():
    html, _ = steward_rows()
    assert len(re.findall(r'<table class="flag-table"', html)) == 31
    assert "document.querySelectorAll('.flag-table').forEach" in html
    assert "document.createElement('details')" in html
    assert "document.createElement('summary')" in html
    assert "node.cloneNode(true)" in html  # Preserve links and inline markup.
    assert "table.hidden = true" in html
    assert ".flag-table[hidden]" in html
    assert "@media print" in html
    assert "@media (min-width: 768px)" in html
    assert "min-height: 44px" in html
    assert "summary:focus-visible" in html
    assert "mini-terminal" not in html
    assert "cleanFlag" not in html
    assert "navigator.clipboard" not in html  # Shared ui.js owns copying.
    assert html.index('src="../js/icons.js?') < html.index('src="../js/ui.js?')
    assert 'data-icon-base="../assets/icons.svg"' in html
    assert re.search(r"\.reference-name\s*\{[^}]*word-break: normal;[^}]*overflow-wrap: normal;", html)
    assert ".reference-toggle-label" in html
    assert "token.className = 'reference-token'" in html
    assert re.search(r"\.reference-body \.reference-token\s*\{\s*white-space: nowrap;", html)
    for example in (
        "gaia steward scan", "gaia steward lane next --prompt", "gaia steward run",
        "gaia steward lane record", "gaia steward full run", "gaia steward full abandon",
    ):
        assert example in html


@pytest.mark.parametrize(("syntax", "expected"), [
    ("scan [--json]", "scan"),
    ("full run [--observe | --triage]", "full run"),
    ("full record RUN_ID STEP_ID --input FILE.json", "full record"),
    ("full abandon RUN_ID --reason TEXT", "full abandon"),
    ("--output, -o <path>", "--output, -o"),
    ("<skillId>", "<skillId>"),
])
def test_short_names_omit_placeholder_tails_without_losing_subcommands(syntax, expected):
    node = shutil.which("node")
    if node is None:
        pytest.skip("Optional JavaScript source check requires Node.js")
    html = HTML_PATH.read_text(encoding="utf-8")
    function = re.search(r"function conciseName\(syntax\) \{.*?\n      \}", html, re.DOTALL)
    assert function is not None
    script = function.group(0) + "\nprocess.stdout.write(JSON.stringify(conciseName(" + json.dumps(syntax) + ")));"
    result = subprocess.run([node, "-e", script], text=True, capture_output=True, check=True)
    assert json.loads(result.stdout) == expected
