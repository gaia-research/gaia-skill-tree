"""The census does not believe an empty listing that the repository's own metadata contradicts (PR #2133, hardening).

``open_issues_count`` counts issues and pull requests alike, and it can lag the listing by a few items. So it is a
lower-confidence sanity signal, never an exact count:

- a listing that walks to an empty first page while the repository reports open items is a false empty: incomplete;
- an empty listing that nothing confirms (the count cannot be read) is incomplete;
- a normal empty repository (empty listing, count 0) is complete;
- a non-empty listing whose count cannot be read is accepted, because the walk itself already proves completeness;
- a count far from the listing (beyond a tenth of the count, at least 5) is incomplete; small drift is complete.

No request for the count is repeated, and every existing completeness check still runs.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from urllib.parse import parse_qs, quote, urlparse

import pytest

from gaia_cli.steward.issuehygiene.census import COMPLETE, validateCensus
from scripts.steward_issue_census import Response, collectCensus, metadataSanity
from tests.steward.issuehygiene.e_fakes import cursorFor, servedPage
from tests.steward.issuehygiene.test_b5_census_pagination import githubRows

REPO = "o/r"
NOW = datetime(2026, 10, 21, 19, 30, tzinfo=timezone.utc)
ROOT = "/repos/o/r"


def repository(rows: list[dict], count: int | None):
    """A repository whose open listing walks in one page. ``count`` None means its metadata cannot be read."""
    calls: list[str] = []

    def fetch(url: str) -> Response:
        calls.append(url)
        parts = urlparse(url)
        if parts.path == ROOT:
            if count is None:
                return Response(404, {}, "{}")
            return Response(200, {}, json.dumps({"open_issues_count": count}))
        if "/actions/workflows" in url:
            return Response(200, {}, json.dumps({"total_count": 0, "workflows": []}))
        if "state=closed" in url:
            return Response(200, {}, "[]")
        page = parse_qs(parts.query).get("page", ["1"])[0]
        return Response(200, {}, json.dumps(rows if page == "1" else []))

    return fetch, calls


def metadata_requests(calls: list[str]) -> int:
    return sum(1 for url in calls if urlparse(url).path == ROOT)


def test_a_false_empty_listing_while_the_repository_reports_open_items_is_incomplete() -> None:
    fetch, _ = repository([], count=5)

    document = collectCensus(REPO, NOW, fetch)

    issues = document["completeness"]["issues"]
    assert issues["complete"] is False
    assert issues["reason"] == "false-empty-suspect"
    assert issues["metadata"]["openIssuesCount"] == 5
    assert validateCensus(document, NOW, 21600).status != COMPLETE


def test_a_normal_empty_repository_is_complete() -> None:
    fetch, _ = repository([], count=0)

    document = collectCensus(REPO, NOW, fetch)

    issues = document["completeness"]["issues"]
    assert issues["complete"] is True, issues.get("reason")
    assert issues["itemCount"] == 0
    assert validateCensus(document, NOW, 21600).status == COMPLETE


def test_an_empty_listing_that_nothing_confirms_is_incomplete() -> None:
    fetch, _ = repository([], count=None)

    document = collectCensus(REPO, NOW, fetch)

    assert document["completeness"]["issues"]["complete"] is False
    assert document["completeness"]["issues"]["reason"] == "empty-unverified"


def test_a_non_empty_listing_is_accepted_when_the_count_cannot_be_read() -> None:
    fetch, _ = repository(githubRows(12), count=None)

    document = collectCensus(REPO, NOW, fetch)

    assert document["completeness"]["issues"]["complete"] is True, document["completeness"]["issues"].get("reason")
    assert document["completeness"]["issues"]["metadata"]["openIssuesCount"] is None


def test_small_drift_between_the_listing_and_the_count_is_complete() -> None:
    fetch, _ = repository(githubRows(100), count=103)

    document = collectCensus(REPO, NOW, fetch)

    assert document["completeness"]["issues"]["complete"] is True, document["completeness"]["issues"].get("reason")


def test_a_count_far_from_the_listing_is_incomplete() -> None:
    fetch, _ = repository(githubRows(100), count=300)

    document = collectCensus(REPO, NOW, fetch)

    assert document["completeness"]["issues"]["complete"] is False
    assert document["completeness"]["issues"]["reason"] == "metadata-count-mismatch"


def test_the_count_is_requested_once_per_census() -> None:
    fetch, calls = repository(githubRows(12), count=12)

    collectCensus(REPO, NOW, fetch)

    assert metadata_requests(calls) == 1


@pytest.mark.parametrize("listed, count, expected", [
    (0, 0, None),
    (0, 4, "false-empty-suspect"),
    (0, None, "empty-unverified"),
    (7, None, None),
    (100, 103, None),
    (100, 111, None),
    (100, 300, "metadata-count-mismatch"),
    (2, 40, "metadata-count-mismatch"),
])
def test_the_sanity_rule_in_one_table(listed: int, count: int | None, expected: str | None) -> None:
    assert metadataSanity(listed, count) == expected


# --- an exact multiple of the page size: GitHub's next link names an empty page after the last full page ---------

CURSOR_BASE = "https://api.github.com/repos/o/r/issues?state=open&per_page=100"


def live_shaped(rows: list[dict], count: int | None):
    """Answers like the live endpoint: a full page carries a ``next`` link, even when the page after it is empty."""
    def fetch(url: str) -> Response:
        parts = urlparse(url)
        if parts.path == ROOT:
            if count is None:
                return Response(404, {}, "{}")
            return Response(200, {}, json.dumps({"open_issues_count": count}))
        if "/actions/workflows" in url:
            return Response(200, {}, json.dumps({"total_count": 0, "workflows": []}))
        if "state=closed" in url:
            return Response(200, {}, "[]")
        page = servedPage(parse_qs(parts.query))
        pageRows = rows[(page - 1) * 100:page * 100]
        headers = {}
        if len(pageRows) == 100:
            headers["link"] = f'<{CURSOR_BASE}&after={quote(cursorFor(page), safe="")}&page={page + 1}>; rel="next"'
        return Response(200, headers, json.dumps(pageRows))

    return fetch


def test_an_exact_multiple_of_the_page_size_is_complete_when_the_count_confirms_it() -> None:
    document = collectCensus(REPO, NOW, live_shaped(githubRows(200), count=200))

    issues = document["completeness"]["issues"]
    assert issues["complete"] is True, issues.get("reason")
    assert issues["itemCount"] == 200


def test_a_single_full_page_is_complete_when_the_count_confirms_it() -> None:
    document = collectCensus(REPO, NOW, live_shaped(githubRows(100), count=100))

    assert document["completeness"]["issues"]["complete"] is True, document["completeness"]["issues"].get("reason")


@pytest.mark.parametrize("count", [None, 300, 150])
def test_an_empty_linked_page_fails_closed_unless_the_count_confirms_the_listed_rows(count) -> None:
    document = collectCensus(REPO, NOW, live_shaped(githubRows(200), count=count))

    issues = document["completeness"]["issues"]
    assert issues["complete"] is False
    assert issues["reason"] == "empty-linked-page"
