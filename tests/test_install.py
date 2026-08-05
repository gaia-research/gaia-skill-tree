"""Tests for named skill install, sync, and uninstall.

NOTE: The pytest Python environment (/root/.local/share/uv/tools/pytest/bin/python)
does NOT have the `yaml` package.  _parse_frontmatter() falls back to a naive
line-by-line parser that cannot handle nested YAML (links.github, suiteComponents).
Tests that call install_skill() must therefore use named-skills.json as the
registry source (pure JSON, no YAML parsing needed).
"""

import json
import os
import sys
import pytest
pytestmark = [pytest.mark.integration, pytest.mark.slow]


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gaia_cli.install import (
    install_skill,
    load_manifest,
    save_manifest,
    uninstall_skill,
    resolve_named_skill_reference,
    _parse_github_url,
    _run_git,
)


def _write_json_registry(tmp_path, entries: list[dict]) -> None:
    """Write registry/named-skills.json from a list of skill meta dicts."""
    registry = tmp_path / "registry"
    registry.mkdir(exist_ok=True)
    buckets: dict = {}
    for meta in entries:
        ref = meta.get("genericSkillRef", meta["id"].replace("/", "-"))
        buckets.setdefault(ref, []).append(meta)
    (registry / "named-skills.json").write_text(
        json.dumps({"buckets": buckets, "awaitingClassification": []}),
        encoding="utf-8",
    )


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestInstallInfra:
    """Tests for low-level install infrastructure utilities."""

    def test_run_git_error_handling(self, monkeypatch, capsys):
        """_run_git catches CalledProcessError and returns False."""
        import subprocess

        def mock_run(*args, **kwargs):
            raise subprocess.CalledProcessError(1, ["git", "clone"])

        monkeypatch.setattr("subprocess.run", mock_run)
        result = _run_git(["clone", "http://example.com/repo.git"])
        assert result is False
        captured = capsys.readouterr()
        assert "Git error:" in captured.err

    def test_parse_github_url(self):
        """_parse_github_url correctly splits repo, branch, and path."""
        # Blob URL
        url = "https://github.com/garrytan/gstack/blob/main/health/SKILL.md"
        repo, branch, subpath = _parse_github_url(url)
        assert repo == "https://github.com/garrytan/gstack.git"
        assert branch == "main"
        assert subpath == "health"

        # Bare repo URL
        url = "https://github.com/gaia-research/gaia-skill-tree"
        repo, branch, subpath = _parse_github_url(url)
        assert repo == "https://github.com/gaia-research/gaia-skill-tree.git"
        assert branch is None
        assert subpath == ""

    def test_parse_github_url_tree_with_subpath(self):
        """tree/ URL extracts the correct subpath rather than installing the repo root."""
        url = "https://github.com/garrytan/gstack/tree/main/review"
        repo, branch, subpath = _parse_github_url(url)
        assert repo == "https://github.com/garrytan/gstack.git"
        assert branch == "main"
        assert subpath == "review"

    def test_parse_github_url_tree_root_only(self):
        """tree/ URL with no subpath (just /tree/branch) returns subpath=''."""
        url = "https://github.com/garrytan/gstack/tree/main"
        repo, branch, subpath = _parse_github_url(url)
        assert repo == "https://github.com/garrytan/gstack.git"
        assert branch == "main"
        assert subpath == ""

    def test_parse_github_url_tree_trailing_slash_stripped(self):
        """tree/ URL with trailing slash produces same result as without."""
        with_slash = _parse_github_url("https://github.com/garrytan/gstack/tree/main/review/")
        without_slash = _parse_github_url("https://github.com/garrytan/gstack/tree/main/review")
        assert with_slash == without_slash

    def test_parse_github_url_tree_deep_subpath(self):
        """tree/ URL with a multi-segment path preserves the full path."""
        url = "https://github.com/owner/repo/tree/main/skills/foo/bar"
        repo, branch, subpath = _parse_github_url(url)
        assert repo == "https://github.com/owner/repo.git"
        assert branch == "main"
        assert subpath == "skills/foo/bar"

    def test_parse_github_url_dir_path_no_md_extension(self):
        """Blob URL pointing to a directory (no .md suffix) → subpath is the full path."""
        url = "https://github.com/garrytan/gstack/blob/main/browse"
        repo, branch, subpath = _parse_github_url(url)
        assert repo == "https://github.com/garrytan/gstack.git"
        assert branch == "main"
        assert subpath == "browse"

    def test_parse_github_url_trailing_slash_stripped(self):
        """Trailing slash on a bare repo URL is stripped before parsing."""
        url = "https://github.com/gaia-research/gaia-skill-tree/"
        repo, branch, subpath = _parse_github_url(url)
        assert repo == "https://github.com/gaia-research/gaia-skill-tree.git"
        assert branch is None
        assert subpath == ""

    def test_parse_github_url_non_github_passthrough(self):
        """Non-GitHub URLs are returned as-is with (url, None, '')."""
        url = "https://gitlab.com/foo/bar"
        repo, branch, subpath = _parse_github_url(url)
        assert repo == url
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
        assert os.path.exists(
            os.path.join(str(tmp_path), ".gaia", "install-manifest.json")
        )


class TestInstallFlow:
    """Tests for the full install / uninstall flow."""

    def test_install_creates_manifest_entry(self, tmp_path, monkeypatch):
        """install_skill adds an entry to the manifest."""
        monkeypatch.chdir(tmp_path)

        def mock_run_git(args, cwd=None):
            if args[0] == "clone":
                source_dir = os.path.join(args[-1], "my-skill")
                os.makedirs(source_dir, exist_ok=True)
            return True

        monkeypatch.setattr("gaia_cli.install._run_git", mock_run_git)
        # Use JSON registry (no YAML needed) to avoid pytest-env naive-parser bug
        _write_json_registry(
            tmp_path,
            [
                {
                    "id": "testuser/my-skill",
                    "name": "My Skill",
                    "links": {
                        "github": "https://github.com/testuser/repo/blob/main/my-skill/SKILL.md"
                    },
                }
            ],
        )
        monkeypatch.setattr(
            "gaia_cli.install.get_global_cache_dir",
            lambda: os.path.join(str(tmp_path), ".gaia", "skills"),
        )

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
        # Flat frontmatter only (naive parser can handle this)
        skill_dir = tmp_path / "registry" / "named" / "testuser"
        skill_dir.mkdir(parents=True)
        (skill_dir / "my-skill.md").write_text(
            "---\nid: testuser/my-skill\n---\nNo link."
        )

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
                {"id": "other/skill", "localPath": "some/path"},
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

    def test_install_creates_symlink_pointing_to_cache(self, tmp_path, monkeypatch):
        """install_skill creates a symlink whose target is inside the global cache dir."""
        monkeypatch.chdir(tmp_path)
        cache_base = str(tmp_path / ".gaia" / "skills")

        def mock_run_git(args, cwd=None):
            if args[0] == "clone":
                skill_dir = os.path.join(args[-1], "my-skill")
                os.makedirs(skill_dir, exist_ok=True)
                with open(os.path.join(skill_dir, "SKILL.md"), "w") as f:
                    f.write("Actual content")
            return True

        monkeypatch.setattr("gaia_cli.install._run_git", mock_run_git)
        monkeypatch.setattr("gaia_cli.install.get_global_cache_dir", lambda: cache_base)
        _write_json_registry(
            tmp_path,
            [
                {
                    "id": "testuser/my-skill",
                    "name": "My Skill",
                    "links": {
                        "github": "https://github.com/testuser/repo/blob/main/my-skill/SKILL.md"
                    },
                }
            ],
        )

        install_skill("testuser/my-skill", str(tmp_path))

        link = tmp_path / ".agents" / "skills" / "my-skill"
        from gaia_cli.windowsLinks import isLinkOrJunction
        assert isLinkOrJunction(str(link)), "Expected a symlink or junction for the installed skill"
        target = os.path.realpath(str(link))
        assert target.startswith(os.path.realpath(cache_base)), (
            f"Link target {target!r} is not inside cache dir {cache_base!r}"
        )

    def test_install_deduplicates_manifest_entry(self, tmp_path, monkeypatch):
        """Re-installing the same skill updates the manifest entry, not appends a duplicate."""
        monkeypatch.chdir(tmp_path)

        def mock_run_git(args, cwd=None):
            if args[0] == "clone":
                os.makedirs(os.path.join(args[-1], "my-skill"), exist_ok=True)
            return True

        monkeypatch.setattr("gaia_cli.install._run_git", mock_run_git)
        monkeypatch.setattr(
            "gaia_cli.install.get_global_cache_dir",
            lambda: str(tmp_path / ".gaia" / "skills"),
        )
        _write_json_registry(
            tmp_path,
            [
                {
                    "id": "testuser/my-skill",
                    "name": "My Skill",
                    "links": {
                        "github": "https://github.com/testuser/repo/blob/main/my-skill/SKILL.md"
                    },
                }
            ],
        )

        install_skill("testuser/my-skill", str(tmp_path))
        install_skill("testuser/my-skill", str(tmp_path))

        manifest = load_manifest()
        entries = [e for e in manifest["installed"] if e["id"] == "testuser/my-skill"]
        assert len(entries) == 1, f"Expected 1 entry, got {len(entries)}"

    def test_install_resolves_by_catalog_ref(self, tmp_path, monkeypatch):
        """install_skill can find a skill by its catalogRef field."""
        monkeypatch.chdir(tmp_path)

        def mock_run_git(args, cwd=None):
            if args[0] == "clone":
                os.makedirs(os.path.join(args[-1], "my-skill"), exist_ok=True)
            return True

        monkeypatch.setattr("gaia_cli.install._run_git", mock_run_git)
        monkeypatch.setattr(
            "gaia_cli.install.get_global_cache_dir",
            lambda: str(tmp_path / ".gaia" / "skills"),
        )
        _write_json_registry(
            tmp_path,
            [
                {
                    "id": "testuser/my-skill",
                    "name": "My Skill",
                    "catalogRef": "testuser-my-skill",
                    "links": {
                        "github": "https://github.com/testuser/repo/blob/main/my-skill/SKILL.md"
                    },
                }
            ],
        )

        result = install_skill("testuser-my-skill", str(tmp_path))

        assert result is True
        manifest = load_manifest()
        assert any(e["id"] == "testuser/my-skill" for e in manifest["installed"])

    def test_install_resolves_by_bare_name(self, tmp_path, monkeypatch):
        """install_skill resolves an unambiguous bare skill name (no contributor prefix)."""
        monkeypatch.chdir(tmp_path)

        def mock_run_git(args, cwd=None):
            if args[0] == "clone":
                os.makedirs(os.path.join(args[-1], "unique-name"), exist_ok=True)
            return True

        monkeypatch.setattr("gaia_cli.install._run_git", mock_run_git)
        monkeypatch.setattr(
            "gaia_cli.install.get_global_cache_dir",
            lambda: str(tmp_path / ".gaia" / "skills"),
        )
        _write_json_registry(
            tmp_path,
            [
                {
                    "id": "testuser/unique-name",
                    "name": "Unique Name",
                    "links": {
                        "github": "https://github.com/testuser/repo/blob/main/unique-name/SKILL.md"
                    },
                }
            ],
        )

        result = install_skill("unique-name", str(tmp_path))

        assert result is True
        manifest = load_manifest()
        assert any(e["id"] == "testuser/unique-name" for e in manifest["installed"])

    def test_install_unknown_skill_returns_false(self, tmp_path, monkeypatch):
        """install_skill returns False when the skill ID is not found in the registry."""
        monkeypatch.chdir(tmp_path)
        # Empty JSON index — no skills defined
        _write_json_registry(tmp_path, [])

        result = install_skill("nobody/nonexistent", str(tmp_path))

        assert result is False

    def test_install_repairs_partial_clone_cache(self, tmp_path, monkeypatch):
        """A cache dir that exists but has no .git (partial/interrupted clone) is
        purged and re-cloned rather than trusted as-is (issue #1442)."""
        monkeypatch.chdir(tmp_path)
        cache_base = str(tmp_path / ".gaia" / "skills")

        # Simulate a prior interrupted clone: directory exists, no .git, no content.
        partial_cache = os.path.join(cache_base, "testuser", "repo")
        os.makedirs(partial_cache, exist_ok=True)

        clone_calls = []

        def mock_run_git(args, cwd=None):
            if args[0] == "clone":
                clone_calls.append(args)
                dest = args[-1]
                os.makedirs(os.path.join(dest, ".git"), exist_ok=True)
                os.makedirs(os.path.join(dest, "my-skill"), exist_ok=True)
            elif args[0] == "pull":
                raise AssertionError("pull should never be attempted on an invalid cache")
            return True

        monkeypatch.setattr("gaia_cli.install._run_git", mock_run_git)
        monkeypatch.setattr("gaia_cli.install.get_global_cache_dir", lambda: cache_base)
        _write_json_registry(
            tmp_path,
            [
                {
                    "id": "testuser/my-skill",
                    "name": "My Skill",
                    "links": {
                        "github": "https://github.com/testuser/repo/blob/main/my-skill/SKILL.md"
                    },
                }
            ],
        )

        result = install_skill("testuser/my-skill", str(tmp_path))

        assert result is True
        assert len(clone_calls) == 1
        assert os.path.isdir(os.path.join(partial_cache, ".git"))

    def test_install_recovers_from_failed_pull(self, tmp_path, monkeypatch):
        """A failed `git pull` on an existing valid cache triggers a re-clone
        instead of silently proceeding with a stale/broken tree (issue #1442)."""
        monkeypatch.chdir(tmp_path)
        cache_base = str(tmp_path / ".gaia" / "skills")
        valid_cache = os.path.join(cache_base, "testuser", "repo")
        os.makedirs(os.path.join(valid_cache, ".git"), exist_ok=True)
        os.makedirs(os.path.join(valid_cache, "my-skill"), exist_ok=True)

        clone_calls = []
        pull_calls = []

        def mock_run_git(args, cwd=None):
            if args[0] == "pull":
                pull_calls.append(args)
                return False
            if args[0] == "clone":
                clone_calls.append(args)
                dest = args[-1]
                os.makedirs(os.path.join(dest, ".git"), exist_ok=True)
                os.makedirs(os.path.join(dest, "my-skill"), exist_ok=True)
            return True

        monkeypatch.setattr("gaia_cli.install._run_git", mock_run_git)
        monkeypatch.setattr("gaia_cli.install.get_global_cache_dir", lambda: cache_base)
        _write_json_registry(
            tmp_path,
            [
                {
                    "id": "testuser/my-skill",
                    "name": "My Skill",
                    "links": {
                        "github": "https://github.com/testuser/repo/blob/main/my-skill/SKILL.md"
                    },
                }
            ],
        )

        result = install_skill("testuser/my-skill", str(tmp_path))

        assert result is True
        assert len(pull_calls) == 1
        assert len(clone_calls) == 1


class TestAmbiguousResolution:
    """Coverage for resolve_named_skill_reference's ambiguity branches (issue #1443)."""

    def test_ambiguous_catalog_ref_raises_value_error(self, tmp_path, monkeypatch):
        """Two skills sharing a catalogRef raise ValueError, not a silent pick."""
        monkeypatch.chdir(tmp_path)
        _write_json_registry(
            tmp_path,
            [
                {
                    "id": "alice/my-skill",
                    "name": "Alice Skill",
                    "catalogRef": "shared-slug",
                },
                {
                    "id": "bob/my-skill",
                    "name": "Bob Skill",
                    "catalogRef": "shared-slug",
                },
            ],
        )

        with pytest.raises(ValueError, match="Ambiguous slug"):
            resolve_named_skill_reference("shared-slug", str(tmp_path))

    def test_ambiguous_bare_name_raises_value_error(self, tmp_path, monkeypatch):
        """Two skills sharing a bare skill-name raise ValueError, not a silent pick."""
        monkeypatch.chdir(tmp_path)
        _write_json_registry(
            tmp_path,
            [
                {"id": "alice/research", "name": "Alice Research"},
                {"id": "bob/research", "name": "Bob Research"},
            ],
        )

        with pytest.raises(ValueError, match="Ambiguous bare name"):
            resolve_named_skill_reference("research", str(tmp_path))

    def test_install_command_reports_ambiguous_catalog_ref(self, tmp_path, monkeypatch, capsys):
        """`gaia install <ambiguous slug>` prints a helpful error and exits(1) instead of a traceback."""
        import argparse
        from gaia_cli.impl import install_command

        monkeypatch.chdir(tmp_path)
        _write_json_registry(
            tmp_path,
            [
                {"id": "alice/my-skill", "name": "Alice Skill", "catalogRef": "shared-slug"},
                {"id": "bob/my-skill", "name": "Bob Skill", "catalogRef": "shared-slug"},
            ],
        )
        args = argparse.Namespace(
            skill_id="shared-slug",
            registry=str(tmp_path),
            list=False,
            suite=False,
            install_location="local",
        )

        with pytest.raises(SystemExit) as excinfo:
            install_command(args)

        assert excinfo.value.code == 1
        captured = capsys.readouterr()
        assert "Ambiguous slug" in captured.err

    def test_skills_install_verb_reports_ambiguous_bare_name(self, tmp_path, monkeypatch, capsys):
        """`gaia skills install <ambiguous name>` prints a helpful error and exits(1) instead of a traceback."""
        import argparse
        from gaia_cli.impl import skills_command

        monkeypatch.chdir(tmp_path)
        _write_json_registry(
            tmp_path,
            [
                {"id": "alice/research", "name": "Alice Research"},
                {"id": "bob/research", "name": "Bob Research"},
            ],
        )
        args = argparse.Namespace(
            skills_command="install",
            skill_id="research",
            registry=str(tmp_path),
            suite=False,
            install_location="local",
            exclude_pending=True,
        )

        with pytest.raises(SystemExit) as excinfo:
            skills_command(args)

        assert excinfo.value.code == 1
        captured = capsys.readouterr()
        assert "Ambiguous bare name" in captured.err
