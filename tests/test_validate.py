import subprocess
import os
import sys
import unittest
import json

import pytest
pytestmark = [pytest.mark.integration, pytest.mark.slow]


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
        [sys.executable, VALIDATE_SCRIPT, "--graph", graph_path],
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

    @pytest.mark.smoke
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
        # PR #827: consolidated all skills to .claude/skills/ — .agents/ removed.
        for skill_name in ("gaia-audit", "gaia-meta-audit"):
            path = os.path.join(REPO_ROOT, ".claude", "skills", skill_name, "SKILL.md")
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

    def test_invalid_github_url_casing_fails_validation(self):
        """validate_named_skills reports an error when links.github URL has invalid casing (e.g. skill.md)."""
        import tempfile
        import shutil
        from scripts.validate import validate_named_skills

        temp_named_dir = tempfile.mkdtemp()
        try:
            fake_author_dir = os.path.join(temp_named_dir, "fake_author")
            os.makedirs(fake_author_dir)
            
            fake_skill_file = os.path.join(fake_author_dir, "skill_with_bad_casing.md")
            frontmatter = (
                "---\n"
                "id: fake_author/skill_with_bad_casing\n"
                "name: Bad Casing Skill\n"
                "contributor: fake_author\n"
                "origin: true\n"
                "genericSkillRef: web-search\n"
                "status: named\n"
                "level: 2★\n"
                "description: A skill that references lowercase skill.md in links.github.\n"
                "links:\n"
                "  github: https://github.com/fake_author/skills/blob/main/skills/skill.md\n"
                "createdAt: '2026-06-07'\n"
                "updatedAt: '2026-06-07'\n"
                "---\n"
            )
            with open(fake_skill_file, "w", encoding="utf-8") as f:
                f.write(frontmatter)

            graph = {"skills": [{"id": "web-search"}]}
            errors = validate_named_skills(graph, named_dir=temp_named_dir)
            self.assertTrue(
                any("invalid casing" in e and "SKILL.md" in e for e in errors),
                f"Expected casing error, got: {errors}"
            )
        finally:
            shutil.rmtree(temp_named_dir)


class TestMetaEpochsMetaSync(unittest.TestCase):
    """Regression guard for the Yggdrasil II structured-provenance schema (#1189).

    Ensures the metaEpochs enum and the optional metaEpoch/migrationBatch timeline
    fields exist in lockstep across the canonical registry/schema/ tree and the
    bundled src/gaia_cli/data/registry/schema/ mirror, and that the pre-existing
    timeline action enum still admits type_change (which the invariant pairs against).
    """

    CANONICAL_META = os.path.join(REPO_ROOT, "registry", "schema", "meta.json")
    BUNDLED_META = os.path.join(
        REPO_ROOT, "src", "gaia_cli", "data", "registry", "schema", "meta.json")
    CANONICAL_NAMED = os.path.join(REPO_ROOT, "registry", "schema", "namedSkill.schema.json")
    BUNDLED_NAMED = os.path.join(
        REPO_ROOT, "src", "gaia_cli", "data", "registry", "schema", "namedSkill.schema.json")
    SYNC_SCRIPT = os.path.join(REPO_ROOT, "scripts", "sync_bundled_schemas.py")

    @staticmethod
    def _load(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def test_meta_epochs_present_in_both_meta_copies(self):
        """metaEpochs.order exists and matches in canonical and bundled meta.json."""
        canonical = self._load(self.CANONICAL_META).get("metaEpochs", {})
        bundled = self._load(self.BUNDLED_META).get("metaEpochs", {})
        self.assertIn("yggdrasil-ii", canonical.get("order", []))
        self.assertIn("yggdrasil-i", canonical.get("order", []))
        self.assertEqual(canonical.get("order"), bundled.get("order"))
        self.assertEqual(canonical.get("labels"), bundled.get("labels"))

    def test_bundle_is_byte_identical(self):
        """sync_bundled_schemas.py --check exits 0 (bundle byte-identical to canonical)."""
        result = subprocess.run(
            [sys.executable, self.SYNC_SCRIPT, "--check"],
            cwd=REPO_ROOT, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_named_schema_declares_provenance_fields_in_both_copies(self):
        """Both namedSkill.schema.json copies declare metaEpoch and migrationBatch."""
        for path in (self.CANONICAL_NAMED, self.BUNDLED_NAMED):
            props = (self._load(path)["definitions"]["timelineEvent"]["properties"])
            self.assertIn("metaEpoch", props, f"metaEpoch missing in {path}")
            self.assertIn("migrationBatch", props, f"migrationBatch missing in {path}")
            # migrationBatch must keep its <slug>@YYYY-MM-DD pattern
            self.assertIn("@", props["migrationBatch"].get("pattern", ""))

    def test_timeline_action_enum_still_contains_type_change(self):
        """The timeline action enum still admits type_change (paired by the invariant)."""
        props = self._load(self.CANONICAL_NAMED)["definitions"]["timelineEvent"]["properties"]
        self.assertIn("type_change", props["action"]["enum"])


if __name__ == "__main__":
    unittest.main()
