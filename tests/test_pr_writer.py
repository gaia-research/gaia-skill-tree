import os
import sys
import tempfile
import unittest
from unittest.mock import patch
import pytest
pytestmark = [pytest.mark.integration]



REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from gaia_cli.prWriter import _run, build_intake_issue_body


class TestPrWriter(unittest.TestCase):
    def test_build_intake_issue_body_contains_summary_table_and_checklists(self):
        batch = {
            "batchId": "20260429000000-tester-repo",
            "userId": "tester",
            "sourceRepo": "tester/repo",
            "generatedAt": "2026-04-29T00:00:00Z",
            "knownSkills": [{"skillId": "web-search"}],
            "proposedSkills": [
                {
                    "id": "semantic-search",
                    "name": "Semantic Search",
                    "type": "atomic",
                }
            ],
            "similarity": [
                {
                    "sourceSkillId": "semantic-search",
                    "targetSkillId": "web-search",
                    "score": 0.73,
                    "reason": "Lexical similarity from Gaia push scan.",
                }
            ],
        }
        body = build_intake_issue_body(batch)
        self.assertIn("Known canonical skills:** `1`", body)
        self.assertIn("Proposed new skills:** `1`", body)
        self.assertIn("`semantic-search`", body)
        self.assertIn("`web-search` (0.730)", body)
        self.assertIn("### Reviewer Checklist", body)
        self.assertIn("### Maintainer Promotion Checklist", body)

    def test_run_exposes_gaia_cli_to_subprocesses_outside_repo_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {}, clear=True):
                result = _run(
                    [
                        sys.executable,
                        "-S",
                        "-c",
                        "import gaia_cli; print(gaia_cli.__name__)",
                    ],
                    cwd=tmp,
                )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("gaia_cli", result.stdout)


if __name__ == "__main__":
    unittest.main()
