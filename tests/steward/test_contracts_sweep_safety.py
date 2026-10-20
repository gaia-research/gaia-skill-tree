"""A corrupted contract subject must keep its debt open (UNKNOWN is never PASS).

Same shape as ``test_sweep_safety``: one controller scan opens real debt, exactly
that subject is corrupted, a second scan runs, and the debt is still open with
the sensor listed under ``partialCoverage``. Legitimate HTML fragments are not
failures and must never be reported as skips.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from gaia_cli.steward import sensors_contracts
from gaia_cli.steward.controller import StewardController
from gaia_cli.steward.primitives import SensorUnavailable
from gaia_cli.steward.sensors_contracts import FrontendContractSensor, TimelineCausalitySensor
from tests.steward.test_sweep_safety import (
    NOW,
    Clock,
    assert_unswept,
    fixture,
    open_ids,
    partial,
    scan_twice,
)

BAD_ORDER = (
    "---\nid: o/a\ntimeline:\n"
    '  - action: x\n    timestamp: "2026-06-11T00:00:00Z"\n'
    '  - action: y\n    timestamp: "2026-06-10T00:00:00Z"\n'
    "---\n# A\n"
)
GOOD = '---\nid: o/b\ntimeline:\n  - action: x\n    timestamp: "2026-06-10T00:00:00Z"\n---\n# B\n'
TIMELINE_FILES = {"registry/named/o/a.md": BAD_ORDER, "registry/named/o/b.md": GOOD}

PAGE = (
    '<!doctype html>\n<html lang="en">\n<head>\n'
    '<meta name="viewport" content="width=device-width">\n<title>{title}</title>\n</head>\n<body></body>\n</html>\n'
)
NO_LANG = PAGE.replace('<html lang="en">', "<html>").format(title="A")
FRONTEND_FILES = {"docs/a.html": NO_LANG, "docs/b.html": PAGE.format(title="B")}


# ------------------------------------------------------------------ timeline


@pytest.mark.parametrize("how", ["non-utf8", "broken-frontmatter", "no-frontmatter", "string-timeline"])
def test_timeline_corrupted_file_keeps_its_debt(tmp_path: Path, how: str) -> None:
    root = fixture(tmp_path, TIMELINE_FILES)

    def corrupt(path: Path) -> None:
        target = path / "registry/named/o/a.md"
        if how == "non-utf8":
            target.write_bytes(BAD_ORDER.encode() + b"\xff\xfe")
        elif how == "broken-frontmatter":
            target.write_text("---\nid: [unterminated\ntimeline: {\n---\n# A\n", encoding="utf-8")
        elif how == "no-frontmatter":
            target.write_text("# A\n\nno frontmatter here\n", encoding="utf-8")
        else:
            target.write_text("---\nid: o/a\ntimeline: \"not a list\"\n---\n# A\n", encoding="utf-8")

    first, second = scan_twice(root, TimelineCausalitySensor(), corrupt)
    assert_unswept(first, second, "timeline_causality_drift", "o/a", "timeline-causality")
    (entry,) = partial(second)["timeline-causality"]["skipped"]
    assert (entry["subjectType"], entry["subjectId"]) == ("named-skill", "o/a")


def test_timeline_fixing_the_file_resolves_the_debt_once_nothing_is_skipped(tmp_path: Path) -> None:
    root = fixture(tmp_path, TIMELINE_FILES)
    controller = StewardController(sensors=[TimelineCausalitySensor()], clock=Clock())
    assert open_ids(controller.scan(root), "timeline_causality_drift") == {"o/a"}
    (root / "registry/named/o/a.md").write_text(GOOD.replace("o/b", "o/a"), encoding="utf-8")
    second = controller.scan(root)
    assert open_ids(second, "timeline_causality_drift") == set()
    assert not second.receipt.partial_coverage


def test_timeline_scan_detailed_reports_skips_without_failing_the_scan(tmp_path: Path) -> None:
    root = fixture(tmp_path, TIMELINE_FILES)
    (root / "registry/named/o/a.md").write_bytes(b"\xff\xfe")
    scan = TimelineCausalitySensor().scan_detailed(root, NOW)
    assert scan.observations == ()
    assert [dict(entry) for entry in scan.skipped] == [
        {"subjectType": "named-skill", "subjectId": "o/a", "reason": "file is not valid UTF-8"}
    ]
    # `scan` stays the plain observation list the controller's legacy path expects.
    assert TimelineCausalitySensor().scan(root, NOW) == []


def test_timeline_with_every_file_unreadable_is_unavailable(tmp_path: Path) -> None:
    root = fixture(tmp_path, {"registry/named/o/a.md": BAD_ORDER})
    (root / "registry/named/o/a.md").write_bytes(b"\xff\xfe")
    with pytest.raises(SensorUnavailable, match="could not be evaluated"):
        TimelineCausalitySensor().scan(root, NOW)


def test_timeline_skip_reasons_never_echo_file_content(tmp_path: Path) -> None:
    secret = "AKIA" + "Q" * 16
    root = fixture(tmp_path, TIMELINE_FILES)
    (root / "registry/named/o/a.md").write_text(f"---\nid: [{secret}\n---\n", encoding="utf-8")
    scan = TimelineCausalitySensor().scan_detailed(root, NOW)
    assert scan.skipped and secret not in repr(scan.skipped)


# ------------------------------------------------------------------ frontend


@pytest.mark.parametrize("how", ["non-utf8", "parser-failure"])
def test_frontend_corrupted_page_keeps_its_debt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, how: str
) -> None:
    root = fixture(tmp_path, FRONTEND_FILES)
    controller = StewardController(sensors=[FrontendContractSensor()], clock=Clock())
    first = controller.scan(root)
    assert "docs/a.html" in open_ids(first, "frontend_contract_drift")
    assert not first.receipt.partial_coverage

    if how == "non-utf8":
        (root / "docs/a.html").write_bytes(NO_LANG.encode() + b"\xff\xfe")
    else:
        (root / "docs/a.html").write_text(NO_LANG + "<!-- PARSER-TRIPWIRE -->\n", encoding="utf-8")
        real_feed = sensors_contracts._ContractParser.feed

        def feed(self, data):  # a parser failure only on the corrupted page
            if "PARSER-TRIPWIRE" in data:
                raise AssertionError("simulated parser failure")
            return real_feed(self, data)

        monkeypatch.setattr(sensors_contracts._ContractParser, "feed", feed)

    second = controller.scan(root)
    assert_unswept(first, second, "frontend_contract_drift", "docs/a.html", "frontend-contract")
    (entry,) = partial(second)["frontend-contract"]["skipped"]
    assert (entry["subjectType"], entry["subjectId"]) == ("html-page", "docs/a.html")


def test_frontend_legitimate_fragments_are_not_skips(tmp_path: Path) -> None:
    files = {
        **FRONTEND_FILES,
        "docs/partials/nav.html": "<nav><a href='/'>home</a></nav>\n",
        "docs/partials/footer.html": "<footer>ok</footer>\n",
    }
    root = fixture(tmp_path, files)
    sensor = FrontendContractSensor()
    scan = sensor.scan_detailed(root, NOW)
    assert scan.skipped == ()
    _, stats = sensor.scan_with_stats(root, NOW)
    assert stats["skippedFragment"] == 2

    controller = StewardController(sensors=[sensor], clock=Clock())
    result = controller.scan(root)
    assert not result.receipt.partial_coverage
    # Complete coverage: fixing the page still resolves its debt.
    (root / "docs/a.html").write_text(PAGE.format(title="A"), encoding="utf-8")
    assert open_ids(controller.scan(root), "frontend_contract_drift") == set()


def test_frontend_inventory_of_only_fragments_is_clean_not_blind(tmp_path: Path) -> None:
    root = fixture(tmp_path, {"docs/partials/nav.html": "<nav>x</nav>\n"})
    scan = FrontendContractSensor().scan_detailed(root, NOW)
    assert scan.observations == () and scan.skipped == ()


def test_frontend_with_every_page_unreadable_is_unavailable(tmp_path: Path) -> None:
    root = fixture(tmp_path, {"docs/a.html": NO_LANG})
    (root / "docs/a.html").write_bytes(b"\xff\xfe")
    with pytest.raises(SensorUnavailable, match="could not be evaluated"):
        FrontendContractSensor().scan(root, NOW)
