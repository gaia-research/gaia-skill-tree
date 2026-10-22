#!/usr/bin/env python3
"""Collect the GitHub issue census for the Steward issue-hygiene sensor (#2130).

Writes `steward-github-census-v1` to `.gaia/steward/inputs/github-issues.json`:

    python scripts/steward_issue_census.py --repo gaia-research/gaia-skill-tree

Stdlib plus the repo's own policy loader. Uses GH_TOKEN or GITHUB_TOKEN when set, otherwise
talks unauthenticated. The HTTPS proxy comes from the environment, as urllib normally honors
it. Pagination follows the server's `Link: rel="next"` URL exactly as sent. The issues endpoint is
cursor-paginated (`after`/`before` on absolute `repositories/<id>` URLs): it never sends `rel="last"`,
and its final page names only `rel="prev"`. A walk therefore ends at a page with no `next` link, and that
end is checked by one probe: the start query at offset `pagesFetched + 1` with no cursor, which must be
empty. The probe never carries the walk's cursor, because a cursor wins over `page` on the real
endpoint and would re-serve the final page. Redirects are never followed: any 3xx fails closed.

The closed window defaults to `issueHygiene.closedWindowDays` in `founder/steward/POLICY.yaml`
(read under `--root`); `--closed-window-days` overrides it. An unreadable policy refuses the run
with exit 2 and writes nothing.

Fail closed: any HTTP error, 3xx (`redirected`), rate limit, unparsable page, page cap, short pagination,
`unlinked-continuation` (a non-empty probe after a page with no next link), `empty-linked-page`,
`foreign-continuation` (a next link off the API origin) or `mutated-during-walk` (a second walk of the
open listing disagrees with the first) writes a census with `completeness.*.complete = false` and the
reason, then exits 3. An incomplete section also carries `diagnostics`: the failing request path and
query, the redirect Location path, the probe page and row count, the pages fetched, and the raw Link
header of the last fetched page. None of it holds a token or a host. A file that looks complete is
never written for a partial fetch. The workflow listing is a separate section: if it fails, only
`workflows.complete` is false, and closures that depend on it stay Class B or C. The token is never
printed and never written to the census.

This collector writes only the census. Removing a stale census is the driver's job
(`scripts/steward_drive.py` deletes the file after an exit 1 failure, and leaves an exit 3 file
for the sensor to report as incomplete).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, NamedTuple

SCHEMA = "steward-github-census-v1"
DEFAULT_REPO = "gaia-research/gaia-skill-tree"
DEFAULT_OUT = Path(".gaia/steward/inputs/github-issues.json")
DEFAULT_CLOSED_WINDOW_DAYS = 30
REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_RELATIVE = Path("founder/steward/POLICY.yaml")
PER_PAGE = 100
MAX_PAGES = 200
TIMEOUT_SECONDS = 30
API = "https://api.github.com"
EXIT_COMPLETE = 0
EXIT_USAGE = 2
EXIT_INCOMPLETE = 3


class FetchError(Exception):
    """A fetch that cannot be trusted. ``reason`` is machine-readable and token-free.

    ``location`` is the path and query of a redirect target (``redirected``), never a host or token.
    """

    def __init__(self, reason: str, location: str | None = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.location = location


@dataclass
class Response:
    status: int
    headers: dict[str, str]
    body: str


@dataclass
class Listing:
    """Rows from one paginated listing plus what the pagination proved about it.

    ``pagesFetched`` counts linked pages only. The empty probe that proves the end of an
    unlinked final page is not a page of the listing, so it is never counted. The diagnostic
    fields describe a failed walk and hold paths, queries and raw Link text, never a token.
    """

    rows: list[dict] = field(default_factory=list)
    pagesFetched: int = 0
    expectedPages: int | None = None
    lastLink: str | None = None
    reason: str | None = None
    failingRequest: str | None = None
    redirectLocation: str | None = None
    lastLinkHeader: str = ""
    probePage: int | None = None
    probeRows: int | None = None

    def adoptFailure(self, other: "Listing") -> None:
        """Copy the diagnostics of a failed walk onto this listing, keeping this listing's counts."""
        self.failingRequest = other.failingRequest
        self.redirectLocation = other.redirectLocation
        self.lastLinkHeader = other.lastLinkHeader
        self.probePage = other.probePage
        self.probeRows = other.probeRows


class Fetched(NamedTuple):
    """One request: its response and page when trusted, otherwise the reason it is not."""

    response: Response | None
    page: list | None
    reason: str | None
    location: str | None


def bodySha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def splitLinkValues(header: str) -> list[tuple[str, list[str]]]:
    """Split a Link header into ``(target, params)`` pairs, following RFC 8288.

    A target runs between ``<`` and ``>``, so a comma inside a URL is not a separator. A parameter runs
    to the next ``;`` or ``,`` outside a quoted string, so a quoted comma stays inside its parameter.
    Text that is not a ``<target>`` value is skipped up to the next comma.
    """
    values: list[tuple[str, list[str]]] = []
    index, size = 0, len(header)
    while index < size:
        if header[index] in " \t,":
            index += 1
            continue
        if header[index] != "<":
            comma = header.find(",", index)
            index = size if comma < 0 else comma
            continue
        close = header.find(">", index + 1)
        if close < 0:
            break
        target = header[index + 1:close]
        index = close + 1
        params: list[str] = []
        while index < size and header[index] != ",":
            if header[index] != ";":
                index += 1
                continue
            index += 1
            start, quoted = index, False
            while index < size and (quoted or header[index] not in ",;"):
                if header[index] == '"':
                    quoted = not quoted
                index += 1
            params.append(header[start:index].strip())
        values.append((target, params))
    return values


def linkRelations(params: list[str]) -> list[str]:
    """The relation types a link's parameters name. ``rel`` and its values are case-insensitive."""
    relations: list[str] = []
    for param in params:
        name, _, value = param.partition("=")
        if name.strip().lower() == "rel":
            relations.extend(value.strip().strip('"').lower().split())
    return relations


def parseLinks(header: str) -> dict[str, str]:
    """Parse an RFC 8288 Link header into ``{rel: url}``. The first target named for a relation wins."""
    links: dict[str, str] = {}
    for target, params in splitLinkValues(header):
        for relation in linkRelations(params):
            links.setdefault(relation, target)
    return links


def headerValue(headers: Mapping[str, str], name: str) -> str:
    """The value of a response header, found by name in any case. Empty when absent."""
    for key, value in headers.items():
        if key.lower() == name.lower():
            return value
    return ""


def lowerHeaders(pairs: Any) -> dict[str, str]:
    """Lower-case header names; a repeated header is joined with ``, `` rather than overwritten."""
    merged: dict[str, str] = {}
    for name, value in pairs:
        key = name.lower()
        merged[key] = f"{merged[key]}, {value}" if key in merged else value
    return merged


def requestPath(url: str) -> str:
    """The path and query of a URL: what a diagnostic may show. Never a host, never a token."""
    parts = urllib.parse.urlsplit(url)
    return parts.path + (f"?{parts.query}" if parts.query else "")


def sameOrigin(url: str) -> bool:
    """Whether a URL names the API origin the census was configured with. The token travels with every request."""
    given, configured = urllib.parse.urlsplit(url), urllib.parse.urlsplit(API)
    return (given.scheme, given.netloc) == (configured.scheme, configured.netloc)


REPOSITORY_ISSUES = re.compile(r"^/repositories/(\d+)/issues$")


def stateFilter(url: str) -> list[str] | None:
    return urllib.parse.parse_qs(urllib.parse.urlsplit(url).query).get("state")


def sameListing(url: str, start: str, allowedPaths: set[str]) -> bool:
    """Whether a ``next`` link continues THIS listing (B8 M-1): the API origin, one of the listing's paths, and the same state.

    The allowed paths are the start query's path and, when GitHub names the repository by id, the ``/repositories/<id>/issues``
    form learned from the first page's own links. A link to another repository, another endpoint or another state
    filter is a foreign continuation.
    """
    if not sameOrigin(url):
        return False
    return urllib.parse.urlsplit(url).path in allowedPaths and stateFilter(url) == stateFilter(start)


def pageNumber(url: str) -> int | None:
    query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    values = query.get("page")
    if not values:
        return None
    try:
        return int(values[0])
    except ValueError:
        return None


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Leave every 3xx as an HTTPError. urllib would follow a GET redirect silently, and the census would
    then report the target's body as this listing's rows."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001 - urllib's signature
        return None


def buildOpener() -> urllib.request.OpenerDirector:
    """An opener for census requests only: it honours the proxy environment and never follows a redirect."""
    return urllib.request.build_opener(_NoRedirect)


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
        with buildOpener().open(request, timeout=TIMEOUT_SECONDS) as response:
            return Response(response.status, lowerHeaders(response.headers.items()), response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        if 300 <= error.code < 400:
            location = headerValue(error.headers or {}, "location")
            raise FetchError("redirected", requestPath(urllib.parse.urljoin(url, location)) if location else None) from None
        lowered = lowerHeaders(error.headers.items() if error.headers else [])
        limited = error.code == 429 or (error.code == 403 and (
            lowered.get("x-ratelimit-remaining") == "0" or "retry-after" in lowered))
        raise FetchError("rate-limited" if limited else f"http-{error.code}") from None
    except (urllib.error.URLError, OSError, ValueError) as error:
        raise FetchError(f"transport-{type(error).__name__}") from None


def offsetProbeUrl(start: str, page: int) -> str:
    """The start listing asked for ``page`` by offset, with no cursor and no other page marker.

    The end probe must not carry the walk's cursor. On the real endpoint a cursor wins over ``page``, so
    keeping one would re-serve the final page. Offset paging from the start query is an independent request.
    """
    parts = urllib.parse.urlsplit(start)
    query = [(key, value) for key, value in urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
             if key not in ("page", "after", "before")]
    query.append(("page", str(page)))
    return urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(query)))


def getPage(fetch: Callable[[str], Response], url: str, extract: Callable[[Any], Any] | None) -> Fetched:
    """One request, judged. A 3xx, an HTTP error, an unparsable body or an unexpected shape is a reason, never a page."""
    try:
        response = fetch(url)
    except FetchError as error:
        return Fetched(None, None, error.reason, error.location)
    if response.status != 200:
        if 300 <= response.status < 400:
            location = headerValue(response.headers, "location")
            return Fetched(None, None, "redirected", requestPath(urllib.parse.urljoin(url, location)) if location else None)
        return Fetched(None, None, f"http-{response.status}", None)
    try:
        decoded = json.loads(response.body)
    except ValueError:
        return Fetched(None, None, "unparsable-page", None)
    page = extract(decoded) if extract is not None else decoded
    if not isinstance(page, list):
        return Fetched(None, None, "unexpected-page-shape", None)
    return Fetched(response, page, None, None)


def numbersOf(rows: list) -> list:
    """Issue numbers in listing order; ``None`` for a malformed row."""
    return [row.get("number") if isinstance(row, dict) else None for row in rows]


def listAll(start: str, fetch: Callable[[str], Response], extract: Callable[[Any], Any] | None = None) -> Listing:
    """Follow the server's ``rel="next"`` links to the end. Never returns partial rows as complete.

    Each next request is the URL the server named, cursor included. Pages are never renumbered to reach
    one, because on the cursor-paginated issues endpoint a renumbered page re-serves an earlier one.

    A page with no ``next`` link ends the walk. A non-empty final page that has no ``last`` link is then
    followed by one probe: the start query at offset ``pagesFetched + 1`` with no cursor. The probe must
    be empty, and it is not counted. A non-empty probe means the listing continued without a link, so
    the walk fails closed as ``unlinked-continuation`` and its rows are not adopted. A linked page that
    comes back empty fails closed as ``empty-linked-page``. Any 3xx fails closed as ``redirected``, and a
    ``next`` link that is not this listing (another origin, path or state filter) fails closed as ``foreign-continuation``.
    Page length is never
    evidence: ``per_page`` is a request the server may not honour.
    """
    listing = Listing()
    url = start
    viaNext = False
    requested: set[str] = set()
    links: dict[str, str] = {}
    page: list = []
    allowedPaths = {urllib.parse.urlsplit(start).path}
    while True:
        if listing.pagesFetched >= MAX_PAGES:
            listing.reason = "page-cap-exceeded"
            listing.failingRequest = requestPath(url)
            return listing
        if url in requested:
            return failListing(listing, "next-loop", url)
        requested.add(url)
        got = getPage(fetch, url, extract)
        if got.reason is not None:
            return failListing(listing, got.reason, url, got.location)
        page = got.page
        if viaNext and not page:
            return failListing(listing, "empty-linked-page", url)
        listing.rows.extend(page)
        listing.pagesFetched += 1
        listing.lastLinkHeader = headerValue(got.response.headers, "link")
        links = parseLinks(listing.lastLinkHeader)
        if not viaNext:
            # The first page's own links name this listing by repository id when GitHub uses that form (B8 M-1).
            for target in links.values():
                match = REPOSITORY_ISSUES.match(urllib.parse.urlsplit(target).path)
                if match:
                    allowedPaths.add(f"/repositories/{match.group(1)}/issues")
        if "last" in links:
            listing.lastLink = links["last"]
            listing.expectedPages = pageNumber(links["last"])
            if listing.expectedPages is None:
                return failListing(listing, "last-page-unparsable", url)
        if "next" not in links:
            break
        if not sameListing(links["next"], start, allowedPaths):
            return failListing(listing, "foreign-continuation", url)
        url = links["next"]
        viaNext = True
    if "last" not in links and page:
        probeUrl = offsetProbeUrl(start, listing.pagesFetched + 1)
        listing.probePage = listing.pagesFetched + 1
        probe = getPage(fetch, probeUrl, extract)
        if probe.reason is not None:
            return failListing(listing, probe.reason, probeUrl, probe.location)
        listing.probeRows = len(probe.page)
        if probe.page:
            return failListing(listing, "unlinked-continuation", probeUrl)
    if listing.expectedPages is None:
        listing.expectedPages = listing.pagesFetched
    if listing.expectedPages != listing.pagesFetched:
        listing.reason = f"pagination-short:{listing.pagesFetched}/{listing.expectedPages}"
    return listing


def failListing(listing: Listing, reason: str, request: str, location: str | None = None) -> Listing:
    """Record why a walk stopped: the reason, the failing request's path and query, and any redirect target."""
    listing.reason = reason
    listing.failingRequest = requestPath(request)
    listing.redirectLocation = location
    return listing


def diagnosticsOf(listing: Listing) -> dict:
    """Non-secret facts that let a failed walk be read from the receipt alone. No token, no host, no body."""
    return {
        "failingRequest": listing.failingRequest,
        "redirectLocation": listing.redirectLocation,
        "probePage": listing.probePage,
        "probeRows": listing.probeRows,
        "pagesFetched": listing.pagesFetched,
        "lastLinkHeader": listing.lastLinkHeader,
    }


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


def collectWorkflows(repo: str, fetch: Callable[[str], Response]) -> dict:
    """The workflow listing with each workflow's state (read-only REST, Class A evidence for A5).

    The response wraps the array as ``{"workflows": [...]}``. A failure here is recorded in this
    section only and never makes the issue census incomplete.
    """
    start = f"{API}/repos/{repo}/actions/workflows?per_page={PER_PAGE}"
    listing = listAll(start, fetch, extract=lambda body: body.get("workflows") if isinstance(body, dict) else None)
    items: list[dict] = []
    malformed = 0
    for raw in listing.rows:
        if not isinstance(raw, dict) or not isinstance(raw.get("path"), str) or not isinstance(raw.get("state"), str):
            malformed += 1
            continue
        items.append({
            "id": raw["id"] if isinstance(raw.get("id"), int) and not isinstance(raw.get("id"), bool) else None,
            "name": raw.get("name") if isinstance(raw.get("name"), str) else "",
            "path": raw["path"],
            "state": raw["state"],
        })
    reason = listing.reason or (f"malformed-rows:{malformed}" if malformed else None)
    section: dict[str, Any] = {
        "complete": reason is None,
        "pagesFetched": listing.pagesFetched,
        "expectedPages": listing.expectedPages if listing.expectedPages is not None else listing.pagesFetched,
        "itemCount": len(items),
        "items": items,
    }
    if reason:
        section["reason"] = reason
        section["diagnostics"] = diagnosticsOf(listing)
    return section


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
            openListing.adoptFailure(confirm)
        elif numbersOf(confirm.rows) != numbersOf(openListing.rows):
            openListing.reason = "mutated-during-walk"
    closedListing = listAll(closedStart, fetch) if openListing.reason is None else Listing(reason="skipped")
    workflows = collectWorkflows(repo, fetch)

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
            "itemCount": len(rows),
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
        failure = next((item for item in (openListing, closedListing) if item.reason and item.reason != "skipped"), None)
        if failure is not None:
            # "pulls" is a projection of this same walk, so it carries the same diagnostics.
            completeness["issues"]["diagnostics"] = diagnosticsOf(failure)
            completeness["pulls"]["diagnostics"] = diagnosticsOf(failure)
    return {
        "schemaVersion": SCHEMA,
        "repo": repo,
        "fetchedAt": isoZ(now),
        "source": "rest",
        "closedWindowDays": closedWindowDays,
        "completeness": completeness,
        "workflows": workflows,
        "issues": rows,
        "recentlyClosed": recent,
    }


def closedWindowDaysFromPolicy(root: Path) -> int:
    """``issueHygiene.closedWindowDays`` from the checkout's POLICY.yaml. Raises when unreadable."""
    import yaml

    sourcePath = str(root / "src")
    if sourcePath not in sys.path:
        sys.path.insert(0, sourcePath)
    from gaia_cli.steward.issuehygiene.hygienepolicy import loadHygienePolicy

    raw = yaml.safe_load((root / POLICY_RELATIVE).read_text(encoding="utf-8"))
    section = raw.get("issueHygiene") if isinstance(raw, dict) else None
    return loadHygienePolicy(section).closedWindowDays


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
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="checkout whose POLICY.yaml sets the closed window")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="census file to write")
    parser.add_argument("--closed-window-days", type=int, default=None,
                        help="override issueHygiene.closedWindowDays from the policy")
    parser.add_argument("--now", default=None, help="RFC 3339 fetchedAt override (tests and replays)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None, fetch: Callable[[str], Response] | None = None) -> int:
    args = parseArgs(argv)
    if "/" not in args.repo or (args.closed_window_days is not None and args.closed_window_days < 0):
        print("error: --repo must be owner/name and --closed-window-days non-negative", file=sys.stderr)
        return EXIT_USAGE
    try:
        closedWindow = args.closed_window_days if args.closed_window_days is not None else closedWindowDaysFromPolicy(args.root)
    except Exception as error:  # noqa: BLE001 - an unreadable policy refuses the run; nothing is written
        print(f"error: issueHygiene policy unreadable: {type(error).__name__}", file=sys.stderr)
        return EXIT_USAGE
    now = datetime.fromisoformat(args.now.replace("Z", "+00:00")) if args.now else datetime.now(timezone.utc)
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or None
    transport = fetch or (lambda url: httpFetch(url, token))
    document = collectCensus(args.repo, now, transport, closedWindow)
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
