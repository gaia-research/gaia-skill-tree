"""
scripts.upstream_watcher.live — GitHub access for the batch planner (#2131).

Reads use the REST LIST endpoints with explicit page iteration rather than
``gh issue list --search``: GitHub's search index lags issue creation by
seconds to minutes, which is exactly how duplicate children and umbrellas
slipped through before. Every failure raises GhError; callers treat that as
unknown evidence and make zero writes (fail closed).
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, NamedTuple
from urllib.parse import quote

from scripts.lib.github_api import (
    GitHubFetchError,
    GitHubNotFound,
    is_permanent_unavailable,
    is_permission_problem,
    is_rate_limited,
)
from scripts.steward_issue_census import Response, listAll

DEFAULT_REPO = "gaia-research/gaia-skill-tree"
PER_PAGE = 100
MAX_PAGES = 100
CLOSED_WINDOW_DAYS = 30
UMBRELLA_LABEL = "upstream:release"  # the closed-umbrella history is LISTed with this label
CHILD_LABEL = "upstream:child"  # the closed-child history is LISTed with this label (rejection memory, M6)
# gh prints "(HTTP 301)" for a transferred issue (its old number now redirects) and
# "(HTTP 404)" / "(HTTP 410)" for a deleted or gone one. All three mean the number
# no longer names a live issue. Every other failure stays a plain GhError.
_ABSENT_RE = re.compile(r"HTTP (301|404|410)\b")


class GhError(RuntimeError):
    """A GitHub CLI call failed or returned an unparseable response."""


class GhNotFound(GhError):
    """GitHub answered 301 (transferred), 404 or 410: the number is definitively absent."""

    def __init__(self, message: str, status: str):
        super().__init__(message)
        self.status = status


class SuiteUnavailable(RuntimeError):
    """A suite is skipped for this run and cannot block the others (H2, C9 H-B).

    ``reason="permanent"`` (H2): the upstream refuses the suite for good (HTTP 451, 410, or a repo-refusal 403).
    ``reason="tree-truncated"`` (C9 H-B): the component tree is truncated and the directory walk could not finish
    within its budget, or a sub-call failed after its retries.

    The watcher skips that suite and lists it under ``unavailable``. It is deliberately NOT an
    UnknownEvidenceError: the run is not blocked, and the skipped suite produces no finding, so it can
    never produce a removal or an approval change.
    """

    def __init__(self, message: str, reason: str = "permanent"):
        super().__init__(message)
        self.reason = reason


# C9 (H-B): a transient GitHub read is retried before it is unknown evidence. Three attempts in all, so two waits:
# 1s after the first failure and 2s after the second. The sleep is looked up at call time so a test can replace it.
RETRY_DELAYS = (1, 2)
RETRY_SLEEP = time.sleep


def is_transient(exc: GitHubFetchError) -> bool:
    """True for a failure that may clear on its own: no response, a 429, a 5xx, or a rate-limited 403.

    A 404, a permanent refusal (451, 410, a repo-refusal 403) and a permission 403 are not transient: retrying
    cannot change them.
    """
    if isinstance(exc, GitHubNotFound) or is_permanent_unavailable(exc):
        return False
    status = exc.status
    if status is None or status == 429 or status >= 500:
        return True
    return status == 403 and is_rate_limited(exc)


def retry_transient(action: Callable[[], Any]) -> Any:
    """Run *action*, retrying a transient GitHub failure with the RETRY_DELAYS backoff. The last error is raised."""
    attempts = len(RETRY_DELAYS) + 1
    for attempt in range(attempts):
        try:
            return action()
        except GitHubFetchError as exc:
            if attempt == attempts - 1 or not is_transient(exc):
                raise
            RETRY_SLEEP(RETRY_DELAYS[attempt])
    raise AssertionError("unreachable: the loop always returns or raises")  # pragma: no cover


def unknown_read_detail(exc: GitHubFetchError) -> str:
    """M-4 (C9): the suffix that makes an unknown-evidence message name a token or App permission problem."""
    if is_permission_problem(exc):
        return (
            " (a permission problem: GitHub answered 'Resource not accessible by integration'; grant the watcher "
            "token or App read access to this repository, then re-run)"
        )
    return ""


class UnknownEvidenceError(RuntimeError):
    """A read the watcher needs to decide what to do failed or came back incomplete.

    Raised on the poll path (release, tree) so the run can exit 3 with zero writes.
    Never caught as "absent" and never turned into an empty result.
    """


def default_repo() -> str:
    return os.environ.get("GITHUB_REPOSITORY") or DEFAULT_REPO


GITHUB_API = "https://api.github.com/"
LIST_ATTEMPTS = 3
LIST_RETRY_SECONDS = 2


def _label_names(issue: dict) -> set[str]:
    return {label["name"] if isinstance(label, dict) else label for label in issue.get("labels", [])}


def _parse_include(out: str) -> Response:
    """Split ``gh api --include`` output into status, lower-cased headers and body. Unparseable output has status 0."""
    parts = re.split(r"\r?\n\r?\n", out, maxsplit=1)
    head, body = parts[0], (parts[1] if len(parts) > 1 else "")
    lines = head.splitlines()
    status_match = re.match(r"HTTP/\S+\s+(\d{3})", lines[0]) if lines else None
    status = int(status_match.group(1)) if status_match else 0
    headers: dict[str, str] = {}
    for line in lines[1:]:
        name, sep, value = line.partition(":")
        if sep:
            headers[name.strip().lower()] = value.strip()
    return Response(status, headers, body)


class LiveGh:
    """Thin wrapper over the ``gh`` CLI. All methods raise GhError on failure."""

    def __init__(self, repo: str | None = None, runner: Callable[..., Any] | None = None):
        self.repo = repo or default_repo()
        # Resolved at construction, not at import, so a patched subprocess.run is honoured.
        self._runner = runner or subprocess.run

    def _run(self, args: list[str], timeout: int = 60) -> str:
        try:
            res = self._runner(args, capture_output=True, text=True, timeout=timeout)
        except Exception as exc:  # noqa: BLE001 — missing gh binary, timeout, ...
            raise GhError(f"gh {args[1] if len(args) > 1 else ''} failed to run: {exc}") from exc
        if res.returncode != 0:
            stderr = str(res.stderr or "").strip()
            message = f"gh {' '.join(args[1:3])} exited {res.returncode}: {stderr}"
            absent = _ABSENT_RE.search(stderr)
            if absent:
                raise GhNotFound(message, absent.group(1))
            raise GhError(message)
        return res.stdout

    def _json(self, args: list[str]) -> Any:
        out = self._run(args)
        try:
            return json.loads(out or "null")
        except json.JSONDecodeError as exc:
            raise GhError(f"unparseable JSON from gh {args[1:3]}: {exc}") from exc

    def list_issues(self, state: str, since: str | None = None, labels: str | None = None) -> list[dict]:
        """Return every issue (PRs included) in *state*, or raise GhError when the listing cannot be proven complete.

        Pagination is the census contract (``scripts.steward_issue_census.listAll``): follow ``rel="next"``, refuse a
        short page before the last, and refuse an empty linked page unless the repository's count confirms it. The
        open listing is confirmed exactly against the repository's ``open_issues_count``, and a labelled open list is
        taken from that verified listing, so no search index is involved. A closed listing has no count to confirm its
        end, so each walk ending on a full page is refused, and the closed read keeps the largest complete walk of up to
        LIST_ATTEMPTS. Only a history every attempt returns empty is accepted as an empty history.
        """
        if state == "open":
            rows = self._verified_open()
            if since:
                rows = [row for row in rows if str(row.get("updated_at") or "") >= since]
            wanted = set(filter(None, (labels or "").split(",")))
            return [row for row in rows if wanted <= _label_names(row)]
        path = f"repos/{self.repo}/issues?state={state}&per_page={PER_PAGE}"
        if since:
            path += f"&since={quote(since, safe='')}"
        if labels:
            path += f"&labels={quote(labels, safe=',')}"
        return self._closed(path, state)

    def _closed(self, path: str, state: str) -> list[dict]:
        """A closed listing, read up to LIST_ATTEMPTS times, keeping the largest complete walk.

        An anomaly can only lose items, never add them, so the largest walk that completed is the best evidence. A walk
        that ends on a full page is not complete, because no count confirms its end, and it is not kept.
        """
        best: list[dict] | None = None
        failure: GhError | None = None
        for attempt in range(LIST_ATTEMPTS):
            if attempt:
                RETRY_SLEEP(LIST_RETRY_SECONDS)
            try:
                listing = self._walk(path)
            except GhError as exc:
                failure = exc
                continue
            if listing.pageSizes and listing.pageSizes[-1] == PER_PAGE:
                failure = GhError(f"{state} issue listing ends on a full page; its end cannot be confirmed (refusing)")
                continue
            if best is None or len(listing.rows) > len(best):
                best = listing.rows
        if best is None:
            raise failure or GhError(f"{state} issue listing was not read")
        return best

    def _verified_open(self) -> list[dict]:
        """The open listing, confirmed exactly against the repository's own open count, read again on a mismatch.

        A mismatch can be a create or close landing between the two reads, so the read is retried a few times. A
        persistent mismatch is unknown evidence, not an empty backlog.
        """
        path = f"repos/{self.repo}/issues?state=open&per_page={PER_PAGE}"
        detail = "no attempt"
        for attempt in range(LIST_ATTEMPTS):
            if attempt:
                RETRY_SLEEP(LIST_RETRY_SECONDS)
            count = self._open_count()
            try:
                listing = self._walk(path, expected=count)
            except GhError as exc:
                # An intermittent empty or short page is retried like a mismatch; a persistent one is refused below.
                detail = str(exc)
                continue
            if count is not None and count == len(listing.rows):
                return listing.rows
            detail = f"listed {len(listing.rows)} open items, repository reports {count}"
        raise GhError(f"open issue listing not confirmed after {LIST_ATTEMPTS} attempts: {detail} (refusing)")

    def _walk(self, path: str, expected: int | None = None) -> Any:
        """One complete walk of *path*, with the census's rules. Raises GhError on any incomplete or inconsistent page."""
        listing = listAll(f"{GITHUB_API}{path}", self._fetch, expectedItems=expected)
        if listing.reason is not None:
            raise GhError(f"issue listing incomplete: {listing.reason} at {listing.failingRequest}")
        if any(size != PER_PAGE for size in listing.pageSizes[:-1]):
            raise GhError("issue listing has a short page before its last page; refusing a truncated list")
        return listing

    def _fetch(self, url: str):
        """One GET for the census walk, through ``gh api --include`` so the Link header is visible."""
        path = url[len(GITHUB_API):] if url.startswith(GITHUB_API) else url
        out = self._run(["gh", "api", "--method", "GET", "--include", path])
        return _parse_include(out)

    def _open_count(self) -> int | None:
        """The repository's ``open_issues_count`` (issues and pull requests alike), or None when it cannot be read."""
        try:
            data = self._json(["gh", "api", f"repos/{self.repo}"])
        except GhError:
            return None
        count = data.get("open_issues_count") if isinstance(data, dict) else None
        return count if isinstance(count, int) and not isinstance(count, bool) and count >= 0 else None

    def get_issue(self, number: int) -> dict:
        data = self._json(["gh", "api", f"repos/{self.repo}/issues/{number}"])
        if not isinstance(data, dict) or "number" not in data:
            raise GhError(f"issue #{number} not returned")
        return data

    def issue_state(self, number: int) -> str:
        """Return ``open``, ``closed`` or ``absent`` for one issue.

        ``absent`` is returned only for a definitive HTTP 301 (transferred), 404 or
        410, and each such answer is announced with a ``::notice::`` naming the
        number. Any other failure raises GhError, so callers treat it as unknown
        evidence.
        """
        try:
            issue = self.get_issue(number)
        except GhNotFound as exc:
            print(
                f"::notice::child #{number} is absent (HTTP {exc.status}); "
                "treated as unresolved, never as resolved",
                file=sys.stderr,
            )
            return "absent"
        return "closed" if issue.get("state") == "closed" else "open"

    def child_state(self, number: int) -> str:
        """The disposition-aware state of one child (M6): ``open``, ``closed-rejected``, ``closed`` or ``absent``.

        ``closed-rejected`` is a closed child carrying upstream:rejected. ``closed`` is a closed child without
        one. ``absent`` is returned only for a definitive 301, 404 or 410 (announced with a ``::notice::``).
        Any other failure raises GhError.
        """
        try:
            issue = self.get_issue(number)
        except GhNotFound as exc:
            print(
                f"::notice::child #{number} is absent (HTTP {exc.status}); "
                "treated as unresolved, never as resolved",
                file=sys.stderr,
            )
            return "absent"
        if issue.get("state") != "closed":
            return "open"
        labels = {label.get("name") if isinstance(label, dict) else label for label in issue.get("labels", [])}
        return "closed-rejected" if "upstream:rejected" in labels else "closed"

    def list_comments(self, number: int) -> list[dict]:
        """Return every comment on *number*, following explicit pages (M5 record comments).

        Any failure raises GhError. A short page ends the walk; reaching MAX_PAGES is an error.
        """
        items: list[dict] = []
        for page in range(1, MAX_PAGES + 1):
            batch = self._json(
                ["gh", "api", "--method", "GET", f"repos/{self.repo}/issues/{number}/comments",
                 "-f", f"per_page={PER_PAGE}", "-f", f"page={page}"]
            )
            if not isinstance(batch, list):
                raise GhError(f"comment page {page} of #{number} is not an array")
            items.extend(batch)
            if len(batch) < PER_PAGE:
                return items
        raise GhError(f"comment list of #{number} exceeded {MAX_PAGES} pages; refusing to truncate")

    def edit_comment(self, comment_id: int, body: str) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as handle:
            handle.write(body)
            body_file = handle.name
        try:
            self._run(
                ["gh", "api", "--method", "PATCH", f"repos/{self.repo}/issues/comments/{comment_id}",
                 "-F", f"body=@{body_file}"]
            )
        finally:
            Path(body_file).unlink(missing_ok=True)

    def delete_comment(self, comment_id: int) -> None:
        """Delete one issue comment: a surplus record chunk (M7). Any failure raises GhError."""
        self._run(["gh", "api", "--method", "DELETE", f"repos/{self.repo}/issues/comments/{comment_id}"])

    def create_issue(self, title: str, labels: list[str], body: str) -> int:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as handle:
            handle.write(body)
            body_file = handle.name
        try:
            url = self._run(
                ["gh", "issue", "create", "--repo", self.repo, "--title", title,
                 "--label", ",".join(labels), "--body-file", body_file]
            ).strip()
        finally:
            Path(body_file).unlink(missing_ok=True)
        number = url.rstrip("/").rsplit("/", 1)[-1]
        if not number.isdigit():
            raise GhError(f"could not parse issue number from {url!r}")
        return int(number)

    def edit_issue(self, number: int, title: str, body: str) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as handle:
            handle.write(body)
            body_file = handle.name
        try:
            self._run(
                ["gh", "issue", "edit", str(number), "--repo", self.repo,
                 "--title", title, "--body-file", body_file]
            )
        finally:
            Path(body_file).unlink(missing_ok=True)

    def edit_labels(self, number: int, add: list[str] | tuple[str, ...] = (), remove: list[str] | tuple[str, ...] = ()) -> None:
        flags: list[str] = []
        for label in add:
            flags += ["--add-label", label]
        for label in remove:
            flags += ["--remove-label", label]
        if flags:
            self._run(["gh", "issue", "edit", str(number), "--repo", self.repo, *flags])

    def comment(self, number: int, body: str) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as handle:
            handle.write(body)
            body_file = handle.name
        try:
            self._run(["gh", "issue", "comment", str(number), "--repo", self.repo, "--body-file", body_file])
        finally:
            Path(body_file).unlink(missing_ok=True)


def closed_since(now: dt.datetime | None = None, days: int = CLOSED_WINDOW_DAYS) -> str:
    """ISO-8601 cutoff for the recently-closed window."""
    now = now or dt.datetime.now(dt.timezone.utc)
    return (now - dt.timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_live(gh: LiveGh, now: dt.datetime | None = None) -> dict:
    """Snapshot open issues, recently closed ones, and the full closed history that must not expire.

    ``issues`` holds open issues, those closed inside the recent window, and every closed
    ``upstream:child`` issue with no window (M6). Rejection memory must survive longer than
    30 days, or a candidate rejected months ago would be proposed again.
    ``closedUmbrellas`` holds every closed ``upstream:release`` issue with no window,
    because carry-forward must find a suite's newest closed umbrella however long ago it
    closed. Pull requests are excluded from both. Returns raw REST dicts.
    Raises GhError on any list failure (including an incomplete page walk), which
    the caller must treat as unknown evidence.
    """
    open_items = gh.list_issues("open")
    closed_items = gh.list_issues("closed", since=closed_since(now))
    closed_children = gh.list_issues("closed", labels=CHILD_LABEL)
    umbrella_items = gh.list_issues("closed", labels=UMBRELLA_LABEL)
    seen: set[int] = set()
    issues = []
    for item in open_items + closed_items + closed_children:
        if item.get("pull_request") or item["number"] in seen:
            continue
        seen.add(item["number"])
        issues.append(item)
    closed_umbrellas = [item for item in umbrella_items if not item.get("pull_request")]
    return {"issues": issues, "closedUmbrellas": closed_umbrellas}


UMBRELLA_TITLE = re.compile(r"^\[upstream\] (?P<repo>[^\s/]+/\S+) → ")


class Umbrellas(NamedTuple):
    """The open umbrellas of one suite. ``canonical`` is the lowest-numbered exact match, or None.

    ``duplicates`` are the other exact matches: they are never written, and Steward reconciles them.
    ``ambiguous`` are open ``upstream:release`` titles that name the suite but do not parse to its identity.
    """

    canonical: dict | None
    duplicates: list[dict]
    ambiguous: list[dict]


def suite_key(owner_repo: str) -> str:
    """A suite's stable identity: owner/repo, lower-cased. GitHub owner and repository names are case-insensitive."""
    return owner_repo.strip().lower()


def umbrella_suite(title: str) -> str | None:
    """The suite key an umbrella title names, or None when the title is not in the umbrella form."""
    match = UMBRELLA_TITLE.match(title or "")
    return suite_key(match.group("repo")) if match else None


def mentions_suite(title: str, key: str) -> bool:
    """Whether *title* names the suite *key* as a whole token: ``gbrain`` does not match ``gbrain-extra``."""
    return re.search(rf"(?<![\w/.-]){re.escape(key)}(?![\w.-])", title.lower()) is not None


def canonical_umbrellas(issues: list[dict], owner_repo: str) -> Umbrellas:
    """Classify the open ``upstream:release`` issues that belong to *owner_repo*.

    Identity is parsed from the title, never matched as a substring, so ``obra/superpowers`` does not claim
    ``obra/superpowers-extra``. A title that contains the suite but does not parse is ambiguous, and the caller
    must refuse to write for that suite rather than guess.
    """
    key = suite_key(owner_repo)
    exact: list[dict] = []
    ambiguous: list[dict] = []
    for issue in issues:
        if issue.get("state") != "open" or issue.get("pull_request"):
            continue
        labels = {label["name"] for label in issue.get("labels", [])}
        if "upstream:release" not in labels:
            continue
        title = issue.get("title") or ""
        parsed = umbrella_suite(title)
        if parsed == key:
            exact.append(issue)
        elif parsed is None and mentions_suite(title, key):
            ambiguous.append(issue)
    exact.sort(key=lambda issue: issue["number"])
    return Umbrellas(exact[0] if exact else None, exact[1:], sorted(ambiguous, key=lambda issue: issue["number"]))
