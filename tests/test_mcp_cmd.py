"""Tests for execute_dev_mcp.

`packages/mcp` (the in-repo prototype MCP server) was deleted — it was never
published. Its standalone successor `@gaia-research/mcp` was decommissioned on
2026-08-19. `gaia dev mcp` spawns no daemon; it prints how to install the Skill
Heaven plugin, which bundles the summon MCP server. These tests lock that in:
no subprocess, no `start`/`stop`/`status` verbs, exit 0, and the printed
instructions must name the install path that actually works today.
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
    assert "claude plugin install skill-heaven@gaia-skill-heaven" in out
    assert "github.com/gaia-research/gaia-skill-heaven" in out
    # Decommissioned and unpublished install paths must never come back as
    # instructions. @gaia-research/mcp may still appear, but only as the
    # deprecation notice.
    assert "claude mcp add gaia" not in out
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
