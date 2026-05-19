"""Tests for named skill install, sync, and uninstall."""
import json
import os
import sys
import tempfile
from unittest.mock import patch
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gaia_cli.install import (
    install_skill,
    load_manifest,
    resolve_named_skill_reference,
    save_manifest,
    uninstall_skill,
    list_installed,
    get_manifest_path,
    get_repo_skills_dir,
    _parse_github_url,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestInstallInfra:
    """Tests for low-level install infrastructure utilities."""

    def test_parse_github_url(self):
        """_parse_github_url correctly splits repo, branch, and path."""
        # Blob URL
        url = "https://github.com/garrytan/gstack/blob/main/health/SKILL.md"
        repo, branch, subpath = _parse_github_url(url)
        assert repo == "https://github.com/garrytan/gstack.git"
        assert branch == "main"
        assert subpath == "health"

        # Bare repo URL
        url = "https://github.com/mbtiongson1/gaia-skill-tree"
        repo, branch, subpath = _parse_github_url(url)
        assert repo == "https://github.com/mbtiongson1/gaia-skill-tree.git"
        assert branch is None
        assert subpath == ""

    def test_manifest_roundtrip(self, tmp_path, monkeypatch):
        """save_manifest and load_manifest round-trip correctly."""
        monkeypatch.chdir(tmp_path)
        os.makedirs(".gaia", exist_ok=True)

        manifest = {
            "installed": [
                {
                    "id": "foo/bar",
                    "installedAt": "2026-04-29T00:00:00Z",
                    "repoUrl": "https://github.com/foo/bar.git",
                    "subpath": "baz",
                    "localPath": ".agents/skills/bar",
                }
            ]
        }
        save_manifest(manifest)
        loaded = load_manifest()
        assert loaded["installed"][0]["id"] == "foo/bar"
        assert loaded["installed"][0]["subpath"] == "baz"

    def test_load_manifest_returns_empty_when_missing(self, tmp_path, monkeypatch):
        """load_manifest returns {'installed': []} when no manifest file exists."""
        monkeypatch.chdir(tmp_path)
        manifest = load_manifest()
        assert manifest == {"installed": []}

    def test_save_manifest_creates_gaia_dir(self, tmp_path, monkeypatch):
        """save_manifest creates .gaia/ directory if it does not exist."""
        monkeypatch.chdir(tmp_path)
        # .gaia does NOT exist yet
        save_manifest({"installed": []})
        assert os.path.exists(os.path.join(str(tmp_path), ".gaia", "install-manifest.json"))


class TestInstallFlow:
    """Tests for the full install / uninstall flow."""

    def test_install_creates_manifest_entry(self, tmp_path, monkeypatch):
        """install_skill adds an entry to the manifest."""
        monkeypatch.chdir(tmp_path)

        # Mock git execution to succeed and create the mock source dir
        def mock_run_git(args, cwd=None):
            # simulate git clone by creating the source directory
            source_dir = os.path.join(str(tmp_path), ".gaia", "skills", "testuser", "repo", "my-skill")
            os.makedirs(source_dir, exist_ok=True)
            return True
        monkeypatch.setattr("gaia_cli.install._run_git", mock_run_git)

        # Create a mock registry with a named skill containing a github link
        skill_dir = tmp_path / "registry" / "named" / "testuser"
        skill_dir.mkdir(parents=True)
        (skill_dir / "my-skill.md").write_text(
            "---\nid: testuser/my-skill\nlinks:\n  github: https://github.com/testuser/repo/blob/main/my-skill/SKILL.md\n---\nContent here."
        )

        # Ensure the global cache dir points to our tmp_path
        monkeypatch.setattr("gaia_cli.install.get_global_cache_dir", lambda: os.path.join(str(tmp_path), ".gaia", "skills"))

        result = install_skill("testuser/my-skill", str(tmp_path))
        assert result is True

        manifest = load_manifest()
        assert len(manifest["installed"]) == 1
        entry = manifest["installed"][0]
        assert entry["id"] == "testuser/my-skill"
        assert entry["repoUrl"] == "https://github.com/testuser/repo.git"
        assert "my-skill" in entry["localPath"]

    def test_install_fails_without_github_link(self, tmp_path, monkeypatch):
        """install_skill fails if the skill has no source repository."""
        monkeypatch.chdir(tmp_path)
        skill_dir = tmp_path / "registry" / "named" / "testuser"
        skill_dir.mkdir(parents=True)
        (skill_dir / "my-skill.md").write_text("---\nid: testuser/my-skill\n---\nNo link.")

        result = install_skill("testuser/my-skill", str(tmp_path))
        assert result is False

    def test_uninstall_removes_from_manifest(self, tmp_path, monkeypatch):
        """uninstall_skill removes the skill from the manifest and cleans up."""
        monkeypatch.chdir(tmp_path)
        os.makedirs(".gaia", exist_ok=True)
        
        test_path = tmp_path / ".agents" / "skills" / "my-skill"
        test_path.parent.mkdir(parents=True, exist_ok=True)
        test_path.write_text("mock")

        manifest = {
            "installed": [
                {"id": "testuser/my-skill", "localPath": str(test_path)},
                {"id": "other/skill", "localPath": "some/path"}
            ]
        }
        save_manifest(manifest)

        result = uninstall_skill("testuser/my-skill")
        assert result is True

        # Check manifest
        loaded = load_manifest()
        assert len(loaded["installed"]) == 1
        assert loaded["installed"][0]["id"] == "other/skill"
        
        # Check cleanup (mock path should be removed)
        assert not test_path.exists()
