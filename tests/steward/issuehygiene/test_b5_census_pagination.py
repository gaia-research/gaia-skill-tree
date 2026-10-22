"""Lane B5, blocker B1 (+ L5, L8, M6-census): GitHub-accurate pagination and census completeness.

The issues endpoint is cursor-paginated. Its ``Link`` header carries ``after``/``before`` cursors on
absolute ``repositories/<id>`` URLs: the first page names only ``next``, a middle page names ``next``
and ``prev``, and the final page names only ``prev``. There is no ``last`` and no ``first`` (B6 captured
this from the live endpoint). Every fake in this file answers that way, through ``realLinkHeader``
and ``servedPage`` from the shared fakes, so the collector meets the server it will really meet.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from gaia_cli.steward.issuehygiene.census import COMPLETE, INCOMPLETE, validateCensus
from tests.steward.issuehygiene.e_fakes import realLinkHeader, servedPage
from scripts.steward_issue_census import (
    Response,
    closedWindowDaysFromPolicy,
    collectCensus,
    collectWorkflows,
    listAll,
    main,
)

REPO = "o/r"
NOW = datetime(2026, 10, 21, 19, 30, tzinfo=timezone.utc)
FIXED_NOW = "2026-10-21T19:30:00Z"
BASE = "https://api.github.com/repos/o/r/issues?state=open&per_page=100"
WORKFLOW_BASE = "https://api.github.com/repos/o/r/actions/workflows?per_page=100"


def githubRows(count: int, start: int = 1) -> list[dict]:
    return [
        {"number": start + index, "title": f"t{start + index}", "state": "open", "labels": [],
         "user": {"login": "alice"}, "body": "b", "created_at": FIXED_NOW, "updated_at": FIXED_NOW}
        for index in range(count)
    ]


def githubListing(rows: list[dict], pageSize: int = 100):
    """A fake that answers like api.github.com: cursor Link headers, next on the first page, next/prev in the middle, prev on the last."""
    pages = [rows[index:index + pageSize] for index in range(0, len(rows), pageSize)]
    total = len(pages)

    def fetch(url: str) -> Response:
        if "state=closed" in url:
            return Response(200, {}, "[]")
        query = parse_qs(urlparse(url).query)
        page = servedPage(query)
        if page > total:
            return Response(200, {}, "[]")
        link = realLinkHeader("open", pageSize, page, total)
        headers = {"link": link} if link else {}
        return Response(200, headers, json.dumps(pages[page - 1]))

    return fetch


@pytest.mark.parametrize("count", [5, 100, 150, 224, 300])
def test_github_accurate_listings_are_complete(count: int) -> None:
    document = collectCensus(REPO, NOW, githubListing(githubRows(count)))

    issues = document["completeness"]["issues"]
    assert issues["complete"] is True, issues.get("reason")
    assert issues["itemCount"] == count
    assert len(document["issues"]) == count
    # The probe that proves the end is not a fetched page. The empty closed-window listing is one page.
    assert issues["pagesFetched"] == issues["expectedPages"] == max(1, -(-count // 100)) + 1
    assert validateCensus(document, NOW, 21600).status == COMPLETE


def test_exact_multiple_of_page_size_completes_on_the_empty_probe() -> None:
    document = collectCensus(REPO, NOW, githubListing(githubRows(200)))

    assert document["completeness"]["issues"]["complete"] is True
    assert document["completeness"]["issues"]["pagesFetched"] == 3


def test_a_probe_that_returns_rows_is_an_unlinked_continuation_and_is_not_adopted() -> None:
    rows = githubRows(100)
    extra = githubRows(3, start=500)

    def fetch(url: str) -> Response:
        if "state=closed" in url:
            return Response(200, {}, "[]")
        if "page=2" in url:
            return Response(200, {}, json.dumps(extra))
        return Response(200, {}, json.dumps(rows))

    listing = listAll(BASE, fetch)

    assert listing.reason == "unlinked-continuation"
    assert all(row["number"] < 500 for row in listing.rows)


def test_an_empty_page_reached_through_a_next_link_fails_closed() -> None:
    def fetch(url: str) -> Response:
        if "state=closed" in url:
            return Response(200, {}, "[]")
        if "page=2" in url:
            return Response(200, {}, "[]")
        return Response(200, {"link": f'<{BASE}&page=2>; rel="next"'},
                        json.dumps(githubRows(100)))

    listing = listAll(BASE, fetch)

    assert listing.reason == "empty-linked-page"


def test_a_truncated_final_page_is_short_not_complete() -> None:
    rows = githubRows(224)
    full = githubListing(rows)

    def fetch(url: str) -> Response:
        if "page=3" in url:
            return Response(500, {}, "{}")
        return full(url)

    document = collectCensus(REPO, NOW, fetch)

    assert document["completeness"]["issues"]["complete"] is False


def test_collector_probe_does_not_inflate_pages_for_the_mutation_confirm_walk() -> None:
    document = collectCensus(REPO, NOW, githubListing(githubRows(150)))

    assert document["completeness"]["issues"]["confirmPagesFetched"] == 2


def test_workflow_listing_is_a_separate_section_whose_failure_does_not_fail_issues() -> None:
    def fetch(url: str) -> Response:
        if "actions/workflows" in url:
            return Response(403, {}, "{}")
        return githubListing(githubRows(3))(url)

    document = collectCensus(REPO, NOW, fetch)

    assert document["completeness"]["issues"]["complete"] is True
    assert document["workflows"]["complete"] is False
    assert document["workflows"]["reason"] == "http-403"


def test_workflow_states_are_collected_from_the_api_wrapper_object() -> None:
    body = {"total_count": 2, "workflows": [
        {"id": 1, "name": "Steward build", "path": ".github/workflows/steward-build.lock.yml", "state": "disabled_manually"},
        {"id": 2, "name": "CI", "path": ".github/workflows/ci.yml", "state": "active"},
    ]}

    def fetch(url: str) -> Response:
        if "actions/workflows" in url:
            return Response(200, {}, json.dumps({"workflows": []} if "page" in parse_qs(urlparse(url).query) else body))
        return githubListing(githubRows(1))(url)

    section = collectWorkflows(REPO, fetch)

    assert section["complete"] is True
    assert section["itemCount"] == 2
    assert {item["path"]: item["state"] for item in section["items"]} == {
        ".github/workflows/steward-build.lock.yml": "disabled_manually",
        ".github/workflows/ci.yml": "active",
    }


def test_workflow_listing_without_a_wrapper_object_is_incomplete() -> None:
    section = collectWorkflows(REPO, lambda url: Response(200, {}, json.dumps([{"path": "x"}])))

    assert section["complete"] is False
    assert section["reason"] == "unexpected-page-shape"


def test_closed_window_is_wired_from_policy_when_no_flag_is_given(tmp_path: Path) -> None:
    policy = tmp_path / "founder" / "steward"
    policy.mkdir(parents=True)
    (policy / "POLICY.yaml").write_text(
        "issueHygiene:\n  maxClosuresPerRun: 10\n  maxCensusAgeSeconds: 21600\n  closedWindowDays: 45\n"
        "  writesEnabled: false\n  enabledRules: []\n  a5Disabled: []\n",
        encoding="utf-8",
    )

    assert closedWindowDaysFromPolicy(tmp_path) == 45


def test_closed_window_policy_unreadable_refuses_the_collector(tmp_path: Path, capsys) -> None:
    (tmp_path / "founder" / "steward").mkdir(parents=True)
    (tmp_path / "founder" / "steward" / "POLICY.yaml").write_text("issueHygiene: [not, a, mapping]\n", encoding="utf-8")

    code = main(["--repo", REPO, "--root", str(tmp_path), "--out", str(tmp_path / "out.json"), "--now", FIXED_NOW],
                fetch=githubListing(githubRows(1)))

    assert code == 2
    assert not (tmp_path / "out.json").exists()


def test_validate_census_refuses_an_item_count_that_does_not_match_the_rows() -> None:
    rows = githubRows(3)
    document = {
        "schemaVersion": "steward-github-census-v1", "repo": REPO, "fetchedAt": FIXED_NOW, "source": "rest",
        "completeness": {
            "issues": {"complete": True, "pagesFetched": 1, "expectedPages": 1, "itemCount": 2, "lastLink": None},
            "pulls": {"complete": True, "pagesFetched": 1, "expectedPages": 1, "itemCount": 0, "lastLink": None},
        },
        "issues": [dict(row, body="b", bodySha256="3e23e8160039594a33894f6564e1b1348bbd7a0088d42c4acb73eeaed59c009d") for row in rows],
        "recentlyClosed": [],
    }

    status = validateCensus(document, NOW, 21600)

    assert status.status == INCOMPLETE
    assert any(reason.startswith("issues-item-count-mismatch") for reason in status.reasons)


def test_validate_census_refuses_a_pulls_item_count_that_hides_a_pull_request() -> None:
    rows = [dict(row, isPullRequest=True, mergedAt=None, body="b",
                 bodySha256="3e23e8160039594a33894f6564e1b1348bbd7a0088d42c4acb73eeaed59c009d")
            for row in githubRows(2)]
    document = {
        "schemaVersion": "steward-github-census-v1", "repo": REPO, "fetchedAt": FIXED_NOW, "source": "rest",
        "completeness": {
            "issues": {"complete": True, "pagesFetched": 1, "expectedPages": 1, "itemCount": 0, "lastLink": None},
            "pulls": {"complete": True, "pagesFetched": 1, "expectedPages": 1, "itemCount": 0, "lastLink": None},
        },
        "issues": rows,
        "recentlyClosed": [],
    }

    status = validateCensus(document, NOW, 21600)

    assert status.status == INCOMPLETE
    assert any(reason.startswith("pulls-item-count-mismatch") for reason in status.reasons)
