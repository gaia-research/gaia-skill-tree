import subprocess
import os
import sys
import unittest
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Define paths
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VALIDATE_SCRIPT = os.path.join(REPO_ROOT, "scripts", "validate.py")
FIXTURES_DIR = os.path.join(REPO_ROOT, "tests", "fixtures")
REAL_GRAPH_PATH = os.path.join(REPO_ROOT, "registry", "gaia.json")

def run_validate(graph_path):
    """Helper to run validate.py and return (exit_code, stdout)."""
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(
        ["python3", VALIDATE_SCRIPT, "--graph", graph_path],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env
    )
    return result.returncode, result.stdout

class TestValidate(unittest.TestCase):
    def test_clean_graph(self):
        """Ensure the real gaia.json passes validation."""
        code, out = run_validate(REAL_GRAPH_PATH)
        self.assertEqual(code, 0, f"Expected clean graph to pass, but it failed with output:\n{out}")
        self.assertIn("All validation checks passed.", out)

    def test_cycle(self):
        """Ensure a cycle is detected."""
        code, out = run_validate(os.path.join(FIXTURES_DIR, "cycle.json"))
        self.assertEqual(code, 1, "Expected cycle graph to fail validation.")
        self.assertIn("Cycle detected:", out)

    def test_missing_ref(self):
        """Ensure a missing reference is detected."""
        code, out = run_validate(os.path.join(FIXTURES_DIR, "missing_ref.json"))
        self.assertEqual(code, 1, "Expected missing ref graph to fail validation.")
        self.assertIn("references missing prerequisite", out)

    def test_duplicate_skill_id(self):
        """Ensure duplicate skill IDs are rejected."""
        code, out = run_validate(os.path.join(FIXTURES_DIR, "duplicate_id.json"))
        self.assertEqual(code, 1, "Expected duplicate skill ID graph to fail validation.")
        self.assertIn("Duplicate skill id", out)

    def test_duplicate_edge(self):
        """Ensure duplicate graph edges are rejected."""
        code, out = run_validate(os.path.join(FIXTURES_DIR, "duplicate_edge.json"))
        self.assertEqual(code, 1, "Expected duplicate edge graph to fail validation.")
        self.assertIn("Duplicate edge", out)

    def test_bad_evidence(self):
        """Ensure insufficient evidence is caught."""
        code, out = run_validate(os.path.join(FIXTURES_DIR, "bad_evidence.json"))
        self.assertEqual(code, 1, "Expected bad evidence graph to fail validation.")
        self.assertIn("needs evidence class", out)

    def test_orphaned_composite(self):
        """Ensure extras with < 2 prerequisites are caught."""
        code, out = run_validate(os.path.join(FIXTURES_DIR, "orphaned_extra.json"))
        self.assertEqual(code, 1, "Expected orphaned extra to fail validation.")
        self.assertIn("needs ≥2 prerequisites", out)

    def test_legendary_no_approval(self):
        """Ensure validated ultimate with < 3 Class A/B evidence is caught."""
        code, out = run_validate(os.path.join(FIXTURES_DIR, "ultimate_no_approval.json"))
        self.assertEqual(code, 1, "Expected ultimate with no approval to fail validation.")
        self.assertIn("Validated ultimate", out)
        self.assertIn("needs ≥3 Class A/B evidence", out)

    def test_atomic_with_prerequisites(self):
        """Ensure a basic skill that declares prerequisites is rejected."""
        code, out = run_validate(os.path.join(FIXTURES_DIR, "basic_with_prereqs.json"))
        self.assertEqual(code, 1, "Expected basic-with-prereqs to fail validation.")
        self.assertIn("must have 0 prerequisites", out)

    def test_demerits_rejected_on_generic_nodes(self):
        """Generic refs are rank-less — demerits are no longer a valid field
        and must be rejected by the schema (additionalProperties: false)."""
        code, out = run_validate(os.path.join(FIXTURES_DIR, "demerits_unknown_id.json"))
        self.assertEqual(code, 1, "Expected demerits on a generic node to fail validation.")
        self.assertIn("demerits", out)
        self.assertIn("Additional properties are not allowed", out)

    def test_seeded_skills_have_no_demerits(self):
        """Generic refs are rank-less, so no seeded skill carries demerits."""
        with open(REAL_GRAPH_PATH, encoding="utf-8") as f:
            graph = json.load(f)

        offenders = [s["id"] for s in graph.get("skills", []) if s.get("demerits")]
        self.assertEqual(
            offenders, [],
            f"No generic skill should carry demerits, but found: {offenders}",
        )

    def test_gaia_audit_skills_are_modeled(self):
        """Ensure Gaia audit workflows are represented as canonical skills."""
        with open(REAL_GRAPH_PATH, encoding="utf-8") as f:
            graph = json.load(f)
        skills = {skill["id"]: skill for skill in graph.get("skills", [])}

        # PR #525: brand-coupled `gaia-audit` / `gaia-meta-audit` were renamed
        # to abstract generics per META §1. The repo-local slash skills at
        # .agents/skills/gaia-{audit,meta-audit}/ implement these generics.
        self.assertIn("registry-entry-audit", skills)
        self.assertIn("registry-health-scan", skills)
        self.assertEqual(
            skills["registry-entry-audit"]["prerequisites"],
            ["retrieve", "cite-sources", "evaluate-output"],
        )
        self.assertIn("registry-entry-audit", skills["registry-health-scan"]["prerequisites"])
        self.assertIn("registry-curation", skills["registry-health-scan"]["prerequisites"])

    def test_contributing_documents_demotion_criteria(self):
        """Ensure review policy documents when skills should be demoted."""
        path = os.path.join(REPO_ROOT, "CONTRIBUTING.md")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        normalized = text.lower()

        self.assertIn("Demotion and Reclassification Criteria", text)
        self.assertIn("outdated", normalized)
        self.assertIn("superseded", normalized)
        self.assertIn("overpromoted", normalized)
        self.assertIn("insufficient usage evidence", normalized)
        self.assertIn("Reviewers should use `/gaia-audit`", text)
        self.assertIn("Reviewers should use `/gaia-meta-audit`", text)

    def test_agents_audit_skills_exist(self):
        """Ensure the repo-local audit slash skills are present."""
        # PR #525: standardized SKILL.md (uppercase) across all .agents/skills/
        # entries to fix Star Bar 404s on case-sensitive GitHub raw paths.
        for skill_name in ("gaia-audit", "gaia-meta-audit"):
            path = os.path.join(REPO_ROOT, ".agents", "skills", skill_name, "SKILL.md")
            self.assertTrue(os.path.exists(path), f"Missing {path}")
            with open(path, encoding="utf-8") as f:
                text = f.read()
            self.assertIn(f"name: {skill_name}", text)
            self.assertIn("description:", text)

class TestNamedSkillValidation(unittest.TestCase):
    """Tests that verify named skill files pass validate_and_group rules."""

    def test_seed_skills_have_valid_levels(self):
        """All seed named skills have a level in the valid set (2★–6★)."""
        from scripts.generateNamedIndex import load_named_skills, validate_and_group

        named_dir = os.path.join(REPO_ROOT, "registry", "named")
        if not os.path.isdir(named_dir):
            self.skipTest("Named skills directory not present.")

        named_skills = load_named_skills(named_dir)
        named_skills = [(fp, fm) for fp, fm in named_skills if not fp.endswith("index.json")]

        with open(REAL_GRAPH_PATH, "r", encoding="utf-8") as f:
            graph_data = json.load(f)
        errors, buckets, *_ = validate_and_group(named_skills, graph_data)

        self.assertEqual(
            errors,
            [],
            f"Seed named skills failed validation:\n" + "\n".join(errors),
        )

    def test_seed_skills_have_no_level_i(self):
        """No seed named skill uses 1★ (which is forbidden for named skills)."""
        from scripts.generateNamedIndex import load_named_skills, parse_frontmatter

        named_dir = os.path.join(REPO_ROOT, "registry", "named")
        if not os.path.isdir(named_dir):
            self.skipTest("Named skills directory not present.")

        named_skills = load_named_skills(named_dir)
        named_skills = [(fp, fm) for fp, fm in named_skills if not fp.endswith("index.json")]

        for fp, fm in named_skills:
            level = fm.get("level", "")
            self.assertNotEqual(
                level,
                "1★",
                f"Seed skill {fp} has forbidden level '1★'.",
            )

    def test_bad_level_fails_validation(self):
        """validate_and_group reports an error when level is '1★'."""
        from scripts.generateNamedIndex import validate_and_group

        named_skills = [
            (
                "registry/named/fake/skill.md",
                {
                    "id": "fake/skill",
                    "name": "Fake",
                    "contributor": "fake",
                    "origin": True,
                    "genericSkillRef": "web-search",
                    "status": "named",
                    "level": "1★",
                    "description": "A fake skill at 1★.",
                },
            )
        ]
        errors, *_ = validate_and_group(named_skills, {"skills": [{"id": "web-search"}]})
        self.assertTrue(
            any("level" in e.lower() or "'1★'" in e or "1★" in e or "2★ or above" in e
                for e in errors),
            f"Expected a level error, got: {errors}",
        )

    def test_missing_required_field_fails_validation(self):
        """validate_and_group reports an error for missing required fields."""
        from scripts.generateNamedIndex import validate_and_group

        named_skills = [
            (
                "registry/named/fake/incomplete.md",
                {
                    "id": "fake/incomplete",
                    # Missing: name, contributor, origin, genericSkillRef, status, level, description
                },
            )
        ]
        errors, *_ = validate_and_group(named_skills, {"skills": []})
        self.assertGreater(len(errors), 0, "Expected errors for missing required fields.")

    def test_unresolved_generic_ref_fails_validation(self):
        """validate_and_group reports an error when genericSkillRef is not in gaia.json."""
        from scripts.generateNamedIndex import validate_and_group

        named_skills = [
            (
                "registry/named/fake/skill.md",
                {
                    "id": "fake/skill",
                    "name": "Fake Skill",
                    "contributor": "fake",
                    "origin": True,
                    "genericSkillRef": "definitely-not-a-real-skill-id",
                    "status": "named",
                    "level": "2★",
                    "description": "A skill that references a nonexistent generic skill.",
                },
            )
        ]
        errors, *_ = validate_and_group(named_skills, {"skills": [{"id": "web-search"}]})
        self.assertTrue(
            any("definitely-not-a-real-skill-id" in e for e in errors),
            f"Expected unresolved-ref error, got: {errors}",
        )


if __name__ == "__main__":
    unittest.main()
