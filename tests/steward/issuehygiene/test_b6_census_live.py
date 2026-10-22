"""Lane B6 (#2130): the census walks the live issues listing to its end, and refuses what it cannot prove.

The live receipt (founder run, gaia-research/gaia-skill-tree, authenticated) read ``issues complete=false
itemCount=233 pagesFetched=3 reason=unlinked-continuation``. Captured from the live endpoint, the issues
listing is cursor-paginated: page 1 names only ``rel="next"``, the middle page ``next`` and ``prev``, and the
final page only ``prev``. The end probe reused the final request's ``after`` cursor while bumping ``page``, so
the probe re-served the final page (33 rows) and the walk read that as a continuation.

Redirects: urllib follows a GET 301/302 silently. A census that followed one could report an empty listing as
complete. Every request the census makes must refuse a 3xx and fail closed as ``redirected``.

Each test here pins one of those facts against a faithful fake or a loopback server, so it fails on the old
collector and passes on the fixed one.
"""

from __future__ import annotations

import http.server
import json
import math
import threading
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

import pytest

import scripts.steward_issue_census as census
from gaia_cli.steward.issuehygiene.census import COMPLETE, validateCensus
from scripts.steward_issue_census import FetchError, Response, collectCensus, httpFetch, listAll, main, parseLinks
from tests.steward.issuehygiene.e_fakes import NOW, NOW_TEXT, REPO, REPO_ID, FakeGitHub, cursorFor, servedPage

BASE = "https://api.github.com/repos/o/r/issues?state=open&per_page=100"
REAL_LISTING = f"https://api.github.com/repositories/{REPO_ID}/issues?state=open&per_page=100"


def issueRows(numbers) -> list[dict]:
    return [
        {"number": number, "title": f"t{number}", "state": "open", "labels": [], "user": {"login": "alice"},
         "body": "b", "created_at": "2026-10-21T19:00:00Z", "updated_at": "2026-10-21T19:00:00Z"}
        for number in numbers
    ]


def liveRepo(issues: int, pulls: int, pageSize: int) -> FakeGitHub:
    gh = FakeGitHub(pageSize=pageSize)
    for index in range(issues):
        gh.add(f"issue {index}")
    for index in range(pulls):
        gh.add(f"pull {index}", pull=True)
    return gh


# -- the walk against the live shape ------------------------------------------------------------

@pytest.mark.parametrize("perPage", [100, 30])
@pytest.mark.parametrize("issues,pulls", [(224, 9), (200, 0)])
def test_live_shaped_listings_walk_to_complete_at_every_page_size(monkeypatch, perPage, issues, pulls) -> None:
    monkeypatch.setattr(census, "PER_PAGE", perPage)
    total = issues + pulls
    document = liveRepo(issues, pulls, perPage).census(NOW)

    section = document["completeness"]["issues"]
    assert section["complete"] is True, section.get("reason")
    assert section["itemCount"] == len(document["issues"]) == total
    assert section["pagesFetched"] == math.ceil(total / perPage) + 1  # open pages, plus the one closed page
    assert section["confirmPagesFetched"] == math.ceil(total / perPage)
    assert validateCensus(document, NOW, 21600).status == COMPLETE


@pytest.mark.parametrize("perPage", [100, 30])
def test_233_rows_are_224_issues_and_9_pulls_and_pulls_come_from_the_same_walk(monkeypatch, perPage) -> None:
    monkeypatch.setattr(census, "PER_PAGE", perPage)
    document = liveRepo(224, 9, perPage).census(NOW)

    issues, pulls = document["completeness"]["issues"], document["completeness"]["pulls"]
    assert issues["complete"] is True and pulls["complete"] is True
    assert pulls["itemCount"] == sum(1 for row in document["issues"] if row["isPullRequest"]) == 9
    assert pulls["pagesFetched"] == issues["pagesFetched"]
    assert pulls["expectedPages"] == issues["expectedPages"]


def test_the_end_probe_is_not_the_final_page_served_again() -> None:
    gh = liveRepo(224, 9, 100)
    gh.census(NOW)

    # Walk: page 1, page 2, page 3 (final, prev only), then one probe. The probe must be page 4,
    # not page 3 re-served through the cursor the final request carried.
    assert gh.listCalls[:4] == [("open", 1), ("open", 2), ("open", 3), ("open", 4)]


# -- Link header parsing (RFC 8288) -------------------------------------------------------------

REAL_FIRST = f'<{REAL_LISTING}&after=Y3Vy%3D&page=2>; rel="next"'
REAL_MIDDLE = REAL_FIRST + f', <{REAL_LISTING}&page=1&before=Y3Vy%3D>; rel="prev"'
REAL_FINAL = f'<{REAL_LISTING}&page=2&before=Y3Vy%3D>; rel="prev"'


@pytest.mark.parametrize("header,expected", [
    (REAL_FIRST, {"next": f"{REAL_LISTING}&after=Y3Vy%3D&page=2"}),
    (REAL_MIDDLE, {"next": f"{REAL_LISTING}&after=Y3Vy%3D&page=2",
                   "prev": f"{REAL_LISTING}&page=1&before=Y3Vy%3D"}),
    (REAL_FINAL, {"prev": f"{REAL_LISTING}&page=2&before=Y3Vy%3D"}),
    ('<https://api.github.com/x?labels=a,b&page=2>; rel="next"', {"next": "https://api.github.com/x?labels=a,b&page=2"}),
    ('<https://api.github.com/x?page=2>; REL="NEXT"', {"next": "https://api.github.com/x?page=2"}),
    ('<https://api.github.com/x?page=2>;rel=next', {"next": "https://api.github.com/x?page=2"}),
    ('<https://api.github.com/x?page=2>; rel="next last"', {"next": "https://api.github.com/x?page=2",
                                                           "last": "https://api.github.com/x?page=2"}),
    ('<https://api.github.com/x?page=2>; title="a, b"; rel="next"', {"next": "https://api.github.com/x?page=2"}),
    ("", {}),
])
def test_link_headers_parse_as_github_and_rfc8288_send_them(header: str, expected: dict) -> None:
    assert parseLinks(header) == expected


# -- a header the census reads by name, whatever its case ---------------------------------------

def test_a_title_case_link_header_name_is_read_not_missed() -> None:
    rows = issueRows(range(1, 201))

    def fetch(url: str) -> Response:
        if "state=closed" in url:
            return Response(200, {}, "[]")
        page = servedPage(parse_qs(urlparse(url).query))
        if page == 1:
            return Response(200, {"Link": f'<{BASE}&after={quote(cursorFor(1))}&page=2>; rel="next"'},
                            json.dumps(rows[:100]))
        if page == 2:
            return Response(200, {}, json.dumps(rows[100:]))
        return Response(200, {}, "[]")

    listing = listAll(BASE, fetch)

    assert listing.reason is None
    assert listing.pagesFetched == 2
    assert len(listing.rows) == 200


def test_repeated_link_headers_are_merged_not_overwritten(monkeypatch, local_github) -> None:
    monkeypatch.setattr(census, "API", local_github.base)

    def respond(path: str, base: str):
        if "state=closed" in path:
            return 200, [], "[]"
        query = parse_qs(urlparse(path).query)
        page = servedPage(query)
        if page == 1:
            nxt = f'<{base}/repos/{REPO}/issues?state=open&per_page=100&after={quote(cursorFor(1))}&page=2>; rel="next"'
            first = f'<{base}/repos/{REPO}/issues?state=open&per_page=100&page=1>; rel="first"'
            return 200, [("Link", nxt), ("Link", first)], json.dumps(issueRows(range(1, 101)))
        if page == 2:
            prev = f'<{base}/repos/{REPO}/issues?state=open&per_page=100&page=1&before={quote(cursorFor(1))}>; rel="prev"'
            return 200, [("Link", prev)], json.dumps(issueRows(range(101, 151)))
        return 200, [], "[]"

    local_github.respond = respond
    listing = listAll(f"{local_github.base}/repos/{REPO}/issues?state=open&per_page=100",
                      lambda url: httpFetch(url, None))

    assert listing.reason is None, listing.reason
    assert listing.pagesFetched == 2
    assert len(listing.rows) == 150


# -- redirects are refused, never followed ------------------------------------------------------

def redirectingIssues(path: str, base: str):
    if "/actions/workflows" in path:
        return 200, [("Content-Type", "application/json")], json.dumps({"workflows": []})
    if path.startswith(f"/repos/{REPO}/issues?state=open"):
        return 301, [("Location", "/elsewhere/issues?state=open&per_page=100")], ""
    return 200, [("Content-Type", "application/json")], "[]"


def test_httpfetch_refuses_to_follow_a_redirect_and_names_its_location(local_github) -> None:
    local_github.respond = redirectingIssues

    with pytest.raises(FetchError) as caught:
        httpFetch(f"{local_github.base}/repos/{REPO}/issues?state=open&per_page=100", "ghp_b6sentinel")

    assert caught.value.reason == "redirected"
    assert caught.value.location == "/elsewhere/issues?state=open&per_page=100"


def test_a_redirected_open_listing_is_incomplete_and_adopts_no_rows(monkeypatch, local_github) -> None:
    monkeypatch.setattr(census, "API", local_github.base)
    local_github.respond = redirectingIssues

    document = collectCensus(REPO, NOW, lambda url: httpFetch(url, None))

    section = document["completeness"]["issues"]
    assert section["complete"] is False
    assert section["reason"] == "redirected"
    assert section["diagnostics"]["redirectLocation"] == "/elsewhere/issues?state=open&per_page=100"
    assert section["diagnostics"]["failingRequest"] == f"/repos/{REPO}/issues?state=open&per_page=100"
    assert document["issues"] == []


def test_any_3xx_on_a_listing_page_fails_closed_as_redirected() -> None:
    def fetch(url: str) -> Response:
        return Response(301, {"location": f"{BASE}&page=2"}, "")

    listing = listAll(BASE, fetch)

    assert listing.reason == "redirected"
    assert listing.rows == []


def test_the_token_reaches_the_api_but_never_the_census(monkeypatch, local_github, tmp_path) -> None:
    monkeypatch.setattr(census, "API", local_github.base)
    monkeypatch.setenv("GH_TOKEN", "ghp_b6sentinel")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    local_github.respond = redirectingIssues
    out = tmp_path / "github-issues.json"

    code = main(["--repo", REPO, "--root", str(tmp_path), "--out", str(out),
                 "--closed-window-days", "30", "--now", NOW_TEXT])

    assert code == census.EXIT_INCOMPLETE
    assert any(auth == "Bearer ghp_b6sentinel" for _, auth in local_github.seen)
    assert "ghp_b6sentinel" not in Path(out).read_text(encoding="utf-8")


# -- foreign continuations and diagnostics ------------------------------------------------------

def test_a_next_link_on_another_host_is_never_followed_with_the_token() -> None:
    requested: list[str] = []

    def fetch(url: str) -> Response:
        requested.append(url)
        if "state=closed" in url:
            return Response(200, {}, "[]")
        link = '<https://evil.example/repos/o/r/issues?state=open&per_page=100&page=2>; rel="next"'
        return Response(200, {"link": link}, json.dumps(issueRows(range(1, 101))))

    listing = listAll(BASE, fetch)

    assert listing.reason == "foreign-continuation"
    assert not any("evil.example" in url for url in requested)


def test_a_next_link_that_loops_back_fails_closed_as_next_loop() -> None:
    def fetch(url: str) -> Response:
        if "state=closed" in url:
            return Response(200, {}, "[]")
        return Response(200, {"link": f'<{BASE}&page=1>; rel="next"'}, json.dumps(issueRows(range(1, 101))))

    listing = listAll(BASE, fetch)

    assert listing.reason == "next-loop"
    assert listing.pagesFetched == 2


def test_an_incomplete_census_records_non_secret_probe_diagnostics() -> None:
    gh = FakeGitHub(pageSize=100, linkMode="none")
    for index in range(150):
        gh.add(f"issue {index}")

    document = gh.census(NOW)

    section = document["completeness"]["issues"]
    assert section["complete"] is False
    assert section["reason"] == "unlinked-continuation"
    diagnostics = section["diagnostics"]
    assert diagnostics["probePage"] == 2
    assert diagnostics["probeRows"] == 50
    assert diagnostics["failingRequest"] == f"/repos/{REPO}/issues?state=open&per_page=100&page=2"
    assert diagnostics["pagesFetched"] == 1
    assert diagnostics["lastLinkHeader"] == ""
    assert "Bearer" not in json.dumps(document)


def test_the_last_fetched_link_header_is_recorded_when_a_walk_fails_mid_listing(monkeypatch) -> None:
    gh = FakeGitHub(pageSize=100)
    for index in range(233):
        gh.add(f"issue {index}")
    gh.pageFailures[("open", 3)] = 502

    document = gh.census(NOW)

    diagnostics = document["completeness"]["issues"]["diagnostics"]
    cursor = quote(cursorFor(2), safe="")
    # The request sent names the repository by path (same listing and cursor); GitHub's raw link keeps its numeric form.
    assert diagnostics["failingRequest"] == f"/repos/gaia-research/gaia-skill-tree/issues?state=open&per_page=100&after={cursor}&page=3"
    assert diagnostics["lastLinkHeader"].startswith("<https://api.github.com/repositories/")
    assert 'rel="next"' in diagnostics["lastLinkHeader"]


# -- a loopback server for the real urllib path -------------------------------------------------

class LocalGitHub:
    """A loopback server that answers census requests from ``respond(path, base)``.

    ``seen`` records each request path with the Authorization header it carried.
    """

    def __init__(self) -> None:
        self.respond = lambda path, base: (404, [], "{}")
        self.seen: list[tuple[str, str | None]] = []
        outer = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args) -> None:  # noqa: D401 - keep test output quiet
                return

            def do_GET(self) -> None:
                outer.seen.append((self.path, self.headers.get("Authorization")))
                status, headers, body = outer.respond(self.path, outer.base)
                payload = body.encode("utf-8")
                self.send_response(status)
                for name, value in headers:
                    self.send_header(name, value)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.base = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def __enter__(self) -> "LocalGitHub":
        self.thread.start()
        return self

    def __exit__(self, *exc) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()


@pytest.fixture
def local_github(monkeypatch):
    monkeypatch.setenv("no_proxy", "127.0.0.1,localhost")
    monkeypatch.setenv("NO_PROXY", "127.0.0.1,localhost")
    with LocalGitHub() as server:
        yield server
