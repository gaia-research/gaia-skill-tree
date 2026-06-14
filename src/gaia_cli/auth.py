"""GitHub Sign-In for the Gaia CLI — device flow (PRD #155).

Implements the MVP from ``GAIA_AUTH_PRD.md``: a ``gh auth login``-style device
flow that verifies you are the GitHub account you claim to be, with read-only
scope and persistent token storage.  No server, no client secret.

Design notes for testers (see ``tests/test_auth.py``):

* **Network is injected, never hard-wired.**  Every GitHub call goes through the
  module-level ``http_request`` function.  Tests monkeypatch
  ``gaia_cli.auth.http_request`` to return canned responses — nothing in this
  module touches the network on its own once that is patched.
* **Sleeping is injected too.**  ``poll_for_token`` takes a ``sleep`` callable
  (defaults to ``time.sleep``) so polling tests run instantly.
* **Token storage degrades gracefully.**  ``keyring`` is an *optional* backend.
  When it is missing or unusable we fall back to a ``chmod 600`` JSON file under
  ``GAIA_HOME`` (gh's hosts-file pattern).  The suite therefore runs green on a
  machine with no keyring installed.

The OAuth ``client_id`` is public (it is not the secret — the secret is unused
in the MVP and stored nowhere).  It resolves env → config → a baked-in
placeholder; ``gaia login`` refuses to talk to GitHub while the placeholder is
still in force, with a friendly "not configured yet" message.
"""

from __future__ import annotations

import json
import os
import stat
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Callable, Optional


# ---------------------------------------------------------------------------
# Endpoints (overridable for tests via monkeypatch, though tests normally just
# patch http_request and ignore the URL).
# ---------------------------------------------------------------------------

DEVICE_CODE_URL = "https://github.com/login/device/code"
ACCESS_TOKEN_URL = "https://github.com/login/oauth/access_token"
USER_API_URL = "https://api.github.com/user"
API_ROOT = "https://api.github.com"

# Public OAuth app client_id.  Resolution order: env > config > this placeholder.
# Marco registers the real app (Settings → Developer settings → OAuth Apps,
# Device Flow enabled) and drops the id in via GAIA_OAUTH_CLIENT_ID or config.
CLIENT_ID_ENV = "GAIA_OAUTH_CLIENT_ID"
PLACEHOLDER_CLIENT_ID = "Ov23liGAIAPLACEHOLDER000"

# Per-session token override (CI / ephemeral). Mirrors gh's GH_TOKEN / GITHUB_TOKEN.
TOKEN_ENV_VARS = ("GAIA_AUTH_TOKEN", "GAIA_TOKEN", "GITHUB_TOKEN", "GH_TOKEN")

# Read-only scope.  Empty string == identity + public read, by construction.
DEFAULT_SCOPE = ""

_USER_AGENT = "gaia-cli"


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class AuthError(Exception):
    """Base class for sign-in failures."""


class AuthNotConfigured(AuthError):
    """Raised when no real OAuth client_id is configured (placeholder in force)."""


class AuthTimeout(AuthError):
    """Raised when the device code expires before the user authorizes."""


class AuthDenied(AuthError):
    """Raised when the user explicitly denies the authorization request."""


# ---------------------------------------------------------------------------
# client_id resolution
# ---------------------------------------------------------------------------

def resolve_client_id(config: Optional[dict] = None) -> str:
    """Return the OAuth client_id: env > config > placeholder.

    ``config`` is an optional already-loaded ``.gaia/config.toml`` mapping; the
    ``oauthClientId`` (or ``clientId``) key is consulted when the env var is
    unset.
    """
    env = os.environ.get(CLIENT_ID_ENV, "").strip()
    if env:
        return env
    if config:
        for key in ("oauthClientId", "clientId", "oauth_client_id"):
            val = config.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
    return PLACEHOLDER_CLIENT_ID


def is_configured(client_id: str) -> bool:
    """True when *client_id* is a real id (non-empty and not the placeholder)."""
    return bool(client_id) and client_id != PLACEHOLDER_CLIENT_ID


# ---------------------------------------------------------------------------
# HTTP — the single injection point.  Tests monkeypatch this.
# ---------------------------------------------------------------------------

def http_request(
    method: str,
    url: str,
    *,
    headers: Optional[dict] = None,
    data: Optional[dict] = None,
    token: Optional[str] = None,
) -> tuple[int, dict]:
    """Perform an HTTP request and return ``(status_code, parsed_json)``.

    ``data`` is form-encoded (GitHub's OAuth endpoints expect that); we always
    send ``Accept: application/json`` so the OAuth endpoints reply with JSON
    rather than a urlencoded body.  A bearer *token* adds the auth header.

    Returns ``(status, {})`` when the body is empty (e.g. 204 from a revoke).
    This is the ONLY function that opens a socket — patch it in tests.
    """
    req_headers = {
        "Accept": "application/json",
        "User-Agent": _USER_AGENT,
    }
    if headers:
        req_headers.update(headers)
    if token:
        req_headers["Authorization"] = f"Bearer {token}"

    body = None
    if data is not None:
        body = urllib.parse.urlencode(data).encode("utf-8")

    req = urllib.request.Request(url, data=body, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:  # noqa: S310 (URL is a constant GitHub endpoint)
            raw = resp.read().decode("utf-8") or ""
            status = resp.getcode()
    except urllib.error.HTTPError as exc:  # 4xx/5xx still carry useful JSON
        raw = exc.read().decode("utf-8") if exc.fp else ""
        status = exc.code

    parsed: dict = {}
    if raw.strip():
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {"raw": raw}
    return status, parsed


# ---------------------------------------------------------------------------
# Device flow
# ---------------------------------------------------------------------------

@dataclass
class DeviceCode:
    """The device-flow handshake payload returned by GitHub."""

    device_code: str
    user_code: str
    verification_uri: str
    expires_in: int = 900
    interval: int = 5

    @classmethod
    def from_response(cls, payload: dict) -> "DeviceCode":
        try:
            return cls(
                device_code=payload["device_code"],
                user_code=payload["user_code"],
                verification_uri=payload.get("verification_uri")
                or payload.get("verification_url")
                or "https://github.com/login/device",
                expires_in=int(payload.get("expires_in", 900)),
                interval=int(payload.get("interval", 5)),
            )
        except KeyError as exc:
            raise AuthError(f"Malformed device-code response (missing {exc}).") from exc


def request_device_code(client_id: str, *, scope: str = DEFAULT_SCOPE) -> DeviceCode:
    """Start the device flow: ask GitHub for a user code + verification URL."""
    status, payload = http_request(
        "POST",
        DEVICE_CODE_URL,
        data={"client_id": client_id, "scope": scope},
    )
    if status != 200 or "device_code" not in payload:
        msg = payload.get("error_description") or payload.get("error") or f"HTTP {status}"
        raise AuthError(f"Could not start device flow: {msg}")
    return DeviceCode.from_response(payload)


def poll_for_token(
    client_id: str,
    device: DeviceCode,
    *,
    sleep: Callable[[float], None] = time.sleep,
    now: Callable[[], float] = time.monotonic,
    max_attempts: Optional[int] = None,
) -> str:
    """Poll the token endpoint until the user authorizes; return the token.

    Honours GitHub's ``authorization_pending`` / ``slow_down`` backoff protocol
    and gives up on ``expired_token`` (→ :class:`AuthTimeout`) or
    ``access_denied`` (→ :class:`AuthDenied`).  ``sleep`` and ``now`` are
    injected so tests drive the loop deterministically with zero real delay.
    """
    interval = max(device.interval, 1)
    deadline = now() + device.expires_in
    attempts = 0
    while True:
        if max_attempts is not None and attempts >= max_attempts:
            raise AuthTimeout("Gave up waiting for authorization.")
        if now() >= deadline:
            raise AuthTimeout("The device code expired before you authorized it.")
        attempts += 1
        sleep(interval)
        status, payload = http_request(
            "POST",
            ACCESS_TOKEN_URL,
            data={
                "client_id": client_id,
                "device_code": device.device_code,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            },
        )
        token = payload.get("access_token")
        if token:
            return token
        error = payload.get("error")
        if error == "authorization_pending":
            continue
        if error == "slow_down":
            # GitHub asks us to back off; honour the new interval if provided.
            interval = int(payload.get("interval", interval + 5))
            continue
        if error == "expired_token":
            raise AuthTimeout("The device code expired before you authorized it.")
        if error == "access_denied":
            raise AuthDenied("Authorization was denied.")
        # Unknown / transport error.
        msg = payload.get("error_description") or error or f"HTTP {status}"
        raise AuthError(f"Token exchange failed: {msg}")


# ---------------------------------------------------------------------------
# Identity + ownership
# ---------------------------------------------------------------------------

def fetch_user(token: str) -> dict:
    """Return the authenticated user's profile (``GET /user``)."""
    status, payload = http_request("GET", USER_API_URL, token=token)
    if status != 200 or "login" not in payload:
        msg = payload.get("message") or f"HTTP {status}"
        raise AuthError(f"Could not verify identity: {msg}")
    return payload


def verify_handle(token: str) -> str:
    """Return just the verified GitHub login for *token*."""
    return fetch_user(token)["login"]


def verify_repo_ownership(token: str, owner: str, repo: str) -> bool:
    """Return True if the token holder owns / admins ``owner/repo``.

    Ownership is judged by the repo's ``owner.login`` matching the verified
    handle, or by an admin ``permissions`` grant on the repo (covers org repos
    the user administers).  A 404 (private/nonexistent to this token) is False.
    """
    verified = verify_handle(token)
    status, payload = http_request(
        "GET", f"{API_ROOT}/repos/{owner}/{repo}", token=token
    )
    if status != 200:
        return False
    repo_owner = (payload.get("owner") or {}).get("login", "")
    if repo_owner and repo_owner.lower() == verified.lower():
        return True
    perms = payload.get("permissions") or {}
    return bool(perms.get("admin"))




# ---------------------------------------------------------------------------
# Token storage — keyring (optional) → chmod-600 file → env override
# ---------------------------------------------------------------------------

_KEYRING_SERVICE = "gaia-cli"
_KEYRING_USERNAME = "github"


def _gaia_home() -> str:
    home = os.environ.get("GAIA_HOME")
    if home:
        return os.path.expanduser(home)
    return os.path.join(os.path.expanduser("~"), ".gaia")


def _hosts_path() -> str:
    """Path to the chmod-600 fallback credentials file (gh's hosts pattern)."""
    return os.path.join(_gaia_home(), "hosts.json")


def _try_keyring():
    """Return the keyring module if importable AND usable, else None."""
    try:
        import keyring  # type: ignore
        # Touch the backend so a misconfigured/headless keyring fails fast here
        # rather than mid-save.
        keyring.get_keyring()
        return keyring
    except Exception:
        return None


@dataclass
class Credentials:
    """A stored sign-in: the token plus the verified handle and metadata."""

    token: str
    login: str
    scope: str = DEFAULT_SCOPE
    source: str = "store"  # store | env

    def public_dict(self) -> dict:
        """A dict safe to print — never includes the token."""
        return {"login": self.login, "scope": self.scope, "source": self.source}


class TokenStore:
    """Persist the GitHub token across sessions.

    Backend order on save/load:
      1. ``$GAIA_AUTH_TOKEN`` (and friends) — per-session override, read-only,
         wins on ``load`` so CI never has to write anything.
      2. OS keyring (if the ``keyring`` package is importable and usable).
      3. A ``chmod 600`` JSON file under ``GAIA_HOME`` (always available).

    The login handle is always mirrored into the file (keyring stores secrets,
    not metadata), so ``whoami`` can show the handle even on a keyring machine.
    """

    def __init__(self, hosts_path: Optional[str] = None):
        self._hosts_path = hosts_path or _hosts_path()

    # -- env override -------------------------------------------------------
    @staticmethod
    def _env_token() -> Optional[str]:
        for var in TOKEN_ENV_VARS:
            val = os.environ.get(var, "").strip()
            if val:
                return val
        return None

    # -- file backend -------------------------------------------------------
    def _read_file(self) -> dict:
        try:
            with open(self._hosts_path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _write_file(self, data: dict) -> None:
        os.makedirs(os.path.dirname(self._hosts_path), exist_ok=True)
        # Write then chmod 600 so the token is never world-readable, even briefly.
        with open(self._hosts_path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        try:
            os.chmod(self._hosts_path, stat.S_IRUSR | stat.S_IWUSR)
        except OSError:
            pass  # Windows / odd filesystems — best effort.

    # -- public API ---------------------------------------------------------
    def save(self, creds: Credentials) -> str:
        """Persist *creds*; return the backend used ('keyring' or 'file')."""
        backend = "file"
        kr = _try_keyring()
        meta = {"login": creds.login, "scope": creds.scope}
        if kr is not None:
            try:
                kr.set_password(_KEYRING_SERVICE, _KEYRING_USERNAME, creds.token)
                backend = "keyring"
            except Exception:
                backend = "file"
        file_data = self._read_file()
        file_data["github.com"] = {
            **meta,
            "backend": backend,
            # Only persist the token in the file when keyring is NOT holding it.
            **({"token": creds.token} if backend == "file" else {}),
        }
        self._write_file(file_data)
        return backend

    def load(self) -> Optional[Credentials]:
        """Return stored credentials, or None if not signed in.

        Env override wins (source='env'); then keyring+file metadata; then a
        token living in the file itself.
        """
        env_token = self._env_token()
        file_data = self._read_file().get("github.com", {})
        if env_token:
            return Credentials(
                token=env_token,
                login=file_data.get("login", ""),
                scope=file_data.get("scope", DEFAULT_SCOPE),
                source="env",
            )
        if not file_data:
            return None
        backend = file_data.get("backend", "file")
        token = file_data.get("token")
        if backend == "keyring":
            kr = _try_keyring()
            if kr is not None:
                try:
                    token = kr.get_password(_KEYRING_SERVICE, _KEYRING_USERNAME)
                except Exception:
                    token = None
        if not token:
            return None
        return Credentials(
            token=token,
            login=file_data.get("login", ""),
            scope=file_data.get("scope", DEFAULT_SCOPE),
            source="store",
        )

    def delete(self) -> bool:
        """Remove stored credentials from both backends. True if anything cleared."""
        cleared = False
        kr = _try_keyring()
        if kr is not None:
            try:
                kr.delete_password(_KEYRING_SERVICE, _KEYRING_USERNAME)
                cleared = True
            except Exception:
                pass
        file_data = self._read_file()
        if "github.com" in file_data:
            del file_data["github.com"]
            self._write_file(file_data)
            cleared = True
        return cleared
