import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLI_PATH = os.path.join(REPO_ROOT, "packages", "cli-npm", "cli", "main.py")
sys.path.insert(0, REPO_ROOT)

from gaia_cli.push import build_skill_batch


class TestGaiaPush(unittest.TestCase):
    def test_push_dry_run_separates_known_and_proposed_skills(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, ".gaia"))
            os.makedirs(os.path.join(tmp, "src"))
            with open(os.path.join(tmp, ".gaia", "config.json"), "w") as f:
                json.dump(
                    {
                        "gaiaUser": "tester",
                        "gaiaRegistryRef": "main",
                        "scanPaths": ["src"],
                    },
                    f,
                )
            with open(os.path.join(tmp, "src", "agent.txt"), "w") as f:
                f.write("/web-search /semantic-search")

            env = os.environ.copy()
            env.pop("GITHUB_REPOSITORY", None)
            env["PYTHONPATH"] = REPO_ROOT
            env["PYTHONIOENCODING"] = "utf-8"
            result = subprocess.run(
                [
                    sys.executable,
                    CLI_PATH,
                    "--registry",
                    REPO_ROOT,
                    "push",
                    "--dry-run",
                ],
                cwd=tmp,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            batch = json.loads(result.stdout)
            self.assertEqual([s["skillId"] for s in batch["knownSkills"]], ["web-search"])
            self.assertEqual([s["id"] for s in batch["proposedSkills"]], ["semantic-search"])
            self.assertEqual(batch["userId"], "tester")
            self.assertEqual(batch["sourceRepo"], "tester/local-repo")

    def test_push_no_pr_writes_batch_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = os.path.join(tmp, "registry")
            os.makedirs(os.path.join(registry, "registry"), exist_ok=True)
            os.makedirs(os.path.join(registry, "registry-for-review", "skill-batches"), exist_ok=True)
            shutil.copyfile(os.path.join(REPO_ROOT, "registry", "gaia.json"), os.path.join(registry, "registry", "gaia.json"))
            os.makedirs(os.path.join(tmp, ".gaia"))
            os.makedirs(os.path.join(tmp, "src"))
            with open(os.path.join(tmp, ".gaia", "config.json"), "w") as f:
                json.dump(
                    {
                        "gaiaUser": "tester",
                        "gaiaRegistryRef": "main",
                        "scanPaths": ["src"],
                    },
                    f,
                )
            with open(os.path.join(tmp, "src", "agent.txt"), "w") as f:
                f.write("/web-search /semantic-search")

            env = os.environ.copy()
            env["PYTHONPATH"] = REPO_ROOT
            env["PYTHONIOENCODING"] = "utf-8"
            result = subprocess.run(
                [
                    sys.executable,
                    CLI_PATH,
                    "--registry",
                    registry,
                    "push",
                    "--no-pr",
                ],
                cwd=tmp,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Skipped issue creation", result.stdout)
            self.assertIn("saved ", result.stdout)
            self.assertTrue(os.listdir(os.path.join(registry, "registry-for-review", "skill-batches")))

    def test_proposed_filtering_keeps_known_and_removes_noise(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = os.path.join(tmp, "registry")
            os.makedirs(os.path.join(registry, "registry"), exist_ok=True)
            shutil.copyfile(os.path.join(REPO_ROOT, "registry", "gaia.json"), os.path.join(registry, "registry", "gaia.json"))
            batch = build_skill_batch(
                {"web-search", "a", "and", "semantic-search"},
                {"gaiaUser": "tester"},
                registry,
            )
            self.assertEqual([s["skillId"] for s in batch["knownSkills"]], ["web-search"])
            self.assertEqual([s["id"] for s in batch["proposedSkills"]], ["semantic-search"])


    def test_proposed_skill_has_lifecycle_pending(self):
        """build_skill_batch sets lifecycle: 'pending' on all proposed skills."""
        with tempfile.TemporaryDirectory() as tmp:
            registry = os.path.join(tmp, "registry")
            os.makedirs(os.path.join(registry, "registry"), exist_ok=True)
            shutil.copyfile(
                os.path.join(REPO_ROOT, "registry", "gaia.json"),
                os.path.join(registry, "registry", "gaia.json"),
            )
            batch = build_skill_batch(
                {"semantic-search", "web-search"},
                {"gaiaUser": "tester"},
                registry,
            )
            proposed = batch.get("proposedSkills", [])
            self.assertGreater(len(proposed), 0, "Expected at least one proposed skill.")
            for skill in proposed:
                self.assertEqual(
                    skill.get("lifecycle"),
                    "pending",
                    f"Expected lifecycle='pending' for proposed skill {skill['id']!r}, "
                    f"got {skill.get('lifecycle')!r}.",
                )

    def test_known_skills_have_no_lifecycle_field(self):
        """build_skill_batch does not add a lifecycle field to known skills."""
        with tempfile.TemporaryDirectory() as tmp:
            registry = os.path.join(tmp, "registry")
            os.makedirs(os.path.join(registry, "registry"), exist_ok=True)
            shutil.copyfile(
                os.path.join(REPO_ROOT, "registry", "gaia.json"),
                os.path.join(registry, "registry", "gaia.json"),
            )
            batch = build_skill_batch(
                {"web-search"},
                {"gaiaUser": "tester"},
                registry,
            )
            for skill in batch.get("knownSkills", []):
                self.assertNotIn(
                    "lifecycle",
                    skill,
                    f"Known skill {skill} should not have a lifecycle field.",
                )


if __name__ == "__main__":
    unittest.main()
