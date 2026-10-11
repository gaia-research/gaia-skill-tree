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
import hashlib
import html
import json
import os
import re
import socket
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

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
CAMPAIGN_HOLDS = {
    "safishamsi/graphify": "#2067",
    "graphify-labs/graphify": "#2067",
}
MAX_PAGES = 10
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

    def __init__(self, transport: Any, retries: int = 2, backoff: float = 0.5,
                 sleep: Callable[[float], None] = time.sleep) -> None:
        self.transport = transport
        self.retries = retries
        self.backoff = backoff
        self.sleep = sleep

    def get(self, path: str) -> Response:
        """GET with retries for transient (5xx / network) failures only."""
        last: ApiError | None = None
        for attempt in range(self.retries + 1):
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
        raise classify_error(resp)

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
            if f.get("status") not in ("removed",) and f.get("changes", 1) != 0:
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


def inspect_pr(client: GitHubClient, owner: str, repo: str, number: int) -> dict[str, Any]:
    """Fetch exact PR status plus patch contents (never rely on the title)."""
    base = f"/repos/{owner}/{repo}/pulls/{number}"
    pr = client.get_ok(base).body
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
    readme: dict[str, Any] = field(default_factory=dict)
    other_files: dict[str, Any] = field(default_factory=dict)
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
               history_urls: list[str], authors: tuple[str, ...], ev: Evidence) -> None:
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
        for pr in open_prs:
            if _is_marker_pr(pr, authors) or _is_weak_candidate(pr):
                n = pr["number"]
                targets.setdefault(n, (owner, repo))
                matched.setdefault(n, set()).add("open_list")

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

        for n in sorted(targets):
            o, r = targets[n]
            info = inspect_pr(client, o, r, n)
            info["matched_by"] = sorted(matched[n])
            raw = info.pop("_raw")
            marker = _is_marker_pr(raw, authors)
            info["ledgered"] = "ledger" in matched[n]
            info["has_gaia_badge"] = bool(info["badge_refs"])
            info["marker_only"] = (not info["has_gaia_badge"]) and marker and not info["ledgered"]
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
    snippets = [ln.strip()[:240] for ln in text.splitlines() if "gaiaskilltree.com/badges" in html.unescape(ln).lower()]
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
                     authors: tuple[str, ...]) -> Evidence:
    ev = Evidence()
    canonical = resolve_identity(client, requested_repo, ev)
    prov = record.get("provisioning", {})
    hist_urls = sorted({h.get("pr_url") for h in prov.get("history", []) if h.get("pr_url")} - {prov.get("pr_url")})
    if canonical is None:
        for c in ("pull_requests", "readme", "other_files"):
            ev.components[c] = {"complete": False, "error_code": "SKIPPED", "detail": "identity unresolved"}
        return ev
    gather_prs(client, canonical, prov.get("pr_url"), hist_urls, authors, ev)
    gather_readme(client, canonical, ev.identity["default_branch"], ev)
    gather_other_files(client, canonical, ev.readme.get("path"), ev)
    return ev


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
    reasons.append("No PR, no badge, complete upstream evidence, no prior outreach.")
    return finish("READY_TO_APPROVE", "REQUEST_HUMAN_APPROVAL")


def reconcile_repo(client: GitHubClient, requested: str, record: dict[str, Any],
                   registry: dict[str, Any], authors: tuple[str, ...] = DEFAULT_CAMPAIGN_AUTHORS,
                   now: Callable[[], datetime] = utcnow) -> dict[str, Any]:
    """Reconcile one repository; never raises for upstream conditions (fails closed)."""
    expected = expected_skills_for_repo(registry, requested)
    try:
        ev = collect_evidence(client, requested, record, authors)
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
            "observed_at": now().isoformat(),
            "complete": ev.complete,
            "components": ev.components,
            "readme_commit_sha": ev.readme.get("commit_sha"),
            "errors": ev.errors,
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
    raise KeyError(f"Repository '{repo}' not found in campaign manifest.")


def reconcile_campaign(client: GitHubClient, manifest: dict[str, Any], registry: dict[str, Any],
                       repos: list[str] | None = None, authors: tuple[str, ...] = DEFAULT_CAMPAIGN_AUTHORS,
                       max_workers: int = 4, now: Callable[[], datetime] = utcnow) -> dict[str, Any]:
    """Read-only reconciliation of selected repos (or the whole manifest)."""
    all_repos = manifest.get("repositories", {})
    if repos:
        keys = [find_record(manifest, r)[0] for r in repos]
    else:
        keys = sorted(all_repos)
    digest_before = manifest_digest(manifest)
    results: dict[str, dict[str, Any]] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, max_workers)) as pool:
        futs = {pool.submit(reconcile_repo, client, k, all_repos[k], registry, authors, now): k for k in keys}
        for fut in concurrent.futures.as_completed(futs):
            results[futs[fut]] = fut.result()
    ordered = {k: results[k] for k in sorted(results)}
    assert manifest_digest(manifest) == digest_before, "reconcile must not mutate the manifest"

    by_class: dict[str, int] = {s: 0 for s in OBSERVED_STATES}
    by_restr: dict[str, int] = {}
    by_cov: dict[str, int] = {}
    anomalies: list[dict[str, str]] = []
    incomplete = 0
    for k, r in ordered.items():
        by_class[r["classification"]] = by_class.get(r["classification"], 0) + 1
        if r["terminal_restriction"]:
            by_restr[r["terminal_restriction"]] = by_restr.get(r["terminal_restriction"], 0) + 1
        lvl = r["coverage"]["level"]
        by_cov[lvl] = by_cov.get(lvl, 0) + 1
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
        },
        "repositories": ordered,
        "anomalies": anomalies,
    }


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


def acquire_reservation(repo: str, worker: str, ttl_minutes: int = 30, directory: Path = DEFAULT_RESERVATION_DIR,
                        now: Callable[[], datetime] = utcnow) -> dict[str, Any]:
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
                       now: Callable[[], datetime] = utcnow) -> dict[str, Any]:
    path = reservation_path(repo, directory)
    try:
        held = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise ReservationError(f"No valid reservation for {repo}: {e}") from e
    if held.get("token") != token:
        raise ReservationError(f"Reservation token mismatch for {repo}")
    if datetime.fromisoformat(held["expires_at"]) < now():
        raise ReservationError(f"Reservation for {repo} expired at {held['expires_at']}; re-run predispatch")
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
    """Return the list of refusal reasons (empty => dispatch permitted). Pure."""
    refusals: list[str] = []
    prov = entry["ledger"]
    status = prov.get("status")
    if entry["classification"] != "READY_TO_APPROVE":
        refusals.append(f"observed state {entry['classification']} is not READY_TO_APPROVE")
    if not entry["evidence"]["complete"]:
        refusals.append("upstream evidence incomplete")
    if entry.get("hold"):
        refusals.append(f"repository is on founder hold {entry['hold']}")
    if entry["terminal_restriction"]:
        refusals.append(f"terminal outreach restriction {entry['terminal_restriction']}")
    if status != "APPROVED" or not prov.get("approved") or not prov.get("approved_by"):
        refusals.append(f"no recorded human approval (ledger status {status})")
    if prov.get("pr_url") or int(prov.get("attempts") or 0) > 0:
        refusals.append("ledger already records a PR URL or attempt")
    if entry["pull_requests"]:
        refusals.append("upstream already has relevant Gaia PR(s)")
    if entry["coverage"]["covered_skill_ids"] or entry["other_files"]:
        refusals.append("Gaia badge already present upstream")
    if not (entry["ledger"].get("canonical_skill")):
        refusals.append("ledger has no canonical skill")
    if entry["anomalies"] and any(a["severity"] in ("high", "medium") for a in entry["anomalies"]):
        refusals.append("unresolved medium/high anomalies")
    return refusals


def predispatch_gate(client: GitHubClient, manifest: dict[str, Any], registry: dict[str, Any], repo: str,
                     worker: str, ttl_minutes: int = 30, authors: tuple[str, ...] = DEFAULT_CAMPAIGN_AUTHORS,
                     directory: Path = DEFAULT_RESERVATION_DIR,
                     now: Callable[[], datetime] = utcnow) -> dict[str, Any]:
    """Mandatory immediately-before-PR check.

    Order: reserve first (so concurrent workers serialize), then refresh upstream
    evidence, then evaluate ledger + approval. On any refusal the reservation is
    released. Returns a verdict dict; ``allowed`` implies the caller holds ``token``.
    """
    key, record = find_record(manifest, repo)
    try:
        res = acquire_reservation(repo, worker, ttl_minutes, directory, now)
    except ReservationError as e:
        return {"allowed": False, "repository": key, "refusals": [str(e)], "reservation": None, "entry": None}
    try:
        entry = reconcile_repo(client, key, record, registry, authors, now)
        refusals = evaluate_dispatch(manifest, key, entry)
    except Exception as e:  # fail closed on anything unexpected
        release_reservation(repo, res["token"], directory=directory)
        return {"allowed": False, "repository": key, "refusals": [f"gate error: {e}"], "reservation": None, "entry": None}
    if refusals:
        release_reservation(repo, res["token"], directory=directory)
        return {"allowed": False, "repository": key, "refusals": refusals, "reservation": None, "entry": entry}
    return {"allowed": True, "repository": key, "refusals": [], "reservation": res, "entry": entry}
