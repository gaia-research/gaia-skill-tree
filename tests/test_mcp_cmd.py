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


def test_dev_mcp_help_reflects_plugin_and_summon():
    """`gaia dev dev --help` help string must reference plugin/summon, not standalone package."""
    from gaia_cli.commands.dev import DevCommand

    parser = argparse.ArgumentParser(prog="gaia dev")
    DevCommand().configure(parser)
    help_text = " ".join(parser.format_help().split())
    assert "Show install instructions for the Skill Heaven plugin and bundled summon MCP server" in help_text
    assert "standalone @gaia-research/mcp server" not in help_text


def test_no_obsolete_mcp_install_commands_in_active_surfaces():
    """Guard against obsolete MCP install commands returning to active surfaces."""
    import json

    repo_root = Path(__file__).resolve().parent.parent

    # 1. .mcp.json
    mcp_json_path = repo_root / ".mcp.json"
    if mcp_json_path.exists():
        mcp_data = json.loads(mcp_json_path.read_text(encoding="utf-8"))
        assert "gaia" not in mcp_data.get("mcpServers", {})

    # 2. AGENTS.md
    agents_md = (repo_root / "AGENTS.md").read_text(encoding="utf-8")
    assert "claude mcp add gaia" not in agents_md
    assert "claude plugin install skill-heaven@gaia-skill-heaven" in agents_md
    assert "@gaia-research/mcp@latest" not in agents_md

    # 3. packages/cli-npm/README.md
    npm_readme = (repo_root / "packages" / "cli-npm" / "README.md").read_text(encoding="utf-8")
    assert "claude mcp add gaia" not in npm_readme
    assert "@gaia-research/mcp@0.1.0" not in npm_readme
    assert "claude plugin install skill-heaven@gaia-skill-heaven" in npm_readme

    # 4. DEV.md
    dev_md = (repo_root / "DEV.md").read_text(encoding="utf-8")
    assert "standalone @gaia-research/mcp npm package (v0.1.0" not in dev_md

    # 5. docs/en/cli-reference.html
    cli_ref = (repo_root / "docs" / "en" / "cli-reference.html").read_text(encoding="utf-8")
    assert "claude mcp add gaia -- npx -y @gaia-research/mcp@0.1.0" not in cli_ref

