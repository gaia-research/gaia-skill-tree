"""Regression tests for preventing nested playbook fixtures from becoming discoverable skills (issue #1692)."""

from __future__ import annotations

from pathlib import Path
import pytest
import yaml

from scripts import check_playbook_contract as contract
from scripts import validate_skills
from src.gaia_cli.scanner import DEFAULT_EXCLUDED_DIRS, _should_prune_dir, scan_skill_mds


ROOT = Path(__file__).resolve().parents[1]


def test_fixtures_dir_is_pruned_by_scanner():
    """Scanner excludes fixtures directories from search paths."""
    assert "fixtures" in DEFAULT_EXCLUDED_DIRS
    assert _should_prune_dir("fixtures") is True


def test_scan_skill_mds_ignores_nested_fixtures(tmp_path: Path):
    """scan_skill_mds does not discover SKILL.md inside a fixtures directory."""
    # Top-level valid skill
    top_skill = tmp_path / ".agents" / "skills" / "my-skill"
    top_skill.mkdir(parents=True)
    (top_skill / "SKILL.md").write_text(
        "---\nname: My Skill\ndescription: Top-level valid skill\n---\n# My Skill\n",
        encoding="utf-8",
    )

    # Nested fixture skill inside a fixtures directory
    fixture_dir = tmp_path / "fixtures" / "playbook-runtime" / "source"
    fixture_dir.mkdir(parents=True)
    (fixture_dir / "SKILL.md").write_text(
        "---\nname: Example Skill\ndescription: Nested fixture\n---\n# Example Skill\n",
        encoding="utf-8",
    )

    found = scan_skill_mds(root=str(tmp_path), global_search=False)
    ids = {s["id"] for s in found}
    names = {s["name"] for s in found}

    assert "/my-skill" in ids
    assert "My Skill" in names
    assert "/source" not in ids
    assert "Example Skill" not in names


def test_validate_skills_get_skill_dirs_is_top_level_only(tmp_path: Path):
    """get_skill_dirs only returns top-level canonical skill directories (*/SKILL.md)."""
    skills_base = tmp_path / ".agents" / "skills"
    
    # Canonical top-level skill
    top_skill = skills_base / "canonical-skill"
    top_skill.mkdir(parents=True)
    (top_skill / "SKILL.md").write_text("---\nname: Canonical\ndescription: Canonical\n---\n", encoding="utf-8")

    # Nested fixture inside canonical skill
    nested = top_skill / "fixtures" / "sub"
    nested.mkdir(parents=True)
    (nested / "SKILL.md").write_text("---\nname: Leaked\ndescription: Leaked\n---\n", encoding="utf-8")

    discovered = validate_skills.get_skill_dirs(str(skills_base))
    assert discovered == [top_skill]


def test_validate_skills_detects_nested_skill_mds(tmp_path: Path):
    """find_nested_skill_mds finds nested SKILL.md files and validate_skill reports error."""
    skills_base = tmp_path / ".agents" / "skills"
    top_skill = skills_base / "test-skill"
    top_skill.mkdir(parents=True)
    (top_skill / "SKILL.md").write_text("---\nname: Test\ndescription: Test description\n---\n", encoding="utf-8")

    nested = top_skill / "fixtures" / "playbook-runtime" / "source"
    nested.mkdir(parents=True)
    nested_skill = nested / "SKILL.md"
    nested_skill.write_text("---\nname: Example Skill\ndescription: Fixture\n---\n", encoding="utf-8")

    # Global detection
    nested_found = validate_skills.find_nested_skill_mds(str(skills_base))
    assert nested_found == [nested_skill]

    # Per-skill validation error
    errors, _ = validate_skills.validate_skill(top_skill)
    assert any("Nested SKILL.md detected" in err for err in errors)


def test_check_playbook_contract_scans_only_top_level_skills(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """validate_repository only globs top-level */SKILL.md, ignoring nested fixture SKILL.md."""
    monkeypatch.setattr(contract, "SCHEMA_PATH", ROOT / "founder/steward/playbook.schema.json")
    skills_base = tmp_path / ".agents" / "skills"
    
    # Top-level non-playbook skill
    top_skill = skills_base / "my-skill"
    top_skill.mkdir(parents=True)
    (top_skill / "SKILL.md").write_text("---\nname: Normal\ndescription: Normal skill\n---\n", encoding="utf-8")

    # Nested fixture with playbookVersion
    nested = top_skill / "fixtures" / "playbook-runtime" / "source"
    nested.mkdir(parents=True)
    (nested / "SKILL.md").write_text(
        "---\nname: Playbook Fixture\ndescription: Fixture\nplaybookVersion: 1\n---\n",
        encoding="utf-8",
    )

    scanned, opted_in, errors = contract.validate_repository(tmp_path)
    assert scanned == 1
    assert opted_in == 0
    assert errors == []
