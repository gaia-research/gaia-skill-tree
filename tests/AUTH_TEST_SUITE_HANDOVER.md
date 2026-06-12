# Handover — GitHub Sign-In CLI test suite (PRD #155)

**Branch:** `claude/cli-testing-suite-rug75i`
**Scope delivered:** the `gaia login` / `gaia logout` device-flow MVP from
`GAIA_AUTH_PRD.md`, the `gaia whoami` GitHub extension, and a complete,
network-free test suite (`tests/test_auth.py`, 50 tests).
**Status:** green — `tests/test_auth.py` 50/50, full suite 810/0. Runs in
~0.2 s (no real network, no real sleeping).

This is the document the next engineer reads before touching the auth surface.

---

## 1. What shipped

| File | Role |
|---|---|
| `src/gaia_cli/auth.py` | **New.** Device flow, identity/ownership checks, token storage. The whole feature lives here. |
| `src/gaia_cli/main.py` | `login_command`, `logout_command`, `whoami` GitHub line; argparse parsers; dispatch; help text; `PUBLIC_COMMANDS`. |
| `tests/test_auth.py` | **New.** 50 tests across every layer. |
| `pyproject.toml` | New optional extra `auth = ["keyring>=24.0"]` (keychain backend; login works without it). |

No registry data, skill-tree, or Hermes-owned files were touched.

---

## 2. Architecture — and *why it is testable*

The design follows one rule: **every side effect is an injection point.** That
is what lets the suite be exhaustive without a network or a clock.

### 2.1 The single network seam
All GitHub traffic goes through **one** function:

```python
auth.http_request(method, url, *, headers=None, data=None, token=None) -> (status, dict)
```

It is the *only* place that opens a socket (`urllib`, stdlib — no new runtime
deps). Every higher-level function (`request_device_code`, `poll_for_token`,
`fetch_user`, `verify_repo_ownership`, `revoke_token`) calls it by **module
global lookup**, so a test monkeypatches `gaia_cli.auth.http_request` once and
the entire module goes offline. See `FakeHTTP` in `tests/test_auth.py`.

`http_request` itself is still tested (`TestHttpRequest`) by faking
`urllib.request.urlopen` — including the 4xx `HTTPError` path, because GitHub's
OAuth endpoints return useful JSON on errors.

### 2.2 The clock/sleep seam
`poll_for_token(client_id, device, *, sleep=time.sleep, now=time.monotonic, max_attempts=None)`
takes `sleep` and `now` as **parameters**. Tests pass `sleep=noop` and a
scripted `now=` iterator to drive the GitHub backoff protocol
(`authorization_pending` → `slow_down` → success / `expired_token` /
`access_denied`) in zero wall-clock time.

> ⚠️ **Gotcha for the next person:** these are real parameters, not module
> attributes. Monkeypatching `auth.time.sleep` does **not** affect the bound
> default — you must pass `sleep=`/`now=` explicitly (the command path uses the
> real defaults; tests pass fakes). The first draft of the suite got this wrong;
> don't reintroduce it.

### 2.3 Token storage — three backends, graceful degradation
`TokenStore` resolves on `load()` in this precedence:

1. **Env override** — `GAIA_AUTH_TOKEN` / `GAIA_TOKEN` / `GITHUB_TOKEN` / `GH_TOKEN`
   (read-only, `source="env"`). CI never has to write anything.
2. **OS keyring** — only if the `keyring` package is importable *and* its backend
   is usable (`_try_keyring()` probes `get_keyring()` so a headless box fails
   fast to the file backend instead of mid-save).
3. **chmod-600 file** — `GAIA_HOME/hosts.json` (gh's hosts pattern). Always
   available. The login *handle* is always mirrored here even on a keyring
   machine, so `whoami` can show it.

`keyring` is **optional**. The suite stubs `_try_keyring()` to `None` by default
(`_clean_auth_env` autouse fixture) and opts into a `_FakeKeyring` only in
`TestKeyringBackend`. **This is why the suite is green on a machine with no
keyring installed.**

### 2.4 client_id resolution + the "not configured" guard
`resolve_client_id(config)` = `GAIA_OAUTH_CLIENT_ID` env → config
(`oauthClientId`/`clientId`) → `PLACEHOLDER_CLIENT_ID`. `is_configured()` is
false for empty/placeholder. `gaia login` refuses to hit GitHub while the
placeholder is in force and prints a friendly setup message (`exit 1`). This is
the agreed "A's resolution order + B's fail-fast guard" decision — wired now,
one env var to go live.

---

## 3. Running the suite

```bash
.venv/bin/python -m pytest tests/test_auth.py -q -p no:cacheprovider   # 50 tests, ~0.2s
.venv/bin/python -m pytest tests/ -q -p no:cacheprovider               # full suite, 810 tests
```

Conventions honoured (per `DEV.md` §3): ANSI stripped via
`tests/helpers.py::strip_ansi`; no writes outside `tmp_path` (`GAIA_HOME` is
isolated by the root `conftest.py`); the `os.exec*` guard is untouched.

---

## 4. Coverage map (`tests/test_auth.py`)

| Class | What it locks down |
|---|---|
| `TestClientId` | env > config > placeholder; blank-env ignored; `is_configured` |
| `TestHttpRequest` | form-encode + JSON parse; bearer/Accept headers; `HTTPError` body; empty 204 body |
| `TestDeviceCode` | `from_response` defaults + malformed; `request_device_code` happy/error |
| `TestPollForToken` | pending→success; slow_down interval bump; expired→Timeout; denied→Denied; unknown→Error; deadline; max_attempts |
| `TestIdentity` | `fetch_user`/`verify_handle`; ownership by owner-match (case-insensitive), admin perms, mismatch, 404 |
| `TestRevoke` | success; unconfigured no-op; errors swallowed |
| `TestTokenStore` | file roundtrip + chmod-600; env override precedence; delete semantics; token never in `public_dict`; corrupt file |
| `TestKeyringBackend` | keyring save keeps token out of the file; keyring delete |
| `TestLoginCommand` | unconfigured guard; happy path persists; `--no-store`; `--repo` ownership; denied; timeout |
| `TestLogoutCommand` | not-signed-in; revoke+clear; `--no-revoke` skips revoke |
| `TestWhoamiGitHubLine` | not signed in; signed in; env-session note |
| `TestParserWiring` | `login`/`logout` registered; flags parse |

---

## 5. What Marco must do to make login *live* (not blocking this PR)

Per PRD §5 rollout step 1:

1. GitHub → Settings → Developer settings → **OAuth Apps** → New. Enable
   **Device Flow**. Callback URL is irrelevant (placeholder). Note the
   **client_id** (public). The client_secret is **unused in the MVP — store it
   nowhere.**
2. Expose the id one of two ways:
   - `export GAIA_OAUTH_CLIENT_ID=Ov23li…` (CI/shell), or
   - `oauthClientId = "Ov23li…"` in `.gaia/config.toml`.
3. (Optional) `pip install -e ".[auth]"` to store the token in the OS keychain
   instead of the chmod-600 file.

No code change is required to go live — that's the whole point of the env/config
resolution.

---

## 6. Deliberately out of scope / follow-ups

These are from the PRD but were **not** built here; flag them, don't silently
assume them done:

- **Remote-repo selection + worktree-style `.gaia` path** (PRD §2 MVP bullet 7 /
  §4). The ownership *primitive* (`verify_repo_ownership`) is shipped and tested;
  the interactive "select remote repos to read, store a worktree path" UX is a
  follow-up. `gaia login --repo owner/repo` already exercises the ownership check
  end-to-end, which is the condition PRD §5.4 says closes #155.
- **Expiring tokens + refresh** — MVP defaults to a plain non-expiring OAuth
  token per PRD §4 ("default to non-expiring unless Marco says otherwise"). If
  Marco opts the app into expiring tokens, add a refresh path in `auth.py` and a
  `TestRefresh` class.
- **Phase 2 web login** — shelved (CLI-forever). Don't build the Worker.
- **`gaia badge sign` / `verify`** (#494) — design against this CLI-issued
  identity; `verify_handle` is the binding primitive it should reuse.

---

## 7. CI note

The branch touches `pyproject.toml` and `src/` (within the `cli/` scope table)
plus this `tests/` doc — all inside the `claude/` experimental scope, so
`branch-scope.yml` is satisfied. No registry/timeline files are touched, so
`meta-guard.yml` does not apply. `keyring` is **not** added to `[dev]`, so CI
runs the suite with the file backend — exactly the path most users hit.
