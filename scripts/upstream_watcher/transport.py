"""
scripts.upstream_watcher.transport — Transport abstraction and deterministic clock.

Provides:
- Clock: SystemClock and VirtualClock for repeatable offline testing.
- Response: Structured HTTP response with status, lowercased headers, and Retry-After.
- BaseTransport: Protocol/abstract base for release, commit, content, and probe requests.
- HttpTransport: Production transport using urllib with header capture and rate-limit handling.
- SimulatedTransport: In-memory mock transport for deterministic offline test fixtures.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from typing import Any

from scripts.lib.github_api import parse_owner_repo_normalized


# ---------------------------------------------------------------------------
# Clock abstraction
# ---------------------------------------------------------------------------


class Clock(ABC):
    """Abstract clock returning ISO-8601 UTC timestamps."""

    @abstractmethod
    def now_utc(self) -> str:
        """Return current time as ISO-8601 UTC string ending in 'Z'."""
        ...

    @abstractmethod
    def now_datetime(self) -> datetime:
        """Return current time as timezone-aware UTC datetime."""
        ...


class SystemClock(Clock):
    """Live wall clock."""

    def now_utc(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def now_datetime(self) -> datetime:
        return datetime.now(timezone.utc)


class VirtualClock(Clock):
    """Deterministic, advanceable virtual clock for offline fixtures."""

    def __init__(self, initial_utc: str | datetime = "2026-10-26T00:00:00Z") -> None:
        if isinstance(initial_utc, str):
            clean = initial_utc.replace("Z", "+00:00")
            self._current = datetime.fromisoformat(clean).astimezone(timezone.utc)
        else:
            self._current = initial_utc.astimezone(timezone.utc)

    def now_utc(self) -> str:
        return self._current.strftime("%Y-%m-%dT%H:%M:%SZ")

    def now_datetime(self) -> datetime:
        return self._current

    def advance_seconds(self, seconds: float) -> None:
        from datetime import timedelta
        self._current += timedelta(seconds=seconds)

    def advance_hours(self, hours: float) -> None:
        self.advance_seconds(hours * 3600.0)

    def set_time(self, new_utc: str | datetime) -> None:
        if isinstance(new_utc, str):
            clean = new_utc.replace("Z", "+00:00")
            self._current = datetime.fromisoformat(clean).astimezone(timezone.utc)
        else:
            self._current = new_utc.astimezone(timezone.utc)


# ---------------------------------------------------------------------------
# Structured Response
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Response:
    """Structured response from a transport operation."""

    status_code: int | None
    data: Any = None
    headers: dict[str, str] = field(default_factory=dict)
    error: str | None = None

    @property
    def is_success(self) -> bool:
        return self.status_code is not None and 200 <= self.status_code < 300

    @property
    def is_rate_limited(self) -> bool:
        if self.status_code in {429, 403}:
            if "retry-after" in self.headers or "x-ratelimit-remaining" in self.headers:
                remaining = self.headers.get("x-ratelimit-remaining", "")
                if remaining == "0" or self.status_code == 429:
                    return True
        return False

    @property
    def retry_after_seconds(self) -> int | None:
        """Parse Retry-After header or calculate from x-ratelimit-reset."""
        if "retry-after" in self.headers:
            try:
                return int(self.headers["retry-after"])
            except ValueError:
                pass
        if "x-ratelimit-reset" in self.headers:
            try:
                reset_epoch = int(self.headers["x-ratelimit-reset"])
                now_epoch = int(time.time())
                return max(0, reset_epoch - now_epoch)
            except ValueError:
                pass
        return None


# ---------------------------------------------------------------------------
# Base Transport
# ---------------------------------------------------------------------------


class BaseTransport(ABC):
    """Abstract interface for upstream requests."""

    @abstractmethod
    def get_release(self, owner: str, repo: str) -> Response:
        """Fetch latest release for repository."""
        ...

    @abstractmethod
    def get_commit(self, owner: str, repo: str, ref: str = "HEAD") -> Response:
        """Fetch commit SHA and info for repository ref."""
        ...

    @abstractmethod
    def get_content(self, owner: str, repo: str, path: str, ref: str = "HEAD") -> Response:
        """Fetch text content of a file (e.g. SKILL.md) in the repository."""
        ...

    @abstractmethod
    def probe(self, url: str) -> Response:
        """Issue HTTP HEAD / probe to check availability and headers."""
        ...


# ---------------------------------------------------------------------------
# Live HTTP Transport
# ---------------------------------------------------------------------------


class HttpTransport(BaseTransport):
    """Production transport wrapping urllib with header capture."""

    def __init__(self, token: str | None = None, timeout: int = 10) -> None:
        self.token = token or os.environ.get("GH_TOKEN", "")
        self.timeout = timeout

    def _headers(self, accept: str = "application/vnd.github+json") -> dict[str, str]:
        headers = {
            "Accept": accept,
            "User-Agent": "gaia-upstream-watcher/1.0",
        }
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        return headers

    def _extract_headers(self, response_headers: Any) -> dict[str, str]:
        headers: dict[str, str] = {}
        if hasattr(response_headers, "items"):
            for k, v in response_headers.items():
                headers[k.lower()] = str(v)
        return headers

    def get_release(self, owner: str, repo: str) -> Response:
        url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
        req = urllib.request.Request(url, headers=self._headers())
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                headers = self._extract_headers(resp.headers)
                data = json.loads(resp.read().decode("utf-8"))
                return Response(status_code=resp.status, data=data, headers=headers)
        except urllib.error.HTTPError as exc:
            headers = self._extract_headers(exc.headers)
            return Response(status_code=exc.code, headers=headers, error=str(exc.reason))
        except Exception as exc:  # noqa: BLE001
            return Response(status_code=None, error=str(exc))
        finally:
            time.sleep(0.05)

    def get_commit(self, owner: str, repo: str, ref: str = "HEAD") -> Response:
        url = f"https://api.github.com/repos/{owner}/{repo}/commits/{ref}"
        req = urllib.request.Request(url, headers=self._headers())
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                headers = self._extract_headers(resp.headers)
                data = json.loads(resp.read().decode("utf-8"))
                return Response(status_code=resp.status, data=data, headers=headers)
        except urllib.error.HTTPError as exc:
            headers = self._extract_headers(exc.headers)
            return Response(status_code=exc.code, headers=headers, error=str(exc.reason))
        except Exception as exc:  # noqa: BLE001
            return Response(status_code=None, error=str(exc))
        finally:
            time.sleep(0.05)

    def get_content(self, owner: str, repo: str, path: str, ref: str = "HEAD") -> Response:
        url = f"https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{path.lstrip('/')}"
        req = urllib.request.Request(url, headers={"User-Agent": "gaia-upstream-watcher/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                headers = self._extract_headers(resp.headers)
                text = resp.read().decode("utf-8", errors="replace")
                return Response(status_code=resp.status, data=text, headers=headers)
        except urllib.error.HTTPError as exc:
            headers = self._extract_headers(exc.headers)
            return Response(status_code=exc.code, headers=headers, error=str(exc.reason))
        except Exception as exc:  # noqa: BLE001
            return Response(status_code=None, error=str(exc))
        finally:
            time.sleep(0.05)

    def probe(self, url: str) -> Response:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "gaia-upstream-watcher/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                headers = self._extract_headers(resp.headers)
                return Response(status_code=resp.status, headers=headers)
        except urllib.error.HTTPError as exc:
            headers = self._extract_headers(exc.headers)
            return Response(status_code=exc.code, headers=headers, error=str(exc.reason))
        except Exception as exc:  # noqa: BLE001
            return Response(status_code=None, error=str(exc))
        finally:
            time.sleep(0.05)


# ---------------------------------------------------------------------------
# Simulated In-Memory Transport for Deterministic Offline Fixtures
# ---------------------------------------------------------------------------


class SimulatedTransport(BaseTransport):
    """In-memory transport for offline test fixtures. Never hits network."""

    def __init__(self) -> None:
        self.releases: dict[str, Response] = {}
        self.commits: dict[tuple[str, str], Response] = {}
        self.contents: dict[tuple[str, str, str], Response] = {}
        self.probes: dict[str, Response] = {}
        self.recorded_requests: list[dict[str, Any]] = []

    def _key(self, owner: str, repo: str) -> str:
        return f"{owner.lower()}/{repo.lower()}"

    def register_release(
        self,
        owner: str,
        repo: str,
        tag: str,
        published_at: str = "2026-10-26T00:00:00Z",
        html_url: str | None = None,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
    ) -> None:
        key = self._key(owner, repo)
        hdrs = {k.lower(): v for k, v in (headers or {}).items()}
        if status_code == 200:
            data = {
                "tag_name": tag,
                "published_at": published_at,
                "html_url": html_url or f"https://github.com/{owner}/{repo}/releases/tag/{tag}",
            }
            self.releases[key] = Response(status_code=200, data=data, headers=hdrs)
        else:
            self.releases[key] = Response(status_code=status_code, headers=hdrs, error=f"HTTP {status_code}")

    def register_commit(
        self,
        owner: str,
        repo: str,
        sha: str,
        ref: str = "HEAD",
        status_code: int = 200,
        headers: dict[str, str] | None = None,
    ) -> None:
        key = (self._key(owner, repo), ref)
        hdrs = {k.lower(): v for k, v in (headers or {}).items()}
        if status_code == 200:
            data = {"sha": sha}
            self.commits[key] = Response(status_code=200, data=data, headers=hdrs)
        else:
            self.commits[key] = Response(status_code=status_code, headers=hdrs, error=f"HTTP {status_code}")

    def register_content(
        self,
        owner: str,
        repo: str,
        path: str,
        content: str,
        ref: str = "HEAD",
        status_code: int = 200,
        headers: dict[str, str] | None = None,
    ) -> None:
        key = (self._key(owner, repo), path.lstrip("/"), ref)
        hdrs = {k.lower(): v for k, v in (headers or {}).items()}
        if status_code == 200:
            self.contents[key] = Response(status_code=200, data=content, headers=hdrs)
        else:
            self.contents[key] = Response(status_code=status_code, headers=hdrs, error=f"HTTP {status_code}")

    def register_probe(
        self,
        url: str,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
    ) -> None:
        hdrs = {k.lower(): v for k, v in (headers or {}).items()}
        self.probes[url.strip()] = Response(status_code=status_code, headers=hdrs)

    def get_release(self, owner: str, repo: str) -> Response:
        key = self._key(owner, repo)
        self.recorded_requests.append({"action": "get_release", "owner": owner, "repo": repo})
        if key in self.releases:
            return self.releases[key]
        return Response(status_code=404, error=f"Release not found for {key}")

    def get_commit(self, owner: str, repo: str, ref: str = "HEAD") -> Response:
        key = (self._key(owner, repo), ref)
        self.recorded_requests.append({"action": "get_commit", "owner": owner, "repo": repo, "ref": ref})
        if key in self.commits:
            return self.commits[key]
        return Response(status_code=404, error=f"Commit not found for {key}")

    def get_content(self, owner: str, repo: str, path: str, ref: str = "HEAD") -> Response:
        key = (self._key(owner, repo), path.lstrip("/"), ref)
        self.recorded_requests.append({"action": "get_content", "owner": owner, "repo": repo, "path": path, "ref": ref})
        if key in self.contents:
            return self.contents[key]
        return Response(status_code=404, error=f"Content not found for {key}")

    def probe(self, url: str) -> Response:
        clean_url = url.strip()
        self.recorded_requests.append({"action": "probe", "url": clean_url})
        if clean_url in self.probes:
            return self.probes[clean_url]
        return Response(status_code=200, headers={})
