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


# ---------------------------------------------------------------------------
# Custom state fixture helpers
# ---------------------------------------------------------------------------

def _make_custom_state(tmp_dir):
    """Seed .gaia/custom_state.json with:
    - one starless (generic) skill mapped to web-search → knownSkills
    - one unmatched proposed skill (semantic-search) → proposedSkills
    - one custom fusion → proposedCombinations
    """
    gaia_dir = os.path.join(tmp_dir, ".gaia")
    os.makedirs(gaia_dir, exist_ok=True)
    custom_state = {
        "customSkills": [
            {
                "id": "/web-search",
                "name": "web-search",
                "description": "Web search skill",
                "match_type": "generic",
                "canon_level": "0★",
                "mapped_to": "/web-search",
                "mapped_score": 1.0,
                "skill_type": "basic",
                "prerequisites": [],
            },
            {
                "id": "/semantic-search",
                "name": "semantic-search",
                "description": "Semantic search candidate",
                "match_type": None,
                "canon_level": "0★",
                "mapped_to": None,
                "mapped_score": 0.0,
                "skill_type": "basic",
                "prerequisites": [],
            },
        ],
        "customFusions": {
            "/research-fusion": {
                "sources": ["/web-search", "/semantic-search"],
                "type": "extra",
                "level": "1★",
            }
        },
    }
    with open(os.path.join(gaia_dir, "custom_state.json"), "w") as f:
        json.dump(custom_state, f)


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
            # Seed custom_state.json so push has something to push
            _make_custom_state(tmp)

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
            # web-search is a starless generic skill → knownSkills with {skillId, localId}
            known_ids = [s["skillId"] for s in batch["knownSkills"]]
            self.assertIn("web-search", known_ids)
            # semantic-search is unmatched → proposedSkills
            proposed_ids = [s["id"] for s in batch["proposedSkills"]]
            self.assertIn("semantic-search", proposed_ids)
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
            # Seed custom_state.json so push has something to push
            _make_custom_state(tmp)

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
            # Seed custom_state.json: web-search as starless generic, semantic-search as unmatched
            _make_custom_state(tmp)
            # chdir to tmp so build_skill_batch reads .gaia/custom_state.json from the right place
            orig_cwd = os.getcwd()
            try:
                os.chdir(tmp)
                batch = build_skill_batch(
                    {},  # raw_tokens ignored in new implementation
                    {"gaiaUser": "tester"},
                    registry,
                    source_repo="tester/local-repo",  # avoid git detection in tests
                )
            finally:
                os.chdir(orig_cwd)
            # knownSkills uses {skillId, localId} shape
            known = {s["skillId"] for s in batch["knownSkills"]}
            self.assertIn("web-search", known)
            # proposedSkills: semantic-search (unmatched)
            proposed = {s["id"] for s in batch["proposedSkills"]}
            self.assertIn("semantic-search", proposed)
            # proposedCombinations: fusion entry
            self.assertEqual(len(batch["proposedCombinations"]), 1)
            combo = batch["proposedCombinations"][0]
            self.assertIn("candidateResult", combo)
            self.assertIn("detectedSkills", combo)
            self.assertIn("levelFloor", combo)
            self.assertIn("type", combo)

    def test_proposed_skill_has_lifecycle_pending(self):
        """build_skill_batch sets lifecycle: 'pending' on all proposed skills."""
        with tempfile.TemporaryDirectory() as tmp:
            registry = os.path.join(tmp, "registry")
            os.makedirs(os.path.join(registry, "registry"), exist_ok=True)
            shutil.copyfile(
                os.path.join(REPO_ROOT, "registry", "gaia.json"),
                os.path.join(registry, "registry", "gaia.json"),
            )
            _make_custom_state(tmp)
            orig_cwd = os.getcwd()
            try:
                os.chdir(tmp)
                batch = build_skill_batch(
                    {},
                    {"gaiaUser": "tester"},
                    registry,
                    source_repo="tester/local-repo",  # avoid git detection in tests
                )
            finally:
                os.chdir(orig_cwd)
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
            _make_custom_state(tmp)
            orig_cwd = os.getcwd()
            try:
                os.chdir(tmp)
                batch = build_skill_batch(
                    {},
                    {"gaiaUser": "tester"},
                    registry,
                    source_repo="tester/local-repo",  # avoid git detection in tests
                )
            finally:
                os.chdir(orig_cwd)
            for skill in batch.get("knownSkills", []):
                self.assertNotIn(
                    "lifecycle",
                    skill,
                    f"Known skill {skill} should not have a lifecycle field.",
                )


if __name__ == "__main__":
    unittest.main()
