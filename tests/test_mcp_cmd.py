"""Tests for execute_dev_mcp."""

import argparse
import sys
from pathlib import Path
import pytest
from gaia_cli.commands import mcp_cmd
pytestmark = [pytest.mark.integration]


def test_execute_dev_mcp_missing_build(tmp_path: Path, monkeypatch, capsys):
    args = argparse.Namespace(mcp_command="start", registry=tmp_path)
    
    # Do not create daemon.js so it fails
    with pytest.raises(SystemExit) as exc:
        mcp_cmd.execute_dev_mcp(args)
    
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "MCP server build not found" in err


def test_execute_dev_mcp_success(tmp_path: Path, monkeypatch):
    args = argparse.Namespace(mcp_command="start", registry=tmp_path)
    
    # Create fake daemon.js
    script_path = tmp_path / "packages" / "mcp" / "dist" / "src" / "daemon.js"
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.touch()
    
    # Mock load_config
    monkeypatch.setattr("gaia_cli.scanner.load_config", lambda: {"gaiaUser": "test_user"})
    
    called_cmds = []
    import subprocess
    monkeypatch.setattr(subprocess, "call", lambda cmd, env: called_cmds.append((cmd, env)) or 0)
    
    res = mcp_cmd.execute_dev_mcp(args)
    
    assert res == 0
    assert len(called_cmds) == 1
    cmd, env = called_cmds[0]
    
    assert cmd == ["node", str(script_path), "start"]
    assert env["GAIA_USER"] == "test_user"
    assert env["GAIA_REGISTRY_PATH"] == str(tmp_path)
