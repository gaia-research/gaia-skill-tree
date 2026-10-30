"""
scripts.lib.github_api — GitHub API client and URL parser.

Ported and generalised from ``scripts/stargazerHeartbeat.py`` so that both
the heartbeat and the upcoming upstream-watcher share identical API call
semantics (upstream-watcher design §9, PR 2 of 7).

Public API
----------
parse_owner_repo(url)
    Extract (owner, repo) from any GitHub URL.  Returns None on failure.

fetch_json(endpoint, token=None, timeout=10)
    Fetch a GitHub API endpoint and return the parsed JSON dict.
    Accepts a full URL or an ``/…`` path (auto-prefixed to api.github.com).
    Same retry/throttle semantics as the heartbeat's ``fetch_stars``.

head_check(url, timeout=10)
    Issue an HTTP HEAD to *url* and return the HTTP status code.
    Returns None on network error.  Safe on ``raw.githubusercontent.com``
    URLs (design §5 — rendered blob/ URLs can serve HTML on 404; raw URLs
    are the canonical liveness target).

fetch_text(url, timeout=10)
    Issue an HTTP GET to *url* and return the decoded response body as text.
    Returns None on network error.  Intended for raw content fetches (e.g.
    a component's ``SKILL.md`` source) — distinct from ``fetch_json``, which
    parses ``api.github.com`` JSON responses.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request

# ---------------------------------------------------------------------------
# GitHub URL parser — ported verbatim from stargazerHeartbeat.parse_owner_repo
# ---------------------------------------------------------------------------

import re

_GH_RE = re.compile(
    r"https?://github\.com/([^/]+)/([^/\s#?]+)"
    r"(?:/(?:blob|tree|stargazers|commits?|releases?)(?:/[^\s#?]*)?)?"
)


def parse_owner_repo(url: str) -> tuple[str, str] | None:
    """Extract ``(owner, repo)`` from a GitHub URL.

    Handles:
    - Bare repo URL: ``https://github.com/owner/repo``
    - ``blob/`` URL: ``https://github.com/owner/repo/blob/main/path``
    - ``tree/`` URL: ``https://github.com/owner/repo/tree/main/dir``
    - ``releases/tag/`` URL: ``https://github.com/owner/repo/releases/tag/v1``
    - ``.git`` suffix stripped automatically.

    Returns ``None`` for non-GitHub URLs or empty input.

    Ported verbatim from ``stargazerHeartbeat.parse_owner_repo``.
    """
    if not url:
        return None
    m = _GH_RE.match(url.strip())
    if not m:
        return None
    owner = m.group(1)
    repo = m.group(2).rstrip("/")
    if repo.endswith(".git"):
        repo = repo[:-4]
    return (owner, repo)


def parse_owner_repo_normalized(url: str) -> tuple[str, str] | None:
    """Extract case-normalized ``(owner.lower(), repo.lower())`` from a GitHub URL.

    GitHub repository paths are ASCII case-insensitive. Normalizing prevents
    false mismatches such as ``Leonxlnx/taste-skill`` vs ``leonxlnx/taste-skill``.
    """
    parsed = parse_owner_repo(url)
    if not parsed:
        return None
    return (parsed[0].lower(), parsed[1].lower())


# ---------------------------------------------------------------------------
# JSON fetch — generalised from stargazerHeartbeat.fetch_stars
# ---------------------------------------------------------------------------

_API_BASE = "https://api.github.com"
_CACHE: dict[str, dict | None] = {}  # URL -> parsed JSON or None on error


class GitHubFetchError(RuntimeError):
    """A strict GitHub GET failed: any status other than a definitive 404, a network error, or an unparseable body.

    ``headers`` (a mapping, case-insensitive for lookups) and ``body`` (text) carry what the response said, so a
    caller can tell a rate limit from a permanent refusal (H2). Both are optional.
    """

    def __init__(self, message: str, status: int | None = None, headers=None, body: str = ""):
        super().__init__(message)
        self.status = status
        self.headers = {str(k).lower(): str(v) for k, v in (headers or {}).items()}
        self.body = body or ""


# H2: statuses that say the resource is unavailable for good.
PERMANENT_UNAVAILABLE_STATUSES = frozenset({451, 410})
# M-4 (C9): a 403 is a permanent refusal only when the repository's own message says so (a DMCA takedown, a blocked
# or disabled repository). It is matched against the response body GitHub returned, never against the URL.
PERMANENT_REFUSAL_RE = re.compile(r"access blocked|dmca|takedown|repository (?:was )?disabled|blocked by", re.IGNORECASE)
# M-4 (C9): a token or App permission problem. Never permanent: it is a visible hard error that names the permission.
PERMISSION_PROBLEM_RE = re.compile(r"resource not accessible by integration", re.IGNORECASE)


def is_rate_limited(exc: GitHubFetchError) -> bool:
    """H2: True when a failed GET carries a rate-limit signal (a spent quota, Retry-After, or a rate-limit message)."""
    headers = getattr(exc, "headers", {}) or {}
    if headers.get("x-ratelimit-remaining") == "0" or "retry-after" in headers:
        return True
    text = f"{getattr(exc, 'body', '') or ''} {exc}".lower()
    return "rate limit" in text or "secondary rate" in text or "abuse detection" in text


def is_permission_problem(exc: GitHubFetchError) -> bool:
    """M-4 (C9): True for a 403 that says the token or App may not read the resource ("Resource not accessible by
    integration"). It is not permanent: the operator grants the permission and the next run reads the suite."""
    return getattr(exc, "status", None) == 403 and bool(PERMISSION_PROBLEM_RE.search(getattr(exc, "body", "") or ""))


def is_permanent_unavailable(exc: GitHubFetchError) -> bool:
    """H2 and M-4 (C9): True when retrying cannot help and the suite must be skipped (not treated as unknown evidence).

    Only these are permanent: 451 (blocked), 410 (gone), and a 403 whose body is the repository's own refusal
    (a DMCA takedown, a blocked or disabled repository). A 403 is never permanent when it is a rate limit or a
    permission problem, and a bare 403 is not permanent either: it says nothing about the repository, so it stays
    unknown evidence (exit 3). 5xx, 429, a timeout and a network error are transient, never permanent.
    """
    status = getattr(exc, "status", None)
    if status in PERMANENT_UNAVAILABLE_STATUSES:
        return True
    if status != 403 or is_rate_limited(exc) or is_permission_problem(exc):
        return False
    return bool(PERMANENT_REFUSAL_RE.search(getattr(exc, "body", "") or ""))


class GitHubNotFound(GitHubFetchError):
    """A strict GitHub GET answered HTTP 404: the resource is definitively absent."""


def fetch_json(
    endpoint: str,
    token: str | None = None,
    timeout: int = 10,
    *,
    strict: bool = False,
) -> dict | None:
    """Fetch *endpoint* and return the parsed JSON dict.

    *endpoint* may be:
    - A full URL: ``https://api.github.com/repos/owner/repo``
    - A path:     ``/repos/owner/repo`` (auto-prefixed to ``api.github.com``)

    Auth: *token* overrides; falls back to ``GH_TOKEN`` env var; unauthenticated
    if neither is set (60 req/hr rate limit).

    Caching: results are cached in-process by full URL.  Re-invoke the script
    to bypass.

    Throttle: a 100 ms sleep fires in ``finally`` (same as heartbeat) to avoid
    saturating the rate limit on bulk runs.

    Returns ``None`` on ``HTTPError``, timeout, or any network error; emits a
    warning to ``stderr``.

    With ``strict=True`` nothing is swallowed and nothing is cached: an HTTP 404
    raises :class:`GitHubNotFound`, and every other failure raises
    :class:`GitHubFetchError`. Callers that treat an error as unknown evidence
    (the upstream watcher) must use strict mode.
    """
    # Normalise to a full URL
    if endpoint.startswith("/"):
        url = f"{_API_BASE}{endpoint}"
    elif not endpoint.startswith("http"):
        url = f"{_API_BASE}/{endpoint}"
    else:
        url = endpoint

    if strict:
        return _fetch_strict(url, token, timeout)

    if url in _CACHE:
        return _CACHE[url]

    resolved_token = token or os.environ.get("GH_TOKEN", "")

    req = urllib.request.Request(
        url,
        headers={"Accept": "application/vnd.github+json"},
    )
    if resolved_token:
        req.add_header("Authorization", f"token {resolved_token}")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
            _CACHE[url] = data
            return data
    except urllib.error.HTTPError as exc:
        print(
            f"  [warn] GitHub API HTTP {exc.code} for {url}: {exc.reason}",
            file=sys.stderr,
        )
        _CACHE[url] = None
        return None
    except Exception as exc:  # noqa: BLE001
        print(f"  [warn] GitHub API error for {url}: {exc}", file=sys.stderr)
        _CACHE[url] = None
        return None
    finally:
        time.sleep(0.1)  # 100 ms throttle — same as heartbeat


def _fetch_strict(url: str, token: str | None, timeout: int) -> dict:
    """Strict GET: return parsed JSON, or raise. Never cached, never swallowed."""
    resolved_token = token or os.environ.get("GH_TOKEN", "")
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    if resolved_token:
        req.add_header("Authorization", f"token {resolved_token}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise GitHubNotFound(f"GitHub API HTTP 404 for {url}", status=404) from exc
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:  # noqa: BLE001 — the body is evidence for the classifier, never a reason to fail differently
            body = ""
        raise GitHubFetchError(
            f"GitHub API HTTP {exc.code} for {url}: {exc.reason}", status=exc.code,
            headers=dict(exc.headers.items()) if exc.headers is not None else None, body=body,
        ) from exc
    except Exception as exc:  # noqa: BLE001 — timeouts, resets, DNS: all unknown evidence
        raise GitHubFetchError(f"GitHub API request failed for {url}: {exc}") from exc
    finally:
        time.sleep(0.1)  # 100 ms throttle, as in the legacy path
    try:
        data = json.loads(raw)
    except ValueError as exc:
        raise GitHubFetchError(f"unparseable JSON from {url}: {exc}") from exc
    if not isinstance(data, dict):
        raise GitHubFetchError(f"unexpected JSON shape from {url}: expected an object")
    return data


# ---------------------------------------------------------------------------
# HEAD check for link liveness (new — used by upstream watcher, design §5)
# ---------------------------------------------------------------------------


def head_check(url: str, timeout: int = 10) -> int | None:
    """Issue an HTTP HEAD to *url* and return the HTTP status code.

    Returns ``None`` on any network-level error (no HTTP response received).

    Notes
    -----
    Design §5 explicitly calls out that rendered GitHub ``blob/`` URLs can
    serve HTML even for paths that 404 on the raw content endpoint.  Callers
    should convert ``github.com/.../blob/…`` URLs to
    ``raw.githubusercontent.com/…`` before passing them here when checking
    SKILL.md liveness:

    .. code-block:: python

        raw_url = url.replace(
            "https://github.com/", "https://raw.githubusercontent.com/"
        ).replace("/blob/", "/")

    This function does NOT do that conversion — the caller decides the
    canonical liveness target.
    """
    req = urllib.request.Request(url, method="HEAD")
    # Some servers reject bare Python UA; mimic a browser-ish UA
    req.add_header("User-Agent", "gaia-upstream-watcher/1.0 (link-liveness)")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:
        # HTTPError is raised for 4xx/5xx — we still have a status code
        return exc.code
    except Exception:  # noqa: BLE001
        return None


# ---------------------------------------------------------------------------
# Raw content fetch (new — used by upstream watcher name-drift detection)
# ---------------------------------------------------------------------------


def fetch_text(url: str, timeout: int = 10) -> str | None:
    """Issue an HTTP GET to *url* and return the decoded response body.

    Returns ``None`` on any network-level error (no response, timeout, 4xx/5xx).
    Intended for ``raw.githubusercontent.com`` content fetches — callers
    should convert rendered ``github.com/.../blob/…`` URLs first (see
    :func:`scripts.upstream_watcher.liveness.blob_to_raw`).
    """
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "gaia-upstream-watcher/1.0 (content-fetch)")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001
        print(f"  [warn] GitHub content fetch error for {url}: {exc}", file=sys.stderr)
        return None
