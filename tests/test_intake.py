import json
import os
import subprocess
import sys
import tempfile
import unittest
import pytest
pytestmark = [pytest.mark.integration, pytest.mark.slow]



REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VALIDATE_INTAKE_SCRIPT = os.path.join(REPO_ROOT, "scripts", "validate_intake.py")
GRAPH_PATH = os.path.join(REPO_ROOT, "registry", "gaia.json")


def run_validate_intake(intake_dir, *extra_args):
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(
        [
            sys.executable,
            VALIDATE_INTAKE_SCRIPT,
            "--intake-dir",
            intake_dir,
            "--graph",
            GRAPH_PATH,
            *extra_args,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )
    return result.returncode, result.stdout


def write_batch(root, batch_id, proposed_id="semantic-search", similarity_target="web-search"):
    os.makedirs(os.path.join(root, "skill-batches"), exist_ok=True)
    batch = {
        "batchId": batch_id,
        "userId": "tester",
        "sourceRepo": "tester/example",
        "generatedAt": "2026-04-29T00:00:00Z",
        "knownSkills": [{"skillId": "web-search"}],
        "proposedSkills": [
            {
                "id": proposed_id,
                "name": "Semantic Search",
                "type": "basic",
                "description": "Finds conceptually related content using meaning rather than exact keyword overlap.",
                "sourceRepo": "tester/example",
            }
        ],
        "similarity": [
            {
                "sourceSkillId": proposed_id,
                "targetSkillId": similarity_target,
                "score": 0.73,
                "reason": "Lexically similar search-oriented capability.",
            }
        ],
    }
    with open(os.path.join(root, "skill-batches", f"{batch_id}.json"), "w") as f:
        json.dump(batch, f)


class TestIntakeValidation(unittest.TestCase):
    def test_valid_batch_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_batch(tmp, "batch-one")
            code, out = run_validate_intake(tmp)
            self.assertEqual(code, 0, out)
            self.assertIn("All intake checks passed.", out)

    def test_duplicate_proposed_id_against_canonical_warns(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_batch(tmp, "batch-one", proposed_id="web-search")
            code, out = run_validate_intake(tmp)
            self.assertEqual(code, 0, out)
            self.assertIn("already exists as a generic skill", out)
            self.assertIn("Treating this proposal as a named-skill submission", out)
            self.assertIn("All intake checks passed.", out)

    def test_strict_duplicate_proposed_id_against_canonical_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_batch(tmp, "batch-one", proposed_id="web-search")
            code, out = run_validate_intake(tmp, "--strict")
            self.assertEqual(code, 1)
            self.assertIn("already exists as a generic skill", out)

    def test_duplicate_proposed_ids_across_batches_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_batch(tmp, "batch-one", proposed_id="semantic-search")
            write_batch(tmp, "batch-two", proposed_id="semantic-search")
            code, out = run_validate_intake(tmp)
            self.assertEqual(code, 1)
            self.assertIn("Duplicate proposed skill", out)

    def test_missing_similarity_reference_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_batch(tmp, "batch-one", similarity_target="missingSkill")
            code, out = run_validate_intake(tmp)
            self.assertEqual(code, 1)
            self.assertIn("unknown targetSkillId", out)


if __name__ == "__main__":
    unittest.main()
