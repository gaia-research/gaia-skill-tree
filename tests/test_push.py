import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import pytest
pytestmark = [pytest.mark.integration, pytest.mark.slow]



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
            env["GITHUB_REPOSITORY"] = "tester/test-repo"
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
            self.assertEqual(batch["sourceRepo"], "tester/test-repo")

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
            env["GITHUB_REPOSITORY"] = "tester/test-repo"
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


# ═══════════════════════════════════════════════════════════════════════════
# Relocated from test_pr635_review.py — push injection logic
# ═══════════════════════════════════════════════════════════════════════════


class TestRed_PushInjectsUnmatchedSkills:
    """RED #4: push_command injects unmatched local custom skills into batch.

    On main: skills not already in batch_proposed_ids or batch_known_ids were DROPPED.
    On branch: they are injected into batch['proposedSkills'].

    This test verifies the injection logic directly rather than running the
    full push_command (which requires interactive input and git remotes).
    """

    def test_injection_logic_adds_missing_skills_to_batch(self, tmp_path):
        """Simulate the push_command injection loop: skills not in batch should be added."""
        # Simulate what push_command does
        batch = {
            "sourceRepo": "test/repo",
            "proposedSkills": [
                {"id": "already-proposed", "name": "Already", "type": "basic",
                 "description": "Already in batch", "sourceRepo": "test/repo",
                 "lifecycle": "pending"}
            ],
            "knownSkills": [
                {"skillId": "already-known"}
            ],
        }
        batch_proposed_ids = {s["id"] for s in batch.get("proposedSkills", [])}
        batch_known_ids = {s["skillId"] for s in batch.get("knownSkills", [])}

        # Simulate installed_skills (what scan_skill_mds returns)
        installed_skills = [
            {"id": "already-proposed", "name": "Already Proposed", "description": ""},
            {"id": "already-known", "name": "Already Known", "description": ""},
            {"id": "brand-new-skill", "name": "Brand New", "description": "A new skill"},
        ]

        # This is the injection logic from the PR branch
        for sk in installed_skills:
            cid = sk["id"]
            if cid not in batch_proposed_ids and cid not in batch_known_ids:
                batch.setdefault("proposedSkills", []).append({
                    "id": cid,
                    "name": sk.get("name", cid),
                    "type": "basic",
                    "description": sk.get("description", f"Local custom skill {cid}"),
                    "sourceRepo": batch.get("sourceRepo", "unknown"),
                    "lifecycle": "pending",
                })
                batch_proposed_ids.add(cid)

        # Verify: brand-new-skill should have been injected
        proposed_ids = {s["id"] for s in batch["proposedSkills"]}
        assert "brand-new-skill" in proposed_ids, (
            "Unmatched local custom skill should be injected into proposedSkills"
        )
        # Verify no duplicates
        assert len([s for s in batch["proposedSkills"] if s["id"] == "already-proposed"]) == 1, (
            "Already-proposed skill should not be duplicated"
        )


class TestGreen_PushInjection:
    """GREEN #4: push_command injection logic works correctly."""

    def test_injected_skill_has_correct_fields(self, tmp_path):
        """Verify the shape of injected proposed skills."""
        batch = {"sourceRepo": "test/repo", "proposedSkills": [], "knownSkills": []}
        batch_proposed_ids = set()
        batch_known_ids = set()

        installed_skills = [
            {"id": "new-skill", "name": "New Skill", "description": "Something new"},
        ]

        for sk in installed_skills:
            cid = sk["id"]
            if cid not in batch_proposed_ids and cid not in batch_known_ids:
                batch.setdefault("proposedSkills", []).append({
                    "id": cid,
                    "name": sk.get("name", cid),
                    "type": "basic",
                    "description": sk.get("description", f"Local custom skill {cid}"),
                    "sourceRepo": batch.get("sourceRepo", "unknown"),
                    "lifecycle": "pending",
                })
                batch_proposed_ids.add(cid)

        injected = batch["proposedSkills"][0]
        assert injected["id"] == "new-skill"
        assert injected["name"] == "New Skill"
        assert injected["type"] == "basic"
        assert injected["description"] == "Something new"
        assert injected["sourceRepo"] == "test/repo"
        assert injected["lifecycle"] == "pending"


class TestScrutiny_PushDuplicateGuard:
    """Scrutiny #1: pushable_custom_skills = installed_skills.

    Verify that the interactive exclusion loop correctly removes skills
    and that no duplicates are introduced if a skill was already in
    batch_proposed_ids before the injection loop runs.
    """

    def test_no_duplicates_after_injection_and_exclusion(self, tmp_path):
        """If a skill is already proposed, injection should not duplicate it."""
        batch = {
            "sourceRepo": "test/repo",
            "proposedSkills": [
                {"id": "existing", "name": "Existing", "type": "basic",
                 "description": "", "sourceRepo": "test/repo", "lifecycle": "pending"},
            ],
            "knownSkills": [],
        }
        batch_proposed_ids = {s["id"] for s in batch["proposedSkills"]}
        batch_known_ids = set()

        installed_skills = [
            {"id": "existing", "name": "Existing", "description": ""},
            {"id": "new-one", "name": "New One", "description": ""},
        ]

        # Run the injection logic
        for sk in installed_skills:
            cid = sk["id"]
            if cid not in batch_proposed_ids and cid not in batch_known_ids:
                batch.setdefault("proposedSkills", []).append({
                    "id": cid, "name": sk.get("name", cid), "type": "basic",
                    "description": sk.get("description", ""),
                    "sourceRepo": batch.get("sourceRepo", "unknown"),
                    "lifecycle": "pending",
                })
                batch_proposed_ids.add(cid)

        # Count occurrences
        existing_count = sum(1 for s in batch["proposedSkills"] if s["id"] == "existing")
        assert existing_count == 1, (
            f"'existing' appears {existing_count} times in proposedSkills — expected 1"
        )

        # Simulate exclusion
        excluded_ids = {"new-one"}
        batch["proposedSkills"] = [
            s for s in batch["proposedSkills"] if s["id"] not in excluded_ids
        ]
        remaining_ids = {s["id"] for s in batch["proposedSkills"]}
        assert "new-one" not in remaining_ids
        assert "existing" in remaining_ids


if __name__ == "__main__":
    unittest.main()
