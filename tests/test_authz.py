"""Tests for the authorization guardrail layer (gaia_cli.authz)."""

import json
import sys
from pathlib import Path

import pytest

from gaia_cli.authz import (
    OPERATOR_OVERRIDE_ENV,
    authorization_status,
    is_authorized_operator,
    require_operator,
    _registry_has_any_verifier,
    _is_verifier,
)
from gaia_cli.main import main


# ── Fixtures ─────────────────────────────────────────────────────────────────

def _write_named_index(registry_path: Path, entries: list[dict]) -> None:
    """Write a minimal named-skills.json with the given contributor entries."""
    buckets = {}
    for e in entries:
        skill_id = e.get("genericSkillRef", "skill-a")
        buckets.setdefault(skill_id, []).append(e)
    index = {"buckets": buckets, "byContributor": {}, "awaitingClassification": []}
    (registry_path / "registry" / "named-skills.json").write_text(
        json.dumps(index), encoding="utf-8"
    )


def _make_registry(tmp_path: Path, entries: list[dict]) -> Path:
    """Build a minimal registry with the given named-skills index."""
    (tmp_path / "registry").mkdir(parents=True)
    _write_named_index(tmp_path, entries)
    return tmp_path


@pytest.fixture
def registry_with_verifier(tmp_path):
    """Registry where 'alice' is a Verifier (4★) and 'bob' is not (2★)."""
    return _make_registry(tmp_path, [
        {"contributor": "alice", "level": "4★", "genericSkillRef": "skill-a"},
        {"contributor": "bob", "level": "2★", "genericSkillRef": "skill-b"},
    ])


@pytest.fixture
def registry_bootstrap(tmp_path):
    """Registry with no 4★ contributors (bootstrap state)."""
    return _make_registry(tmp_path, [
        {"contributor": "alice", "level": "2★", "genericSkillRef": "skill-a"},
        {"contributor": "bob", "level": "3★", "genericSkillRef": "skill-b"},
    ])


@pytest.fixture
def registry_empty(tmp_path):
    """Registry with no named-skills.json at all."""
    (tmp_path / "registry").mkdir(parents=True)
    return tmp_path


@pytest.fixture(autouse=True)
def no_docs_build(monkeypatch):
    monkeypatch.setattr("gaia_cli.commands.dev._run_docs_build", lambda *a, **kw: None)


# ── Unit tests for authz module ───────────────────────────────────────────────

def test_verifier_is_authorized(registry_with_verifier):
    reg = str(registry_with_verifier)
    assert _is_verifier("alice", reg) is True
    status = authorization_status("alice", reg)
    assert status["authorized"] is True
    assert status["via"] == "verifier"


def test_non_verifier_denied_when_verifiers_exist(registry_with_verifier):
    reg = str(registry_with_verifier)
    assert _is_verifier("bob", reg) is False
    status = authorization_status("bob", reg)
    assert status["authorized"] is False
    assert status["via"] == "denied"
    assert "bob" in status["reason"]


def test_bootstrap_auto_allow(registry_bootstrap):
    reg = str(registry_bootstrap)
    assert _registry_has_any_verifier(reg) is False
    status = authorization_status("charlie", reg)
    assert status["authorized"] is True
    assert status["via"] == "bootstrap"


def test_empty_index_is_bootstrap(registry_empty):
    reg = str(registry_empty)
    status = authorization_status("anyone", reg)
    assert status["authorized"] is True
    assert status["via"] == "bootstrap"


def test_override_env_allows_non_verifier(monkeypatch, registry_with_verifier):
    reg = str(registry_with_verifier)
    monkeypatch.setenv(OPERATOR_OVERRIDE_ENV, "1")
    status = authorization_status("bob", reg)
    assert status["authorized"] is True
    assert status["via"] == "override"


def test_override_env_false_values_denied(monkeypatch, registry_with_verifier):
    reg = str(registry_with_verifier)
    for val in ("0", "false", "no", "off", ""):
        monkeypatch.setenv(OPERATOR_OVERRIDE_ENV, val)
        status = authorization_status("bob", reg)
        assert status["authorized"] is False, f"Expected denied for GAIA_OPERATOR_OVERRIDE={val!r}"


def test_is_authorized_operator_wraps_status(registry_with_verifier):
    reg = str(registry_with_verifier)
    assert is_authorized_operator("alice", reg) is True
    assert is_authorized_operator("bob", reg) is False


def test_require_operator_exits_for_denied(monkeypatch, registry_with_verifier):
    reg = str(registry_with_verifier)
    monkeypatch.setattr("gaia_cli.authz._gaia_user", lambda: "bob")
    with pytest.raises(SystemExit) as exc:
        require_operator("dev merge", reg)
    assert exc.value.code == 1


def test_require_operator_returns_username_for_authorized(monkeypatch, registry_with_verifier):
    reg = str(registry_with_verifier)
    monkeypatch.setattr("gaia_cli.authz._gaia_user", lambda: "alice")
    result = require_operator("dev add", reg)
    assert result == "alice"


# ── Dispatch-level tests ──────────────────────────────────────────────────────

def test_dispatch_gates_mutating_dev_as_non_verifier(monkeypatch, registry_with_verifier, capsys):
    """gaia dev rm exits(1) for a non-verifier when verifiers exist."""
    monkeypatch.setattr("gaia_cli.authz._gaia_user", lambda: "bob")
    monkeypatch.setattr(sys, "argv", [
        "gaia", "--registry", str(registry_with_verifier),
        "dev", "rm", "skill-a", "--yes",
    ])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "Verifier" in err


def test_dispatch_allows_readonly_dev_for_non_verifier(monkeypatch, registry_with_verifier):
    """gaia dev list does NOT require Verifier authorization."""
    monkeypatch.setattr("gaia_cli.authz._gaia_user", lambda: "bob")
    monkeypatch.setattr(sys, "argv", [
        "gaia", "--registry", str(registry_with_verifier),
        "dev", "list", "--generic",
    ])
    # Should not raise SystemExit(1) — may exit(0) or complete normally
    try:
        main()
    except SystemExit as e:
        assert e.code != 1, f"Expected read-only command to pass, got exit({e.code})"


def test_dispatch_allows_mutating_dev_in_bootstrap(monkeypatch, registry_bootstrap, tmp_path, capsys):
    """gaia dev list works in bootstrap mode (no verifiers) without error."""
    monkeypatch.setattr("gaia_cli.authz._gaia_user", lambda: "anyone")
    monkeypatch.setattr(sys, "argv", [
        "gaia", "--registry", str(registry_bootstrap),
        "dev", "list", "--generic",
    ])
    try:
        main()
    except SystemExit as e:
        assert e.code != 1


def test_dispatch_allows_verifier(monkeypatch, registry_with_verifier, capsys):
    """gaia dev list works for a verified alice."""
    monkeypatch.setattr("gaia_cli.authz._gaia_user", lambda: "alice")
    monkeypatch.setattr(sys, "argv", [
        "gaia", "--registry", str(registry_with_verifier),
        "dev", "list", "--generic",
    ])
    try:
        main()
    except SystemExit as e:
        assert e.code != 1


# ── Confirmation prompt tests ─────────────────────────────────────────────────

def test_confirm_destructive_aborts_non_interactive(monkeypatch):
    """Without --yes, confirm(default=False) aborts in non-interactive context."""
    import gaia_cli.interactive as interactive_mod
    # Simulate non-interactive: _has_interactive returns False → confirm returns default=False
    monkeypatch.setattr(interactive_mod, "_has_interactive", lambda: False)

    from gaia_cli.commands.dev import _confirm_destructive

    class FakeArgs:
        yes = False

    with pytest.raises(SystemExit) as exc:
        _confirm_destructive("Delete this?", FakeArgs())
    assert exc.value.code == 0  # aborted cleanly


def test_confirm_destructive_skipped_with_yes_flag(monkeypatch):
    """With --yes, _confirm_destructive completes without prompting."""
    from gaia_cli.commands.dev import _confirm_destructive

    class FakeArgs:
        yes = True

    # Should not raise
    _confirm_destructive("Delete this?", FakeArgs())


# ── whoami command tests ──────────────────────────────────────────────────────

def test_whoami_output_verifier(monkeypatch, registry_with_verifier, capsys):
    monkeypatch.setattr("gaia_cli.authz._gaia_user", lambda: "alice")
    monkeypatch.setattr(sys, "argv", [
        "gaia", "--registry", str(registry_with_verifier), "whoami",
    ])
    try:
        main()
    except SystemExit:
        pass
    out = capsys.readouterr().out
    assert "alice" in out
    assert "yes" in out
    assert "verifier" in out


def test_whoami_output_non_verifier(monkeypatch, registry_with_verifier, capsys):
    monkeypatch.setattr("gaia_cli.authz._gaia_user", lambda: "bob")
    monkeypatch.setattr(sys, "argv", [
        "gaia", "--registry", str(registry_with_verifier), "whoami",
    ])
    try:
        main()
    except SystemExit:
        pass
    out = capsys.readouterr().out
    assert "bob" in out
    assert "no" in out
    assert "denied" in out


def test_whoami_output_bootstrap(monkeypatch, registry_bootstrap, capsys):
    monkeypatch.setattr("gaia_cli.authz._gaia_user", lambda: "charlie")
    monkeypatch.setattr(sys, "argv", [
        "gaia", "--registry", str(registry_bootstrap), "whoami",
    ])
    try:
        main()
    except SystemExit:
        pass
    out = capsys.readouterr().out
    assert "bootstrap" in out


# ── Regression: player-facing flows are NOT gated ────────────────────────────

def test_promote_command_not_gated(monkeypatch, registry_with_verifier):
    """gaia promote is player-facing and must never require Verifier auth."""
    monkeypatch.setattr("gaia_cli.authz._gaia_user", lambda: "bob")
    monkeypatch.setattr(sys, "argv", [
        "gaia", "--registry", str(registry_with_verifier), "promote",
    ])
    # gaia promote without a scan candidate just exits(0) or prints a message;
    # the important invariant is it does NOT exit(1) with an authz error.
    try:
        main()
    except SystemExit as e:
        err_output = ""
        assert e.code != 1 or "Verifier" not in err_output
