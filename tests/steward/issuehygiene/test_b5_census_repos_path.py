"""The live census walks GitHub's cursor links from any network, including one that refuses numeric repository paths.

GitHub names a repository by id in its ``next`` links (``/repositories/<id>/issues``). A network proxy may refuse that
form with a 403. ``followable`` requests the same listing by its ``/repos/<owner>/<repo>/issues`` path instead, keeping
the cursor and every query parameter. Completeness is unchanged: every check still runs on the link GitHub sent, and a
link to another state or another repository still fails closed.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse

import pytest

from gaia_cli.steward.issuehygiene.census import COMPLETE, validateCensus
from tests.steward.issuehygiene.e_fakes import realLinkHeader, servedPage
from scripts.steward_issue_census import Response, collectCensus, followable

REPO = "o/r"
NOW = datetime(2026, 10, 21, 19, 30, tzinfo=timezone.utc)
FIXED_NOW = "2026-10-21T19:30:00Z"


def rows(count: int) -> list[dict]:
    return [
        {"number": index + 1, "title": f"t{index + 1}", "state": "open", "labels": [], "user": {"login": "alice"},
         "body": "b", "created_at": FIXED_NOW, "updated_at": FIXED_NOW}
        for index in range(count)
    ]


class ProxyLikeGitHub:
    """Answers like api.github.com with numeric-id cursor links, and refuses numeric repository paths like a proxy."""

    def __init__(self, count: int):
        self.pages = [rows(count)[index:index + 100] for index in range(0, count, 100)]
        self.requested: list[str] = []

    def __call__(self, url: str) -> Response:
        self.requested.append(url)
        parts = urlparse(url)
        if parts.path.startswith("/repositories/"):
            return Response(403, {}, '{"message":"Numeric-ID repository paths are not supported through this proxy."}')
        if "state=closed" in url:
            return Response(200, {}, "[]")
        page = servedPage(parse_qs(parts.query))
        if page > len(self.pages):
            return Response(200, {}, "[]")
        link = realLinkHeader("open", 100, page, len(self.pages))
        return Response(200, {"link": link} if link else {}, json.dumps(self.pages[page - 1]))


@pytest.mark.parametrize("count", [150, 224])
def test_a_numeric_id_listing_is_walked_to_the_end_through_a_proxy_that_refuses_it(count: int) -> None:
    github = ProxyLikeGitHub(count)

    document = collectCensus(REPO, NOW, github)

    issues = document["completeness"]["issues"]
    assert issues["complete"] is True, issues.get("reason")
    assert issues["itemCount"] == count
    assert validateCensus(document, NOW, 21600).status == COMPLETE


def test_every_followed_page_is_requested_by_the_repos_path_and_the_cursor_is_kept() -> None:
    github = ProxyLikeGitHub(150)

    collectCensus(REPO, NOW, github)

    open_pages = [url for url in github.requested if "state=open" in url]
    assert not [url for url in open_pages if "/repositories/" in url], "no numeric-id request is ever sent"
    follow = [url for url in open_pages if "after=" in url]
    assert follow and all(url.startswith("https://api.github.com/repos/o/r/issues?") for url in follow)


def test_followable_keeps_the_cursor_and_every_query_parameter_exactly() -> None:
    start = "https://api.github.com/repos/o/r/issues?state=open&per_page=100"
    link = ("https://api.github.com/repositories/1221716703/issues?state=open&per_page=100"
            "&after=Y3Vyc29yOnYyOpLPAAABoM3OHADPAAAAAUrtuyA%3D&page=2")

    assert followable(link, start) == (
        "https://api.github.com/repos/o/r/issues?state=open&per_page=100"
        "&after=Y3Vyc29yOnYyOpLPAAABoM3OHADPAAAAAUrtuyA%3D&page=2"
    )


def test_followable_leaves_a_repos_path_link_alone() -> None:
    start = "https://api.github.com/repos/o/r/issues?state=open&per_page=100"
    link = "https://api.github.com/repos/o/r/issues?state=open&per_page=100&after=abc&page=2"
    assert followable(link, start) == link


def test_a_numeric_id_next_link_for_another_state_still_fails_closed() -> None:
    """Rewriting the path never widens what is accepted: the state filter is checked on the link GitHub sent."""
    first = ("<https://api.github.com/repositories/1221716703/issues?state=closed&per_page=100"
             "&after=abc&page=2>; rel=\"next\"")

    def fetch(url: str) -> Response:
        if "state=closed" in url:
            return Response(200, {}, "[]")
        return Response(200, {"link": first}, json.dumps(rows(100)))

    document = collectCensus(REPO, NOW, fetch)

    assert document["completeness"]["issues"]["complete"] is False
    assert document["completeness"]["issues"]["reason"] == "foreign-continuation"
