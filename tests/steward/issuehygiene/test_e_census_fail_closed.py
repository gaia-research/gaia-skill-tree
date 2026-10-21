"""Adversarial lane E, scenarios 1 and 15: pagination, missing pages, stale census, auth failure.

Every test here fails closed or documents a defect. Nothing touches the network: the collector
is driven through ``FakeGitHub.fetch`` and ``httpFetch`` is driven through a patched
``urllib.request.urlopen``.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import timedelta
from pathlib import Path

import pytest

from gaia_cli.steward.issuehygiene.census import COMPLETE, INCOMPLETE, MISSING, STALE, validateCensus
from gaia_cli.steward.issuehygiene.sensor import CENSUS_INPUT, IssueHygieneSensor
from gaia_cli.steward.primitives import SensorUnavailable
from scripts.steward_issue_census import MAX_PAGES, FetchError, Response, collectCensus, httpFetch
from tests.steward.issuehygiene.e_fakes import NOW, NOW_TEXT, REPO, FakeGitHub, makeCheckout


def openRows(gh: FakeGitHub, count: int) -> None:
    for index in range(count):
        gh.add(f"[intake] candidate {index}", body=f"candidate {index}", labels=("upstream:child",))


def fakeRow(number: int) -> dict:
    return {
        "number": number, "title": f"row {number}", "state": "open", "state_reason": None, "labels": [],
        "user": {"login": "github-actions[bot]"}, "body": "", "created_at": "2026-10-21T10:00:00Z",
        "updated_at": "2026-10-21T10:00:00Z", "closed_at": None, "comments": 0,
    }


# --- scenario 1: pagination and missing pages fail closed ------------------------------------


def test_complete_multi_page_listing_is_complete() -> None:
    gh = FakeGitHub(pageSize=2)
    openRows(gh, 5)
    doc = gh.census(NOW)
    assert doc["completeness"]["issues"]["complete"] is True
    # pagesFetched counts the open walk (3 pages) plus the empty closed-window walk (1 page).
    assert doc["completeness"]["issues"]["pagesFetched"] == doc["completeness"]["issues"]["expectedPages"] == 4
    assert sorted(row["number"] for row in doc["issues"]) == sorted(gh.issues)


def test_missing_middle_page_is_incomplete_and_keeps_no_partial_rows_as_complete() -> None:
    gh = FakeGitHub(pageSize=2)
    openRows(gh, 5)
    gh.pageFailures[("open", 2)] = 502
    doc = gh.census(NOW)
    assert doc["completeness"]["issues"]["complete"] is False
    assert doc["completeness"]["issues"]["reason"] == "http-502"
    assert doc["completeness"]["pulls"]["complete"] is False  # the pulls section shares the verdict


def test_rate_limited_last_page_is_incomplete_not_partial() -> None:
    gh = FakeGitHub(pageSize=2)
    openRows(gh, 5)
    gh.pageFailures[("open", 3)] = 429
    doc = gh.census(NOW)
    assert doc["completeness"]["issues"]["complete"] is False
    assert doc["completeness"]["issues"]["reason"] == "rate-limited"


def test_listing_that_stops_before_the_promised_last_page_is_short() -> None:
    """Page 1 keeps rel="last" (page 3) but drops rel="next": the walk ends early and must not look whole."""

    gh = FakeGitHub(pageSize=2)
    openRows(gh, 5)
    original = gh.listPage

    def dropNext(state, page, since=None):
        status, headers, body = original(state, page, since)
        if state == "open" and page == 1:
            headers = {"link": headers["link"].split(",")[-1]}
        return status, headers, body

    gh.listPage = dropNext
    doc = gh.census(NOW)
    assert doc["completeness"]["issues"]["complete"] is False
    assert doc["completeness"]["issues"]["reason"].startswith("pagination-short:1/3")


def test_unparsable_last_link_is_incomplete() -> None:
    def fetch(url: str) -> Response:
        return Response(200, {"link": '<https://api.github.com/repos/x/y/issues?state=open>; rel="last"'}, "[]")

    doc = collectCensus(REPO, NOW, fetch)
    assert doc["completeness"]["issues"]["complete"] is False
    assert doc["completeness"]["issues"]["reason"] == "last-page-unparsable"


@pytest.mark.parametrize(("response", "reason"), [
    (Response(500, {}, "[]"), "http-500"),
    (Response(200, {}, "<html>maintenance</html>"), "unparsable-page"),
    (Response(200, {}, json.dumps({"message": "not a list"})), "unexpected-page-shape"),
])
def test_bad_pages_are_incomplete_with_a_machine_reason(response: Response, reason: str) -> None:
    doc = collectCensus(REPO, NOW, lambda url: response)
    assert doc["completeness"]["issues"]["complete"] is False
    assert doc["completeness"]["issues"]["reason"] == reason
    assert doc["issues"] == []


def test_endless_next_links_hit_the_page_cap_and_are_incomplete() -> None:
    calls: list[str] = []

    def fetch(url: str) -> Response:
        calls.append(url)
        return Response(200, {"link": f'<{url}&page={len(calls) + 1}>; rel="next"'}, json.dumps([fakeRow(len(calls))]))

    doc = collectCensus(REPO, NOW, fetch)
    assert len(calls) == MAX_PAGES
    assert doc["completeness"]["issues"]["complete"] is False
    assert doc["completeness"]["issues"]["reason"].startswith("page-cap-exceeded")


def test_a_failure_on_the_open_listing_never_lets_the_closed_listing_mark_it_complete() -> None:
    gh = FakeGitHub(pageSize=2)
    openRows(gh, 3)
    gh.pageFailures[("open", 1)] = 500
    doc = gh.census(NOW)
    assert doc["completeness"]["issues"]["complete"] is False
    assert [row for row in doc["recentlyClosed"]] == []  # the closed listing was never walked


@pytest.mark.xfail(
    strict=True,
    reason=(
        "DEFECT (fail-open): a full first page with no Link header is taken as the whole listing. "
        "collectCensus accepts expectedPages = pagesFetched when rel=last is absent, so a degraded "
        "response that drops every Link header yields complete:true with 2 of 5 rows. A full page "
        "(len == per_page) without rel=next must not terminate the walk as complete."
    ),
)
def test_full_page_without_any_link_header_is_not_reported_complete() -> None:
    gh = FakeGitHub(pageSize=2, linkMode="none")
    openRows(gh, 5)
    doc = gh.census(NOW)
    assert len(doc["issues"]) == 2  # the walk stopped after one page; the census must say so
    assert doc["completeness"]["issues"]["complete"] is False


@pytest.mark.xfail(
    strict=True,
    reason=(
        "DEFECT (fail-open under concurrent mutation): an issue closed after page 1 is served shifts the "
        "remaining open rows left, so page 2 skips one open issue while every page is present. The collector "
        "verifies page counts only, so complete:true is reported without an open issue. Completeness must "
        "survive a mid-walk close (for example a confirming second walk or a per-row cross-check)."
    ),
)
def test_an_open_issue_shifted_past_a_page_boundary_by_a_concurrent_close_is_not_silently_dropped() -> None:
    gh = FakeGitHub(pageSize=2)
    openRows(gh, 5)  # numbers 1001 to 1005, newest first on the listing
    gh.pageHooks[("open", 2)] = lambda g: g.close(max(g.issues), "completed")  # 1005 closes after page 1 was served
    doc = gh.census(NOW)
    present = {row["number"] for row in doc["issues"]}
    stillOpen = {number for number, row in gh.issues.items() if row["state"] == "open"}
    assert stillOpen <= present or doc["completeness"]["issues"]["complete"] is False


def test_a_single_short_page_with_no_link_header_is_complete() -> None:
    gh = FakeGitHub(pageSize=100, linkMode="none")
    openRows(gh, 2)
    doc = gh.census(NOW)
    assert doc["completeness"]["issues"]["complete"] is True
    assert len(doc["issues"]) == 2


# --- scenario 15: stale census and auth failure fail closed -----------------------------------


def test_census_exactly_at_the_policy_age_is_still_complete_and_one_second_older_is_stale() -> None:
    at = NOW - timedelta(seconds=21600)
    gh = FakeGitHub()
    openRows(gh, 1)
    fresh = gh.census(at)
    assert validateCensus(fresh, NOW, 21600).status == COMPLETE
    stale = gh.census(at - timedelta(seconds=1))
    assert validateCensus(stale, NOW, 21600).status == STALE


def test_auth_failure_mid_walk_is_incomplete_with_the_status_reason_and_never_a_partial_file() -> None:
    gh = FakeGitHub(pageSize=2)
    openRows(gh, 5)
    gh.pageFailures[("open", 2)] = 401
    doc = gh.census(NOW)
    verdict = validateCensus(doc, NOW, 21600)
    assert verdict.status == INCOMPLETE
    assert doc["completeness"]["issues"]["reason"] == "http-401"


def test_forbidden_without_a_rate_limit_header_is_http_403_not_rate_limited(monkeypatch) -> None:
    def refuse(request, timeout=None):
        raise urllib.error.HTTPError(request.full_url, 403, "Forbidden", {}, None)

    monkeypatch.setattr(urllib.request, "urlopen", refuse)
    with pytest.raises(FetchError) as caught:
        httpFetch("https://api.github.com/repos/x/y/issues", "tok-SECRET-123")
    assert caught.value.reason == "http-403"
    assert "SECRET" not in caught.value.reason


def test_forbidden_with_exhausted_rate_limit_is_rate_limited(monkeypatch) -> None:
    def limited(request, timeout=None):
        raise urllib.error.HTTPError(request.full_url, 403, "Forbidden", {"x-ratelimit-remaining": "0"}, None)

    monkeypatch.setattr(urllib.request, "urlopen", limited)
    with pytest.raises(FetchError) as caught:
        httpFetch("https://api.github.com/repos/x/y/issues", "tok")
    assert caught.value.reason == "rate-limited"


def test_transport_error_reason_never_echoes_the_token(monkeypatch) -> None:
    def broken(request, timeout=None):
        raise urllib.error.URLError("connection refused tok-SECRET-123")

    monkeypatch.setattr(urllib.request, "urlopen", broken)
    with pytest.raises(FetchError) as caught:
        httpFetch("https://api.github.com/repos/x/y/issues", "tok-SECRET-123")
    assert caught.value.reason == "transport-URLError"
    assert "SECRET" not in caught.value.reason


def test_sensor_refuses_an_incomplete_census_with_coverage_unknown(tmp_path: Path) -> None:
    gh = FakeGitHub(pageSize=2)
    openRows(gh, 5)
    gh.pageFailures[("open", 2)] = 502
    root = makeCheckout(tmp_path, census=gh.census(NOW))
    with pytest.raises(SensorUnavailable, match="incomplete"):
        IssueHygieneSensor().scan_detailed(root, NOW_TEXT)


def test_sensor_refuses_a_stale_census_with_coverage_unknown(tmp_path: Path) -> None:
    gh = FakeGitHub()
    openRows(gh, 1)
    root = makeCheckout(tmp_path, census=gh.census(NOW - timedelta(hours=7)))
    with pytest.raises(SensorUnavailable, match="stale"):
        IssueHygieneSensor().scan_detailed(root, NOW_TEXT)


def test_sensor_treats_an_absent_census_as_not_evaluated_not_healthy(tmp_path: Path) -> None:
    from gaia_cli.steward.primitives import SensorNotEvaluated

    root = makeCheckout(tmp_path)
    assert not (root / CENSUS_INPUT).exists()
    with pytest.raises(SensorNotEvaluated):
        IssueHygieneSensor().scan_detailed(root, NOW_TEXT)


def test_unreadable_census_is_missing_not_complete(tmp_path: Path) -> None:
    from gaia_cli.steward.issuehygiene.census import loadCensus

    root = makeCheckout(tmp_path, census="{truncated")
    assert loadCensus(root / CENSUS_INPUT, now=NOW).status.status == MISSING
