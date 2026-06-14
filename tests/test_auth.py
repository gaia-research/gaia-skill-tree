"""Complete CLI test suite for GitHub Sign-In (PRD #155 — `gaia login`).

Covers every layer of `gaia_cli/auth.py` plus the `login` / `logout` / `whoami`
command surface in `main.py`, with zero network and zero real sleeping:

  * client_id resolution + the "not configured" guard
  * `http_request` parsing (fake urlopen, incl. the HTTPError/4xx path)
  * the device flow: request_device_code, poll_for_token (pending/slow_down/
    expired/denied/timeout/max_attempts), fetch_user, verify_repo_ownership,
    revoke_token
  * TokenStore: file roundtrip + chmod, env override precedence, keyring backend
    (fake), delete semantics
  * command integration: login happy-path / unconfigured / denied / timed-out /
    --no-store / --repo, logout (+revoke), and the whoami GitHub status line

Network is injected via `gaia_cli.auth.http_request`; tests monkeypatch it.
Sleeping is injected into `poll_for_token`. Nothing here opens a socket.
"""

from __future__ import annotations

import io
import json
import os
import stat
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from helpers import strip_ansi
from gaia_cli import auth
from gaia_cli.auth import (
    AuthDenied,
    AuthError,
    AuthTimeout,
    Credentials,
    DeviceCode,
    TokenStore,
)


# ---------------------------------------------------------------------------
# Determinism: scrub auth-relevant env so a CI GITHUB_TOKEN can't leak in.
# (GAIA_HOME is already isolated to tmp by the root conftest.)
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clean_auth_env(monkeypatch):
    for var in (auth.CLIENT_ID_ENV, *auth.TOKEN_ENV_VARS):
        monkeypatch.delenv(var, raising=False)
    # Default: no real keyring during tests unless a test opts in.
    monkeypatch.setattr(auth, "_try_keyring", lambda: None)


# ---------------------------------------------------------------------------
# A scripted fake for http_request.
# ---------------------------------------------------------------------------

class FakeHTTP:
    """Records calls and returns scripted ``(status, payload)`` responses.

    Match rules, in order: an exact route registered via ``route(method, frag)``
    (substring match on URL), else a FIFO queue for repeated POSTs to the token
    endpoint via ``queue_token(...)``.
    """

    def __init__(self):
        self.calls = []
        self._routes = []          # (method, frag, (status, payload))
        self._token_queue = []     # (status, payload) consumed in order

    def route(self, method, frag, status, payload):
        self._routes.append((method, frag, (status, payload)))
        return self

    def queue_token(self, status, payload):
        self._token_queue.append((status, payload))
        return self

    def __call__(self, method, url, *, headers=None, data=None, token=None):
        self.calls.append(SimpleNamespace(
            method=method, url=url, headers=headers, data=data, token=token
        ))
        for m, frag, resp in self._routes:
            if m == method and frag in url:
                return resp
        if "oauth/access_token" in url and self._token_queue:
            return self._token_queue.pop(0)
        raise AssertionError(f"unexpected HTTP call: {method} {url}")

    def install(self, monkeypatch):
        monkeypatch.setattr(auth, "http_request", self)
        return self


@pytest.fixture
def http(monkeypatch):
    return FakeHTTP().install(monkeypatch)


# ===========================================================================
# client_id resolution
# ===========================================================================

class TestClientId:
    def test_placeholder_when_nothing_set(self):
        assert auth.resolve_client_id() == auth.PLACEHOLDER_CLIENT_ID
        assert auth.is_configured(auth.resolve_client_id()) is False

    def test_env_wins(self, monkeypatch):
        monkeypatch.setenv(auth.CLIENT_ID_ENV, "Ov23liREALID")
        assert auth.resolve_client_id({"oauthClientId": "from-config"}) == "Ov23liREALID"
        assert auth.is_configured("Ov23liREALID") is True

    def test_config_fallback(self):
        assert auth.resolve_client_id({"oauthClientId": "cfg-id"}) == "cfg-id"
        assert auth.resolve_client_id({"clientId": "cfg-id2"}) == "cfg-id2"

    def test_blank_env_is_ignored(self, monkeypatch):
        monkeypatch.setenv(auth.CLIENT_ID_ENV, "   ")
        assert auth.resolve_client_id({"oauthClientId": "cfg"}) == "cfg"

    def test_is_configured_rejects_empty(self):
        assert auth.is_configured("") is False


# ===========================================================================
# http_request — the one real network function, tested with a fake urlopen.
# ===========================================================================

class _FakeResp:
    def __init__(self, body, code=200):
        self._body = body.encode("utf-8")
        self._code = code

    def read(self):
        return self._body

    def getcode(self):
        return self._code

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class TestHttpRequest:
    def test_form_encodes_and_parses_json(self, monkeypatch):
        captured = {}

        def fake_urlopen(req):
            captured["url"] = req.full_url
            captured["method"] = req.method
            captured["data"] = req.data
            captured["headers"] = req.headers
            return _FakeResp(json.dumps({"ok": True}))

        monkeypatch.setattr(auth.urllib.request, "urlopen", fake_urlopen)
        status, payload = auth.http_request(
            "POST", "https://example.test/x", data={"a": "b c"}, token="tok"
        )
        assert (status, payload) == (200, {"ok": True})
        assert captured["data"] == b"a=b+c"
        # Header keys are capitalized by urllib's Request.
        assert captured["headers"]["Authorization"] == "Bearer tok"
        assert captured["headers"]["Accept"] == "application/json"

    def test_httperror_body_is_parsed(self, monkeypatch):
        err = auth.urllib.error.HTTPError(
            url="u", code=422, msg="x", hdrs=None,
            fp=io.BytesIO(json.dumps({"error": "bad"}).encode()),
        )

        def boom(req):
            raise err

        monkeypatch.setattr(auth.urllib.request, "urlopen", boom)
        status, payload = auth.http_request("POST", "https://example.test/x")
        assert status == 422
        assert payload == {"error": "bad"}

    def test_empty_body_returns_empty_dict(self, monkeypatch):
        monkeypatch.setattr(
            auth.urllib.request, "urlopen", lambda req: _FakeResp("", code=204)
        )
        assert auth.http_request("DELETE", "https://example.test/x") == (204, {})


# ===========================================================================
# Device flow
# ===========================================================================

class TestDeviceCode:
    def test_from_response_defaults(self):
        dc = DeviceCode.from_response({
            "device_code": "dc", "user_code": "AAAA-BBBB",
            "verification_uri": "https://github.com/login/device",
        })
        assert dc.user_code == "AAAA-BBBB"
        assert dc.interval == 5 and dc.expires_in == 900

    def test_from_response_missing_field(self):
        with pytest.raises(AuthError):
            DeviceCode.from_response({"user_code": "x"})

    def test_request_device_code(self, http):
        http.route("POST", "device/code", 200, {
            "device_code": "DC", "user_code": "WXYZ-1234",
            "verification_uri": "https://github.com/login/device",
            "interval": 7,
        })
        dc = auth.request_device_code("cid")
        assert dc.device_code == "DC" and dc.interval == 7
        assert http.calls[0].data == {"client_id": "cid", "scope": ""}

    def test_request_device_code_error(self, http):
        http.route("POST", "device/code", 404, {"error": "Not Found"})
        with pytest.raises(AuthError):
            auth.request_device_code("cid")


def _device(interval=1, expires=900):
    return DeviceCode(
        device_code="DC", user_code="U", verification_uri="uri",
        expires_in=expires, interval=interval,
    )


_NOOP = lambda *_a, **_k: None


class TestPollForToken:
    def test_pending_then_success(self, http):
        http.queue_token(200, {"error": "authorization_pending"})
        http.queue_token(200, {"access_token": "gho_TOKEN"})
        token = auth.poll_for_token("cid", _device(), sleep=_NOOP)
        assert token == "gho_TOKEN"
        assert len(http.calls) == 2

    def test_slow_down_bumps_interval(self, http):
        seen = []
        http.queue_token(200, {"error": "slow_down", "interval": 9})
        http.queue_token(200, {"access_token": "T"})
        token = auth.poll_for_token("cid", _device(interval=1), sleep=seen.append)
        assert token == "T"
        # First sleep at the original interval, second at the bumped one.
        assert seen == [1, 9]

    def test_expired_token_raises_timeout(self, http):
        http.queue_token(200, {"error": "expired_token"})
        with pytest.raises(AuthTimeout):
            auth.poll_for_token("cid", _device(), sleep=_NOOP)

    def test_access_denied(self, http):
        http.queue_token(200, {"error": "access_denied"})
        with pytest.raises(AuthDenied):
            auth.poll_for_token("cid", _device(), sleep=_NOOP)

    def test_unknown_error(self, http):
        http.queue_token(200, {"error": "weird", "error_description": "nope"})
        with pytest.raises(AuthError):
            auth.poll_for_token("cid", _device(), sleep=_NOOP)

    def test_deadline_exceeded(self, http):
        # now() jumps past the deadline on the first check → timeout, no HTTP.
        ticks = iter([0.0, 10_000.0, 10_000.0])
        with pytest.raises(AuthTimeout):
            auth.poll_for_token("cid", _device(expires=1),
                                sleep=_NOOP, now=lambda: next(ticks))
        assert http.calls == []

    def test_max_attempts(self, http):
        with pytest.raises(AuthTimeout):
            auth.poll_for_token("cid", _device(), sleep=_NOOP, max_attempts=0)


# ===========================================================================
# Identity + ownership
# ===========================================================================

class TestIdentity:
    def test_fetch_user(self, http):
        http.route("GET", "/user", 200, {"login": "marco", "id": 7})
        assert auth.verify_handle("tok") == "marco"
        assert http.calls[0].token == "tok"

    def test_fetch_user_error(self, http):
        http.route("GET", "/user", 401, {"message": "Bad credentials"})
        with pytest.raises(AuthError):
            auth.fetch_user("tok")

    def test_ownership_owner_match(self, http):
        http.route("GET", "/user", 200, {"login": "marco"})
        http.route("GET", "/repos/marco/repo", 200, {"owner": {"login": "marco"}})
        assert auth.verify_repo_ownership("tok", "marco", "repo") is True

    def test_ownership_case_insensitive(self, http):
        http.route("GET", "/user", 200, {"login": "Marco"})
        http.route("GET", "/repos/marco/repo", 200, {"owner": {"login": "marco"}})
        assert auth.verify_repo_ownership("tok", "marco", "repo") is True

    def test_ownership_admin_permission(self, http):
        http.route("GET", "/user", 200, {"login": "marco"})
        http.route("GET", "/repos/org/repo", 200,
                   {"owner": {"login": "org"}, "permissions": {"admin": True}})
        assert auth.verify_repo_ownership("tok", "org", "repo") is True

    def test_ownership_mismatch(self, http):
        http.route("GET", "/user", 200, {"login": "marco"})
        http.route("GET", "/repos/other/repo", 200,
                   {"owner": {"login": "other"}, "permissions": {"admin": False}})
        assert auth.verify_repo_ownership("tok", "other", "repo") is False

    def test_ownership_404(self, http):
        http.route("GET", "/user", 200, {"login": "marco"})
        http.route("GET", "/repos/x/y", 404, {"message": "Not Found"})
        assert auth.verify_repo_ownership("tok", "x", "y") is False


class TestRevoke:
    def test_revoke_success(self, http):
        http.route("DELETE", "/applications/", 204, {})
        assert auth.revoke_token("real-id", "tok") is True

    def test_revoke_unconfigured_noop(self, http):
        assert auth.revoke_token(auth.PLACEHOLDER_CLIENT_ID, "tok") is False
        assert http.calls == []

    def test_revoke_swallows_errors(self, monkeypatch):
        def boom(*a, **k):
            raise RuntimeError("network down")
        monkeypatch.setattr(auth, "http_request", boom)
        assert auth.revoke_token("real-id", "tok") is False


# ===========================================================================
# TokenStore
# ===========================================================================

class TestTokenStore:
    def test_file_roundtrip_and_chmod(self):
        store = TokenStore()
        backend = store.save(Credentials(token="gho_X", login="marco"))
        assert backend == "file"
        loaded = store.load()
        assert loaded.token == "gho_X" and loaded.login == "marco"
        assert loaded.source == "store"
        # chmod 600 (skip the assertion on platforms without POSIX perms).
        if os.name == "posix":
            mode = stat.S_IMODE(os.stat(store._hosts_path).st_mode)
            assert mode == 0o600

    def test_load_none_when_absent(self):
        assert TokenStore().load() is None

    def test_env_override_wins(self, monkeypatch):
        store = TokenStore()
        store.save(Credentials(token="stored", login="marco"))
        monkeypatch.setenv("GAIA_AUTH_TOKEN", "env-token")
        loaded = store.load()
        assert loaded.token == "env-token"
        assert loaded.source == "env"
        assert loaded.login == "marco"  # handle still surfaced from the file

    def test_delete(self):
        store = TokenStore()
        store.save(Credentials(token="t", login="m"))
        assert store.delete() is True
        assert store.load() is None
        assert store.delete() is False  # nothing left to clear

    def test_public_dict_hides_token(self):
        creds = Credentials(token="secret", login="marco")
        assert "secret" not in json.dumps(creds.public_dict())
        assert creds.public_dict()["login"] == "marco"

    def test_corrupt_file_is_ignored(self):
        store = TokenStore()
        os.makedirs(os.path.dirname(store._hosts_path), exist_ok=True)
        with open(store._hosts_path, "w") as fh:
            fh.write("{ not json")
        assert store.load() is None


class _FakeKeyring:
    """Minimal in-memory keyring stand-in."""

    def __init__(self):
        self._store = {}

    def get_keyring(self):
        return self

    def set_password(self, service, user, pw):
        self._store[(service, user)] = pw

    def get_password(self, service, user):
        return self._store.get((service, user))

    def delete_password(self, service, user):
        if (service, user) not in self._store:
            raise KeyError("no such password")
        del self._store[(service, user)]


class TestKeyringBackend:
    def test_save_uses_keyring_and_keeps_token_out_of_file(self, monkeypatch):
        fake = _FakeKeyring()
        monkeypatch.setattr(auth, "_try_keyring", lambda: fake)
        store = TokenStore()
        backend = store.save(Credentials(token="kr-token", login="marco"))
        assert backend == "keyring"
        # The chmod-600 file must hold metadata but NOT the token.
        with open(store._hosts_path) as fh:
            on_disk = json.load(fh)
        assert "token" not in on_disk["github.com"]
        assert on_disk["github.com"]["login"] == "marco"
        # load() pulls the token back out of the keyring.
        assert store.load().token == "kr-token"

    def test_delete_clears_keyring(self, monkeypatch):
        fake = _FakeKeyring()
        monkeypatch.setattr(auth, "_try_keyring", lambda: fake)
        store = TokenStore()
        store.save(Credentials(token="kr-token", login="marco"))
        assert store.delete() is True
        assert store.load() is None


# ===========================================================================
# Command integration — login / logout / whoami
# ===========================================================================

def _capture(capsys):
    out = capsys.readouterr()
    return strip_ansi(out.out), strip_ansi(out.err)


class TestLoginCommand:
    def _args(self, **kw):
        base = {"repo": None, "no_store": False}
        base.update(kw)
        return SimpleNamespace(**base)

    def test_unconfigured_guard(self, capsys):
        with pytest.raises(SystemExit) as exc:
            from gaia_cli.main import login_command
            login_command(self._args())
        assert exc.value.code == 1
        _, err = _capture(capsys)
        assert "isn't configured yet" in err
        assert auth.CLIENT_ID_ENV in err

    def test_happy_path_stores_token(self, monkeypatch, capsys):
        monkeypatch.setenv(auth.CLIENT_ID_ENV, "real-id")
        monkeypatch.setattr(auth, "request_device_code",
                            lambda cid, **k: _device())
        monkeypatch.setattr(auth, "poll_for_token",
                            lambda cid, dev, **k: "gho_TOKEN")
        monkeypatch.setattr(auth, "fetch_user",
                            lambda tok: {"login": "marco"})
        from gaia_cli.main import login_command
        login_command(self._args())
        out, _ = _capture(capsys)
        assert "Signed in as marco" in out
        # Token persisted and re-loadable.
        assert TokenStore().load().token == "gho_TOKEN"

    def test_no_store_skips_persistence(self, monkeypatch, capsys):
        monkeypatch.setenv(auth.CLIENT_ID_ENV, "real-id")
        monkeypatch.setattr(auth, "request_device_code", lambda cid, **k: _device())
        monkeypatch.setattr(auth, "poll_for_token", lambda cid, dev, **k: "T")
        monkeypatch.setattr(auth, "fetch_user", lambda tok: {"login": "marco"})
        from gaia_cli.main import login_command
        login_command(self._args(no_store=True))
        out, _ = _capture(capsys)
        assert "not stored" in out
        assert TokenStore().load() is None

    def test_repo_ownership_reported(self, monkeypatch, capsys):
        monkeypatch.setenv(auth.CLIENT_ID_ENV, "real-id")
        monkeypatch.setattr(auth, "request_device_code", lambda cid, **k: _device())
        monkeypatch.setattr(auth, "poll_for_token", lambda cid, dev, **k: "T")
        monkeypatch.setattr(auth, "fetch_user", lambda tok: {"login": "marco"})
        monkeypatch.setattr(auth, "verify_repo_ownership",
                            lambda tok, o, r: True)
        from gaia_cli.main import login_command
        login_command(self._args(repo="marco/gaia-skill-tree"))
        out, _ = _capture(capsys)
        assert "Ownership of marco/gaia-skill-tree: ✓ verified" in out

    def test_denied(self, monkeypatch, capsys):
        monkeypatch.setenv(auth.CLIENT_ID_ENV, "real-id")
        monkeypatch.setattr(auth, "request_device_code", lambda cid, **k: _device())
        def deny(*a, **k):
            raise AuthDenied("nope")
        monkeypatch.setattr(auth, "poll_for_token", deny)
        from gaia_cli.main import login_command
        with pytest.raises(SystemExit) as exc:
            login_command(self._args())
        assert exc.value.code == 1
        _, err = _capture(capsys)
        assert "denied" in err.lower()

    def test_timeout(self, monkeypatch, capsys):
        monkeypatch.setenv(auth.CLIENT_ID_ENV, "real-id")
        monkeypatch.setattr(auth, "request_device_code", lambda cid, **k: _device())
        def timeout(*a, **k):
            raise AuthTimeout("expired")
        monkeypatch.setattr(auth, "poll_for_token", timeout)
        from gaia_cli.main import login_command
        with pytest.raises(SystemExit) as exc:
            login_command(self._args())
        assert exc.value.code == 1
        _, err = _capture(capsys)
        assert "timed out" in err.lower()


class TestLogoutCommand:
    def test_not_signed_in(self, capsys):
        from gaia_cli.main import logout_command
        logout_command(SimpleNamespace(no_revoke=False))
        out, _ = _capture(capsys)
        assert "Not signed in" in out

    def test_logout_revokes_and_clears(self, monkeypatch, capsys):
        TokenStore().save(Credentials(token="T", login="marco"))
        monkeypatch.setenv(auth.CLIENT_ID_ENV, "real-id")
        revoked = {}
        monkeypatch.setattr(auth, "revoke_token",
                            lambda cid, tok: revoked.setdefault("hit", True) or True)
        from gaia_cli.main import logout_command
        logout_command(SimpleNamespace(no_revoke=False))
        out, _ = _capture(capsys)
        assert "Signed out (marco)" in out
        assert "revoked" in out
        assert revoked.get("hit") is True
        assert TokenStore().load() is None

    def test_logout_no_revoke(self, monkeypatch, capsys):
        TokenStore().save(Credentials(token="T", login="marco"))
        called = {}
        monkeypatch.setattr(auth, "revoke_token",
                            lambda *a: called.setdefault("hit", True))
        from gaia_cli.main import logout_command
        logout_command(SimpleNamespace(no_revoke=True))
        out, _ = _capture(capsys)
        assert "Signed out" in out
        assert "hit" not in called  # revoke skipped
        assert TokenStore().load() is None


class TestWhoamiGitHubLine:
    def _args(self):
        return SimpleNamespace(registry=".")

    def test_not_signed_in(self, capsys):
        from gaia_cli.main import whoami_command
        whoami_command(self._args())
        out, _ = _capture(capsys)
        assert "GitHub:    not signed in" in out

    def test_signed_in(self, capsys):
        TokenStore().save(Credentials(token="T", login="marco"))
        from gaia_cli.main import whoami_command
        whoami_command(self._args())
        out, _ = _capture(capsys)
        assert "signed in as marco" in out

    def test_env_session_note(self, monkeypatch, capsys):
        TokenStore().save(Credentials(token="T", login="marco"))
        monkeypatch.setenv("GAIA_AUTH_TOKEN", "env-token")
        from gaia_cli.main import whoami_command
        whoami_command(self._args())
        out, _ = _capture(capsys)
        assert "session token via env" in out


# ===========================================================================
# argparse wiring — login/logout reachable and flags parse
# ===========================================================================

class TestParserWiring:
    def test_commands_registered(self):
        from gaia_cli.main import PUBLIC_COMMANDS, get_parser
        assert "login" in PUBLIC_COMMANDS and "logout" in PUBLIC_COMMANDS
        parser, _ = get_parser()
        ns = parser.parse_args(["login", "--repo", "a/b", "--no-store"])
        assert ns.command == "login" and ns.repo == "a/b" and ns.no_store is True
        ns2 = parser.parse_args(["logout", "--no-revoke"])
        assert ns2.command == "logout" and ns2.no_revoke is True
