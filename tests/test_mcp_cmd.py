"""Tests for execute_dev_mcp.

`packages/mcp` (the in-repo prototype MCP server) was deleted — it was never
published. `gaia dev mcp` no longer spawns a local node daemon; it prints how to
install the standalone, published `@gaia-research/mcp` npm package. These tests
lock that in: no subprocess, no `start`/`stop`/`status` verbs, exit 0, and the
printed instructions must name the package that actually exists.
"""

import argparse
import subprocess
from pathlib import Path

import pytest

from gaia_cli.commands import mcp_cmd

pytestmark = [pytest.mark.integration]


def test_execute_dev_mcp_prints_standalone_instructions(tmp_path: Path, capsys):
    args = argparse.Namespace(registry=tmp_path)

    assert mcp_cmd.execute_dev_mcp(args) == 0

    out = capsys.readouterr().out
    assert "@gaia-research/mcp@0.1.0" in out
    assert "claude mcp add gaia" in out
    assert "github.com/gaia-research/gaia-mcp" in out
    # The unpublished names must never come back.
    assert "@gaia-registry/mcp-server" not in out
    assert "packages/mcp" not in out


def test_execute_dev_mcp_spawns_no_subprocess(tmp_path: Path, monkeypatch):
    """No local daemon exists to launch, so nothing may be exec'd."""
    args = argparse.Namespace(registry=tmp_path)

    def _boom(*a, **kw):  # pragma: no cover - only runs on regression
        raise AssertionError(f"gaia dev mcp must not spawn a subprocess: {a}")

    monkeypatch.setattr(subprocess, "call", _boom)
    monkeypatch.setattr(subprocess, "run", _boom)
    monkeypatch.setattr(subprocess, "Popen", _boom)

    assert mcp_cmd.execute_dev_mcp(args) == 0


def test_dev_mcp_has_no_daemon_subcommands():
    """`start`/`stop`/`status` are gone with the prototype they drove."""
    from gaia_cli.commands.dev import DevCommand

    parser = argparse.ArgumentParser(prog="gaia dev")
    DevCommand().configure(parser)

    with pytest.raises(SystemExit):
        parser.parse_args(["mcp", "start"])
