#!/usr/bin/env python3
"""Collect the GitHub issue census for the Steward issue-hygiene sensor (#2130).

Writes `steward-github-census-v1` to `.gaia/steward/inputs/github-issues.json`:

    python scripts/steward_issue_census.py --repo gaia-research/gaia-skill-tree

Stdlib only. Uses GH_TOKEN or GITHUB_TOKEN when set, otherwise talks unauthenticated.
The HTTPS proxy comes from the environment, as urllib normally honors it. Pagination
follows REST `Link: rel="next"` to the end, and the expected page count comes from
`rel="last"` when present.

Fail closed: any HTTP error, rate limit, unparsable page, page cap, short pagination,
`unlinked-continuation` (a page with no next or last link that is followed by rows) or
`mutated-during-walk` (a second walk of the open listing disagrees with the first) writes a
census with `completeness.*.complete = false` and the reason, then exits 3. A file that looks
complete is never written for a partial fetch. The token is never printed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

SCHEMA = "steward-github-census-v1"
DEFAULT_REPO = "gaia-research/gaia-skill-tree"
DEFAULT_OUT = Path(".gaia/steward/inputs/github-issues.json")
DEFAULT_CLOSED_WINDOW_DAYS = 30
PER_PAGE = 100
MAX_PAGES = 200
TIMEOUT_SECONDS = 30
API = "https://api.github.com"
EXIT_COMPLETE = 0
EXIT_USAGE = 2
EXIT_INCOMPLETE = 3


class FetchError(Exception):
    """A fetch that cannot be trusted. ``reason`` is machine-readable and token-free."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass
class Response:
    status: int
    headers: dict[str, str]
    body: str


@dataclass
class Listing:
    """Rows from one paginated listing plus what the pagination proved about it."""

    rows: list[dict] = field(default_factory=list)
    pagesFetched: int = 0
    expectedPages: int | None = None
    lastLink: str | None = None
    reason: str | None = None


def bodySha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parseLinks(header: str) -> dict[str, str]:
    """Parse an RFC 8288 Link header into ``{rel: url}``."""
    links: dict[str, str] = {}
    for part in header.split(","):
        pieces = part.strip().split(";")
        if len(pieces) < 2:
            continue
        target = pieces[0].strip()
        if not (target.startswith("<") and target.endswith(">")):
            continue
        for param in pieces[1:]:
            name, _, value = param.strip().partition("=")
            if name.strip() == "rel":
                links[value.strip().strip('"')] = target[1:-1]
    return links


def pageNumber(url: str) -> int | None:
    query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    values = query.get("page")
    if not values:
        return None
    try:
        return int(values[0])
    except ValueError:
        return None


def httpFetch(url: str, token: str | None) -> Response:
    """One GET. Errors become FetchError with a reason that never contains the token."""
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "gaia-steward-issue-census",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            lowered = {name.lower(): value for name, value in response.headers.items()}
            return Response(response.status, lowered, response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        lowered = {name.lower(): value for name, value in (error.headers or {}).items()}
        limited = error.code == 429 or (error.code == 403 and (
            lowered.get("x-ratelimit-remaining") == "0" or "retry-after" in lowered))
        raise FetchError("rate-limited" if limited else f"http-{error.code}") from None
    except (urllib.error.URLError, OSError, ValueError) as error:
        raise FetchError(f"transport-{type(error).__name__}") from None


def withPage(url: str, page: int) -> str:
    """The same listing URL asking for ``page`` in place of whatever page it names."""
    parts = urllib.parse.urlsplit(url)
    query = [(key, value) for key, value in urllib.parse.parse_qsl(parts.query, keep_blank_values=True) if key != "page"]
    query.append(("page", str(page)))
    return urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(query)))


def numbersOf(rows: list) -> list:
    """Issue numbers in listing order; ``None`` for a malformed row."""
    return [row.get("number") if isinstance(row, dict) else None for row in rows]


def listAll(start: str, fetch: Callable[[str], Response]) -> Listing:
    """Follow ``rel="next"`` to the end. Never returns partial rows as complete.

    The end of a listing is proven two ways only. A ``rel="last"`` link must match the number
    of pages fetched. Without ``next`` or ``last``, a non-empty page is followed by a probe of
    the next page, and the walk ends only if that probe is empty. Page length is not evidence:
    ``per_page`` is a request the server may not honour, so a full page with no Link header is
    not the last page. A non-empty probe means the listing continued without a link. The walk
    then fails closed, and the probe rows are not adopted.
    """
    listing = Listing()
    url: str | None = start
    probing = False
    while url:
        if listing.pagesFetched >= MAX_PAGES:
            listing.reason = "page-cap-exceeded"
            return listing
        requested = url
        try:
            response = fetch(url)
        except FetchError as error:
            listing.reason = error.reason
            return listing
        if response.status != 200:
            listing.reason = f"http-{response.status}"
            return listing
        try:
            page = json.loads(response.body)
        except ValueError:
            listing.reason = "unparsable-page"
            return listing
        if not isinstance(page, list):
            listing.reason = "unexpected-page-shape"
            return listing
        if probing and page:
            listing.reason = "unlinked-continuation"
            return listing
        listing.rows.extend(page)
        listing.pagesFetched += 1
        links = parseLinks(response.headers.get("link", ""))
        if "last" in links:
            listing.lastLink = links["last"]
            listing.expectedPages = pageNumber(links["last"])
            if listing.expectedPages is None:
                listing.reason = "last-page-unparsable"
                return listing
        url = links.get("next")
        probing = url is None and "last" not in links and bool(page)
        if probing:
            url = withPage(requested, (pageNumber(requested) or 1) + 1)
    if listing.expectedPages is None:
        listing.expectedPages = listing.pagesFetched
    if listing.expectedPages != listing.pagesFetched:
        listing.reason = f"pagination-short:{listing.pagesFetched}/{listing.expectedPages}"
    return listing


def toRow(raw: dict) -> dict:
    body = raw.get("body") or ""
    isPull = "pull_request" in raw
    pull = raw.get("pull_request") or {}
    labels = [label["name"] for label in raw.get("labels") or [] if isinstance(label, dict) and "name" in label]
    return {
        "number": raw["number"],
        "title": raw.get("title") or "",
        "state": raw.get("state"),
        "stateReason": raw.get("state_reason"),
        "labels": labels,
        "author": (raw.get("user") or {}).get("login"),
        "createdAt": raw.get("created_at"),
        "updatedAt": raw.get("updated_at"),
        "closedAt": raw.get("closed_at"),
        "comments": raw.get("comments", 0),
        "body": body,
        "bodySha256": bodySha256(body),
        "isPullRequest": isPull,
        "mergedAt": pull.get("merged_at") if isPull else None,
        "headRef": None,
        "baseRef": None,
    }


def isoZ(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def collectCensus(
    repo: str,
    now: datetime,
    fetch: Callable[[str], Response],
    closedWindowDays: int = DEFAULT_CLOSED_WINDOW_DAYS,
) -> dict:
    """Build the census document. Pure apart from ``fetch``; never raises on fetch failure."""
    openStart = f"{API}/repos/{repo}/issues?state=open&per_page={PER_PAGE}"
    cutoff = now - timedelta(days=closedWindowDays)
    closedStart = (
        f"{API}/repos/{repo}/issues?state=closed&per_page={PER_PAGE}"
        f"&since={urllib.parse.quote(isoZ(cutoff))}"
    )
    openListing = listAll(openStart, fetch)
    confirmPages = 0
    if openListing.reason is None:
        # A close or create between pages shifts every later page, and a shifted page can skip an
        # open issue while each page still looks present. Page counts cannot see that. The open
        # listing therefore counts only if an identical second walk returns the same numbers in
        # the same order. Re-fetching page 1 alone would miss a shift that starts on a later page.
        confirm = listAll(openStart, fetch)
        confirmPages = confirm.pagesFetched
        if confirm.reason is not None:
            openListing.reason = confirm.reason
        elif numbersOf(confirm.rows) != numbersOf(openListing.rows):
            openListing.reason = "mutated-during-walk"
    closedListing = listAll(closedStart, fetch) if openListing.reason is None else Listing(reason="skipped")

    reasons = [item.reason for item in (openListing, closedListing) if item.reason and item.reason != "skipped"]
    rows: list[dict] = []
    closed: list[dict] = []
    malformed = 0
    for listing, target in ((openListing, rows), (closedListing, closed)):
        for raw in listing.rows:
            if not isinstance(raw, dict) or not isinstance(raw.get("number"), int):
                malformed += 1
                continue
            target.append(toRow(raw))
    recent = []
    for row in closed:
        closedAt = row.get("closedAt")
        try:
            when = datetime.fromisoformat(closedAt.replace("Z", "+00:00")) if closedAt else None
        except ValueError:
            when = None
        if when is not None and when >= cutoff:
            recent.append(row)
    if malformed:
        reasons.append(f"malformed-rows:{malformed}")

    complete = not reasons
    pagesFetched = openListing.pagesFetched + closedListing.pagesFetched
    # A listing that failed midway has no trustworthy expectation; complete:false is authoritative there.
    expectedPages = sum(
        item.expectedPages if item.expectedPages is not None else item.pagesFetched
        for item in (openListing, closedListing)
    )
    pulls = [row for row in rows if row["isPullRequest"]]
    reason = ";".join(reasons) or None
    completeness = {
        "issues": {
            "complete": complete, "pagesFetched": pagesFetched, "expectedPages": expectedPages,
            "confirmPagesFetched": confirmPages,
            "itemCount": sum(1 for row in rows if not row["isPullRequest"]),
            "lastLink": openListing.lastLink,
        },
        "pulls": {
            "complete": complete, "pagesFetched": pagesFetched, "expectedPages": expectedPages,
            "confirmPagesFetched": confirmPages,
            "itemCount": len(pulls), "lastLink": openListing.lastLink,
        },
    }
    if reason:
        completeness["issues"]["reason"] = reason
        completeness["pulls"]["reason"] = reason
    return {
        "schemaVersion": SCHEMA,
        "repo": repo,
        "fetchedAt": isoZ(now),
        "source": "rest",
        "closedWindowDays": closedWindowDays,
        "completeness": completeness,
        "issues": rows,
        "recentlyClosed": recent,
    }


def writeAtomic(path: Path, document: dict) -> None:
    """Write via a temp file in the same directory, then rename into place."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp = tempfile.mkstemp(dir=str(path.parent), prefix=".github-issues-", suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(document, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
        os.replace(temp, path)
    except BaseException:
        if os.path.exists(temp):
            os.unlink(temp)
        raise


def parseArgs(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--repo", default=DEFAULT_REPO, help="owner/name (default %(default)s)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="census file to write")
    parser.add_argument("--closed-window-days", type=int, default=DEFAULT_CLOSED_WINDOW_DAYS)
    parser.add_argument("--now", default=None, help="RFC 3339 fetchedAt override (tests and replays)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None, fetch: Callable[[str], Response] | None = None) -> int:
    args = parseArgs(argv)
    if "/" not in args.repo or args.closed_window_days < 0:
        print("error: --repo must be owner/name and --closed-window-days non-negative", file=sys.stderr)
        return EXIT_USAGE
    now = datetime.fromisoformat(args.now.replace("Z", "+00:00")) if args.now else datetime.now(timezone.utc)
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or None
    transport = fetch or (lambda url: httpFetch(url, token))
    document = collectCensus(args.repo, now, transport, args.closed_window_days)
    writeAtomic(args.out, document)
    complete = document["completeness"]["issues"]["complete"]
    counts = f"issues={len(document['issues'])} closed={len(document['recentlyClosed'])}"
    if complete:
        print(f"census complete: {counts} -> {args.out}")
        return EXIT_COMPLETE
    reason = document["completeness"]["issues"].get("reason", "unknown")
    print(f"census INCOMPLETE ({reason}): {counts} -> {args.out}", file=sys.stderr)
    return EXIT_INCOMPLETE


if __name__ == "__main__":
    sys.exit(main())
