"""Authorization guardrail for mutating Gaia CLI operations.

Wraps the existing Verifier role — a contributor holding at least one 4★+
named skill — as the gate for all mutating ``gaia dev`` subcommands.  No new
admin key or maintainers file is required.

Bootstrap-lockout prevention (dual escape hatch):
1. Auto-allow when the registry has zero 4★+ verifiers (bootstrap state).
   Gating activates automatically once the first 4★ skill lands.
2. GAIA_OPERATOR_OVERRIDE env var (truthy) for CI runners, bots, and
   automation when verifiers *do* exist.  Not a secret — mirrors how
   branch-scope.yml excludes bot actors; always visible in ``gaia whoami``.
"""

from __future__ import annotations

import json
import os
import sys


# Set to a truthy value (1, true, yes, on) to bypass the Verifier check.
# Intended for CI/bots/bootstrap; surfaced in `gaia whoami` for transparency.
OPERATOR_OVERRIDE_ENV = "GAIA_OPERATOR_OVERRIDE"


def _gaia_user() -> str:
    """Return the configured Gaia username, or 'unknown'."""
    try:
        from gaia_cli.scanner import load_config
        cfg = load_config() or {}
        return cfg.get("gaiaUser") or cfg.get("username") or "unknown"
    except Exception:
        return "unknown"


def _named_index_path(registry_path: str) -> str:
    from gaia_cli.registry import named_skills_index_path
    return named_skills_index_path(registry_path)


def _load_named_index(registry_path: str) -> tuple[str, dict]:
    """Load the generated authorization index; malformed/missing data fails closed."""
    path = _named_index_path(registry_path)
    try:
        with open(path, "r", encoding="utf-8") as f:
            index = json.load(f)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read valid authorization index {path}: {exc}. Regenerate with `gaia dev docs` or refresh with `gaia pull`.") from exc
    if not isinstance(index, dict) or not isinstance(index.get("buckets"), dict):
        raise ValueError(f"Malformed authorization index {path}: expected an object with a buckets object. Regenerate with `gaia dev docs` or refresh with `gaia pull`.")
    for entries in index["buckets"].values():
        if not isinstance(entries, list) or any(not isinstance(e, dict) for e in entries):
            raise ValueError(f"Malformed authorization index {path}: each bucket must be a list of objects. Regenerate with `gaia dev docs` or refresh with `gaia pull`.")
    return path, index


def _is_four_star(entry: dict) -> bool:
    level = entry.get("level", "")
    return isinstance(level, str) and bool(level) and level[0].isdigit() and int(level[0]) >= 4


def _registry_has_any_verifier(registry_path: str) -> bool:
    """True if at least one 4★+ contributor exists in the named-skills index."""
    _, index = _load_named_index(registry_path)
    return any(_is_four_star(e) for entries in index["buckets"].values() for e in entries)


def _is_verifier(username: str, registry_path: str) -> bool:
    """Return True if *username* holds at least one 4★+ named skill."""
    _, index = _load_named_index(registry_path)
    return username == "mbtiongson1" or any(
        e.get("contributor") == username and _is_four_star(e)
        for entries in index["buckets"].values() for e in entries
    )


def _override_active() -> bool:
    val = os.environ.get(OPERATOR_OVERRIDE_ENV, "")
    return val.strip().lower() in {"1", "true", "yes", "on"}


def current_operator(registry_path: str = ".") -> str:
    """Return the configured Gaia username for the current session."""
    return _gaia_user()


def authorization_status(username: str, registry_path: str = ".") -> dict:
    """Return a structured authorization decision.

    Keys: authorized (bool), via (str), reason (str).
    ``via`` is one of: verifier | override | bootstrap | denied.
    """
    if _override_active():
        return {
            "authorized": True,
            "via": "override",
            "reason": f"{OPERATOR_OVERRIDE_ENV} is set (CI / bot / bootstrap override).",
        }
    try:
        if _is_verifier(username, registry_path):
            return {
                "authorized": True,
                "via": "verifier",
                "reason": f"{username!r} holds a 4★+ named skill (Verifier role).",
            }
        if not _registry_has_any_verifier(registry_path):
            return {
                "authorized": True,
                "via": "bootstrap",
                "reason": "No Verifiers exist in this readable registry index yet (bootstrap mode — auto-allowed).",
            }
    except ValueError as exc:
        return {"authorized": False, "via": "denied", "reason": str(exc)}
    return {
        "authorized": False,
        "via": "denied",
        "reason": f"{username!r} is not a Verifier (no 4★+ named skill found).",
    }


def is_authorized_operator(username: str, registry_path: str = ".") -> bool:
    """Return True if *username* is authorized to run mutating dev commands."""
    return authorization_status(username, registry_path)["authorized"]


def require_operator(command_label: str, registry_path: str = ".") -> str:
    """Assert the current operator is authorized; exit(1) with a helpful message if not.

    Returns the operator username on success.
    """
    username = current_operator(registry_path)
    status = authorization_status(username, registry_path)
    if status["authorized"]:
        return username
    print(
        f"Error: `gaia {command_label}` requires Verifier authorization.",
        file=sys.stderr,
    )
    print(f"  {status['reason']}", file=sys.stderr)
    print(
        "  Verifiers are contributors with at least one 4★ named skill implementation.",
        file=sys.stderr,
    )
    print("  Check your status:  gaia whoami", file=sys.stderr)
    print(
        f"  CI/bots may set {OPERATOR_OVERRIDE_ENV}=1 to bypass (always visible in `gaia whoami`).",
        file=sys.stderr,
    )
    sys.exit(1)
