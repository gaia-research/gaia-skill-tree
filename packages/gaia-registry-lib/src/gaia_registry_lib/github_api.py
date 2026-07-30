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


# ---------------------------------------------------------------------------
# JSON fetch — generalised from stargazerHeartbeat.fetch_stars
# ---------------------------------------------------------------------------

_API_BASE = "https://api.github.com"
_CACHE: dict[str, dict | None] = {}  # URL -> parsed JSON or None on error


def fetch_json(
    endpoint: str,
    token: str | None = None,
    timeout: int = 10,
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
    """
    # Normalise to a full URL
    if endpoint.startswith("/"):
        url = f"{_API_BASE}{endpoint}"
    elif not endpoint.startswith("http"):
        url = f"{_API_BASE}/{endpoint}"
    else:
        url = endpoint

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
