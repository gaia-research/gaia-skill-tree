"""
Tests for src/gaia_cli/commands/pushFromFile.py

Covers:
- _validate_skill: all validation rules including edge cases flagged in review
- _load_yaml_file: structural YAML guards
- build_from_file_batch: happy path, validation error path, fromFile flag
"""
import os
import sys
import unittest

import pytest

pytestmark = [pytest.mark.integration]

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from gaia_cli.commands.pushFromFile import (
    _load_yaml_file,
    _validate_skill,
    build_from_file_batch,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _good_basic(**overrides):
    """Return a minimal valid basic skill entry."""
    base = {
        "id": "my-skill",
        "name": "My Skill",
        "type": "basic",
        "prerequisites": [],
        "description": "A clear ten-char+ description of the capability.",
        "attribution": {"type": "self-made"},
        "evidence": [
            {
                "grade": "B",
                "type": "repo",
                "url": "https://github.com/owner/repo/blob/main/SKILL.md",
            }
        ],
    }
    base.update(overrides)
    return base


def _good_fusion(**overrides):
    """Return a minimal valid fusion skill entry with a known prereq."""
    base = _good_basic(
        id="my-fusion",
        type="fusion",
        prerequisites=["plan-decompose"],
    )
    base.update(overrides)
    return base


_KNOWN_IDS = {"plan-decompose", "executing-plans", "web-search"}


# ---------------------------------------------------------------------------
# _validate_skill — happy paths
# ---------------------------------------------------------------------------

class TestValidateSkillHappyPaths(unittest.TestCase):
    def test_valid_basic_returns_no_errors(self):
        errors = _validate_skill(_good_basic(), 0, _KNOWN_IDS)
        self.assertEqual(errors, [])

    def test_valid_fusion_returns_no_errors(self):
        errors = _validate_skill(_good_fusion(), 0, _KNOWN_IDS)
        self.assertEqual(errors, [])

    def test_valid_skill_with_named_block(self):
        entry = _good_basic(
            named={
                "contributor": "othmanadi",
                "level": "3★",
                "links_github": "https://github.com/owner/repo/blob/main/SKILL.md",
            }
        )
        errors = _validate_skill(entry, 0, _KNOWN_IDS)
        self.assertEqual(errors, [])


# ---------------------------------------------------------------------------
# _validate_skill — id validation
# ---------------------------------------------------------------------------

class TestValidateSkillId(unittest.TestCase):
    def test_bad_id_uppercase_rejected(self):
        errors = _validate_skill(_good_basic(id="BadID"), 0, _KNOWN_IDS)
        self.assertTrue(any("must match" in e for e in errors), errors)

    def test_bad_id_underscore_rejected(self):
        errors = _validate_skill(_good_basic(id="bad_id"), 0, _KNOWN_IDS)
        self.assertTrue(any("must match" in e for e in errors), errors)

    def test_missing_id_rejected(self):
        entry = _good_basic()
        del entry["id"]
        errors = _validate_skill(entry, 0, _KNOWN_IDS)
        self.assertTrue(any("'id' is required" in e for e in errors), errors)


# ---------------------------------------------------------------------------
# _validate_skill — type validation (Yggdrasil II)
# ---------------------------------------------------------------------------

class TestValidateSkillType(unittest.TestCase):
    def test_type_extra_rejected(self):
        errors = _validate_skill(_good_basic(type="extra"), 0, _KNOWN_IDS)
        self.assertTrue(any("basic' or 'fusion'" in e for e in errors), errors)

    def test_type_ultimate_rejected(self):
        errors = _validate_skill(_good_basic(type="ultimate"), 0, _KNOWN_IDS)
        self.assertTrue(any("basic' or 'fusion'" in e for e in errors), errors)

    def test_type_unique_rejected(self):
        errors = _validate_skill(_good_basic(type="unique"), 0, _KNOWN_IDS)
        self.assertTrue(any("basic' or 'fusion'" in e for e in errors), errors)


# ---------------------------------------------------------------------------
# _validate_skill — prerequisites validation
# ---------------------------------------------------------------------------

class TestValidateSkillPrereqs(unittest.TestCase):
    def test_fusion_prereq_not_in_registry(self):
        errors = _validate_skill(_good_fusion(prerequisites=["nonexistent-id"]), 0, set())
        self.assertTrue(any("does not exist in registry" in e for e in errors), errors)

    def test_fusion_empty_prereqs_rejected(self):
        errors = _validate_skill(_good_fusion(prerequisites=[]), 0, _KNOWN_IDS)
        self.assertTrue(any("requires at least one prerequisite" in e for e in errors), errors)

    def test_basic_with_nonempty_prereqs_rejected(self):
        errors = _validate_skill(_good_basic(prerequisites=["web-search"]), 0, _KNOWN_IDS)
        self.assertTrue(any("empty prerequisites list" in e for e in errors), errors)

    def test_prereqs_null_basic_passes_silently(self):
        # prerequisites: null on a basic skill — should not error (null → treated as empty)
        entry = _good_basic()
        entry["prerequisites"] = None
        errors = _validate_skill(entry, 0, _KNOWN_IDS)
        typeErrors = [e for e in errors if "prerequisites" in e]
        self.assertEqual(typeErrors, [], f"Unexpected prereq errors: {typeErrors}")

    def test_prereqs_string_scalar_rejected(self):
        # prerequisites: "plan-decompose" — YAML string, not a list
        # Must produce a clear error, NOT silently iterate over characters
        entry = _good_fusion()
        entry["prerequisites"] = "plan-decompose"
        errors = _validate_skill(entry, 0, _KNOWN_IDS)
        self.assertTrue(
            any("must be a list" in e for e in errors),
            f"Expected 'must be a list' error, got: {errors}",
        )
        # Must NOT produce character-by-character errors like '"p" does not exist'
        charErrors = [e for e in errors if 'does not exist' in e and len(e.split("'")[1]) == 1]
        self.assertEqual(charErrors, [], f"Character-by-character errors leaked: {charErrors}")


# ---------------------------------------------------------------------------
# _validate_skill — description validation
# ---------------------------------------------------------------------------

class TestValidateSkillDescription(unittest.TestCase):
    def test_description_too_short_rejected(self):
        errors = _validate_skill(_good_basic(description="short"), 0, _KNOWN_IDS)
        self.assertTrue(any("at least 10 characters" in e for e in errors), errors)

    def test_description_none_rejected(self):
        entry = _good_basic()
        entry["description"] = None
        errors = _validate_skill(entry, 0, _KNOWN_IDS)
        self.assertTrue(any("at least 10 characters" in e for e in errors), errors)


# ---------------------------------------------------------------------------
# _validate_skill — evidence validation
# ---------------------------------------------------------------------------

class TestValidateSkillEvidence(unittest.TestCase):
    def test_evidence_tree_url_rejected(self):
        entry = _good_basic(
            evidence=[{
                "grade": "B",
                "type": "repo",
                "url": "https://github.com/owner/repo/tree/main/skills/foo",
            }]
        )
        errors = _validate_skill(entry, 0, _KNOWN_IDS)
        self.assertTrue(any("use blob/ URLs" in e for e in errors), errors)

    def test_evidence_missing_url_rejected(self):
        entry = _good_basic(evidence=[{"grade": "B", "type": "repo"}])
        errors = _validate_skill(entry, 0, _KNOWN_IDS)
        self.assertTrue(any("'url' is required" in e for e in errors), errors)

    def test_evidence_bad_grade_rejected(self):
        entry = _good_basic(
            evidence=[{"grade": "Z", "type": "repo", "url": "https://github.com/a/b"}]
        )
        errors = _validate_skill(entry, 0, _KNOWN_IDS)
        self.assertTrue(any("must be A, B, or C" in e for e in errors), errors)

    def test_evidence_missing_entirely_rejected(self):
        entry = _good_basic(evidence=[])
        errors = _validate_skill(entry, 0, _KNOWN_IDS)
        self.assertTrue(any("at least one evidence entry" in e for e in errors), errors)


# ---------------------------------------------------------------------------
# _validate_skill — named block validation
# ---------------------------------------------------------------------------

class TestValidateSkillNamed(unittest.TestCase):
    def test_named_level_missing_rejected(self):
        # named block present but level key absent — must error
        entry = _good_basic(named={"contributor": "foo", "links_github": "https://github.com/a/b"})
        errors = _validate_skill(entry, 0, _KNOWN_IDS)
        self.assertTrue(
            any("level" in e and "required" in e for e in errors),
            f"Expected level-required error, got: {errors}",
        )

    def test_named_level_1star_rejected(self):
        entry = _good_basic(named={"contributor": "foo", "level": "1★", "links_github": "https://github.com/a/b"})
        errors = _validate_skill(entry, 0, _KNOWN_IDS)
        self.assertTrue(any("star rating" in e for e in errors), errors)

    def test_named_links_github_missing_rejected(self):
        # named block present, links_github absent — must error
        entry = _good_basic(named={"contributor": "foo", "level": "2★"})
        errors = _validate_skill(entry, 0, _KNOWN_IDS)
        self.assertTrue(
            any("links_github" in e and "required" in e for e in errors),
            f"Expected links_github-required error, got: {errors}",
        )

    def test_named_links_github_tree_url_rejected(self):
        entry = _good_basic(named={
            "contributor": "foo",
            "level": "2★",
            "links_github": "https://github.com/a/b/tree/main/skill",
        })
        errors = _validate_skill(entry, 0, _KNOWN_IDS)
        self.assertTrue(any("use blob/ URLs" in e for e in errors), errors)

    def test_named_contributor_missing_rejected(self):
        entry = _good_basic(named={"level": "2★", "links_github": "https://github.com/a/b"})
        errors = _validate_skill(entry, 0, _KNOWN_IDS)
        self.assertTrue(any("contributor" in e for e in errors), errors)


# ---------------------------------------------------------------------------
# _load_yaml_file
# ---------------------------------------------------------------------------

class TestLoadYamlFile(unittest.TestCase):
    def _write_tmp(self, content, suffix=".yml"):
        import tempfile
        fd, path = tempfile.mkstemp(suffix=suffix)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def test_valid_file_returns_data(self):
        path = self._write_tmp("skills:\n  - id: test\n")
        data, err = _load_yaml_file(path)
        os.unlink(path)
        self.assertIsNone(err)
        self.assertEqual(data["skills"], [{"id": "test"}])

    def test_missing_skills_key_returns_error(self):
        path = self._write_tmp("other: value\n")
        data, err = _load_yaml_file(path)
        os.unlink(path)
        self.assertIsNone(data)
        self.assertIn("missing the required", err)

    def test_empty_skills_list_returns_error(self):
        path = self._write_tmp("skills: []\n")
        data, err = _load_yaml_file(path)
        os.unlink(path)
        self.assertIsNone(data)
        self.assertIn("non-empty", err)

    def test_invalid_yaml_returns_error(self):
        path = self._write_tmp("skills: [\n  unclosed bracket\n")
        data, err = _load_yaml_file(path)
        os.unlink(path)
        self.assertIsNone(data)
        self.assertIn("YAML parse error", err)

    def test_missing_file_returns_error(self):
        data, err = _load_yaml_file("/nonexistent/path/skills.yml")
        self.assertIsNone(data)
        self.assertIn("Cannot read file", err)


# ---------------------------------------------------------------------------
# build_from_file_batch
# ---------------------------------------------------------------------------

class TestBuildFromFileBatch(unittest.TestCase):
    def _config(self):
        return {"gaiaUser": "testuser"}

    def test_valid_batch_sets_from_file_flag(self):
        skills = [_good_basic()]
        batch, errors = build_from_file_batch(
            skills, self._config(), ".", "testuser/repo"
        )
        self.assertEqual(errors, [])
        self.assertIsNotNone(batch)
        self.assertTrue(batch.get("fromFile"), "fromFile flag must be True")

    def test_invalid_skill_returns_none_and_errors(self):
        skills = [_good_basic(id="INVALID_ID")]
        batch, errors = build_from_file_batch(
            skills, self._config(), ".", "testuser/repo"
        )
        self.assertIsNone(batch)
        self.assertTrue(len(errors) > 0)

    def test_valid_batch_proposed_skills_count(self):
        skills = [_good_basic(id="skill-one"), _good_basic(id="skill-two")]
        batch, errors = build_from_file_batch(
            skills, self._config(), ".", "testuser/repo"
        )
        self.assertEqual(errors, [])
        self.assertEqual(len(batch["proposedSkills"]), 2)

    def test_batch_id_contains_from_file_suffix(self):
        skills = [_good_basic()]
        batch, _ = build_from_file_batch(
            skills, self._config(), ".", "testuser/repo"
        )
        self.assertIn("from-file", batch["batchId"])


if __name__ == "__main__":
    unittest.main()
