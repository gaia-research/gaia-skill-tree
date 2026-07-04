"""Unit tests for gaia update — Issue #938.

The prior implementation always did an editable install from the local
checkout when a pyproject.toml was found there, which pinned the CLI to the
checkout's version even when PyPI had a newer wheel published. These tests
lock in the PyPI-prefer decision.
"""

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from gaia_cli import impl


def _make_args(tmp_path: Path) -> SimpleNamespace:
    # Registry must contain a pyproject.toml for the editable-install branch to trigger.
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "gaia-cli"\nversion = "5.1.6"\n', encoding="utf-8")
    return SimpleNamespace(registry=str(tmp_path), allow_downgrade=False)


class _FakeCompleted:
    def __init__(self, returncode: int = 0, stderr: str = ""):
        self.returncode = returncode
        self.stderr = stderr


def test_fetch_pypi_latest_version_parses_info_version():
    """_fetch_pypi_latest_version returns info.version from PyPI JSON response."""
    fake_body = json.dumps({"info": {"version": "5.11.5"}}).encode()
    fake_resp = MagicMock()
    fake_resp.read.return_value = fake_body
    fake_resp.__enter__.return_value = fake_resp
    fake_resp.__exit__.return_value = None
    with patch("urllib.request.urlopen", return_value=fake_resp):
        assert impl._fetch_pypi_latest_version("gaia-cli") == "5.11.5"


def test_fetch_pypi_latest_version_returns_none_on_network_error():
    import urllib.error
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("no dns")):
        assert impl._fetch_pypi_latest_version("gaia-cli") is None


def test_update_prefers_pypi_when_installed_is_older(tmp_path, monkeypatch, capsys):
    """When PyPI has a newer version than installed, run pip install --upgrade gaia-cli."""
    args = _make_args(tmp_path)

    monkeypatch.setattr(impl, "_fetch_pypi_latest_version", lambda *a, **kw: "5.11.5")
    monkeypatch.setattr(impl, "_installed_gaia_cli_version", lambda: "5.1.6")

    calls = []

    def fake_run(cmd, *a, **kw):
        calls.append(list(cmd))
        return _FakeCompleted(returncode=0)

    monkeypatch.setattr(impl.subprocess, "run", fake_run)

    impl.update_command(args)

    # We expect a pip install with --upgrade for the PyPI package, and NOT an editable install.
    pip_cmds = [c for c in calls if len(c) >= 4 and c[1] == "-m" and c[2] == "pip"]
    assert any("gaia-cli" in c and "--upgrade" in c for c in pip_cmds), \
        f"Expected pip install --upgrade gaia-cli; saw {pip_cmds}"
    assert not any("-e" in c for c in pip_cmds), \
        f"Should not have run an editable install when PyPI is newer; saw {pip_cmds}"

    out = capsys.readouterr().out
    assert "5.11.5" in out and "5.1.6" in out


def test_update_falls_back_to_editable_when_installed_matches_pypi(tmp_path, monkeypatch):
    """When installed == PyPI, the editable install is a valid fallback (dev workflow)."""
    args = _make_args(tmp_path)

    monkeypatch.setattr(impl, "_fetch_pypi_latest_version", lambda *a, **kw: "5.11.5")
    monkeypatch.setattr(impl, "_installed_gaia_cli_version", lambda: "5.11.5")

    calls = []

    def fake_run(cmd, *a, **kw):
        calls.append(list(cmd))
        return _FakeCompleted(returncode=0)

    monkeypatch.setattr(impl.subprocess, "run", fake_run)

    impl.update_command(args)

    pip_cmds = [c for c in calls if len(c) >= 4 and c[1] == "-m" and c[2] == "pip"]
    # Should NOT have called `pip install gaia-cli --upgrade`; should have called `-e <registry>`.
    assert not any("--upgrade" in c for c in pip_cmds), \
        f"Should not force an upgrade when at PyPI parity; saw {pip_cmds}"
    assert any("-e" in c and str(tmp_path) in c for c in pip_cmds), \
        f"Expected editable install fallback; saw {pip_cmds}"


def test_update_falls_back_to_editable_when_pypi_unreachable(tmp_path, monkeypatch, capsys):
    """If PyPI can't be reached, do the editable install rather than crash."""
    args = _make_args(tmp_path)

    monkeypatch.setattr(impl, "_fetch_pypi_latest_version", lambda *a, **kw: None)
    monkeypatch.setattr(impl, "_installed_gaia_cli_version", lambda: "5.1.6")

    calls = []

    def fake_run(cmd, *a, **kw):
        calls.append(list(cmd))
        return _FakeCompleted(returncode=0)

    monkeypatch.setattr(impl.subprocess, "run", fake_run)

    impl.update_command(args)

    pip_cmds = [c for c in calls if len(c) >= 4 and c[1] == "-m" and c[2] == "pip"]
    assert any("-e" in c for c in pip_cmds), \
        f"Expected editable install when PyPI unreachable; saw {pip_cmds}"

    err = capsys.readouterr().err
    assert "PyPI" in err or "pypi" in err.lower()
