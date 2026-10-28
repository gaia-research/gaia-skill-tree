"""Shared in-memory fakes for the issue-hygiene adversarial lane (E).

Nothing here touches the network. Three seams, all shaped like the real ones:

- ``FakeGitHub`` serves REST-shaped issue listings (``page``/``per_page``/``Link``) to the
  real census collector, with page-shift hooks, pagination failure injection, a
  delayed search index and per-call concurrent-mutation hooks.
- ``FakeForge`` implements ``closure.IssueForge`` over a ``FakeGitHub``, with failure
  injection, crash points (``SimulatedCrash`` is a BaseException, so no ``except
  Exception`` in the closure path can swallow it) and a write log.
- ``makeCheckout`` builds a temporary git checkout with the real ``POLICY.yaml``, a
  ``.gaia/steward/inputs/github-issues.json`` census and ``registry/`` files, which the
  sensor, the runner and the closure planner all read.

Helpers reused by the ordinary ``/gaia-steward-full`` end-to-end test that follows lane D2:
``closeRound`` (census -> reconcile -> plan -> execute), ``seedFromDocument`` and
``makeCheckout``.
"""

from __future__ import annotations

import base64
import json
import math
import shutil
import subprocess
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.parse import parse_qs, quote, urlparse

import yaml

from gaia_cli.steward.issuehygiene.census import Census, validateCensus
from gaia_cli.steward.issuehygiene.closure import ForgeBlockedError, ForgeItemError, _executeProvenClosures as executeClosures, planClosures
from gaia_cli.steward.issuehygiene.hygienepolicy import KNOWN_RULE_IDS, HygienePolicy, loadHygienePolicy
from gaia_cli.steward.issuehygiene.reconcile import reconcile
from gaia_cli.steward.issuehygiene.registryindex import buildRegistryIndex
from scripts.steward_issue_census import FetchError, Response, collectCensus

REPO = "gaia-research/gaia-skill-tree"
REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "issuehygiene" / "census-four-families.json"
CENSUS_INPUT = Path(".gaia/steward/inputs/github-issues.json")
BOT = "github-actions[bot]"
CLOCK_START = datetime(2026, 10, 21, 19, 0, tzinfo=timezone.utc)
NOW = datetime(2026, 10, 21, 19, 30, tzinfo=timezone.utc)
NOW_TEXT = "2026-10-21T19:30:00Z"
API = "https://api.github.com"
# The numeric id GitHub puts in issue Link headers for gaia-research/gaia-skill-tree (B6, live receipt).
REPO_ID = 1221716703


def cursorFor(page: int) -> str:
    """An opaque cursor naming ``page``, shaped like GitHub's base64 cursors."""
    return base64.urlsafe_b64encode(f"cursor:v2:{page}".encode("ascii")).decode("ascii")


def pageForCursor(cursor: str) -> int:
    return int(base64.urlsafe_b64decode(cursor.encode("ascii")).decode("ascii").rsplit(":", 1)[1])


def servedPage(query: Mapping[str, list[str]]) -> int:
    """The page the issues endpoint serves for a query string.

    On the real endpoint a cursor wins: ``after`` serves the page after the cursor's page and ``page``
    is ignored, so a request that keeps the cursor and only bumps ``page`` re-serves the same rows.
    """
    if "after" in query:
        return pageForCursor(query["after"][0]) + 1
    if "before" in query:
        return pageForCursor(query["before"][0])
    return int(query["page"][0]) if "page" in query else 1


def realLinkHeader(state: str, perPage: int, page: int, total: int, repoId: int = REPO_ID) -> str:
    """The Link header GitHub's issues endpoint sends for ``page`` of ``total``.

    Captured from the live endpoint (B6): absolute ``repositories/<id>`` URLs carrying ``after``/``before``
    cursors. The first page names only ``next``, a middle page names ``next`` and ``prev``, and the final
    page names only ``prev``. There is no ``last`` and no ``first``.
    """
    base = f"https://api.github.com/repositories/{repoId}/issues?state={state}&per_page={perPage}"
    links = []
    if page < total:
        links.append(f'<{base}&after={quote(cursorFor(page), safe="")}&page={page + 1}>; rel="next"')
    if page > 1:
        links.append(f'<{base}&page={page - 1}&before={quote(cursorFor(page - 1), safe="")}>; rel="prev"')
    return ", ".join(links)


def patchOpener(monkeypatch: Any, transport: Callable[..., Any]) -> None:
    """Route every census request through ``transport(request, timeout=...)``.

    The census sends its requests through a no-redirect opener (B6), so that opener is the seam a test
    replaces. ``transport`` returns a response or raises the error the test wants the census to see.
    """

    class _Opener:
        def open(self, request, timeout=None):
            return transport(request, timeout=timeout)

    monkeypatch.setattr(urllib.request, "build_opener", lambda *handlers: _Opener())


class SimulatedCrash(BaseException):
    """The process dies at this point. A BaseException, so nothing in the closure path catches it."""


def isoAt(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def loadFixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def defaultPolicy(**overrides: Any) -> HygienePolicy:
    raw: dict[str, Any] = {
        "maxClosuresPerRun": 10,
        "maxCensusAgeSeconds": 21600,
        "closedWindowDays": 30,
        "enabledRules": list(KNOWN_RULE_IDS),
        "a5Disabled": [],
        "writesEnabled": True,
    }
    raw.update(overrides)
    return loadHygienePolicy(raw)


class FakeGitHub:
    """An issue tracker that answers the census collector's REST listing.

    Rows are stored in GitHub's raw shape. Listings sort by number descending, which is
    GitHub's default ``created`` order, so a newly created issue shifts every later page.
    """

    def __init__(self, repo: str = REPO, pageSize: int = 100, linkMode: str = "real"):
        self.repo = repo
        self.pageSize = pageSize
        self.linkMode = linkMode  # real (GitHub's cursor Link shape) | none (no Link header at all)
        self.issues: dict[int, dict] = {}
        self.comments: dict[int, list[dict]] = {}
        self.clock = CLOCK_START
        self.nextNumber = 1000
        self.pageFailures: dict[tuple[str, int], int] = {}
        self.pageHooks: dict[tuple[str, int], Callable[["FakeGitHub"], None]] = {}
        self.callHooks: dict[tuple[str, int], Callable[["FakeGitHub"], None]] = {}
        self.hiddenFromSearch: set[int] = set()
        self.listCalls: list[tuple[str, int]] = []
        self.searchCalls: list[str] = []
        self.workflows: list[dict] = []
        self.login = "steward-bot"

    # -- clock and identity -------------------------------------------------

    def tick(self) -> str:
        self.clock = self.clock + timedelta(seconds=1)
        return isoAt(self.clock)

    def allocate(self) -> int:
        self.nextNumber += 1
        return self.nextNumber

    # -- writes used to build a scenario -----------------------------------

    def add(self, title: str, body: str = "", labels: tuple[str, ...] = (), author: str = BOT,
            number: int | None = None, pull: bool = False, mergedAt: str | None = None,
            state: str = "open", stateReason: str | None = None, updatedAt: str | None = None) -> int:
        number = number if number is not None else self.allocate()
        stamp = updatedAt or self.tick()
        self.issues[number] = {
            "number": number, "title": title, "state": state, "state_reason": stateReason,
            "labels": [{"name": name} for name in labels], "user": {"login": author},
            "body": body, "created_at": stamp, "updated_at": stamp,
            "closed_at": stamp if state == "closed" else None, "comments": 0,
            **({"pull_request": {"merged_at": mergedAt}} if pull else {}),
        }
        self.comments.setdefault(number, [])
        return number

    def edit(self, number: int, **fields: Any) -> None:
        self.issues[number].update(fields)
        self.issues[number]["updated_at"] = self.tick()

    def close(self, number: int, stateReason: str = "completed") -> None:
        self.edit(number, state="closed", state_reason=stateReason, closed_at=self.issues[number]["updated_at"])

    def relabel(self, number: int, add: tuple[str, ...] = (), remove: tuple[str, ...] = ()) -> None:
        names = [label["name"] for label in self.issues[number]["labels"]]
        names = [name for name in names if name not in remove] + [name for name in add if name not in names]
        self.edit(number, labels=[{"name": name} for name in names])

    # -- reads -------------------------------------------------------------

    def rowsFor(self, state: str) -> list[dict]:
        rows = [row for row in self.issues.values() if row["state"] == state]
        return sorted(rows, key=lambda row: row["number"], reverse=True)

    def listPage(self, state: str, page: int, since: str | None = None) -> tuple[int, dict, str]:
        self.listCalls.append((state, page))
        hook = self.pageHooks.pop((state, page), None)
        if hook is not None:
            hook(self)
        if (state, page) in self.pageFailures:
            return self.pageFailures[(state, page)], {}, "{}"
        rows = self.rowsFor(state)
        if since is not None and state == "closed":
            cutoff = datetime.fromisoformat(since.replace("Z", "+00:00"))
            rows = [row for row in rows if datetime.fromisoformat(row["closed_at"].replace("Z", "+00:00")) >= cutoff]
        total = math.ceil(len(rows) / self.pageSize)
        start = (page - 1) * self.pageSize
        body = rows[start:start + self.pageSize] if page <= total else []
        headers: dict[str, str] = {}
        if self.linkMode == "real":
            link = realLinkHeader(state, self.pageSize, page, total, REPO_ID)
            if link:
                headers["link"] = link
        return 200, headers, json.dumps(body)

    def fetch(self, url: str) -> Response:
        """The ``fetch`` seam of ``scripts.steward_issue_census.collectCensus``."""

        if "/actions/workflows" in url:
            return Response(200, {}, json.dumps({"total_count": len(self.workflows), "workflows": self.workflows}))
        if urlparse(url).path == f"/repos/{self.repo}":
            # The repository's own metadata: open_issues_count counts issues and pull requests alike.
            return Response(200, {}, json.dumps({"open_issues_count": len(self.rowsFor("open"))}))
        query = parse_qs(urlparse(url).query)
        state = query["state"][0]
        page = servedPage(query)
        since = query["since"][0] if "since" in query else None
        status, headers, body = self.listPage(state, page, since)
        if status == 429:
            raise FetchError("rate-limited")
        return Response(status, headers, body)

    def census(self, now: datetime = NOW, closedWindowDays: int = 30) -> dict:
        return collectCensus(self.repo, now, self.fetch, closedWindowDays)

    def search(self, query: str) -> list[int]:
        """Title search with an index that lags creation. LIST always sees every issue."""

        self.searchCalls.append(query)
        return sorted(
            number for number, row in self.issues.items()
            if number not in self.hiddenFromSearch and query.lower() in row["title"].lower()
        )

    def flushSearchIndex(self) -> None:
        self.hiddenFromSearch.clear()


def seedFromDocument(gh: FakeGitHub, document: Mapping[str, Any]) -> None:
    """Load every row of a census document (open and recently closed) into the fake."""

    for row in list(document.get("issues") or []) + list(document.get("recentlyClosed") or []):
        gh.issues[row["number"]] = {
            "number": row["number"], "title": row["title"], "state": row["state"],
            "state_reason": row.get("stateReason"), "labels": [{"name": name} for name in row.get("labels") or []],
            "user": {"login": row.get("author") or ""}, "body": row.get("body") or "",
            "created_at": row.get("createdAt"), "updated_at": row.get("updatedAt"), "closed_at": row.get("closedAt"),
            "comments": row.get("comments", 0),
            **({"pull_request": {"merged_at": row.get("mergedAt")}} if row.get("isPullRequest") else {}),
        }
        gh.comments.setdefault(row["number"], [])


class FakeForge:
    """``closure.IssueForge`` over a ``FakeGitHub``.

    ``failures`` maps (method, issue) to an exception raised once, before the call takes
    effect. ``crashAfter`` holds (method, issue) pairs after which the process dies: the
    call has already happened, the caller never sees it return.
    """

    def __init__(self, gh: FakeGitHub, failures: Mapping[tuple[str, int], Exception] | None = None,
                 crashAfter: set[tuple[str, int]] | None = None):
        self.gh = gh
        self.failures = dict(failures or {})
        self.crashAfter = set(crashAfter or ())
        self.writes: list[tuple] = []

    def _enter(self, method: str, number: int) -> None:
        hook = self.gh.callHooks.pop((method, number), None)
        if hook is not None:
            hook(self.gh)
        exc = self.failures.pop((method, number), None)
        if exc is not None:
            raise exc

    def _leave(self, method: str, number: int) -> None:
        if (method, number) in self.crashAfter:
            self.crashAfter.discard((method, number))
            raise SimulatedCrash(f"{method} #{number}")

    def getIssue(self, number: int) -> dict:
        self._enter("getIssue", number)
        row = self.gh.issues.get(number)
        if row is None or "pull_request" in row:
            raise ForgeItemError("not-an-issue")
        return {
            "number": number, "title": row["title"], "state": row["state"], "stateReason": row.get("state_reason"),
            "updatedAt": row["updated_at"], "body": row["body"], "locked": False,
            "htmlUrl": f"https://github.com/{self.gh.repo}/issues/{number}",
            "labels": sorted(label["name"] for label in row["labels"]),
        }

    def whoami(self) -> str:
        self._enter("whoami", 0)
        if self.gh.login is None:
            raise ForgeItemError("whoami: no login")
        return self.gh.login

    def listComments(self, number: int) -> list[dict]:
        self._enter("listComments", number)
        return [dict(comment) for comment in self.gh.comments.get(number, [])]

    def addComment(self, number: int, body: str) -> str | None:
        self._enter("addComment", number)
        comments = self.gh.comments.setdefault(number, [])
        url = f"https://github.com/{self.gh.repo}/issues/{number}#issuecomment-{number * 100 + len(comments) + 1}"
        comments.append({"body": body, "url": url, "author": self.gh.login})
        self.gh.issues[number]["comments"] = len(comments)
        self.gh.issues[number]["updated_at"] = self.gh.tick()
        self.writes.append(("comment", number))
        self._leave("addComment", number)
        return url

    def closeIssue(self, number: int, stateReason: str, duplicateOf: int | None = None) -> None:
        self._enter("closeIssue", number)
        self.gh.close(number, stateReason)
        self.writes.append(("close", number, stateReason, duplicateOf))
        self._leave("closeIssue", number)


class ForgeFailure:
    """Shorthand for the two failure classes the closure path understands."""

    @staticmethod
    def blocked(text: str = "http-401") -> ForgeBlockedError:
        return ForgeBlockedError(text)

    @staticmethod
    def item(text: str = "http-502") -> ForgeItemError:
        return ForgeItemError(text)


def copySchema(root: Path) -> None:
    """The tracked namedSkill schema, which the registry index reads for the status allowlist (B7 M4)."""

    target = root / "registry" / "schema" / "namedSkill.schema.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(REPO_ROOT / "registry" / "schema" / "namedSkill.schema.json", target)


def editPolicy(root: Path, overrides: Mapping[str, Any]) -> None:
    """Rewrite the checkout's POLICY.yaml ``issueHygiene`` block, keeping every other key."""

    target = root / "founder" / "steward" / "POLICY.yaml"
    raw = yaml.safe_load(target.read_text(encoding="utf-8"))
    raw["issueHygiene"] = {**raw["issueHygiene"], **overrides}
    target.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")


def approveClosureFixture(root: Path) -> None:
    """Synthetic founder ruling in a temporary test checkout, never the repository."""
    from gaia_cli.steward.issuehygiene.authority import DECISION_PATH, DECISION_ID
    target = root / DECISION_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"schemaVersion": "steward-decision-v1", "id": DECISION_ID,
                                 "status": "decided", "resolution": "approved"}), encoding="utf-8")


def makeCheckout(
    tmp: Path,
    census: Mapping[str, Any] | str | None = None,
    named: Mapping[str, str] | None = None,
    policy: Mapping[str, Any] | None = None,
    workflows: Mapping[str, str] | None = None,
    nodes: Mapping[str, str] | None = None,
) -> Path:
    """A temporary git checkout with the real POLICY.yaml and the given census and registry.

    A test checkout is a writable fixture by default: ``writesEnabled`` is set to true, because the
    shipped policy is dry-run (B5). Pass ``policy={"writesEnabled": False}`` to test the dry-run.
    ``census`` may be a document (written as JSON) or a raw string (written verbatim, for truncated or
    corrupt files). ``named`` maps ``contributor/slug`` to file text. ``registry/named`` always exists,
    as it does in a real checkout.
    """

    root = tmp / "checkout"
    root.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / "founder" / "steward").mkdir(parents=True)
    shutil.copy(REPO_ROOT / "founder" / "steward" / "POLICY.yaml", root / "founder" / "steward" / "POLICY.yaml")
    approveClosureFixture(root)
    copySchema(root)
    editPolicy(root, {"writesEnabled": True, **(policy or {})})
    (root / "registry" / "named").mkdir(parents=True, exist_ok=True)
    if census is not None:
        target = root / CENSUS_INPUT
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(census if isinstance(census, str) else json.dumps(census), encoding="utf-8")
    for identifier, text in (named or {}).items():
        contributor, slug = identifier.split("/")
        target = root / "registry" / "named" / contributor / f"{slug}.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    for relPath, text in (nodes or {}).items():
        target = root / "registry" / "nodes" / relPath
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    for name, text in (workflows or {}).items():
        target = root / ".github" / "workflows" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    return root


def censusOf(document: Mapping[str, Any], now: datetime = NOW, maxAgeSeconds: int = 21600) -> Census:
    return Census(dict(document), validateCensus(document, now, maxAgeSeconds), "fake")


def closeRound(gh: FakeGitHub, root: Path, receipts: Path, runId: str, forge: FakeForge,
               policy: HygienePolicy | None = None, now: datetime = NOW,
               document: Mapping[str, Any] | None = None) -> tuple[dict, list[dict], list[dict]]:
    """One pass in-process: census -> reconcile -> plan -> execute. Returns (manifest, plans, results)."""

    policy = policy or defaultPolicy()
    doc = dict(document) if document is not None else gh.census(now)
    manifest = reconcile(censusOf(doc, now, policy.maxCensusAgeSeconds), buildRegistryIndex(root), policy, now)
    plans = planClosures(manifest, policy)
    results = executeClosures(plans, forge, receipts, now, runId)
    return manifest, plans, results


def rowsWithNumbers(document: Mapping[str, Any], numbers: set[int]) -> list[dict]:
    return [row for row in document["issues"] if row["number"] in numbers]


__all__ = [
    "BOT", "CENSUS_INPUT", "FIXTURE", "NOW", "NOW_TEXT", "REPO", "REPO_ROOT",
    "FakeForge", "FakeGitHub", "ForgeFailure", "SimulatedCrash",
    "censusOf", "closeRound", "defaultPolicy", "editPolicy", "loadFixture", "makeCheckout", "seedFromDocument",
]
