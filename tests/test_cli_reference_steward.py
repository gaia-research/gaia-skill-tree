import re
from pathlib import Path


REPO_ROOT = Path(__file__).parent.parent


def test_steward_lifecycle_synopses_wrap_inside_their_card():
    html = (REPO_ROOT / "docs/en/cli-reference.html").read_text(encoding="utf-8")
    rows = re.findall(
        r'<tr class="steward-full-synopsis" data-no-copy>(.*?)</tr>',
        html,
        flags=re.DOTALL,
    )

    assert len(rows) == 4
    for row in rows:
        assert row.count("<td") == 3
        assert "<code>full " in row
        assert "</code>" in row
        assert "style=\"max-width: 420px;\"" in row
        assert "<td>—</td>" in row

    assert "full run [--observe | --triage | --verify | --retro]" in rows[0]
    assert "full record RUN_ID STEP_ID --input FILE.json" in rows[1]
    assert "full abandon RUN_ID --reason TEXT" in rows[2]
    assert "full status [--ledger {auto,git,local}]" in rows[3]
    assert "Run or resume the deterministic pipeline." in rows[0]
    assert "Actions needing a model or forge are emitted for a driver." in rows[0]
    assert "Record a driver's outcome for an action emitted by" in rows[1]
    assert "End an open run with an auditable reason." in rows[2]
    assert "unbuilt work stays adoptable by a later run." in rows[2]
    assert "Read-only view of the ledger and active run." in rows[3]

    steward_table = re.search(
        r'<div class="cmd-card" id="steward">.*?<table class="flag-table" data-no-copy>(.*?)</table>',
        html,
        flags=re.DOTALL,
    )
    assert steward_table is not None
    steward_body = re.search(r"<tbody>(.*?)</tbody>", steward_table.group(1), flags=re.DOTALL)
    assert steward_body is not None
    all_steward_rows = re.findall(r"<tr(?:\s[^>]*)?>.*?</tr>", steward_body.group(1), flags=re.DOTALL)
    assert len(all_steward_rows) == 12
    assert all(row.count("<td") == 3 for row in all_steward_rows)
    for command in (
        "scan [--json]", "run [--json]", "dispatch &lt;debt_id&gt; [--prompt] [--json]",
        "lane status [--json]", "lane next [--prompt] [--json]",
        "lane record &lt;debt_id&gt; --verdict {accept,reject,escalate} [--note &lt;text&gt;]",
        "verify &lt;debt_id&gt; --diff &lt;diff&gt; --proof &lt;json&gt; [--prompt]",
        "founder [--json]", "full run [--observe | --triage | --verify | --retro]",
        "full record RUN_ID STEP_ID --input FILE.json", "full abandon RUN_ID --reason TEXT",
        "full status [--ledger {auto,git,local}]",
    ):
        assert command in steward_table.group(1)

    assert re.search(r'<table class="flag-table" data-no-copy>.*?Subcommand / Flag', html, re.DOTALL)
    assert "#steward .flag-table {\n      table-layout: fixed;" in html
    assert "#steward .flag-table td:first-child {\n      display: table-cell;\n      white-space: normal;\n      overflow-wrap: anywhere;" in html
    assert "#steward .flag-table td:first-child code," in html
    assert "#steward .flag-table th:nth-child(3),\n    #steward .flag-table td:nth-child(3) {\n      width: 15%;" in html
    assert "#steward .flag-table tbody td:nth-child(n) {\n        display: block;\n        width: auto;" in html
    assert "#steward .steward-full-synopsis td code {\n        word-break: normal;\n        overflow-wrap: anywhere;" in html
    assert "#steward .flag-table th {\n        padding-left: 0.35rem;" not in html
    assert "#steward .mini-terminal-screen" not in html
    assert "if (row.closest('[data-no-copy]')) return;" in html
    assert "if (row.hasAttribute('data-no-copy')) return;" not in html

    authored_example = re.search(
        r'<div class="cmd-card" id="steward">.*?<div class="example-block">(.*?)</div>\s*</div>\s*</div>',
        html,
        re.DOTALL,
    )
    assert authored_example is not None
    for example in (
        "gaia steward scan", "gaia steward lane next --prompt", "gaia steward run",
        "gaia steward lane record", "gaia steward full run", "gaia steward full abandon",
    ):
        assert example in authored_example.group(1)
    assert "miniTerminal.className = 'mini-terminal-copy';" in html
