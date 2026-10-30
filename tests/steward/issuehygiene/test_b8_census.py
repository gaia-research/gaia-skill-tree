"""Lane B8 M-1 and the LOW items: census continuation stays on the listing, census rows are judged strictly,
and the credential scrub catches short token assignments.

Nothing here reaches the network: the census walk is driven by an in-memory fetch.
"""

from __future__ import annotations

import json
from pathlib import Path

from gaia_cli.steward.primitives.redact import scrub
from gaia_cli.steward.issuehygiene.census import INCOMPLETE, validateCensus
from scripts.steward_issue_census import API, Response, listAll
from tests.steward.issuehygiene.e_fakes import REPO
from tests.steward.issuehygiene.test_b_reconcile import NOW, mkRow

START = f"{API}/repos/{REPO}/issues?state=open&per_page=100"


def page(rows: list, nextUrl: str | None = None) -> Response:
    headers = {"link": f'<{nextUrl}>; rel="next"'} if nextUrl else {}
    return Response(200, headers, json.dumps(rows))


def walk(pages: dict[str, Response]):
    def fetch(url: str) -> Response:
        if url not in pages:
            return Response(200, {}, "[]")
        return pages[url]
    return listAll(START, fetch)


def test_a_next_link_to_another_repository_is_a_foreign_continuation() -> None:
    other = f"{API}/repos/someone/else/issues?state=open&per_page=100&page=2"
    listing = walk({START: page([{"number": 1}], other), other: page([{"number": 99}])})
    assert listing.reason == "foreign-continuation"


def test_a_next_link_on_another_path_of_the_same_origin_is_a_foreign_continuation() -> None:
    pulls = f"{API}/repos/{REPO}/pulls?state=open&per_page=100&page=2"
    listing = walk({START: page([{"number": 1}], pulls), pulls: page([{"number": 99}])})
    assert listing.reason == "foreign-continuation"


def test_a_next_link_that_changes_the_state_filter_is_a_foreign_continuation() -> None:
    closed = f"{API}/repos/{REPO}/issues?state=closed&per_page=100&page=2"
    listing = walk({START: page([{"number": 1}], closed), closed: page([{"number": 2}])})
    assert listing.reason == "foreign-continuation"


def test_a_next_link_on_the_same_listing_is_followed() -> None:
    second = f"{API}/repos/{REPO}/issues?state=open&per_page=100&page=2"
    listing = walk({START: page([{"number": 1}], second), second: page([{"number": 2}])})
    assert listing.reason is None
    assert [row["number"] for row in listing.rows] == [1, 2]


# --- LOW: census rows are judged strictly -----------------------------------------------------------

def census(rows: list) -> dict:
    return {
        "schemaVersion": "steward-github-census-v1", "repo": REPO, "fetchedAt": "2026-10-21T19:00:00Z",
        "source": "rest",
        "completeness": {
            "issues": {"complete": True, "pagesFetched": 1, "expectedPages": 1, "itemCount": len(rows), "lastLink": None},
            "pulls": {"complete": True, "pagesFetched": 1, "expectedPages": 1, "itemCount": 0, "lastLink": None},
        },
        "issues": rows, "recentlyClosed": [],
    }


def test_a_duplicate_issue_number_in_the_open_listing_is_incomplete() -> None:
    row = mkRow(10, "[intake] one")
    status = validateCensus(census([row, dict(row)]), NOW, 21600)
    assert status.status == INCOMPLETE
    assert any(reason.startswith("issues-duplicate-number:#10") for reason in status.reasons)


def test_a_non_open_row_in_the_open_listing_is_incomplete() -> None:
    row = mkRow(11, "[intake] closed though listed open", state="closed")
    status = validateCensus(census([row]), NOW, 21600)
    assert status.status == INCOMPLETE
    assert any(reason.startswith("issues-row-not-open:#11") for reason in status.reasons)


def test_an_open_unique_listing_is_still_complete() -> None:
    assert validateCensus(census([mkRow(12, "[intake] fine")]), NOW, 21600).status == "complete"


# --- LOW: short token assignments are scrubbed ------------------------------------------------------

def test_a_short_dotted_token_assignment_is_scrubbed() -> None:
    assert "abc123.def456" not in scrub("token=abc123.def456")
    assert "abc123..." not in scrub("token=abc123...")
    assert "abc123" not in scrub("token = abc123.def")


def test_code_access_is_not_mistaken_for_a_token() -> None:
    assert scrub('os.environ["TOKEN"]') == 'os.environ["TOKEN"]'
    assert scrub("secret = config.get_secret(") == "secret = config.get_secret("


def test_the_contract_documents_the_cursor_listing_assumption() -> None:
    contract = (Path(__file__).resolve().parents[3] / "founder" / "handovers"
                / "2026-10-21-steward-issue-hygiene-architecture.md").read_text(encoding="utf-8")
    assert "cursor-listing assumption" in contract
