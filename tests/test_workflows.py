import os
import unittest
import pytest
pytestmark = [pytest.mark.integration, pytest.mark.slow]



REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUTO_TRIAGE_PATH = os.path.join(REPO_ROOT, ".github", "workflows", "auto-triage.yml")
BRANCH_SCOPE_PATH = os.path.join(REPO_ROOT, ".github", "workflows", "branch-scope.yml")


class TestWorkflowConfig(unittest.TestCase):
    def test_auto_triage_watches_intake_paths(self):
        with open(AUTO_TRIAGE_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn('- "registry-for-review/**"', content)
        self.assertIn('gh label create "intake"', content)
        self.assertIn('--add-label "intake"', content)

    def test_auto_triage_uses_pull_request_target(self):
        """Regression: pull_request gives read-only token on fork PRs, breaking label writes."""
        with open(AUTO_TRIAGE_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("pull_request_target", content)
        self.assertNotIn("on:\n  pull_request:\n", content)

    def test_branch_scope_allows_dev_schema_consolidation(self):
        with open(BRANCH_SCOPE_PATH, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("have no forward restriction", content)
        self.assertIn('[ "$PREFIX" != "unrestricted" ]', content)
        self.assertIn("skip-scope-check", content)
        self.assertNotIn("!startsWith(github.head_ref || '', 'dev/')", content)

        # Every prefix CLAUDE.md documents as unrestricted must classify as
        # unrestricted here. integration/* is the one multi-PR work assembles
        # on, so a missing case statement fails exactly the branch shape the
        # founder ruling requires.
        for prefix in ("dev", "integration", "claude", "codex", "gemini", "chore", "fix"):
            self.assertIn(f'{prefix}/*)', content)
            self.assertRegex(content, rf'{prefix}/\*\)\s+PREFIX="unrestricted"')


if __name__ == "__main__":
    unittest.main()
