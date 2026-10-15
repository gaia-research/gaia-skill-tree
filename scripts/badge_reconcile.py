#!/usr/bin/env python3
"""Upstream badge reconciliation engine (Issue #2069, Campaign #1817).

Read-only observation of what upstream GitHub repositories look like *right now*
compared with Gaia's campaign ledger. Produces an observed state and a
recommended action that are deliberately independent of the authoritative
campaign lifecycle (``manifest.json``). Nothing in this module writes to the
manifest, to GitHub, or to upstream repositories; the only side effect is the
local reservation file used by the pre-dispatch gate.

Design rules
------------
* Fail closed. Any incomplete search, rate limit, permission failure, ambiguous
  attribution or unresolved repository identity yields ``UNKNOWN`` / a refusal.
  ``UNKNOWN`` never means ready.
* A merged PR is not adoption: only a Gaia badge in the *current default-branch
  README* counts as adoption.
* A contributor-level badge (handle / rank / skills) never proves coverage of a
  specific Named Skill.
* Terminal outreach restrictions recorded in the ledger (DECLINED, OPTED_OUT,
  NO_RESPONSE) are preserved and always block dispatch.
"""

from __future__ import annotations

import base64
import concurrent.futures
import contextlib
import hashlib
import html
import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

try:  # imported as scripts.badge_reconcile (tests) or run via the planner script
    from scripts import badge_policy as bp
except ImportError:  # pragma: no cover - direct script execution
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from scripts import badge_policy as bp

SCHEMA_VERSION = 1
GITHUB_API = "https://api.github.com"

# Observed states (never written back to the ledger by reconcile).
OBSERVED_STATES = (
    "PR_OPEN",
    "ADOPTED",
    "ALREADY_ADOPTED",
    "PARTIAL_COVERAGE",
    "CLOSED_UNMERGED",
    "READY_TO_APPROVE",
    "NEEDS_REVIEW",
    "UNKNOWN",
)

# Ledger statuses that permanently restrict outreach.
TERMINAL_RESTRICTIONS = ("DECLINED", "OPTED_OUT", "NO_RESPONSE")
# Ledger statuses that mean outreach already happened / is in flight.
CONTACTED_STATUSES = ("PR_OPEN", "ADOPTED", "ALREADY_ADOPTED", "DECLINED", "OPTED_OUT", "NO_RESPONSE")

DEFAULT_CAMPAIGN_AUTHORS = ("mbtiongson1",)
# Founder holds: repo (normalized, incl. known renames) -> tracking issue. Held repos are
# never recommended for approval and never pass the pre-dispatch gate.
# Mirrors plan_badge_provisioning.REPO_MIGRATIONS (lowercased) so old names still resolve.
KNOWN_MIGRATIONS = {"safishamsi/graphify": "graphify-labs/graphify"}
CAMPAIGN_HOLDS = {
    "safishamsi/graphify": "#2067",
    "graphify-labs/graphify": "#2067",
}
MAX_PAGES = 10
# Unmarked open PRs get a full diff inspection up to this many per repo (newest first).
# Beyond it the scan is explicitly INCOMPLETE and a repo can never be READY_TO_APPROVE.
MAX_OPEN_SCAN = 40
INSPECT_WORKERS = 6  # concurrent PR diff fetches per repository
DOC_SUFFIXES = (".md", ".mdx", ".markdown", ".rst", ".adoc", ".txt", ".html", ".htm")
PER_PAGE = 100

GAIA_URL_RE = re.compile(
    r"""https?://(?:www\.)?gaiaskilltree\.com/badges/[^\s)"'<>\]]+""", re.IGNORECASE
)
DEEP_LINK_RE = re.compile(
    r"""https?://(?:www\.)?gaiaskilltree\.com/named/?#explorer/[^\s)"'<>\]]+""", re.IGNORECASE
)
CONTRIBUTOR_STEMS = {"handle", "rank", "skills"}
GAIA_HOST_RE = re.compile(r"gaiaskilltree\.com", re.IGNORECASE)  # text marker, not URL validation
PR_URL_RE = re.compile(r"^https?://github\.com/([^/]+)/([^/]+)/pull/(\d+)/?$", re.IGNORECASE)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# GitHub transport
# ---------------------------------------------------------------------------


@dataclass
class Response:
    status: int
    headers: dict[str, str]
    body: Any


class TransportError(Exception):
    """Network-level failure (no HTTP response)."""


class UrllibTransport:
    """Read-only GET transport against the GitHub REST API."""

    def __init__(self, token: str | None = None, timeout: float = 30.0) -> None:
        self.token = token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or self._gh_token()
        self.timeout = timeout

    @staticmethod
    def _gh_token() -> str | None:
        try:
            out = subprocess.run(
                ["gh", "auth", "token"], capture_output=True, text=True, timeout=15, check=False
            )
            tok = out.stdout.strip()
            return tok or None
        except (OSError, subprocess.SubprocessError):
            return None

    def get(self, url: str) -> Response:
        if not url.startswith("http"):
            url = GITHUB_API + url
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "gaia-badge-reconcile/1",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310
                raw = resp.read().decode("utf-8", "replace")
                return Response(resp.status, {k.lower(): v for k, v in resp.headers.items()}, _loads(raw))
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", "replace") if e.fp else ""
            return Response(e.code, {k.lower(): v for k, v in (e.headers or {}).items()}, _loads(raw))
        except (urllib.error.URLError, socket.timeout, OSError) as e:
            raise TransportError(str(e)) from e


def _loads(raw: str) -> Any:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except ValueError:
        return raw


class ApiError(Exception):
    def __init__(self, code: str, message: str, status: int | None = None) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.status = status


class GitHubClient:
    """Thin wrapper adding error classification, bounded retries and pagination."""

    # GitHub search budgets: 30 req/min (issues) and 10 req/min (code) when authenticated.
    SEARCH_INTERVALS = {"issues": 2.2, "code": 6.5}

    def __init__(self, transport: Any, retries: int = 2, backoff: float = 0.5,
                 sleep: Callable[[float], None] = time.sleep,
                 search_intervals: dict[str, float] | None = None,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self.transport = transport
        self.retries = retries
        self.backoff = backoff
        self.sleep = sleep
        self.clock = clock
        self.search_intervals = dict(self.SEARCH_INTERVALS if search_intervals is None else search_intervals)
        self._search_next: dict[str, float] = {}
        self._search_lock = threading.Lock()
        self._rate_limited: ApiError | None = None  # circuit breaker: stop spending calls once limited
        self._local = threading.local()  # per-thread call budget (policy scan cost guard)
        self.total_calls = 0
        self._count_lock = threading.Lock()

    @contextlib.contextmanager
    def budget(self, max_calls: int):
        """Bound the API calls the current thread may spend; past it every call raises BUDGET_EXHAUSTED.

        Retries count as calls. The yielded dict reports ``used`` and ``exhausted``.
        """
        state = {"max": max_calls, "used": 0, "exhausted": False}
        prev = getattr(self._local, "budget", None)
        self._local.budget = state
        try:
            yield state
        finally:
            self._local.budget = prev

    def _spend(self) -> None:
        state = getattr(self._local, "budget", None)
        if state is not None:
            if state["used"] >= state["max"]:
                state["exhausted"] = True
                raise ApiError("BUDGET_EXHAUSTED", f"per-repo call budget of {state['max']} reached")
            state["used"] += 1
        with self._count_lock:
            self.total_calls += 1

    def _throttle_search(self, path: str) -> None:
        """Space search calls across all worker threads so a campaign-wide run stays within budget."""
        if not path.startswith("/search/"):
            return
        bucket = "code" if path.startswith("/search/code") else "issues"
        interval = self.search_intervals.get(bucket, 0.0)
        if interval <= 0:
            return
        with self._search_lock:
            now = self.clock()
            at = max(now, self._search_next.get(bucket, 0.0))
            self._search_next[bucket] = at + interval
        if at > now:
            self.sleep(at - now)

    def get(self, path: str) -> Response:
        """GET with retries for transient (5xx / network) failures only."""
        if self._rate_limited is not None:
            raise self._rate_limited
        last: ApiError | None = None
        self._throttle_search(path)
        for attempt in range(self.retries + 1):
            self._spend()
            try:
                resp = self.transport.get(path)
            except TransportError as e:
                last = ApiError("NETWORK_ERROR", str(e))
            else:
                if resp.status >= 500:
                    last = ApiError("SERVER_ERROR", f"HTTP {resp.status}", resp.status)
                else:
                    return resp
            if attempt < self.retries:
                self.sleep(self.backoff * (2 ** attempt))
        assert last is not None
        raise last

    def get_ok(self, path: str) -> Any:
        """GET expecting 200; classify every other status into an ApiError."""
        resp = self.get(path)
        if resp.status == 200:
            return resp
        err = classify_error(resp)
        if err.code == "RATE_LIMITED":
            self._rate_limited = err
        raise err

    def paginate(self, path: str, items_key: str | None = None, max_pages: int = MAX_PAGES
                 ) -> tuple[list[Any], bool, dict[str, Any]]:
        """Return (items, complete, meta). Incomplete when truncated or flagged by GitHub."""
        sep = "&" if "?" in path else "?"
        url: str | None = f"{path}{sep}per_page={PER_PAGE}"
        items: list[Any] = []
        complete = True
        meta: dict[str, Any] = {"pages": 0}
        while url:
            if meta["pages"] >= max_pages:
                complete = False
                meta["truncated"] = True
                break
            resp = self.get_ok(url)
            meta["pages"] += 1
            body = resp.body
            if items_key is not None:
                if not isinstance(body, dict):
                    raise ApiError("BAD_RESPONSE", "expected object from search endpoint")
                if body.get("incomplete_results"):
                    complete = False
                    meta["incomplete_results"] = True
                meta["total_count"] = body.get("total_count")
                body = body.get(items_key, [])
            if not isinstance(body, list):
                raise ApiError("BAD_RESPONSE", "expected list payload")
            items.extend(body)
            url = _next_link(resp.headers.get("link", ""))
        total = meta.get("total_count")
        if items_key is not None and isinstance(total, int) and total > len(items):
            complete = False
            meta["truncated"] = True
        return items, complete, meta


def classify_error(resp: Response) -> ApiError:
    msg = ""
    if isinstance(resp.body, dict):
        msg = str(resp.body.get("message", ""))
    remaining = resp.headers.get("x-ratelimit-remaining")
    if resp.status == 429 or (resp.status == 403 and (remaining == "0" or "rate limit" in msg.lower())):
        return ApiError("RATE_LIMITED", msg or "rate limited", resp.status)
    if resp.status == 403:
        return ApiError("PERMISSION_DENIED", msg or "forbidden", resp.status)
    if resp.status == 401:
        return ApiError("PERMISSION_DENIED", msg or "unauthorized", resp.status)
    if resp.status == 404:
        return ApiError("NOT_FOUND", msg or "not found", resp.status)
    if resp.status in (301, 302, 307, 308):
        return ApiError("UNFOLLOWED_REDIRECT", f"HTTP {resp.status}", resp.status)
    return ApiError("HTTP_ERROR", f"HTTP {resp.status} {msg}".strip(), resp.status)


def _next_link(link_header: str) -> str | None:
    for part in link_header.split(","):
        m = re.match(r'\s*<([^>]+)>\s*;\s*rel="next"', part)
        if m:
            return m.group(1)
    return None


# ---------------------------------------------------------------------------
# Badge normalization
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BadgeRef:
    handle: str
    stem: str
    style: str  # "wordmark" | "seal"
    repo_param: str | None
    url: str

    @property
    def key(self) -> tuple[str, str]:
        return (self.handle, self.stem)


def normalize_repo_name(name: str) -> str:
    return urllib.parse.unquote(name).strip().strip("/").lower()


def parse_badge_url(raw: str) -> BadgeRef | None:
    """Normalize one Gaia badge URL (case, encoding, query, Honesty/worker paths)."""
    url = html.unescape(raw).rstrip(".,;")
    parsed = urllib.parse.urlparse(url)
    segs = [urllib.parse.unquote(s) for s in parsed.path.split("/") if s]
    if not segs or segs[0].lower() != "badges":
        return None
    segs = segs[1:]
    if segs and segs[0].lower() == "_assets":
        segs = segs[1:]
    if len(segs) != 2 or not segs[1].lower().endswith(".svg"):
        return None
    handle = segs[0].lower()
    stem = segs[1][:-4].lower()
    style = "wordmark"
    if stem.endswith("-seal"):
        style = "seal"
        stem = stem[: -len("-seal")]
    qs = urllib.parse.parse_qs(parsed.query)
    repo_param = qs.get("repo", [None])[0]
    return BadgeRef(handle, stem, style, normalize_repo_name(repo_param) if repo_param else None,
                    f"https://gaiaskilltree.com{parsed.path}")


def extract_badges(text: str) -> tuple[list[BadgeRef], list[str]]:
    """All Gaia badge refs (Markdown + HTML + bare) and deep links found in text."""
    refs: list[BadgeRef] = []
    seen: set[tuple[str, str, str, str | None]] = set()
    for m in GAIA_URL_RE.finditer(html.unescape(text)):
        ref = parse_badge_url(m.group(0))
        if ref is None:
            continue
        k = (ref.handle, ref.stem, ref.style, ref.repo_param)
        if k not in seen:
            seen.add(k)
            refs.append(ref)
    links = sorted({urllib.parse.unquote(m.group(0)).rstrip(".,;").lower()
                    for m in DEEP_LINK_RE.finditer(html.unescape(text))})
    return refs, links


# ---------------------------------------------------------------------------
# Expected skills / coverage
# ---------------------------------------------------------------------------


def expected_skills_for_repo(registry: dict[str, Any], repo: str) -> list[dict[str, Any]]:
    """All eligible Named Skills mapped to this repo (every contributor, case-insensitive)."""
    key = normalize_repo_name(repo)
    out: dict[str, dict[str, Any]] = {}
    for handle, cinfo in registry.get("contributors", {}).items():
        by_id = {s["id"]: s for s in cinfo.get("namedSkills", [])}
        for r, ids in cinfo.get("skillsByRepo", {}).items():
            if normalize_repo_name(r) != key:
                continue
            for sid in ids:
                s = by_id.get(sid)
                if not s:
                    continue
                file = s.get("file", f"{sid.split('/')[-1]}.svg")
                out[sid] = {
                    "id": sid,
                    "name": s.get("name", sid),
                    "rank": s.get("rank", 0),
                    "handle": handle.lower(),
                    "stem": file[:-4].lower() if file.endswith(".svg") else file.lower(),
                }
    return sorted(out.values(), key=lambda s: (-int(s["rank"] or 0), s["id"]))


def compute_coverage(expected: list[dict[str, Any]], refs: list[BadgeRef]) -> dict[str, Any]:
    by_key = {(s["handle"], s["stem"]): s for s in expected}
    covered: dict[str, dict[str, Any]] = {}
    contributor_level: list[dict[str, str]] = []
    unmapped: list[dict[str, str]] = []
    for ref in refs:
        s = by_key.get(ref.key)
        if s:
            entry = covered.setdefault(s["id"], {"id": s["id"], "styles": [], "urls": []})
            if ref.style not in entry["styles"]:
                entry["styles"].append(ref.style)
            if ref.url not in entry["urls"]:
                entry["urls"].append(ref.url)
        elif ref.stem in CONTRIBUTOR_STEMS:
            contributor_level.append({"handle": ref.handle, "stem": ref.stem, "style": ref.style, "url": ref.url})
        else:
            unmapped.append({"handle": ref.handle, "stem": ref.stem, "style": ref.style, "url": ref.url})
    exp_ids = [s["id"] for s in expected]
    cov_ids = sorted(covered)
    hit = [i for i in exp_ids if i in covered]
    if not exp_ids:
        level = "unknown"
    elif len(hit) == len(exp_ids):
        level = "full"
    elif hit:
        level = "partial"
    else:
        level = "none"
    return {
        "level": level,
        "covered_skill_ids": cov_ids,
        "missing_skill_ids": [i for i in exp_ids if i not in covered],
        "details": [covered[i] for i in cov_ids],
        "contributor_level_badges": contributor_level,
        "unmapped_badges": unmapped,
    }


# ---------------------------------------------------------------------------
# Evidence gathering
# ---------------------------------------------------------------------------


def parse_pr_url(url: str | None) -> tuple[str, str, int] | None:
    if not url:
        return None
    m = PR_URL_RE.match(url.strip())
    if not m:
        return None
    return m.group(1), m.group(2), int(m.group(3))


def _added_lines(files: list[dict[str, Any]]) -> tuple[str, bool]:
    """Concatenate added patch lines; flag whether any file lacked a patch."""
    chunks: list[str] = []
    missing = False
    for f in files:
        patch = f.get("patch")
        if patch is None:
            doc_like = str(f.get("filename", "")).lower().endswith(DOC_SUFFIXES)
            if doc_like and f.get("status") not in ("removed",) and f.get("changes", 1) != 0:
                missing = True
            continue
        for line in patch.splitlines():
            if line.startswith("+") and not line.startswith("+++"):
                chunks.append(line[1:])
    return "\n".join(chunks), missing


def _is_weak_candidate(pr: dict[str, Any]) -> bool:
    """Generic 'badge' wording: enough to *inspect* the diff, never enough to claim attribution."""
    head_ref = ((pr.get("head") or {}).get("ref") or "").lower()
    return "badge" in head_ref or "badge" in (pr.get("title") or "").lower()


def _is_marker_pr(pr: dict[str, Any], authors: tuple[str, ...]) -> bool:
    """Strong Gaia attribution markers (branch, text, or campaign author)."""
    head_ref = ((pr.get("head") or {}).get("ref") or "").lower()
    title = (pr.get("title") or "").lower()
    body = (pr.get("body") or "").lower()
    user = ((pr.get("user") or {}).get("login") or "").lower()
    return (
        head_ref.startswith("gaia/badge")
        or bool(GAIA_HOST_RE.search(body))
        or "gaia skill tree" in title
        or "gaia skill tree" in body
        or user in {a.lower() for a in authors}
    )


def inspect_pr(client: GitHubClient, owner: str, repo: str, number: int,
               payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Fetch exact PR status plus patch contents (never rely on the title)."""
    base = f"/repos/{owner}/{repo}/pulls/{number}"
    pr = payload if payload is not None else client.get_ok(base).body
    if not isinstance(pr, dict):
        raise ApiError("BAD_RESPONSE", f"PR {number} payload not an object")
    files, complete, _meta = client.paginate(f"{base}/files")
    added, patch_missing = _added_lines(files)
    refs, links = extract_badges(added)
    state = "open" if pr.get("state") == "open" else ("merged" if pr.get("merged") or pr.get("merged_at") else "closed_unmerged")
    return {
        "number": number,
        "url": pr.get("html_url") or f"https://github.com/{owner}/{repo}/pull/{number}",
        "state": state,
        "merged": state == "merged",
        "merged_at": pr.get("merged_at"),
        "title": pr.get("title"),
        "author": (pr.get("user") or {}).get("login"),
        "head": {"ref": (pr.get("head") or {}).get("ref"), "sha": (pr.get("head") or {}).get("sha"),
                 "repo": ((pr.get("head") or {}).get("repo") or {}).get("full_name")},
        "base": {"ref": (pr.get("base") or {}).get("ref"), "sha": (pr.get("base") or {}).get("sha")},
        "files": [f.get("filename") for f in files],
        "files_complete": complete,
        "patch_unavailable": patch_missing or not complete,
        "badges": [{"handle": r.handle, "stem": r.stem, "style": r.style, "url": r.url} for r in refs],
        "badge_refs": refs,
        "deep_links": links,
        "_raw": pr,
    }


@dataclass
class Evidence:
    """Everything observed for one repo. ``complete`` is the AND of all components."""

    identity: dict[str, Any] = field(default_factory=dict)
    prs: list[dict[str, Any]] = field(default_factory=list)
    ignored_prs: list[int] = field(default_factory=list)
    open_scan: dict[str, Any] = field(default_factory=dict)
    readme: dict[str, Any] = field(default_factory=dict)
    other_files: dict[str, Any] = field(default_factory=dict)
    readme_text: str | None = None  # decoded README (policy signals); never serialized into receipts
    components: dict[str, dict[str, Any]] = field(default_factory=dict)
    errors: list[dict[str, str]] = field(default_factory=list)

    def fail(self, component: str, err: ApiError) -> None:
        self.components[component] = {"complete": False, "error_code": err.code, "detail": str(err)}
        self.errors.append({"component": component, "code": err.code, "detail": str(err)})

    def ok(self, component: str, **extra: Any) -> None:
        self.components[component] = {"complete": True, "error_code": None, **extra}

    @property
    def complete(self) -> bool:
        required = ("identity", "pull_requests", "readme", "other_files")
        return all(self.components.get(c, {}).get("complete") for c in required)


def resolve_identity(client: GitHubClient, requested: str, ev: Evidence) -> str | None:
    """Resolve canonical owner/name, GitHub id, default branch. Returns canonical full name."""
    try:
        body = client.get_ok(f"/repos/{requested}").body
    except ApiError as e:
        ev.fail("identity", e)
        return None
    if not isinstance(body, dict) or not body.get("id") or not body.get("full_name"):
        ev.fail("identity", ApiError("BAD_RESPONSE", "repository payload missing id/full_name"))
        return None
    canonical = body["full_name"]
    aliases = sorted({requested, canonical} - {canonical}) if requested != canonical else []
    renamed = normalize_repo_name(requested) != normalize_repo_name(canonical)
    ev.identity = {
        "requested": requested,
        "canonical": canonical,
        "github_id": body["id"],
        "default_branch": body.get("default_branch"),
        "archived": bool(body.get("archived")),
        "disabled": bool(body.get("disabled")),
        "has_issues": body.get("has_issues"),
        "has_discussions": body.get("has_discussions"),
        "html_url": body.get("html_url") or f"https://github.com/{canonical}",
        "aliases": aliases,
        "renamed": renamed,
        "case_normalized": (not renamed) and requested != canonical,
    }
    if not body.get("default_branch"):
        ev.fail("identity", ApiError("BAD_RESPONSE", "no default branch"))
        return None
    ev.ok("identity")
    return canonical


def gather_prs(client: GitHubClient, canonical: str, ledger_pr_url: str | None,
               history_urls: list[str], authors: tuple[str, ...], ev: Evidence,
               open_scan_limit: int = MAX_OPEN_SCAN) -> None:
    """Combine ledger-recorded PRs, the live open-PR list, and search for unledgered PRs."""
    owner, repo = canonical.split("/", 1)
    targets: dict[int, tuple[str, str]] = {}  # number -> (owner, repo) to fetch from
    matched: dict[int, set[str]] = {}
    complete = True
    try:
        for url in [ledger_pr_url, *history_urls]:
            parsed = parse_pr_url(url)
            if parsed:
                o, r, n = parsed
                targets[n] = (o, r)
                matched.setdefault(n, set()).add("ledger")
            elif url:
                raise ApiError("BAD_LEDGER_URL", f"unparseable ledger PR URL: {url}")

        # Authoritative (non-index) view of all open PRs.
        open_prs, open_complete, _ = client.paginate(f"/repos/{owner}/{repo}/pulls?state=open")
        complete &= open_complete
        unmarked: list[dict[str, Any]] = []
        for pr in open_prs:
            if _is_marker_pr(pr, authors) or _is_weak_candidate(pr):
                n = pr["number"]
                targets.setdefault(n, (owner, repo))
                matched.setdefault(n, set()).add("open_list")
            else:
                unmarked.append(pr)
        # Unmarked open PRs may still carry a Gaia badge (odd title/branch/author): inspect the
        # diff of up to `open_scan_limit` of them rather than trusting metadata.
        scan_pool = [pr for pr in unmarked if pr["number"] not in targets][:open_scan_limit]
        open_payloads = {pr["number"]: pr for pr in scan_pool}
        scan_incomplete = (len(unmarked) > open_scan_limit) or not open_complete
        for n in open_payloads:
            targets.setdefault(n, (owner, repo))
            matched.setdefault(n, set()).add("open_scan")

        # Index-based search for merged / closed / unledgered PRs.
        queries = ["gaiaskilltree.com", '"Gaia Skill Tree" in:title,body']
        queries += [f"author:{a}" for a in authors]
        for q in queries:
            enc = urllib.parse.quote(f"repo:{canonical} is:pr {q}", safe=":/")
            items, ok, _ = client.paginate(f"/search/issues?q={enc}", items_key="items")
            complete &= ok
            for it in items:
                n = it["number"]
                targets.setdefault(n, (owner, repo))
                matched.setdefault(n, set()).add("search")

        def _inspect(n: int) -> dict[str, Any]:
            o, r = targets[n]
            return inspect_pr(client, o, r, n, open_payloads.get(n) if matched[n] == {"open_scan"} else None)

        order = sorted(targets)
        with concurrent.futures.ThreadPoolExecutor(max_workers=INSPECT_WORKERS) as pool:
            inspected = list(pool.map(_inspect, order))  # first ApiError propagates (fail closed)
        for n, info in zip(order, inspected):
            info["matched_by"] = sorted(matched[n])
            raw = info.pop("_raw")
            marker = _is_marker_pr(raw, authors)
            info["ledgered"] = "ledger" in matched[n]
            info["has_gaia_badge"] = bool(info["badge_refs"])
            info["marker_only"] = (not info["has_gaia_badge"]) and marker and not info["ledgered"]
            if matched[n] == {"open_scan"} and not info["has_gaia_badge"]:
                # Unmarked PR sampled only by the open scan: a clean diff is unrelated; an
                # uninspectable one makes the scan (not the PR list) incomplete.
                if info["patch_unavailable"]:
                    scan_incomplete = True
                else:
                    ev.ignored_prs.append(n)
                continue
            if (not info["has_gaia_badge"] and not info["ledgered"] and not marker
                    and not info["patch_unavailable"]):
                # Weak candidate whose full diff is clean: unrelated badge PR.
                ev.ignored_prs.append(n)
                continue
            if not info["files_complete"]:
                complete = False
            ev.prs.append(info)
    except ApiError as e:
        ev.fail("pull_requests", e)
        return
    ev.open_scan = {"complete": not scan_incomplete, "open_total": len(open_prs),
                    "unmarked_total": len(unmarked), "unmarked_inspected": len(scan_pool),
                    "limit": open_scan_limit}
    if complete:
        ev.ok("pull_requests", searched=queries, inspected=len(ev.prs))
    else:
        ev.fail("pull_requests", ApiError("INCOMPLETE", "PR listing/search truncated or flagged incomplete"))


def gather_readme(client: GitHubClient, canonical: str, branch: str, ev: Evidence) -> None:
    try:
        b = client.get_ok(f"/repos/{canonical}/branches/{urllib.parse.quote(branch, safe='')}").body
        commit_sha = ((b or {}).get("commit") or {}).get("sha")
    except ApiError as e:
        ev.fail("readme", e)
        return
    if not commit_sha:
        ev.fail("readme", ApiError("BAD_RESPONSE", "branch payload missing commit sha"))
        return
    try:
        body = client.get_ok(f"/repos/{canonical}/readme?ref={commit_sha}").body
    except ApiError as e:
        if e.code == "NOT_FOUND":
            ev.readme = {"present": False, "commit_sha": commit_sha, "branch": branch}
            ev.ok("readme", present=False)
            return
        ev.fail("readme", e)
        return
    if not isinstance(body, dict) or body.get("encoding") != "base64" or body.get("content") is None:
        ev.fail("readme", ApiError("INCOMPLETE", "README content unavailable (too large or unsupported encoding)"))
        return
    try:
        text = base64.b64decode(body["content"]).decode("utf-8", "replace")
    except ValueError:
        ev.fail("readme", ApiError("BAD_RESPONSE", "README base64 decode failed"))
        return
    refs, links = extract_badges(text)
    snippets = [ln.strip()[:240] for ln in text.splitlines() if GAIA_URL_RE.search(html.unescape(ln))]
    ev.readme_text = text
    ev.readme = {
        "present": True,
        "path": body.get("path"),
        "html_url": body.get("html_url"),
        "blob_sha": body.get("sha"),
        "commit_sha": commit_sha,
        "branch": branch,
        "badge_refs": refs,
        "badges": [{"handle": r.handle, "stem": r.stem, "style": r.style, "repo_param": r.repo_param,
                    "url": r.url} for r in refs],
        "deep_links": links,
        "snippets": snippets[:6],
    }
    ev.ok("readme", present=True)


def gather_other_files(client: GitHubClient, canonical: str, readme_path: str | None, ev: Evidence) -> None:
    """Detect a Gaia badge in non-README files (reported separately from adoption)."""
    enc = urllib.parse.quote(f"gaiaskilltree.com/badges repo:{canonical}", safe=":/")
    try:
        items, ok, _ = client.paginate(f"/search/code?q={enc}", items_key="items")
    except ApiError as e:
        ev.fail("other_files", e)
        return
    if not ok:
        ev.fail("other_files", ApiError("INCOMPLETE", "code search truncated or flagged incomplete"))
        return
    paths = sorted({it.get("path") for it in items if it.get("path") and it.get("path") != readme_path})
    ev.other_files = {"paths": paths}
    ev.ok("other_files", paths=paths)


def collect_evidence(client: GitHubClient, requested_repo: str, record: dict[str, Any],
                     authors: tuple[str, ...], open_scan_limit: int = MAX_OPEN_SCAN) -> Evidence:
    ev = Evidence()
    canonical = resolve_identity(client, requested_repo, ev)
    prov = record.get("provisioning", {})
    hist_urls = sorted({h.get("pr_url") for h in prov.get("history", []) if h.get("pr_url")} - {prov.get("pr_url")})
    if canonical is None:
        for c in ("pull_requests", "readme", "other_files"):
            ev.components[c] = {"complete": False, "error_code": "SKIPPED", "detail": "identity unresolved"}
        return ev
    gather_prs(client, canonical, prov.get("pr_url"), hist_urls, authors, ev, open_scan_limit)
    gather_readme(client, canonical, ev.identity["default_branch"], ev)
    gather_other_files(client, canonical, ev.readme.get("path"), ev)
    return ev


# ---------------------------------------------------------------------------
# Policy evidence gathering (Issue #2074): scoped, budgeted, read-only
# ---------------------------------------------------------------------------

DEFAULT_POLICY_LEDGER = Path(__file__).resolve().parent.parent / "campaigns" / "badge-provisioning" / "policy-ledger.jsonl"


@dataclass(frozen=True)
class PolicyConfig:
    """Cost guard for the per-repo contribution-channel scan.

    Worst case per repo is roughly: <=5 directory listings + ``max_files`` file reads + <=2 searches per
    searched name (``max_search_names``) + ``max_comment_fetches`` comment reads, all inside ``call_budget``.
    Exceeding any cap makes the repo ``UNKNOWN`` and is flagged; it never widens the scan.
    """

    call_budget: int = 36
    max_files: int = 12
    max_comment_fetches: int = 6
    max_search_names: int = 3
    max_pages: int = 2
    events: tuple = ()
    scan: bool = True  # False: do not call GitHub for policy; still overlay the offline policy ledger


def load_policy_events(path: Path = DEFAULT_POLICY_LEDGER) -> tuple[dict[str, Any], ...]:
    """Policy ledger events, fail-closed: a corrupt or tampered chain raises ``bp.LedgerError``."""
    events = bp.read_events(path)
    problems = bp.verify_chain(events)
    if problems:
        raise bp.LedgerError("policy ledger chain broken: " + "; ".join(problems))
    return tuple(events)


def _fetch_text(client: GitHubClient, canonical: str, path: str, ref: str) -> tuple[str, str]:
    url = f"/repos/{canonical}/contents/{urllib.parse.quote(path)}?ref={urllib.parse.quote(ref, safe='')}"
    body = client.get_ok(url).body
    if not isinstance(body, dict) or body.get("encoding") != "base64" or body.get("content") is None:
        raise ApiError("INCOMPLETE", f"{path} content unavailable (too large or unsupported encoding)")
    try:
        text = base64.b64decode(body["content"]).decode("utf-8", "replace")
    except ValueError as e:
        raise ApiError("BAD_RESPONSE", f"{path} base64 decode failed") from e
    return text, body.get("html_url") or f"https://github.com/{canonical}/blob/{ref}/{path}"


def _authority_of(comment: dict[str, Any], authors: tuple[str, ...]) -> str:
    user = comment.get("user") or {}
    login = (user.get("login") or "").lower()
    if login in {a.lower() for a in authors}:
        return "campaign"
    if user.get("type") == "Bot" or login.endswith("[bot]"):
        return "policy_bot"
    if comment.get("author_association") in bp.AUTHORITY_ASSOCIATIONS:
        return "maintainer"
    return "contributor"


def gather_policy_raw(client: GitHubClient, canonical: str, ev: Evidence, requested: str, record: dict[str, Any],
                      authors: tuple[str, ...], cfg: PolicyConfig, observed_at: str,
                      state: dict[str, Any]) -> dict[str, Any]:
    """Read-only, budgeted scan of one repository's contribution-channel signals.

    Never raises for upstream conditions: every failure becomes an ``incomplete_reasons`` entry, which
    the decision turns into ``UNKNOWN``.
    """
    ident = ev.identity
    ref = ev.readme.get("commit_sha") or ident.get("default_branch") or "HEAD"
    raw: dict[str, Any] = {"scanned": True, "signals": [], "issue_channel_inputs": None,
                           "files": {"present": [], "absent": [], "skipped": []},
                           "prior_items": [], "comments": {}, "incomplete_reasons": [], "notes": []}
    counts = {"listings": 0, "files_fetched": 0, "searches": 0, "comment_fetches": 0}

    def note(reason: str) -> None:
        if reason not in raw["incomplete_reasons"]:
            raw["incomplete_reasons"].append(reason)

    def listing(path: str) -> list[dict[str, Any]]:
        counts["listings"] += 1
        q = f"?ref={urllib.parse.quote(ref, safe='')}"
        body = client.get_ok(f"/repos/{canonical}/contents{('/' + urllib.parse.quote(path)) if path else ''}{q}").body
        if not isinstance(body, list):
            raise ApiError("BAD_RESPONSE", f"{path or '/'} listing is not a directory")
        return body

    def listing_or_none(path: str) -> list[dict[str, Any]] | None:
        try:
            return listing(path)
        except ApiError as e:
            if e.code == "NOT_FOUND":
                return None
            note(f"policy_listing:{path}:{e.code}")
            return None

    with client.budget(cfg.call_budget) as spent:
        # --- README (already fetched by the reconciler; zero extra calls) --------------------------
        if ev.readme_text is not None:
            raw["files"]["present"].append(ev.readme.get("path") or "README")
            raw["signals"] += bp.extract_signals("readme", ev.readme_text, ev.readme.get("html_url"),
                                                 ev.readme.get("path"), observed_at)
        elif ev.readme.get("present") is False:
            raw["files"]["absent"].append("README")
        else:
            note("readme_unavailable")

        # --- directory listings -> candidate policy files -------------------------------------------
        try:
            root = listing("")
        except ApiError as e:
            note(f"policy_listing:/:{e.code}")
            root = None
        if root is not None:
            rmap = {e["name"].lower(): e for e in root}
            gh: list[dict[str, Any]] = []
            if rmap.get(".github", {}).get("type") == "dir":
                gh = listing_or_none(".github") or []
            gmap = {e["name"].lower(): e for e in gh}

            def pick(name: str) -> tuple[str, list[dict[str, Any]]] | None:
                for base, m, prefix in ((".github", gmap, ".github/"), ("", rmap, "")):
                    e = m.get(name.lower())
                    if e and e.get("type") == "dir":
                        entries = listing_or_none(prefix + e["name"])
                        if entries is not None:
                            return prefix + e["name"], entries
                return None

            issue_dir, pr_dir = pick("ISSUE_TEMPLATE"), pick("PULL_REQUEST_TEMPLATE")
            wf = None
            if gmap.get("workflows", {}).get("type") == "dir":
                entries = listing_or_none(".github/workflows")
                wf = (".github/workflows", entries) if entries is not None else None
            cands, absent = bp.select_policy_files(root, gh, issue_dir, pr_dir, wf)
            raw["files"]["absent"] += absent
            chosen, skipped = cands[:cfg.max_files], cands[cfg.max_files:]
            if skipped:
                raw["files"]["skipped"] = [c["path"] for c in skipped]
                note(f"policy_file_budget_exceeded:{len(skipped)}_skipped")
            config_text: str | None = None
            templates: list[tuple[str, str]] = []
            for c in chosen:
                try:
                    text, url = _fetch_text(client, canonical, c["path"], ref)
                except ApiError as e:
                    if e.code == "NOT_FOUND":
                        raw["files"]["absent"].append(c["path"])
                    else:
                        note(f"policy_file:{c['path']}:{e.code}")
                    continue
                counts["files_fetched"] += 1
                raw["files"]["present"].append(c["path"])
                kind = c["kind"]
                if kind == "issue_config":
                    config_text = text
                elif kind == "issue_template":
                    templates.append((c["path"], text))
                sigs = bp.extract_signals(kind, text, url, c["path"], observed_at,
                                          authority="policy_workflow" if kind == "workflow" else "repository_file")
                if kind == "workflow" and not any(s["effect"] in ("ISSUE_FIRST", "NO_OUTREACH") for s in sigs):
                    sigs.append(bp.workflow_name_only_signal(c["path"], url, observed_at))
                raw["signals"] += sigs
            raw["issue_channel_inputs"] = {
                "issues_enabled": ident.get("has_issues"), "config_text": config_text,
                "templates": templates, "discussions_enabled": ident.get("has_discussions")}

        # --- prior outreach across channels (PRs + issues, aliases, renames) --------------------------
        names: list[str] = []
        for n in (canonical, requested, record.get("repository"), *sorted(bp.repo_keys([canonical], KNOWN_MIGRATIONS))):
            if n and bp.normalize_repo_name(n) not in {bp.normalize_repo_name(x) for x in names}:
                names.append(n)
        for i, name in enumerate(names[:cfg.max_search_names]):
            queries = [f'repo:{name} (gaiaskilltree.com OR "Gaia Skill Tree")'] + [f"repo:{name} author:{a}" for a in authors[:1]]
            for q in queries:
                counts["searches"] += 1
                enc = urllib.parse.quote(q, safe=":/")
                try:
                    items, ok, _ = client.paginate(f"/search/issues?q={enc}", items_key="items", max_pages=cfg.max_pages)
                except ApiError as e:
                    if i > 0 and e.status in (404, 422):  # an old alias GitHub can no longer search is not a gap
                        raw["notes"].append(f"alias_search_skipped:{name}:{e.code}")
                    else:
                        note(f"prior_search:{e.code}")
                    continue
                if not ok:
                    note("prior_search_incomplete")
                raw["prior_items"] += items
        if len(names) > cfg.max_search_names:
            note("prior_search_alias_budget_exceeded")

        # --- comments: maintainer/bot replies, closure explanations, approval evidence ----------------
        keys = bp.repo_keys([canonical, requested, *names], KNOWN_MIGRATIONS)
        issues, search_prs = bp.normalize_prior_items(raw["prior_items"], authors, keys)
        targets: list[tuple[str, str, int, str]] = []  # (kind, url, number, state)
        for e in state["active_approvals"]:
            m = bp.ISSUE_URL_RE.match(e["data"]["issue_url"])
            if m:
                targets.append(("issue", e["data"]["issue_url"], int(m.group(3)), "approval"))
        targets += [("issue", i["url"], i["number"], i["state"]) for i in issues if i["gaia_authored"]]
        gaia_prs = [p for p in ev.prs if p["state"] != "open" and (p["ledgered"] or p["has_gaia_badge"])]
        targets += [("pr", p["url"], p["number"], p["state"]) for p in gaia_prs]
        targets += [("pr", p["url"], p["number"], p["state"]) for p in search_prs
                    if p["gaia_authored"] and p["state"] != "open"]
        seen_t: set[str] = set()
        uniq: list[tuple[str, str, int, str]] = []
        for t in targets:
            if bp._norm_url(t[1]) not in seen_t:
                seen_t.add(bp._norm_url(t[1]))
                uniq.append(t)
        if len(uniq) > cfg.max_comment_fetches:
            note(f"comment_fetch_budget_exceeded:{len(uniq) - cfg.max_comment_fetches}_unread")
        for kind, url, number, st in uniq[:cfg.max_comment_fetches]:
            m = re.match(r"https?://github\.com/([^/]+)/([^/]+)/", url)
            if not m:
                note("comment_target_unparseable")
                continue
            counts["comment_fetches"] += 1
            try:
                comments, ok, _ = client.paginate(f"/repos/{m.group(1)}/{m.group(2)}/issues/{number}/comments",
                                                  max_pages=cfg.max_pages)
            except ApiError as e:
                raw["comments"][bp._norm_url(url)] = None
                note(f"comments:{e.code}")
                continue
            if not ok:
                raw["comments"][bp._norm_url(url)] = None
                note("comments_incomplete")
                continue
            raw["comments"][bp._norm_url(url)] = comments
            explained = False
            for c in comments:
                authority = _authority_of(c, authors)
                if authority in ("campaign", "contributor"):
                    continue
                sigs = bp.extract_signals("comment", c.get("body") or "", c.get("html_url") or url, None, observed_at,
                                          authority=authority, comment_author_ok=(authority == "maintainer"))
                explained |= any(s["effect"] in ("ISSUE_FIRST", "NO_OUTREACH") for s in sigs)
                raw["signals"] += sigs
            if kind == "pr" and st == "closed_unmerged" and not explained:
                raw["signals"].append(bp.unexplained_closure_signal(url, None, observed_at))
        for i in issues:
            if i["gaia_authored"] and i["state"] == "closed" and i.get("state_reason") == "not_planned":
                raw["signals"].append(bp.issue_not_planned_signal(i["url"], i.get("closed_at"), observed_at))
        if spent["exhausted"]:
            note("policy_call_budget_exhausted")
        raw["cost"] = {"api_calls": spent["used"], "budget": cfg.call_budget, "budget_exhausted": spent["exhausted"],
                       **counts}
    return raw


# ---------------------------------------------------------------------------
# Decision engine
# ---------------------------------------------------------------------------


def classify(record: dict[str, Any], expected: list[dict[str, Any]], ev: Evidence,
             coverage: dict[str, Any] | None) -> dict[str, Any]:
    """Pure function: ledger record + evidence -> observed state, action, anomalies."""
    prov = record.get("provisioning", {})
    ledger_status = record.get("status")
    restriction = ledger_status if ledger_status in TERMINAL_RESTRICTIONS else (
        prov.get("outcome") if prov.get("outcome") in TERMINAL_RESTRICTIONS else None)
    anomalies: list[dict[str, str]] = []
    reasons: list[str] = []

    def anomaly(code: str, severity: str, detail: str) -> None:
        anomalies.append({"code": code, "severity": severity, "detail": detail})

    contacted = (
        ledger_status in CONTACTED_STATUSES
        or bool(prov.get("pr_url"))
        or int(prov.get("attempts") or 0) > 0
        or any(h.get("to_status") in CONTACTED_STATUSES for h in prov.get("history", []))
    )

    hold = None
    for name in (record.get("repository"), ev.identity.get("requested"), ev.identity.get("canonical")):
        if name and normalize_repo_name(name) in CAMPAIGN_HOLDS:
            hold = CAMPAIGN_HOLDS[normalize_repo_name(name)]

    def finish(state: str, action: str) -> dict[str, Any]:
        if hold and action in ("REQUEST_HUMAN_APPROVAL", "RETRY_RECONCILE_NO_DISPATCH"):
            action = f"HELD_UNDER_{hold.lstrip('#')}_DO_NOT_REQUEST_APPROVAL"
        if restriction:
            action = "NO_OUTREACH_TERMINAL_RESTRICTION"
        return {
            "hold": hold,
            "observed_state": state,
            "recommended_action": action,
            "terminal_restriction": restriction,
            "ledger_status": ledger_status,
            "reasons": reasons,
            "anomalies": anomalies,
        }

    for e in ev.errors:
        anomaly(f"api_{e['code'].lower()}", "high", f"{e['component']}: {e['detail']}")

    if not ev.complete:
        reasons.append("Upstream evidence incomplete; failing closed.")
        return finish("UNKNOWN", "RETRY_RECONCILE_NO_DISPATCH")

    ident = ev.identity
    if ident.get("renamed"):
        anomaly("repo_renamed", "info", f"{ident['requested']} redirects to {ident['canonical']}")
    elif ident.get("case_normalized"):
        anomaly("repo_case_normalized", "info", f"{ident['requested']} -> {ident['canonical']}")
    declared = (record.get("preflight") or {}).get("default_branch")
    if declared and declared != "UNKNOWN" and declared != ident.get("default_branch"):
        anomaly("default_branch_changed", "medium",
                f"ledger default_branch={declared} upstream={ident.get('default_branch')}")
    if ident.get("archived") or ident.get("disabled"):
        anomaly("repo_archived", "high", "Repository is archived or disabled.")

    # Only PRs proven relevant (ledgered, or diff contains a Gaia badge) count as PR_OPEN;
    # unproven marker-only / uninspectable candidates are routed to NEEDS_REVIEW below.
    relevant = [p for p in ev.prs if p["ledgered"] or p["has_gaia_badge"]]
    open_prs = [p for p in relevant if p["state"] == "open"]
    merged_prs = [p for p in relevant if p["state"] == "merged"]
    closed_prs = [p for p in relevant if p["state"] == "closed_unmerged"]
    for p in ev.prs:
        if not p["ledgered"] and p["has_gaia_badge"]:
            anomaly("unledgered_pr", "medium", f"PR #{p['number']} ({p['state']}) carries a Gaia badge but is not in the ledger")
        if p["has_gaia_badge"] is False and p["ledgered"]:
            anomaly("ledgered_pr_without_badge", "medium", f"Ledger PR #{p['number']} no longer contains a Gaia badge diff")
        if p["patch_unavailable"] and not p["has_gaia_badge"]:
            anomaly("patch_unavailable", "medium", f"PR #{p['number']} patch could not be fully inspected")
    ambiguous = [p for p in ev.prs if p["marker_only"] or (p["patch_unavailable"] and not p["has_gaia_badge"])]
    if len(open_prs) > 1:
        anomaly("duplicate_open_prs", "high", "Multiple open Gaia PRs: " + ", ".join(f"#{p['number']}" for p in open_prs))

    readme = ev.readme
    cov = coverage or {"level": "unknown", "covered_skill_ids": [], "contributor_level_badges": [],
                       "unmapped_badges": []}
    if readme.get("present") is False:
        anomaly("readme_missing", "medium", "Default branch has no README.")
    if cov["contributor_level_badges"]:
        anomaly("contributor_level_badge_only" if cov["level"] == "none" else "contributor_level_badge",
                "medium", "Contributor-level badge present; does not prove Named Skill coverage.")
    if cov["unmapped_badges"]:
        anomaly("unmapped_gaia_badge", "medium", "Gaia badge URL does not map to an eligible Named Skill.")
    other = ev.other_files.get("paths", [])
    if other:
        anomaly("badge_in_other_file", "medium", "Gaia badge URL found outside README: " + ", ".join(other))
    for b in readme.get("badges", []):
        rp = b.get("repo_param")
        if rp and rp != normalize_repo_name(ident["canonical"]):
            anomaly("badge_repo_param_mismatch", "low", f"badge ?repo={rp} differs from {ident['canonical']}")

    # Ledger vs upstream discrepancies (observational only).
    if ledger_status == "PR_OPEN" and not open_prs:
        anomaly("ledger_pr_open_but_not_open_upstream", "high", "Ledger says PR_OPEN but no open Gaia PR upstream.")
    if ledger_status in ("ADOPTED", "ALREADY_ADOPTED") and cov["level"] != "full":
        anomaly("ledger_adopted_but_badge_missing", "high", "Ledger says adopted but README coverage is not full.")
    readme_keys = {r.key for r in readme.get("badge_refs", [])}
    for p in merged_prs:
        if not ({r.key for r in p["badge_refs"]} & readme_keys):
            anomaly("merged_without_badge", "high",
                    f"PR #{p['number']} merged but its badge is not on the current default-branch README.")

    if ev.open_scan and not ev.open_scan.get("complete"):
        anomaly("open_pr_scan_incomplete", "medium",
                f"Inspected {ev.open_scan.get('unmarked_inspected')} of {ev.open_scan.get('unmarked_total')} "
                "unmarked open PRs; an unmarked Gaia badge PR cannot be ruled out.")

    has_campaign_pr = any(p["ledgered"] for p in ev.prs) or bool(prov.get("pr_url"))

    # --- precedence -------------------------------------------------------
    if cov["level"] == "full":
        if has_campaign_pr or contacted:
            reasons.append("All eligible skills present on default-branch README; campaign provenance recorded.")
            return finish("ADOPTED", "RECORD_ADOPTED_VIA_APPLY_AFTER_LEAD_REVIEW")
        reasons.append("All eligible skills present on default-branch README with no campaign PR.")
        return finish("ALREADY_ADOPTED", "RECORD_ALREADY_ADOPTED_AFTER_LEAD_REVIEW")
    if open_prs:
        reasons.append("Relevant outbound PR is open: " + ", ".join(f"#{p['number']}" for p in open_prs))
        return finish("PR_OPEN", "DO_NOT_DISPATCH_WAIT_FOR_MAINTAINER")
    if cov["level"] == "partial":
        reasons.append(f"Partial coverage: missing {cov.get('missing_skill_ids')}")
        return finish("PARTIAL_COVERAGE", "EXPLICIT_REVIEW_REQUIRED_NO_AUTO_OUTREACH")
    if merged_prs:
        reasons.append("Merged Gaia PR exists but current README lacks the badge (reverted, moved or edited).")
        return finish("NEEDS_REVIEW", "EXPLICIT_REVIEW_REQUIRED_NO_AUTO_OUTREACH")
    if cov["contributor_level_badges"] or cov["unmapped_badges"] or other:
        reasons.append("Gaia badge presence that does not prove Named Skill coverage.")
        return finish("NEEDS_REVIEW", "EXPLICIT_REVIEW_REQUIRED_NO_AUTO_OUTREACH")
    if ambiguous:
        reasons.append("Candidate PRs with ambiguous attribution or uninspectable patches.")
        return finish("NEEDS_REVIEW", "EXPLICIT_REVIEW_REQUIRED_NO_AUTO_OUTREACH")
    if closed_prs:
        reasons.append("Gaia PR closed without merge: " + ", ".join(f"#{p['number']}" for p in closed_prs))
        return finish("CLOSED_UNMERGED", "EXPLICIT_REVIEW_REQUIRED_NO_AUTO_OUTREACH")
    if readme.get("present") is False or ident.get("archived") or ident.get("disabled"):
        reasons.append("Repository cannot receive a README badge as-is.")
        return finish("NEEDS_REVIEW", "EXPLICIT_REVIEW_REQUIRED_NO_AUTO_OUTREACH")
    if contacted:
        reasons.append("Ledger records prior outreach but upstream shows no PR or badge.")
        anomaly("ledger_contacted_but_no_upstream_trace", "high", "Prior outreach not visible upstream.")
        return finish("NEEDS_REVIEW", "EXPLICIT_REVIEW_REQUIRED_NO_AUTO_OUTREACH")
    if record.get("eligibility") not in ("READY", "PILOT_CANDIDATE") or not record.get("canonical_skill"):
        reasons.append(f"Ledger eligibility {record.get('eligibility')} is not dispatchable.")
        return finish("NEEDS_REVIEW", "EXPLICIT_REVIEW_REQUIRED_NO_AUTO_OUTREACH")
    if ev.open_scan and not ev.open_scan.get("complete"):
        reasons.append(
            f"Open-PR scan incomplete ({ev.open_scan.get('unmarked_inspected')} of "
            f"{ev.open_scan.get('unmarked_total')} unmarked open PRs inspected, limit {ev.open_scan.get('limit')}); "
            "an unmarked PR with a Gaia badge cannot be ruled out. Failing closed.")
        return finish("UNKNOWN", "RETRY_RECONCILE_NO_DISPATCH")
    reasons.append("No PR, no badge, complete upstream evidence, no prior outreach.")
    return finish("READY_TO_APPROVE", "REQUEST_HUMAN_APPROVAL")


def policy_anomalies(pol: dict[str, Any]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    comp = pol["completeness"]
    if not pol["scanned"]:
        out.append({"code": "policy_not_scanned", "severity": "info",
                    "detail": "Contribution-channel policy not scanned for this repo (scope guard); channel is UNKNOWN."})
        return out
    if not comp["complete"]:
        out.append({"code": "policy_scan_incomplete", "severity": "medium",
                    "detail": "Policy evidence incomplete, channel fails closed to UNKNOWN: " + ", ".join(comp["incomplete_reasons"])})
    if pol["cost"].get("budget_exhausted"):
        out.append({"code": "policy_budget_exhausted", "severity": "medium",
                    "detail": f"Per-repo call budget of {pol['cost'].get('budget')} was exhausted."})
    approved_url = (pol["approval"].get("record") or {}).get("issue_url") if pol["approval"]["state"] == "VERIFIED" else None
    for i in pol["prior_issues"]:
        sev = "info" if approved_url and bp._norm_url(i["url"]) == bp._norm_url(approved_url) else "medium"
        out.append({"code": "prior_gaia_issue", "severity": sev,
                    "detail": f"Issue {i['url']} ({i['state']}) is part of this repo's single outreach attempt; no second issue or PR."})
    if pol["approval"]["state"] not in ("MISSING", "VERIFIED"):
        out.append({"code": "approval_unverified", "severity": "high",
                    "detail": f"Recorded maintainer approval is {pol['approval']['state']}: "
                              + ", ".join(pol["approval"].get("failed_checks", []))})
    if pol["channel"] == "ISSUE_FIRST":
        out.append({"code": "issue_first_required", "severity": "info",
                    "detail": "Repo requires an approved issue before an outside PR."})
    for c in pol["conflicts"]:
        out.append({"code": "policy_signal_conflict", "severity": "low", "detail": c})
    return out


def reconcile_repo(client: GitHubClient, requested: str, record: dict[str, Any],
                   registry: dict[str, Any], authors: tuple[str, ...] = DEFAULT_CAMPAIGN_AUTHORS,
                   now: Callable[[], datetime] = utcnow, open_scan_limit: int = MAX_OPEN_SCAN,
                   policy: PolicyConfig | None = None) -> dict[str, Any]:
    """Reconcile one repository; never raises for upstream conditions (fails closed).

    ``policy`` enables the contribution-channel scan (Issue #2074). Without it the repo's
    ``policy_channel`` is ``UNKNOWN`` (not scanned), which the dispatch gate treats as a hold.
    """
    expected = expected_skills_for_repo(registry, requested)
    try:
        ev = collect_evidence(client, requested, record, authors, open_scan_limit)
    except ApiError as e:  # defensive: a late failure must not escape as success
        ev = Evidence()
        ev.fail("identity", e)
        for c in ("pull_requests", "readme", "other_files"):
            ev.components.setdefault(c, {"complete": False, "error_code": "SKIPPED", "detail": str(e)})
    coverage = None
    if ev.complete and ev.readme.get("present"):
        coverage = compute_coverage(expected, ev.readme.get("badge_refs", []))
    elif ev.complete:
        coverage = compute_coverage(expected, [])
    decision = classify(record, expected, ev, coverage)
    prov = record.get("provisioning", {})
    aliases = sorted({a for a in [requested, *ev.identity.get("aliases", [])] if a != ev.identity.get("canonical")})
    observed_at = now().isoformat()
    canonical_name = ev.identity.get("canonical") or requested
    names = [canonical_name, requested, record.get("repository") or requested]
    pstate = bp.ledger_state(list(policy.events) if policy else [], names, KNOWN_MIGRATIONS)
    ledger_prs = [u for u in [prov.get("pr_url"), *[h.get("pr_url") for h in prov.get("history", [])]] if u]
    ledger_prs = list(dict.fromkeys(ledger_prs))
    if policy is None or not policy.scan:
        pol = bp.unscanned_policy(observed_at, pstate, names)
    else:
        if not ev.identity.get("canonical"):
            raw = {"scanned": True, "signals": [], "incomplete_reasons": ["identity_unresolved"],
                   "cost": {"api_calls": 0, "budget": policy.call_budget, "budget_exhausted": False}}
        else:
            try:
                raw = gather_policy_raw(client, canonical_name, ev, requested, record, authors, policy, observed_at, pstate)
            except Exception as e:  # fail closed on anything unexpected
                raw = {"scanned": True, "signals": [], "incomplete_reasons": [f"policy_scan_error:{type(e).__name__}"],
                       "cost": {"api_calls": 0, "budget": policy.call_budget, "budget_exhausted": False}}
        pol = bp.assemble_policy(
            raw, record=record, state=pstate, observed_at=observed_at, authors=authors,
            flags={"archived": ev.identity.get("archived"), "disabled": ev.identity.get("disabled"),
                   "html_url": ev.identity.get("html_url"), "observed_at": observed_at},
            terminal_restriction=decision["terminal_restriction"],
            upstream_prs=[{"url": p["url"], "state": p["state"]} for p in ev.prs],
            ledger_pr_urls=ledger_prs, names=names, migrations=KNOWN_MIGRATIONS,
            upstream_complete=ev.complete)
    decision["anomalies"] = [*decision["anomalies"], *policy_anomalies(pol)]
    if pol["scanned"] and decision["recommended_action"] == "REQUEST_HUMAN_APPROVAL":
        # Never put a repo in front of a human for approval while its contribution channel forbids or
        # has not cleared outreach, or while an earlier issue/PR stage already used the single attempt.
        if not pol["approval_required"]["satisfied"]:
            decision["recommended_action"] = f"HOLD_POLICY_CHANNEL_{pol['channel']}_DO_NOT_REQUEST_APPROVAL"
        elif pol["prior_issue_urls"] and not (pol["channel"] == "ISSUE_FIRST" and pol["approval"]["state"] == "VERIFIED"):
            decision["recommended_action"] = "HOLD_EXISTING_ISSUE_STAGE_DO_NOT_REQUEST_APPROVAL"
    return {
        "repository": ev.identity.get("canonical") or requested,
        "requested_name": requested,
        "github_id": ev.identity.get("github_id"),
        "default_branch": ev.identity.get("default_branch"),
        "aliases": aliases,
        "identity": {k: v for k, v in ev.identity.items() if k != "aliases"},
        "expected_skills": [{"id": s["id"], "name": s["name"], "rank": s["rank"]} for s in expected],
        "readme": {k: v for k, v in ev.readme.items() if k != "badge_refs"},
        "badges_found": ev.readme.get("badges", []),
        "coverage": coverage or {"level": "unknown", "covered_skill_ids": [], "missing_skill_ids": [s["id"] for s in expected]},
        "other_files": ev.other_files.get("paths", []),
        "pull_requests": [
            {k: v for k, v in p.items() if k not in ("badge_refs",)} for p in ev.prs
        ],
        "ignored_pr_numbers": sorted(ev.ignored_prs),
        "evidence": {
            "observed_at": observed_at,
            "complete": ev.complete,
            "components": ev.components,
            "readme_commit_sha": ev.readme.get("commit_sha"),
            "errors": ev.errors,
            "open_pr_scan": ev.open_scan,
        },
        "ledger": {
            "status": record.get("status"),
            "eligibility": record.get("eligibility"),
            "canonical_skill": record.get("canonical_skill"),
            "approved": prov.get("approved", False),
            "approved_by": prov.get("approved_by"),
            "approved_at": prov.get("approved_at"),
            "attempts": prov.get("attempts", 0),
            "attempted_at": prov.get("attempted_at"),
            "pr_url": prov.get("pr_url"),
            "outcome": prov.get("outcome"),
            "history": prov.get("history", []),
        },
        "classification": decision["observed_state"],
        "recommended_action": decision["recommended_action"],
        "terminal_restriction": decision["terminal_restriction"],
        "hold": decision["hold"],
        "reasons": decision["reasons"],
        "anomalies": decision["anomalies"],
        # --- contribution-channel policy (Issue #2074) ---
        "policy_channel": pol["channel"],
        "policy_sources": pol["sources"],
        "prior_issue_urls": pol["prior_issue_urls"],
        "approval_required": pol["approval_required"],
        "recommended_next_action": pol["recommended_next_action"],
        "policy_complete": pol["completeness"]["complete"],
        "policy_cost": pol["cost"],
        "policy": pol,
    }


# ---------------------------------------------------------------------------
# Campaign-level reconcile + receipts
# ---------------------------------------------------------------------------


def manifest_digest(manifest: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()


def find_record(manifest: dict[str, Any], repo: str) -> tuple[str, dict[str, Any]]:
    want = normalize_repo_name(repo)
    for k, v in manifest.get("repositories", {}).items():
        if normalize_repo_name(k) == want:
            return k, v
    # Known upstream migrations (e.g. safishamsi/graphify -> Graphify-Labs/graphify).
    moved = KNOWN_MIGRATIONS.get(want)
    if moved:
        for k, v in manifest.get("repositories", {}).items():
            if normalize_repo_name(k) == moved:
                return k, v
    raise KeyError(f"Repository '{repo}' not found in campaign manifest.")


def reconcile_campaign(client: GitHubClient, manifest: dict[str, Any], registry: dict[str, Any],
                       repos: list[str] | None = None, authors: tuple[str, ...] = DEFAULT_CAMPAIGN_AUTHORS,
                       max_workers: int = 4, now: Callable[[], datetime] = utcnow,
                       open_scan_limit: int = MAX_OPEN_SCAN,
                       policy: PolicyConfig | None = None) -> dict[str, Any]:
    """Read-only reconciliation of selected repos (or the whole manifest).

    ``policy`` turns on the per-repo contribution-channel scan. Callers should scope it with ``repos``;
    a full-campaign policy scan is never required and costs up to ``policy.call_budget`` calls per repo.
    """
    all_repos = manifest.get("repositories", {})
    if repos:
        keys = [find_record(manifest, r)[0] for r in repos]
    else:
        keys = sorted(all_repos)
    digest_before = manifest_digest(manifest)
    results: dict[str, dict[str, Any]] = {}
    calls_before = getattr(client, "total_calls", 0)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, max_workers)) as pool:
        futs = {pool.submit(reconcile_repo, client, k, all_repos[k], registry, authors, now, open_scan_limit, policy): k
                for k in keys}
        for fut in concurrent.futures.as_completed(futs):
            results[futs[fut]] = fut.result()
    ordered = {k: results[k] for k in sorted(results)}
    assert manifest_digest(manifest) == digest_before, "reconcile must not mutate the manifest"

    by_class: dict[str, int] = {s: 0 for s in OBSERVED_STATES}
    by_restr: dict[str, int] = {}
    by_cov: dict[str, int] = {}
    by_channel: dict[str, int] = {c: 0 for c in bp.CHANNELS}
    anomalies: list[dict[str, str]] = []
    incomplete = 0
    policy_calls = policy_scanned = policy_incomplete = 0
    for k, r in ordered.items():
        by_class[r["classification"]] = by_class.get(r["classification"], 0) + 1
        if r["terminal_restriction"]:
            by_restr[r["terminal_restriction"]] = by_restr.get(r["terminal_restriction"], 0) + 1
        lvl = r["coverage"]["level"]
        by_cov[lvl] = by_cov.get(lvl, 0) + 1
        by_channel[r["policy_channel"]] += 1
        policy_calls += int(r["policy_cost"].get("api_calls") or 0)
        policy_scanned += 1 if r["policy"]["scanned"] else 0
        policy_incomplete += 1 if (r["policy"]["scanned"] and not r["policy_complete"]) else 0
        if not r["evidence"]["complete"]:
            incomplete += 1
        for a in r["anomalies"]:
            anomalies.append({"repository": r["repository"], **a})
    sev = {"high": 0, "medium": 1, "low": 2, "info": 3}
    anomalies.sort(key=lambda a: (sev.get(a["severity"], 9), a["repository"], a["code"]))
    return {
        "schema_version": SCHEMA_VERSION,
        "campaign": manifest.get("campaign"),
        "issue": "#2069",
        "policy_issue": "#2074",
        "mode": "read-only",
        "generated_at": now().isoformat(),
        "manifest_sha256": digest_before,
        "scope": "subset" if repos else "full-campaign",
        "summary": {
            "repositories": len(ordered),
            "by_classification": {k: v for k, v in by_class.items() if v},
            "by_terminal_restriction": by_restr,
            "by_coverage": by_cov,
            "incomplete_evidence": incomplete,
            "anomalies": len(anomalies),
            "by_policy_channel": {k: v for k, v in by_channel.items() if v},
            "policy_incomplete": policy_incomplete,
        },
        "cost": {
            "repositories_in_scope": len(ordered),
            "policy_repositories_scanned": policy_scanned,
            "policy_api_calls": policy_calls,
            "policy_call_budget_per_repo": policy.call_budget if (policy and policy.scan) else 0,
            "api_calls_total": getattr(client, "total_calls", 0) - calls_before,
            "full_campaign_scan_required": False,
        },
        "repositories": ordered,
        "anomalies": anomalies,
    }


_MD_UNSAFE = re.compile(r"[\x00-\x1f\x7f|`<>\[\]()!*_~#\\]")


def md_untrusted(text: Any, limit: int = 240) -> str:
    """Upstream text is data, never markup: neutralize anything that could render as a link, image, table or HTML."""
    # A bare @handle in a receipt pasted into a GitHub comment would notify that person (external contact):
    # a zero-width space after the @ defuses it while keeping the text readable.
    return _MD_UNSAFE.sub(" ", str(text or ""))[:limit].strip().replace("@", "@\u200b")


_SAFE_URL = re.compile(r"^https://github\.com/[A-Za-z0-9_.\-/#?=&%:@+~]+$")


def md_url(url: Any) -> str:
    return str(url) if _SAFE_URL.match(str(url or "")) else "(non-GitHub or unrecognized URL omitted)"


def render_markdown(receipt: dict[str, Any]) -> str:
    s = receipt["summary"]
    lines = [
        f"# Upstream Badge Reconciliation Receipt ({receipt['issue']})",
        "",
        f"- Campaign: {receipt['campaign']}",
        f"- Mode: **{receipt['mode']}** (no manifest, upstream or GitHub mutation)",
        f"- Generated: {receipt['generated_at']}",
        f"- Scope: {receipt['scope']} ({s['repositories']} repositories)",
        f"- Manifest SHA-256: `{receipt['manifest_sha256'][:16]}…`",
        "",
        "## Summary",
        "",
        "| Classification | Count |", "|---|---|",
    ]
    for k, v in s["by_classification"].items():
        lines.append(f"| {k} | {v} |")
    lines += ["", f"Incomplete evidence: **{s['incomplete_evidence']}** · Anomalies: **{s['anomalies']}**"]
    if s.get("by_policy_channel") is not None:
        lines.append("Policy channels (#2074): " + (", ".join(f"{k}={v}" for k, v in s["by_policy_channel"].items()) or "none")
                     + f" · policy scans incomplete: **{s.get('policy_incomplete', 0)}**")
        c = receipt.get("cost", {})
        lines.append(f"Cost: {c.get('policy_api_calls', 0)} policy API calls over {c.get('policy_repositories_scanned', 0)} "
                     f"scanned repo(s) (budget {c.get('policy_call_budget_per_repo', 0)}/repo; "
                     f"{c.get('api_calls_total', 0)} calls total; full-campaign scan required: "
                     f"{'yes' if c.get('full_campaign_scan_required') else 'no'}).")
    if s["by_terminal_restriction"]:
        lines.append("Terminal restrictions: " + ", ".join(f"{k}={v}" for k, v in s["by_terminal_restriction"].items()))
    lines += ["", "## Repositories", "",
              "| Repository | GitHub ID | Skills (covered/expected) | PRs | Ledger | Classification | Next action | Evidence |",
              "|---|---|---|---|---|---|---|---|"]
    for r in receipt["repositories"].values():
        cov = r["coverage"]
        prs = ", ".join(f"[#{p['number']}]({p['url']}) {p['state']}" for p in r["pull_requests"]) or "–"
        ev = r["evidence"]
        fresh = ev["observed_at"] + (f" @{ev['readme_commit_sha'][:8]}" if ev.get("readme_commit_sha") else "")
        fresh += "" if ev["complete"] else " **INCOMPLETE**"
        lines.append(
            f"| {r['repository']}{' (HOLD ' + r['hold'] + ')' if r.get('hold') else ''} | {r['github_id'] or '?'} | "
            f"{len(cov['covered_skill_ids'])}/{len(r['expected_skills'])} ({cov['level']}) | {prs} | "
            f"{r['ledger']['status']} | **{r['classification']}**"
            f"{' / ' + r['terminal_restriction'] if r['terminal_restriction'] else ''} | "
            f"{r['recommended_action']} | {fresh} |"
        )
    lines += ["", "## Contribution-channel policy (#2074)", "",
              "| Repository | Channel | Approval required | Prior issues | Complete | API calls | Next action |",
              "|---|---|---|---|---|---|---|"]
    for r in receipt["repositories"].values():
        ar = r["approval_required"]
        appr = ("maintainer approval: " + ar["maintainer_approval_state"]) if ar["maintainer_approval"] else (
            "campaign approval only" if ar["campaign_human_approval"] else "none (hold)")
        issues = ", ".join(md_url(u) for u in r["prior_issue_urls"]) or "–"
        lines.append(f"| {r['repository']} | **{r['policy_channel']}**"
                     f"{' (partial: ' + r['policy']['partial_channel'] + ')' if r['policy'].get('partial_channel') and r['policy_channel'] == 'UNKNOWN' else ''}"
                     f" | {appr} | {issues} | {'yes' if r['policy_complete'] else '**NO**'} | "
                     f"{r['policy_cost'].get('api_calls', 0)}/{r['policy_cost'].get('budget', 0)} | {r['recommended_next_action']} |")
    for r in receipt["repositories"].values():
        if not r["policy"]["scanned"]:
            continue
        lines += ["", f"### {r['repository']}: {r['policy_channel']}", ""]
        lines.append("- Why: " + "; ".join(r["policy"]["channel_reasons"]))
        lines.append(f"- Observed: {r['policy']['observed_at']}")
        lines.append(f"- Next: {r['policy']['next_action_detail']}")
        if r["policy"]["completeness"]["incomplete_reasons"]:
            lines.append("- **Incomplete**: " + ", ".join(r["policy"]["completeness"]["incomplete_reasons"]))
        for sg in r["policy_sources"]:
            if sg.get("decisive"):
                lines.append(f"- `{sg['effect']}` ({sg['kind']}, {sg['authority']}, {sg['strength']}) "
                             f"{md_untrusted(sg.get('path') or 'source', 80)} {md_url(sg.get('source_url'))}: "
                             f"\"{md_untrusted(sg['excerpt'])}\"")
        for hc in r["policy"]["historical_closures"]:
            lines.append(f"- Historical closure (never erased): {hc['pr_url']} {hc['state']} {hc['closed_at']} ({hc['kind']})")
    lines += ["", "## Anomalies", ""]
    if not receipt["anomalies"]:
        lines.append("None.")
    for a in receipt["anomalies"]:
        lines.append(f"- **{a['severity']}** `{a['code']}` — {a['repository']}: {a['detail']}")
    lines.append("")
    return "\n".join(lines)


def write_receipt(receipt: dict[str, Any], out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    jp, mp = out_dir / "receipt.json", out_dir / "receipt.md"
    jp.write_text(json.dumps(receipt, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    mp.write_text(render_markdown(receipt), encoding="utf-8")
    return jp, mp


# ---------------------------------------------------------------------------
# Pre-dispatch gate + reservations
# ---------------------------------------------------------------------------

DEFAULT_RESERVATION_DIR = Path(__file__).resolve().parent.parent / "campaigns" / "badge-provisioning" / ".reservations"


class ReservationError(Exception):
    pass


def _slug(repo: str) -> str:
    return normalize_repo_name(repo).replace("/", "__")


def reservation_path(repo: str, directory: Path = DEFAULT_RESERVATION_DIR) -> Path:
    return directory / f"{_slug(repo)}.lock"


def ledger_snapshot(record: dict[str, Any]) -> dict[str, Any]:
    """The authorization-relevant ledger facts a reservation is bound to."""
    prov = record.get("provisioning", {})
    return {
        "status": record.get("status"),
        "approved": bool(prov.get("approved")),
        "approved_by": prov.get("approved_by"),
        "approved_at": prov.get("approved_at"),
        "attempts": int(prov.get("attempts") or 0),
        "pr_url": prov.get("pr_url"),
        "outcome": prov.get("outcome"),
        "history_len": len(prov.get("history", [])),
    }


def acquire_reservation(repo: str, worker: str, ttl_minutes: int = 30, directory: Path = DEFAULT_RESERVATION_DIR,
                        now: Callable[[], datetime] = utcnow,
                        ledger_snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
    """Exclusive per-repo reservation via O_CREAT|O_EXCL (atomic on a local filesystem).

    Expired reservations are NOT silently stolen; they must be released explicitly.
    Local only: it cannot coordinate workers on other machines.
    """
    directory.mkdir(parents=True, exist_ok=True)
    path = reservation_path(repo, directory)
    t = now()
    data = {
        "repository": normalize_repo_name(repo),
        "worker": worker,
        "token": uuid.uuid4().hex,
        "pid": os.getpid(),
        "host": socket.gethostname(),
        "acquired_at": t.isoformat(),
        "expires_at": (t + timedelta(minutes=ttl_minutes)).isoformat(),
        "ledger_snapshot": ledger_snapshot,
    }
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        try:
            held = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            held = {"worker": "UNREADABLE"}
        raise ReservationError(
            f"{repo} already reserved by {held.get('worker')} until {held.get('expires_at')}; "
            "release explicitly if stale"
        ) from None
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(data, indent=2) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    return data


def verify_reservation(repo: str, token: str, directory: Path = DEFAULT_RESERVATION_DIR,
                       now: Callable[[], datetime] = utcnow,
                       current_snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
    """Validate token + expiry and, when given, that the ledger still matches the gate-time snapshot.

    A token authorizes one PR for the ledger state it was issued against. Any change to status,
    approval, attempts, PR URL, outcome or history (e.g. DECLINED / OPTED_OUT) voids it.
    """
    path = reservation_path(repo, directory)
    try:
        held = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise ReservationError(f"No valid reservation for {repo}: {e}") from e
    if held.get("token") != token:
        raise ReservationError(f"Reservation token mismatch for {repo}")
    if datetime.fromisoformat(held["expires_at"]) < now():
        raise ReservationError(f"Reservation for {repo} expired at {held['expires_at']}; re-run predispatch")
    if current_snapshot is not None and held.get("ledger_snapshot") != current_snapshot:
        raise ReservationError(
            f"Ledger for {repo} changed since predispatch (status now {current_snapshot.get('status')}); "
            "authorization void, re-run predispatch")
    return held


def release_reservation(repo: str, token: str | None = None, force: bool = False,
                        directory: Path = DEFAULT_RESERVATION_DIR) -> bool:
    path = reservation_path(repo, directory)
    if not path.exists():
        return False
    if not force:
        try:
            held = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            raise ReservationError(f"Unreadable reservation for {repo}; use force: {e}") from e
        if held.get("token") != token:
            raise ReservationError(f"Reservation token mismatch for {repo}")
    path.unlink()
    return True


def evaluate_dispatch(manifest: dict[str, Any], repo: str, entry: dict[str, Any]) -> list[str]:
    """Return the list of refusal reasons (empty => dispatch permitted). Pure.

    Contribution-channel policy (Issue #2074) is part of the gate: only ``PR_ALLOWED`` passes, or
    ``ISSUE_FIRST`` once a maintainer approval is recorded AND verified against upstream comments.
    ``NO_OUTREACH`` / ``UNKNOWN`` are internal holds. Issue and PR are two stages of ONE attempt.
    """
    refusals: list[str] = []
    prov = entry["ledger"]
    status = prov.get("status")
    pol = entry.get("policy") or {}
    waived = bool(pol.get("pr_history_waived"))  # earlier PR(s) closed under the repo's own issue-first policy
    if entry["classification"] != "READY_TO_APPROVE" and not (waived and entry["classification"] == "CLOSED_UNMERGED"):
        refusals.append(f"observed state {entry['classification']} is not READY_TO_APPROVE")
    if not entry["evidence"]["complete"]:
        refusals.append("upstream evidence incomplete")
    if entry.get("hold"):
        refusals.append(f"repository is on founder hold {entry['hold']}")
    if entry["terminal_restriction"]:
        refusals.append(f"terminal outreach restriction {entry['terminal_restriction']}")
    if status != "APPROVED" or not prov.get("approved") or not prov.get("approved_by"):
        refusals.append(f"no recorded human approval (ledger status {status})")
    if (prov.get("pr_url") or int(prov.get("attempts") or 0) > 0) and not waived:
        refusals.append("ledger already records a PR URL or attempt")
    if entry["pull_requests"] and not waived:
        refusals.append("upstream already has relevant Gaia PR(s)")
    if entry["coverage"]["covered_skill_ids"] or entry["other_files"]:
        refusals.append("Gaia badge already present upstream")
    if not (entry["ledger"].get("canonical_skill")):
        refusals.append("ledger has no canonical skill")
    if entry["anomalies"] and any(a["severity"] in ("high", "medium") for a in entry["anomalies"]):
        refusals.append("unresolved medium/high anomalies")
    # --- contribution-channel policy (Issue #2074) ---
    if not pol or not pol.get("scanned"):
        refusals.append("contribution-channel policy not scanned (policy_channel UNKNOWN)")
    else:
        channel = pol["channel"]
        if not pol["completeness"]["complete"]:
            refusals.append("policy evidence incomplete: " + ", ".join(pol["completeness"]["incomplete_reasons"]))
        if channel in ("NO_OUTREACH", "UNKNOWN"):
            refusals.append(f"policy channel {channel} is an internal hold (no PR, no issue)")
        elif channel == "ISSUE_FIRST" and pol["approval"]["state"] != "VERIFIED":
            refusals.append(f"policy channel ISSUE_FIRST needs a verified recorded maintainer approval "
                            f"(approval state {pol['approval']['state']})")
        if pol["prior_prs"] and not waived:
            refusals.append("cross-channel duplicate: a Gaia PR already exists for this repo (found by policy search "
                            "or ledger): " + ", ".join(p["url"] for p in pol["prior_prs"]))
        if pol["prior_issue_urls"] and not (channel == "ISSUE_FIRST" and pol["approval"]["state"] == "VERIFIED"):
            refusals.append("cross-channel duplicate: a Gaia issue already exists for this repo "
                            "(issue and PR are stages of one outreach attempt): " + ", ".join(pol["prior_issue_urls"]))
        unexpected = [u for u in pol["prior_issue_urls"]
                      if channel == "ISSUE_FIRST" and pol["approval"]["state"] == "VERIFIED"
                      and bp._norm_url(u) != bp._norm_url((pol["approval"].get("record") or {}).get("issue_url"))]
        if unexpected:
            refusals.append("more than one Gaia issue exists; only the single approved proposal is allowed: "
                            + ", ".join(unexpected))
    return refusals


def predispatch_gate(client: GitHubClient, manifest: dict[str, Any], registry: dict[str, Any], repo: str,
                     worker: str, ttl_minutes: int = 30, authors: tuple[str, ...] = DEFAULT_CAMPAIGN_AUTHORS,
                     directory: Path = DEFAULT_RESERVATION_DIR,
                     now: Callable[[], datetime] = utcnow,
                     open_scan_limit: int = MAX_OPEN_SCAN,
                     policy: PolicyConfig | None = None,
                     ledger_path: Path = DEFAULT_POLICY_LEDGER) -> dict[str, Any]:
    """Mandatory immediately-before-PR check.

    Order: reserve first (so concurrent workers serialize), then refresh upstream
    evidence, then evaluate ledger + approval. On any refusal the reservation is
    released. Returns a verdict dict; ``allowed`` implies the caller holds ``token``.

    The contribution-channel policy scan (Issue #2074) is always on here: it is part of the gate.
    ``policy`` overrides its caps and ledger events; by default the policy ledger at ``ledger_path``
    is loaded (a corrupt or tampered ledger fails closed).
    """
    key, record = find_record(manifest, repo)
    try:
        res = acquire_reservation(repo, worker, ttl_minutes, directory, now,
                                  ledger_snapshot=ledger_snapshot(record))
    except ReservationError as e:
        return {"allowed": False, "repository": key, "refusals": [str(e)], "reservation": None, "entry": None}
    try:
        pcfg = policy if policy is not None else PolicyConfig(events=load_policy_events(ledger_path))
        entry = reconcile_repo(client, key, record, registry, authors, now, open_scan_limit, pcfg)
        refusals = evaluate_dispatch(manifest, key, entry)
    except Exception as e:  # fail closed on anything unexpected
        release_reservation(repo, res["token"], directory=directory)
        return {"allowed": False, "repository": key, "refusals": [f"gate error: {e}"], "reservation": None, "entry": None}
    if refusals:
        release_reservation(repo, res["token"], directory=directory)
        return {"allowed": False, "repository": key, "refusals": refusals, "reservation": None, "entry": entry}
    return {"allowed": True, "repository": key, "refusals": [], "reservation": res, "entry": entry}
