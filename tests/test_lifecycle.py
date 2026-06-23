import json
import os
import sys
import tempfile
import unittest
import pytest
pytestmark = [pytest.mark.integration, pytest.mark.slow]


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestNamePromotion(unittest.TestCase):
    """Test gaia name promotion from intake batch to registry/named/."""

    def _make_batch(self, tmp, skill_id="new-skill"):
        batch = {
            "batchId": "test-batch-001",
            "userId": "tester",
            "sourceRepo": "tester/repo",
            "generatedAt": "2026-04-29T00:00:00Z",
            "knownSkills": [],
            "proposedSkills": [
                {
                    "id": skill_id,
                    "name": "New Skill",
                    "type": "atomic",
                    "description": "A brand new skill for testing.",
                    "sourceRepo": "tester/repo",
                    "lifecycle": "awakened",
                }
            ],
            "similarity": [],
        }
        path = os.path.join(tmp, "batch.json")
        with open(path, "w") as f:
            json.dump(batch, f)
        return path

    def test_find_awakened_skill_found(self):
        """find_awakened_skill returns skill data for a known skill ID."""
        from gaia_cli.name import find_awakened_skill
        with tempfile.TemporaryDirectory() as tmp:
            batch_path = self._make_batch(tmp, "new-skill")
            skill = find_awakened_skill(batch_path, "new-skill")
            self.assertIsNotNone(skill)
            self.assertEqual(skill["id"], "new-skill")

    def test_find_awakened_skill_not_found_raises(self):
        """find_awakened_skill raises ValueError for unknown skill ID."""
        from gaia_cli.name import find_awakened_skill
        with tempfile.TemporaryDirectory() as tmp:
            batch_path = self._make_batch(tmp, "new-skill")
            with self.assertRaises(ValueError):
                find_awakened_skill(batch_path, "nonexistent-skill")

    def test_promote_to_named_creates_file(self):
        """promote_to_named creates registry/named/{contributor}/{skill_name}.md."""
        from gaia_cli.name import promote_to_named
        with tempfile.TemporaryDirectory() as tmp:
            registry = os.path.join(tmp, "registry")
            os.makedirs(os.path.join(registry, "registry", "named"), exist_ok=True)
            skill_data = {
                "id": "new-skill",
                "name": "New Skill",
                "description": "A brand new skill for testing.",
                "lifecycle": "awakened",
            }
            promote_to_named(skill_data, "alice", "new-skill", registry)
            expected = os.path.join(registry, "registry", "named", "alice", "new-skill.md")
            self.assertTrue(os.path.exists(expected), f"Expected file at {expected}")

    def test_promote_to_named_file_contains_frontmatter(self):
        """promote_to_named writes valid YAML frontmatter."""
        from gaia_cli.name import promote_to_named
        with tempfile.TemporaryDirectory() as tmp:
            registry = os.path.join(tmp, "registry")
            os.makedirs(os.path.join(registry, "registry", "named"), exist_ok=True)
            skill_data = {
                "id": "new-skill",
                "name": "New Skill",
                "description": "A brand new skill for testing.",
            }
            promote_to_named(skill_data, "alice", "new-skill", registry)
            md_path = os.path.join(registry, "registry", "named", "alice", "new-skill.md")
            content = open(md_path).read()
            self.assertIn("contributor: alice", content)
            self.assertIn("origin: true", content)
            self.assertIn("status: named", content)

    def test_update_batch_lifecycle(self):
        """update_batch_lifecycle changes the lifecycle field in the batch file."""
        from gaia_cli.name import update_batch_lifecycle
        with tempfile.TemporaryDirectory() as tmp:
            batch_path = self._make_batch(tmp, "new-skill")
            update_batch_lifecycle(batch_path, "new-skill", "named")
            with open(batch_path) as f:
                batch = json.load(f)
            skill = next(s for s in batch["proposedSkills"] if s["id"] == "new-skill")
            self.assertEqual(skill["lifecycle"], "named")


if __name__ == "__main__":
    unittest.main()
