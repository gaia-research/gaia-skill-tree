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
from pathlib import Path
from typing import Any, Callable

DEFAULT_REPO = "gaia-research/gaia-skill-tree"
PER_PAGE = 100
MAX_PAGES = 100
CLOSED_WINDOW_DAYS = 30
UMBRELLA_LABEL = "upstream:release"  # the closed-umbrella history is LISTed with this label
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


class UnknownEvidenceError(RuntimeError):
    """A read the watcher needs to decide what to do failed or came back incomplete.

    Raised on the poll path (release, tree) so the run can exit 3 with zero writes.
    Never caught as "absent" and never turned into an empty result.
    """


def default_repo() -> str:
    return os.environ.get("GITHUB_REPOSITORY") or DEFAULT_REPO


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
        """Return every issue (PRs included) in *state*, following explicit pages.

        A short page ends pagination. Reaching MAX_PAGES without a short page is
        an error, never a silent truncation. *labels* is a comma-separated filter
        applied by GitHub's list endpoint, not by search.
        """
        items: list[dict] = []
        for page in range(1, MAX_PAGES + 1):
            args = [
                "gh", "api", "--method", "GET", f"repos/{self.repo}/issues",
                "-f", f"state={state}", "-f", f"per_page={PER_PAGE}", "-f", f"page={page}",
            ]
            if since:
                args += ["-f", f"since={since}"]
            if labels:
                args += ["-f", f"labels={labels}"]
            batch = self._json(args)
            if not isinstance(batch, list):
                raise GhError(f"issue list page {page} is not an array")
            items.extend(batch)
            if len(batch) < PER_PAGE:
                return items
        raise GhError(f"issue list exceeded {MAX_PAGES} pages; refusing to truncate")

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
    """Snapshot open issues, recently closed ones, and the full closed umbrella history.

    ``issues`` holds open issues plus those closed inside the recent window.
    ``closedUmbrellas`` holds every closed ``upstream:release`` issue with no
    window, because carry-forward must find a suite's newest closed umbrella however
    long ago it closed. Pull requests are excluded from both. Returns raw REST dicts.
    Raises GhError on any list failure (including an incomplete page walk), which
    the caller must treat as unknown evidence.
    """
    open_items = gh.list_issues("open")
    closed_items = gh.list_issues("closed", since=closed_since(now))
    umbrella_items = gh.list_issues("closed", labels=UMBRELLA_LABEL)
    issues = [item for item in open_items + closed_items if not item.get("pull_request")]
    closed_umbrellas = [item for item in umbrella_items if not item.get("pull_request")]
    return {"issues": issues, "closedUmbrellas": closed_umbrellas}


def open_umbrellas(issues: list[dict], prefix: str) -> list[dict]:
    """Open ``upstream:release`` issues whose title starts with *prefix*."""
    found = []
    for issue in issues:
        if issue.get("state") != "open" or issue.get("pull_request"):
            continue
        labels = {label["name"] for label in issue.get("labels", [])}
        if "upstream:release" in labels and issue.get("title", "").startswith(prefix):
            found.append(issue)
    return sorted(found, key=lambda issue: issue["number"])
