import os
import sys
import tempfile
import unittest
from unittest.mock import patch
import pytest
pytestmark = [pytest.mark.integration]



REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from gaia_cli.prWriter import _run, _render_named_block, build_intake_issue_body


class TestPrWriterBatchRender(unittest.TestCase):
    """Tests for the rich/legacy rendering split and named block safety."""

    def _base_batch(self, **overrides):
        base = {
            "batchId": "test-batch",
            "userId": "testuser",
            "sourceRepo": "owner/repo",
            "generatedAt": "2026-01-01T00:00:00Z",
            "fromFile": False,
            "knownSkills": [],
            "proposedSkills": [],
            "similarity": [],
        }
        base.update(overrides)
        return base

    def test_fromfile_true_minimal_skill_uses_details_blocks(self):
        """fromFile=True must gate rich rendering even with no attribution/evidence."""
        batch = self._base_batch(
            fromFile=True,
            proposedSkills=[{"id": "minimal-skill", "name": "Minimal", "type": "basic"}],
        )
        body = build_intake_issue_body(batch)
        self.assertIn("<details>", body, "fromFile=True batch must use <details> blocks")

    def test_fromfile_false_minimal_skill_uses_flat_table(self):
        """fromFile=False with no rich fields must fall back to legacy flat table."""
        batch = self._base_batch(
            fromFile=False,
            proposedSkills=[{"id": "minimal-skill", "name": "Minimal", "type": "basic"}],
        )
        body = build_intake_issue_body(batch)
        self.assertNotIn("<details>", body)
        self.assertIn("| ID |", body)

    def test_checklist_headings_are_lowercase(self):
        """Heading case must match what prWriter emits (fixes pre-existing assertion)."""
        batch = self._base_batch()
        body = build_intake_issue_body(batch)
        self.assertIn("### Reviewer checklist", body)
        self.assertIn("### Maintainer promotion checklist", body)

    def test_render_named_block_brace_in_contributor_does_not_raise(self):
        """Braces in contributor handle must not cause IndexError/KeyError."""
        named = {
            "contributor": "user{broken}",
            "level": "3★",
            "links_github": "https://github.com/a/b",
        }
        try:
            result = _render_named_block(named, "my-skill")
        except (IndexError, KeyError) as exc:
            self.fail(f"_render_named_block raised {type(exc).__name__}: {exc}")
        self.assertIn("my-skill", result)
        self.assertIn("user{broken}", result)

    def test_render_named_block_skill_id_embedded_correctly(self):
        """Named block must embed skillId directly, not via deferred format()."""
        named = {"contributor": "foo", "level": "2★", "links_github": "https://github.com/a/b"}
        result = _render_named_block(named, "my-target-skill")
        self.assertIn("foo/my-target-skill", result)


class TestPrWriterLegacy(unittest.TestCase):
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
        self.assertIn("| Known canonical skills | `1` |", body)
        self.assertIn("| Proposed new skills | `1` |", body)
        self.assertIn("`semantic-search`", body)
        self.assertIn("`web-search` (0.730)", body)
        self.assertIn("### Reviewer checklist", body)
        self.assertIn("### Maintainer promotion checklist", body)

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
