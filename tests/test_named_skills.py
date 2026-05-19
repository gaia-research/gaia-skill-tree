import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class TestNamedSkillFrontmatter(unittest.TestCase):
    """Test YAML frontmatter parsing in generateNamedIndex."""

    def test_parse_valid_frontmatter(self):
        """parse_frontmatter correctly extracts key-value data."""
        from scripts.generateNamedIndex import parse_frontmatter
        content = """---
id: karpathy/autoresearch
name: AutoResearch
contributor: karpathy
origin: true
genericSkillRef: autonomous-research-agent
status: named
level: "2★"
description: Autonomous paper search and synthesis.
createdAt: "2026-04-29"
updatedAt: "2026-04-29"
---

## Overview
Body text here.
"""
        fm, _ = parse_frontmatter(content)
        self.assertEqual(fm.get("id"), "karpathy/autoresearch")
        self.assertEqual(fm.get("contributor"), "karpathy")
        self.assertTrue(fm.get("origin"))
        self.assertEqual(fm.get("level"), "2★")

    def test_parse_missing_frontmatter_returns_empty(self):
        """parse_frontmatter raises ValueError when no --- delimiters exist."""
        from scripts.generateNamedIndex import parse_frontmatter
        content = "No frontmatter here."
        with self.assertRaises(ValueError):
            parse_frontmatter(content)

    def test_parse_frontmatter_with_links(self):
        """parse_frontmatter handles nested links object."""
        from scripts.generateNamedIndex import parse_frontmatter
        content = """---
id: test/skill
name: Test
contributor: test
origin: false
genericSkillRef: web-search
status: named
level: "2★"
description: A test skill.
links:
  github: https://github.com/test/skill
createdAt: "2026-04-29"
updatedAt: "2026-04-29"
---
"""
        fm, _ = parse_frontmatter(content)
        links = fm.get("links", {})
        self.assertIn("github", links)


class TestNamedSkillIndexGeneration(unittest.TestCase):
    """Test generateNamedIndex.py bucket grouping and origin uniqueness."""

    def test_single_origin_per_bucket(self):
        """validate_and_group allows only one origin per genericSkillRef."""
        from scripts.generateNamedIndex import validate_and_group

        named_skills = [
            ("registry/named/alice/skill.md", {"id": "alice/skill", "name": "Skill", "contributor": "alice", "origin": True, "genericSkillRef": "web-search", "status": "named", "level": "2★", "description": "Alice's version."}),
            ("registry/named/bob/skill.md",   {"id": "bob/skill",   "name": "Skill", "contributor": "bob",   "origin": True, "genericSkillRef": "web-search", "status": "named", "level": "2★", "description": "Bob's version."}),
        ]
        valid_ids = {"web-search"}
        errors, *_ = validate_and_group(named_skills, valid_ids)
        self.assertTrue(any("origin" in e.lower() for e in errors), f"Expected origin duplicate error, got: {errors}")

    def test_bucket_groups_by_generic_ref(self):
        """validate_and_group returns correct bucket grouping."""
        from scripts.generateNamedIndex import validate_and_group

        named_skills = [
            ("registry/named/alice/skill-a.md", {"id": "alice/skill-a", "name": "Skill A", "contributor": "alice", "origin": True, "genericSkillRef": "web-search", "status": "named", "level": "2★", "description": "Alice version."}),
            ("registry/named/bob/skill-b.md",   {"id": "bob/skill-b",   "name": "Skill B", "contributor": "bob",   "origin": False, "genericSkillRef": "web-search", "status": "named", "level": "2★", "description": "Bob version."}),
            ("registry/named/carol/code.md",     {"id": "carol/code",    "name": "Carol Code", "contributor": "carol", "origin": True, "genericSkillRef": "code-generation", "status": "named", "level": "2★", "description": "Carol version."}),
        ]
        valid_ids = {"web-search", "code-generation"}
        errors, buckets, *_ = validate_and_group(named_skills, valid_ids)
        self.assertEqual(errors, [])
        self.assertIn("web-search", buckets)
        self.assertEqual(len(buckets["web-search"]), 2)
        self.assertEqual(buckets["web-search"][0]["role"], "origin")
        self.assertEqual(buckets["web-search"][1]["role"], "variant")
        self.assertIn("code-generation", buckets)
        self.assertEqual(len(buckets["code-generation"]), 1)

    def test_seed_index_json_is_valid(self):
        """The committed registry/named-skills.json is valid JSON with expected structure."""
        index_path = os.path.join(REPO_ROOT, "registry", "named-skills.json")
        if not os.path.exists(index_path):
            self.skipTest("registry/named-skills.json not present.")
        with open(index_path, encoding="utf-8") as f:
            index = json.load(f)
        self.assertIn("buckets", index)
        self.assertIn("generatedAt", index)
        self.assertIsInstance(index["buckets"], dict)


class TestInstallModule(unittest.TestCase):
    """Test the install/sync/uninstall logic."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        # Create a fake registry with a named skill
        self.registry = os.path.join(self.tmp, "registry")
        named_dir = os.path.join(self.registry, "registry", "named", "alice")
        os.makedirs(named_dir, exist_ok=True)
        self.skill_path = os.path.join(named_dir, "my-skill.md")
        with open(self.skill_path, "w") as f:
            f.write("---\nid: alice/my-skill\nlinks:\n  github: https://github.com/alice/repo/blob/main/my-skill/SKILL.md\n---\n\n# My Skill\n")
        # Working directory for install
        self.repo_dir = os.path.join(self.tmp, "repo")
        os.makedirs(self.repo_dir, exist_ok=True)
        self.orig_dir = os.getcwd()
        os.chdir(self.repo_dir)

    def tearDown(self):
        os.chdir(self.orig_dir)
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    @patch("gaia_cli.install._run_git", return_value=True)
    def test_install_creates_manifest(self, mock_run_git):
        """install_skill creates .gaia/install-manifest.json."""
        from gaia_cli.install import install_skill, get_manifest_path, load_manifest
        result = install_skill("alice/my-skill", self.registry)
        self.assertTrue(result)
        self.assertTrue(os.path.exists(get_manifest_path()))
        manifest = load_manifest()
        ids = [e["id"] for e in manifest["installed"]]
        self.assertIn("alice/my-skill", ids)

    @patch("gaia_cli.install._run_git", return_value=True)
    def test_uninstall_removes_from_manifest(self, mock_run_git):
        """uninstall_skill removes entry from manifest."""
        from gaia_cli.install import install_skill, uninstall_skill, load_manifest
        install_skill("alice/my-skill", self.registry)
        uninstall_skill("alice/my-skill")
        manifest = load_manifest()
        ids = [e["id"] for e in manifest["installed"]]
        self.assertNotIn("alice/my-skill", ids)

    def test_install_nonexistent_skill_fails(self):
        """install_skill returns False for unknown skill."""
        from gaia_cli.install import install_skill
        result = install_skill("nobody/fake-skill", self.registry)
        self.assertFalse(result)

    @patch("gaia_cli.install._run_git", return_value=True)
    def test_update_skills_pulls_repos(self, mock_run_git):
        """update_skills runs git pull on installed repos."""
        import io
        import os
        from contextlib import redirect_stdout
        from gaia_cli.install import install_skill, update_skills, get_global_cache_dir
        install_skill("alice/my-skill", self.registry)
        
        # Create the cache dir so update_skills finds it
        os.makedirs(os.path.join(get_global_cache_dir(), "alice", "repo"), exist_ok=True)
        
        buf = io.StringIO()
        with redirect_stdout(buf):
            update_skills(self.registry)
        output = buf.getvalue()
        self.assertIn("Checking for updates", output)
        self.assertIn("Pulling", output)


if __name__ == "__main__":
    unittest.main()
