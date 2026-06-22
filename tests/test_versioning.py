"""Tests for the polyglot monorepo versioning utilities."""

import json
from pathlib import Path

import pytest
from gaia_cli import versioning

def test_bump_version():
    assert versioning.bump_version("1.2.3", "patch") == "1.2.4"
    assert versioning.bump_version("1.2.3", "minor") == "1.3.0"
    assert versioning.bump_version("1.2.3", "major") == "2.0.0"

    with pytest.raises(ValueError, match="Unknown version bump"):
        versioning.bump_version("1.2.3", "unknown")

    with pytest.raises(ValueError, match="Invalid semantic version"):
        versioning.bump_version("1.2", "patch")


def setup_mock_project(tmp_path: Path, pyproject_v="1.0.0", npm_v="1.0.0", mcp_v="1.0.0", registry_v="1.0.0", docs_v="1.0.0"):
    # pyproject.toml
    (tmp_path / "pyproject.toml").write_text(f'version = "{pyproject_v}"', encoding="utf-8")
    
    # packages/cli-npm/package.json
    (tmp_path / "packages" / "cli-npm").mkdir(parents=True, exist_ok=True)
    (tmp_path / "packages" / "cli-npm" / "package.json").write_text(json.dumps({"version": npm_v}), encoding="utf-8")
    
    # packages/mcp/package.json
    (tmp_path / "packages" / "mcp").mkdir(parents=True, exist_ok=True)
    (tmp_path / "packages" / "mcp" / "package.json").write_text(json.dumps({"version": mcp_v}), encoding="utf-8")
    
    # registry/gaia.json
    (tmp_path / "registry").mkdir(parents=True, exist_ok=True)
    (tmp_path / "registry" / "gaia.json").write_text(json.dumps({"version": registry_v}), encoding="utf-8")
    
    # docs/graph/gaia.json
    (tmp_path / "docs" / "graph").mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs" / "graph" / "gaia.json").write_text(json.dumps({"version": docs_v}), encoding="utf-8")


def test_read_versions(tmp_path: Path, monkeypatch):
    setup_mock_project(tmp_path)
    
    # Mock registry_graph_path because it depends on the root argument differently
    monkeypatch.setattr(versioning, "registry_graph_path", lambda root: str(Path(root) / "registry" / "gaia.json"))
    
    versions = versioning.read_versions(tmp_path)
    
    assert versions["pyproject"] == "1.0.0"
    assert versions["cliNPM"] == "1.0.0"
    assert versions["mcp"] == "1.0.0"
    assert versions["registry"] == "1.0.0"
    assert versions["docsGraph"] == "1.0.0"


def test_verify_lockstep(tmp_path: Path, monkeypatch):
    setup_mock_project(tmp_path)
    monkeypatch.setattr(versioning, "registry_graph_path", lambda root: str(Path(root) / "registry" / "gaia.json"))
    
    # Should not raise
    assert versioning.verify_lockstep(tmp_path) == "1.0.0"
    
    # Make them out of sync
    setup_mock_project(tmp_path, mcp_v="1.0.1")
    with pytest.raises(ValueError, match="Version files disagree before bump:"):
        versioning.verify_lockstep(tmp_path)


def test_sync_versions(tmp_path: Path, monkeypatch):
    setup_mock_project(tmp_path, pyproject_v="1.0.0", npm_v="1.0.0", mcp_v="1.0.0", registry_v="1.0.0", docs_v="1.0.0")
    monkeypatch.setattr(versioning, "registry_graph_path", lambda root: str(Path(root) / "registry" / "gaia.json"))
    
    versioning.sync_versions(tmp_path, "2.0.0")
    
    versions = versioning.read_versions(tmp_path)
    assert versions["pyproject"] == "2.0.0"
    assert versions["cliNPM"] == "2.0.0"
    assert versions["mcp"] == "2.0.0"
    assert versions["registry"] == "2.0.0"
    assert versions["docsGraph"] == "2.0.0"


def test_bump_versions(tmp_path: Path, monkeypatch):
    setup_mock_project(tmp_path)
    monkeypatch.setattr(versioning, "registry_graph_path", lambda root: str(Path(root) / "registry" / "gaia.json"))
    
    new_version = versioning.bump_versions(tmp_path, "minor")
    assert new_version == "1.1.0"
    
    versions = versioning.read_versions(tmp_path)
    assert all(v == "1.1.0" for v in versions.values())


def test_read_versions_missing_optional_files(tmp_path: Path, monkeypatch):
    (tmp_path / "pyproject.toml").write_text('version = "1.0.0"', encoding="utf-8")
    
    (tmp_path / "packages" / "cli-npm").mkdir(parents=True, exist_ok=True)
    (tmp_path / "packages" / "cli-npm" / "package.json").write_text(json.dumps({"version": "1.0.0"}), encoding="utf-8")
    
    (tmp_path / "packages" / "mcp").mkdir(parents=True, exist_ok=True)
    (tmp_path / "packages" / "mcp" / "package.json").write_text(json.dumps({"version": "1.0.0"}), encoding="utf-8")
    
    monkeypatch.setattr(versioning, "registry_graph_path", lambda root: str(Path(root) / "registry" / "gaia.json"))
    
    versions = versioning.read_versions(tmp_path)
    
    assert versions["pyproject"] == "1.0.0"
    assert versions["cliNPM"] == "1.0.0"
    assert versions["mcp"] == "1.0.0"
    assert "registry" not in versions
    assert "docsGraph" not in versions

