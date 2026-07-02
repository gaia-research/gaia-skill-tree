import os
import unittest

import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestApexTenureBackfill(unittest.TestCase):
    """Lock the approved mattpocock/skills evidence-tenure backfill."""

    def _read_frontmatter(self, filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        parts = content.split("---", 2)
        if len(parts) < 3:
            raise ValueError(f"No frontmatter found in {filepath}")
        return yaml.safe_load(parts[1])

    def test_mattpocock_skills_backfilled_rows_only(self):
        filepath = os.path.join(
            REPO_ROOT, "registry", "named", "mattpocock", "skills.md"
        )
        fm = self._read_frontmatter(filepath)
        evidence = fm.get("evidence", [])

        expected = {
            "https://github.com/mattpocock/skills/stargazers": "2026-02-03",
            "https://arxiv.org/abs/2602.20867": "2026-02-24",
        }

        for source, source_started_at in expected.items():
            with self.subTest(source=source):
                row = next((r for r in evidence if r.get("source") == source), None)
                self.assertIsNotNone(row, f"Evidence row not found: {source}")
                self.assertEqual(row.get("sourceStartedAt"), source_started_at)

    def test_backfill_does_not_claim_apex_tenure_passed(self):
        filepath = os.path.join(
            REPO_ROOT, "registry", "named", "mattpocock", "skills.md"
        )
        fm = self._read_frontmatter(filepath)

        self.assertFalse(
            fm.get("apexGateStatus", {}).get("sourceTenureDaysGte180AorS"),
            "Backfilled tenure dates must not flip the apex tenure gate in this PR.",
        )
