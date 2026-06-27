import json
import os
import sys
from pathlib import Path
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gaia_cli.main import main
from gaia_cli import push as push_mod
from gaia_cli import graph as graph_mod
from gaia_cli import scanner

pytestmark = [pytest.mark.integration]

def run_cli(monkeypatch, argv: list[str]):
    monkeypatch.setattr(sys, "argv", ["gaia", *argv])
    try:
        main()
    except SystemExit as e:
        raise e

def test_init_workspace_flag(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    import gaia_cli.main as gaia_main
    
    # Patch fetch_command and _detect_github_username so no network/external calls
    monkeypatch.setattr(gaia_main, "fetch_command", lambda args: None)
    monkeypatch.setattr(gaia_main, "_detect_github_username", lambda: None)
    
    # Run init --workspace
    run_cli(monkeypatch, ["init", "--user", "testuser", "--workspace", "--yes"])
    
    config_path = tmp_path / ".gaia" / "config.toml"
    assert config_path.exists()
    
    config = scanner.load_config()
    assert config.get("workspaceMode") is True

def test_init_no_remote_falls_back_to_workspace(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    import gaia_cli.main as gaia_main
    
    monkeypatch.setattr(gaia_main, "fetch_command", lambda args: None)
    monkeypatch.setattr(gaia_main, "_detect_github_username", lambda: None)
    
    # Make detect_source_repo raise NonPublicRepoError
    monkeypatch.setattr(push_mod, "detect_source_repo",
                        lambda config: (_ for _ in ()).throw(push_mod.NonPublicRepoError("testuser")))
                        
    run_cli(monkeypatch, ["init", "--user", "testuser", "--yes"])
    
    config_path = tmp_path / ".gaia" / "config.toml"
    assert config_path.exists()
    
    config = scanner.load_config()
    assert config.get("workspaceMode") is True

def test_push_prevented_in_workspace_mode(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    
    # Setup minimal registry first
    registry = tmp_path / "registry"
    registry.mkdir()
    (registry / "gaia.json").write_text(
        json.dumps({
            "version": "1.0.0",
            "generatedAt": "2026-06-10",
            "skills": []
        }),
        encoding="utf-8"
    )
    (registry / "named-skills.json").write_text(json.dumps({"buckets": {}}), encoding="utf-8")

    # Write a config with workspaceMode = true
    gaia_dir = tmp_path / ".gaia"
    gaia_dir.mkdir()
    (gaia_dir / "config.toml").write_text(
        f"workspaceMode = true\nusername = \"testuser\"\nlocalRegistryPath = \"{tmp_path}\"\n",
        encoding="utf-8"
    )
    
    with pytest.raises(SystemExit) as excinfo:
        run_cli(monkeypatch, ["--registry", str(tmp_path), "push"])
        
    assert excinfo.value.code == 1
    err = capsys.readouterr().err
    assert "not supported in Workspace Mode" in err

def test_whoami_mode_reporting(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    
    # Write a config with workspaceMode = true
    gaia_dir = tmp_path / ".gaia"
    gaia_dir.mkdir()
    (gaia_dir / "config.toml").write_text("workspaceMode = true\nusername = \"testuser\"\n", encoding="utf-8")
    
    try:
        run_cli(monkeypatch, ["whoami"])
    except SystemExit:
        pass
    out = capsys.readouterr().out
    assert "Mode:      Workspace Mode" in out

def test_graph_watermark_injected(monkeypatch, tmp_path):
    # Setup registry first
    registry = tmp_path / "registry"
    registry.mkdir()
    (registry / "gaia.json").write_text(
        json.dumps({
            "version": "1.0.0",
            "generatedAt": "2026-06-10",
            "skills": []
        }),
        encoding="utf-8"
    )
    (registry / "named-skills.json").write_text(json.dumps({"buckets": {}}), encoding="utf-8")
    
    # Render SVG with is_workspace=True
    out_svg, _ = graph_mod.write_graph_artifact(tmp_path, fmt="svg", is_workspace=True)
    svg_content = out_svg.read_text(encoding="utf-8")
    assert "WORKSPACE ONLY" in svg_content
    
    # Render HTML with is_workspace=True
    out_html, _ = graph_mod.write_graph_artifact(tmp_path, fmt="html", is_workspace=True)
    html_content = out_html.read_text(encoding="utf-8")
    assert "workspace-watermark" in html_content
    assert "Workspace Mode" in html_content
