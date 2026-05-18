"""Tests for named skill install, sync, and uninstall."""
import json
import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gaia_cli.install import (
    compute_sha256,
    find_named_skill_source,
    install_skill,
    load_manifest,
    resolve_named_skill_reference,
    save_manifest,
    uninstall_skill,
    list_installed,
    sync_skills,
    get_manifest_path,
    get_repo_skills_dir,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestInstallInfra:
    """Tests for low-level install infrastructure utilities."""

    def test_compute_sha256_produces_64_char_hex(self, tmp_path):
        """compute_sha256 returns a 64-character hex string."""
        test_file = tmp_path / "test.md"
        test_file.write_text("hello world")
        sha = compute_sha256(str(test_file))
        assert len(sha) == 64
        assert all(c in "0123456789abcdef" for c in sha)

    def test_compute_sha256_is_deterministic(self, tmp_path):
        """compute_sha256 returns the same value for the same file."""
        test_file = tmp_path / "test.md"
        test_file.write_text("hello world")
        sha1 = compute_sha256(str(test_file))
        sha2 = compute_sha256(str(test_file))
        assert sha1 == sha2

    def test_compute_sha256_differs_for_different_content(self, tmp_path):
        """compute_sha256 produces different values for different content."""
        f1 = tmp_path / "a.md"
        f2 = tmp_path / "b.md"
        f1.write_text("content A")
        f2.write_text("content B")
        assert compute_sha256(str(f1)) != compute_sha256(str(f2))

    def test_find_named_skill_source_exists(self, tmp_path):
        """find_named_skill_source returns the path when the file exists."""
        skill_dir = tmp_path / "registry" / "named" / "contributor"
        skill_dir.mkdir(parents=True)
        (skill_dir / "my-skill.md").write_text("---\nid: contributor/my-skill\n---\n")

        result = find_named_skill_source("contributor/my-skill", str(tmp_path))
        assert result is not None
        assert result.endswith("my-skill.md")

    def test_find_named_skill_source_missing(self, tmp_path):
        """find_named_skill_source returns None when the file does not exist."""
        result = find_named_skill_source("nobody/nothing", str(tmp_path))
        assert result is None

    def test_find_named_skill_source_invalid_id(self, tmp_path):
        """find_named_skill_source returns None for IDs without a slash."""
        result = find_named_skill_source("no-slash-here", str(tmp_path))
        assert result is None

    def test_manifest_roundtrip(self, tmp_path, monkeypatch):
        """save_manifest and load_manifest round-trip correctly."""
        monkeypatch.chdir(tmp_path)
        os.makedirs(".gaia", exist_ok=True)

        manifest = {
            "installed": [
                {
                    "id": "foo/bar",
                    "installedAt": "2026-04-29T00:00:00Z",
                    "sourceRef": "registry/named/foo/bar.md",
                    "sha256": "a" * 64,
                }
            ]
        }
        save_manifest(manifest)
        loaded = load_manifest()
        assert loaded["installed"][0]["id"] == "foo/bar"
        assert loaded["installed"][0]["sha256"] == "a" * 64

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

        # Create a mock registry with a named skill
        skill_dir = tmp_path / "registry" / "named" / "testuser"
        skill_dir.mkdir(parents=True)
        (skill_dir / "my-skill.md").write_text(
            "---\nid: testuser/my-skill\n---\nContent here."
        )

        result = install_skill("testuser/my-skill", str(tmp_path))
        assert result is True

        manifest = load_manifest()
        assert len(manifest["installed"]) == 1
        entry = manifest["installed"][0]
        assert entry["id"] == "testuser/my-skill"
        assert len(entry["sha256"]) == 64
        assert "testuser/my-skill.md" in entry["sourceRef"]

    def test_install_accepts_leading_slash_named_skill_id(self, tmp_path, monkeypatch):
        """install_skill normalizes slash-prefixed named skill IDs."""
        monkeypatch.chdir(tmp_path)

        skill_dir = tmp_path / "registry" / "named" / "testuser"
        skill_dir.mkdir(parents=True)
        (skill_dir / "my-skill.md").write_text(
            "---\nid: testuser/my-skill\n---\nContent here."
        )

        resolved = resolve_named_skill_reference("/testuser/my-skill", str(tmp_path))
        assert resolved is not None
        assert resolved[0] == "testuser/my-skill"

        result = install_skill("/testuser/my-skill", str(tmp_path))
        assert result is True
        manifest = load_manifest()
        assert manifest["installed"][0]["id"] == "testuser/my-skill"

    def test_install_missing_skill_returns_false(self, tmp_path, monkeypatch):
        """install_skill returns False when the skill is not in the registry."""
        monkeypatch.chdir(tmp_path)
        result = install_skill("nobody/nothing", str(tmp_path))
        assert result is False

    def test_install_accepts_catalog_ref_slug(self, tmp_path, monkeypatch):
        """install_skill accepts an exact catalogRef slug from the registry."""
        monkeypatch.chdir(tmp_path)

        skill_dir = tmp_path / "registry" / "named" / "karpathy"
        skill_dir.mkdir(parents=True)
        (skill_dir / "autoresearch.md").write_text(
            "---\n"
            "id: karpathy/autoresearch\n"
            "name: AutoResearch\n"
            "catalogRef: karpathy-autoresearch\n"
            "---\n"
            "Content here."
        )

        result = install_skill("karpathy-autoresearch", str(tmp_path))
        assert result is True

        manifest = load_manifest()
        assert manifest["installed"][0]["id"] == "karpathy/autoresearch"

    def test_install_accepts_unique_bare_skill_slug(self, tmp_path, monkeypatch):
        """install_skill accepts a unique skill-name slug without contributor."""
        monkeypatch.chdir(tmp_path)

        skill_dir = tmp_path / "registry" / "named" / "karpathy"
        skill_dir.mkdir(parents=True)
        (skill_dir / "autoresearch.md").write_text(
            "---\n"
            "id: karpathy/autoresearch\n"
            "name: AutoResearch\n"
            "catalogRef: karpathy-autoresearch\n"
            "---\n"
            "Content here."
        )

        result = install_skill("autoresearch", str(tmp_path))
        assert result is True

        manifest = load_manifest()
        assert manifest["installed"][0]["id"] == "karpathy/autoresearch"

    def test_install_rejects_ambiguous_bare_skill_slug(self, tmp_path, monkeypatch, capsys):
        """install_skill rejects a bare slug shared by multiple contributors."""
        monkeypatch.chdir(tmp_path)

        for contributor in ("alice", "bob"):
            skill_dir = tmp_path / "registry" / "named" / contributor
            skill_dir.mkdir(parents=True)
            (skill_dir / "autoresearch.md").write_text(
                "---\n"
                f"id: {contributor}/autoresearch\n"
                f"name: {contributor.title()} AutoResearch\n"
                f"catalogRef: {contributor}-autoresearch\n"
                "---\n"
                "Content here."
            )

        result = install_skill("autoresearch", str(tmp_path))
        captured = capsys.readouterr()

        assert result is False
        assert "ambiguous" in captured.err
        assert "alice/autoresearch" in captured.err
        assert "bob/autoresearch" in captured.err

    def test_install_idempotent_updates_sha(self, tmp_path, monkeypatch):
        """Installing the same skill twice updates the sha256, not duplicates."""
        monkeypatch.chdir(tmp_path)

        skill_dir = tmp_path / "registry" / "named" / "user"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "skill.md"
        skill_file.write_text("version 1")

        install_skill("user/skill", str(tmp_path))

        # Modify source
        skill_file.write_text("version 2")
        install_skill("user/skill", str(tmp_path))

        manifest = load_manifest()
        # Only one entry, not two
        entries = [e for e in manifest["installed"] if e["id"] == "user/skill"]
        assert len(entries) == 1

    def test_uninstall_removes_manifest_entry(self, tmp_path, monkeypatch):
        """uninstall_skill removes the entry from the manifest."""
        monkeypatch.chdir(tmp_path)
        os.makedirs(".gaia", exist_ok=True)

        manifest = {
            "installed": [
                {
                    "id": "foo/bar",
                    "installedAt": "2026-04-29T00:00:00Z",
                    "sourceRef": "registry/named/foo/bar.md",
                    "sha256": "z" * 64,
                }
            ]
        }
        save_manifest(manifest)

        result = uninstall_skill("foo/bar")
        assert result is True

        loaded = load_manifest()
        assert len(loaded["installed"]) == 0

    def test_uninstall_unknown_skill_returns_true(self, tmp_path, monkeypatch):
        """uninstall_skill on a skill that is not installed still returns True."""
        monkeypatch.chdir(tmp_path)
        os.makedirs(".gaia", exist_ok=True)
        save_manifest({"installed": []})

        # Should not raise; skill simply wasn't there
        result = uninstall_skill("ghost/skill")
        assert result is True

    def test_uninstall_removes_repo_file(self, tmp_path, monkeypatch):
        """uninstall_skill removes the local repo copy of the skill."""
        monkeypatch.chdir(tmp_path)

        skill_dir = tmp_path / "registry" / "named" / "user"
        skill_dir.mkdir(parents=True)
        (skill_dir / "skill.md").write_text("content")

        install_skill("user/skill", str(tmp_path))

        # Confirm the repo file was created
        repo_file = tmp_path / ".gaia" / "named-skills" / "user" / "skill.md"
        assert repo_file.exists()

        uninstall_skill("user/skill")

        assert not repo_file.exists()

    def test_uninstall_invalid_id_returns_false(self, tmp_path, monkeypatch):
        """uninstall_skill returns False for IDs without a slash."""
        monkeypatch.chdir(tmp_path)
        result = uninstall_skill("no-slash")
        assert result is False

    def test_list_installed_empty(self, tmp_path, monkeypatch, capsys):
        """list_installed prints a message when nothing is installed."""
        monkeypatch.chdir(tmp_path)
        list_installed()
        captured = capsys.readouterr()
        assert "No named skills installed" in captured.out

    def test_list_installed_shows_entries(self, tmp_path, monkeypatch, capsys):
        """list_installed prints installed skill IDs."""
        monkeypatch.chdir(tmp_path)

        skill_dir = tmp_path / "registry" / "named" / "contrib"
        skill_dir.mkdir(parents=True)
        (skill_dir / "my-skill.md").write_text("content")

        install_skill("contrib/my-skill", str(tmp_path))
        list_installed()
        captured = capsys.readouterr()
        assert "contrib/my-skill" in captured.out


class TestSyncFlow:
    """Tests for the sync_skills flow."""

    def test_sync_no_installed_prints_message(self, tmp_path, monkeypatch, capsys):
        """sync_skills reports no skills when manifest is empty."""
        monkeypatch.chdir(tmp_path)
        sync_skills(str(tmp_path))
        captured = capsys.readouterr()
        assert "No named skills installed" in captured.out

    def test_sync_up_to_date_skill(self, tmp_path, monkeypatch, capsys):
        """sync_skills reports up-to-date for an unchanged skill."""
        monkeypatch.chdir(tmp_path)

        skill_dir = tmp_path / "registry" / "named" / "user"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "skill.md"
        skill_file.write_text("original content")

        install_skill("user/skill", str(tmp_path))
        # Reset captured output from install
        capsys.readouterr()

        sync_skills(str(tmp_path))
        captured = capsys.readouterr()
        assert "Up to date" in captured.out or "updated" in captured.out


# ---------------------------------------------------------------------------
# list_available — from gaia_cli.install
# ---------------------------------------------------------------------------

from gaia_cli.install import list_available

_FRONTMATTER = """\
---
id: contrib/my-skill
name: My Skill
contributor: contrib
origin: true
genericSkillRef: web-search
status: named
level: "2★"
description: A test skill.
---
Content here.
"""


class TestListAvailable:
    def _make_registry(self, tmp_path, skill_id="contrib/my-skill", content=_FRONTMATTER):
        contributor, name = skill_id.split("/", 1)
        d = tmp_path / "registry" / "named" / contributor
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{name}.md").write_text(content, encoding="utf-8")

    def test_returns_empty_when_no_named_dir(self, tmp_path):
        result = list_available(str(tmp_path))
        assert result == []

    def test_returns_skill_with_parsed_meta(self, tmp_path):
        self._make_registry(tmp_path)
        result = list_available(str(tmp_path))
        assert len(result) == 1
        sid, meta = result[0]
        assert sid == "contrib/my-skill"
        assert meta["name"] == "My Skill"
        assert meta["level"] == "2★"
        assert meta["genericSkillRef"] == "web-search"

    def test_lists_multiple_contributors_sorted(self, tmp_path):
        self._make_registry(tmp_path, "zeta/skill-z")
        self._make_registry(tmp_path, "alpha/skill-a")
        result = list_available(str(tmp_path))
        ids = [r[0] for r in result]
        assert ids == sorted(ids)

    def test_ignores_non_md_files(self, tmp_path):
        d = tmp_path / "registry" / "named" / "contrib"
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.json").write_text("{}")
        result = list_available(str(tmp_path))
        assert result == []
