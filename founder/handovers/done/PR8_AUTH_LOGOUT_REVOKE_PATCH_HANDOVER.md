# Patch Handover: `gaia logout` — honest revoke for the secret-less MVP (#155)

**Type:** Small surgical patch · **Branch:** `cli/logout-honest-revoke` · **Refs #155**
**Origin:** Review finding on PR #669 (merged `b4d6659d`). See #669 comment 4700324066 and #155 comment 4700531852.
**Scope:** `src/gaia_cli/auth.py`, `src/gaia_cli/main.py`, `tests/test_auth.py`. No registry/timeline/Hermes files — `meta-guard` / `branch-scope` are satisfied by the `cli/` prefix.

## The problem

`gaia logout` advertises that it revokes the GitHub token server-side. It can't, by design:

- `auth.revoke_token()` calls `DELETE /applications/{client_id}/token`.
- That endpoint requires **HTTP Basic auth with `client_id:client_secret`** — it is an *app-authenticated* endpoint, not a user-token one.
- The MVP deliberately stores **no client secret** (PRD §5). So against live GitHub the call returns **401**, `revoke_token` returns `False`, and logout silently falls back to clearing locally.
- `tests/test_auth.py::test_revoke_success` mocks a `204` and asserts `True`, so the suite gives **false confidence** in a function that is a no-op in production.

Net: the function is dead against the real API, and the `--no-revoke` flag + "revoke the stored token" help text overpromise.

## The fix (recommended): make logout honest, point to GitHub's UI

The empty-scope identity token is low-risk, and users *can* revoke it in GitHub's UI. So: clear locally, tell them where to fully revoke, and delete the dead code + misleading test.

### 1. `src/gaia_cli/auth.py` — remove `revoke_token`

Delete the entire `revoke_token(...)` function (the `DELETE /applications/{client_id}/token` block). Nothing else in `auth.py` references it.

### 2. `src/gaia_cli/main.py` — rewrite `logout_command`

Replace the current body with:

```python
def logout_command(args):
    """Sign out of GitHub by clearing the locally stored token (PRD #155).

    The MVP stores no client secret, and GitHub's revocation endpoint
    (DELETE /applications/{client_id}/token) requires client_id:client_secret
    Basic auth — so a server-side revoke isn't possible here. We clear the
    local token and point the user at GitHub's UI to fully revoke if they want.
    """
    from gaia_cli import auth

    store = auth.TokenStore()
    creds = store.load()
    if not creds:
        print("Not signed in — nothing to do.")
        return

    if creds.source == "env":
        print("Signed in via an environment token — unset it to fully sign out.")

    store.delete()
    handle = f" ({creds.login})" if creds.login else ""
    print(f"✓ Signed out{handle}. Local token cleared.")

    config = load_config() or {}
    client_id = auth.resolve_client_id(config)
    if auth.is_configured(client_id):
        print("  To fully revoke this authorization, visit:")
        print(f"  https://github.com/settings/connections/applications/{client_id}")
    else:
        print("  To fully revoke: GitHub → Settings → Applications → Authorized OAuth Apps.")
```

### 3. `src/gaia_cli/main.py` — drop the `--no-revoke` flag, fix help text

In `get_parser()` replace the `logout` subparser block:

```python
    subparsers.add_parser(
        "logout",
        help="Sign out of GitHub (clears the local token; revoke in GitHub settings)",
    )
```

(Remove the `logout_parser.add_argument("--no-revoke", ...)` lines — the flag is meaningless once revoke is gone, and it shipped only in #669 so there's no released surface to preserve.)

### 4. `tests/test_auth.py`

- Remove `revoke_token` from the top-of-file import (currently imported alongside the other `auth` names).
- Delete `test_revoke_success`, `test_revoke_unconfigured_noop`, `test_revoke_swallows_errors`.
- Delete the argparse assertion that parses `["logout", "--no-revoke"]`.
- Replace `test_logout_revokes_and_clears` with a test that asserts logout **clears locally and prints the revoke URL** (no "revoked" claim), e.g.:

```python
def test_logout_clears_and_points_to_revoke_url(self, monkeypatch, capsys):
    TokenStore().save(Credentials(token="T", login="marco"))
    monkeypatch.setenv(auth.CLIENT_ID_ENV, "Ov23litFvQBfMkwbIxfg")
    from gaia_cli.main import logout_command
    logout_command(SimpleNamespace())
    out, _ = _capture(capsys)
    assert "Signed out (marco)" in out
    assert "settings/connections/applications/Ov23litFvQBfMkwbIxfg" in out
    assert "revoked" not in out.lower()
    assert TokenStore().load() is None
```

- Repurpose/remove `test_logout_no_revoke` (its premise is gone). Keep any env-token logout-message test.

## Acceptance criteria

- `python -m pytest tests/test_auth.py` and the **full suite** pass.
- `gaia logout` clears the local token and prints the GitHub revoke URL; it never claims a server-side revoke.
- `gaia logout` help text no longer says "revoke the stored token"; `--no-revoke` is gone.
- No reference to `revoke_token` remains anywhere (`grep -rn revoke_token src tests` is clean).

## Notes

- PRD §4's "`gaia logout` … revokes via the API" is amended for the MVP to "clears locally; user revokes in GitHub's UI" (no client secret stored). If a server-side revoke is ever wanted, it's a Phase-2 item that requires opting the app into storing the secret.
- **Alternative (not recommended):** keep `revoke_token` and `--no-revoke` as Phase-2 stubs and just fix the test to stop asserting real revocation. Leaves dead code; only choose this if you expect to wire the secret soon.
