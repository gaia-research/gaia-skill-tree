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

    assert "#steward .flag-table {\n      table-layout: fixed;" in html
    assert "#steward .flag-table .flag-text {\n      white-space: normal;\n      overflow-wrap: anywhere;" in html
    assert "#steward .steward-full-synopsis td:first-child {\n      display: table-cell;" in html
    assert "overflow-wrap: anywhere;\n      white-space: normal;" in html
    assert "if (row.hasAttribute('data-no-copy')) return;" in html
