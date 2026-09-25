"""Tests for scripts/quick_validate_skill.py and playbook validation reconciliation."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from scripts import quick_validate_skill as qv
from scripts import validate_skills


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures" / "skills"


def write_temp_skill(dir_path: Path, data: dict, body: str = "# Sample Skill\n") -> Path:
    dir_path.mkdir(parents=True, exist_ok=True)
    skill_md = dir_path / "SKILL.md"
    skill_md.write_text(
        f"---\n{yaml.safe_dump(data, sort_keys=False)}---\n\n{body}",
        encoding="utf-8",
    )
    return skill_md


def test_valid_ordinary_skill(tmp_path: Path):
    data = {
        "name": "sample-ordinary-skill",
        "description": "A valid ordinary skill with standard frontmatter fields.",
        "license": "MIT",
        "compatibility": "Python 3.10+",
        "metadata": {"category": "test"},
    }
    write_temp_skill(tmp_path / "ordinary", data)
    valid, message = qv.validate_skill(tmp_path / "ordinary")
    assert valid is True
    assert message == "Skill is valid!"


def test_valid_playbook_dev_calibrate():
    dev_calibrate_path = REPO_ROOT / ".agents" / "skills" / "dev-calibrate"
    valid, message = qv.validate_skill(dev_calibrate_path, check_contract=True)
    assert valid is True
    assert message == "Skill is valid!"


def test_valid_playbook_fixture():
    fixture_path = FIXTURES_DIR / "valid-playbook"
    valid, message = qv.validate_skill(fixture_path, check_contract=True)
    assert valid is True
    assert message == "Skill is valid!"


def test_invalid_unknown_field_fixture():
    fixture_path = FIXTURES_DIR / "invalid-unknown-field"
    valid, message = qv.validate_skill(fixture_path)
    assert valid is False
    assert "Unexpected key(s) in SKILL.md frontmatter: unexpectedProperty" in message


def test_invalid_playbook_unknown_field_fixture():
    fixture_path = FIXTURES_DIR / "invalid-playbook-unknown-field"
    valid, message = qv.validate_skill(fixture_path)
    assert valid is False
    assert "Unexpected key(s) in SKILL.md frontmatter: inventedPlaybookField" in message


def test_invalid_ordinary_with_playbook_fields_fixture():
    fixture_path = FIXTURES_DIR / "invalid-ordinary-with-playbook-fields"
    valid, message = qv.validate_skill(fixture_path)
    assert valid is False
    assert "Unexpected key(s) in SKILL.md frontmatter:" in message
    assert "class" in message
    assert "objective" in message
    assert "steps" in message


def test_unsupported_playbook_version(tmp_path: Path):
    data = {
        "name": "future-playbook",
        "description": "Playbook with an unsupported version number.",
        "playbookVersion": 2,
    }
    write_temp_skill(tmp_path / "p2", data)
    valid, message = qv.validate_skill(tmp_path / "p2")
    assert valid is False
    assert "Unsupported playbookVersion '2'; only playbookVersion: 1 is supported" in message


def test_missing_required_fields(tmp_path: Path):
    no_name = tmp_path / "no-name"
    write_temp_skill(no_name, {"description": "Missing name."})
    valid, msg = qv.validate_skill(no_name)
    assert valid is False
    assert "Missing 'name'" in msg

    no_desc = tmp_path / "no-desc"
    write_temp_skill(no_desc, {"name": "has-name"})
    valid, msg = qv.validate_skill(no_desc)
    assert valid is False
    assert "Missing 'description'" in msg


@pytest.mark.parametrize(
    "bad_name",
    [
        "InvalidUpperCase",
        "invalid_underscore",
        "-leading-hyphen",
        "trailing-hyphen-",
        "double--hyphen",
        "a" * 65,
    ],
)
def test_invalid_names(tmp_path: Path, bad_name: str):
    skill_dir = tmp_path / "bad"
    write_temp_skill(skill_dir, {"name": bad_name, "description": "Valid description."})
    valid, msg = qv.validate_skill(skill_dir)
    assert valid is False


def test_description_too_long(tmp_path: Path):
    skill_dir = tmp_path / "long-desc"
    write_temp_skill(skill_dir, {"name": "long-desc", "description": "x" * 1025})
    valid, msg = qv.validate_skill(skill_dir)
    assert valid is False
    assert "Description is too long" in msg


def test_strict_upstream_angle_brackets(tmp_path: Path):
    skill_dir = tmp_path / "angle-brackets"
    write_temp_skill(
        skill_dir,
        {"name": "angle-brackets", "description": "Trigger on <placeholder>"},
    )
    # Default Gaia mode allows trigger notation
    valid_default, _ = qv.validate_skill(skill_dir, strict_upstream=False)
    assert valid_default is True

    # Strict upstream mode forbids angle brackets
    valid_strict, msg_strict = qv.validate_skill(skill_dir, strict_upstream=True)
    assert valid_strict is False
    assert "Description cannot contain angle brackets" in msg_strict


def test_adapt_upstream_validator_mock(tmp_path: Path):
    # Simulate an upstream validator that strictly permits only the 6 Anthropic base properties
    def upstream_validator(path: Path) -> tuple[bool, str]:
        skill_md = path / "SKILL.md"
        content = skill_md.read_text()
        fm = yaml.safe_load(content.split("---")[1])
        base_allowed = {"name", "description", "license", "allowed-tools", "metadata", "compatibility"}
        unexpected = set(fm.keys()) - base_allowed
        if unexpected:
            return False, f"Unexpected key(s) in SKILL.md frontmatter: {', '.join(sorted(unexpected))}"
        return True, "Skill is valid!"

    dev_calibrate_path = REPO_ROOT / ".agents" / "skills" / "dev-calibrate"

    # Direct upstream invocation fails on dev-calibrate (reproducing the exact issue #1690 finding)
    direct_valid, direct_msg = upstream_validator(dev_calibrate_path)
    assert direct_valid is False
    assert "Unexpected key(s) in SKILL.md frontmatter:" in direct_msg
    assert "playbookVersion" in direct_msg

    # Adapted validator succeeds on dev-calibrate
    adapted = qv.adapt_upstream_validator(upstream_validator)
    adapted_valid, adapted_msg = adapted(dev_calibrate_path)
    assert adapted_valid is True
    assert adapted_msg == "Skill is valid!"

    # Adapted validator still catches invalid unknown field in an ordinary skill
    adapted_invalid, adapted_invalid_msg = adapted(FIXTURES_DIR / "invalid-unknown-field")
    assert adapted_invalid is False
    assert "unexpectedProperty" in adapted_invalid_msg


def test_adapt_real_skill_creator_if_present():
    real_paths = [
        Path.home() / ".claude/plugins/marketplaces/claude-plugins-official/plugins/skill-creator/skills/skill-creator/scripts/quick_validate.py",
        Path.home() / ".codex/skills/.system/skill-creator/scripts/quick_validate.py",
    ]
    existing = [p for p in real_paths if p.is_file()]
    if not existing:
        pytest.skip("No external skill-creator quick_validate.py found in environment")

    spec = importlib.util.spec_from_file_location("real_quick_validate", existing[0])
    assert spec is not None and spec.loader is not None
    real_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(real_mod)

    dev_calibrate_path = REPO_ROOT / ".agents" / "skills" / "dev-calibrate"

    # 1. Proves the bug exists on raw upstream quick_validate.py:
    # Direct upstream call fails on dev-calibrate
    raw_valid, raw_msg = real_mod.validate_skill(dev_calibrate_path)
    assert raw_valid is False
    assert "Unexpected key(s) in SKILL.md frontmatter:" in raw_msg

    # 2. Proves the fix works via adapter:
    adapted = qv.adapt_upstream_validator(real_mod.validate_skill)
    adapted_valid, adapted_msg = adapted(dev_calibrate_path)
    assert adapted_valid is True
    assert adapted_msg == "Skill is valid!"


def test_cli_execution():
    # Test scripts/quick_validate_skill.py on valid fixture
    res1 = subprocess.run(
        [sys.executable, "scripts/quick_validate_skill.py", str(FIXTURES_DIR / "valid-playbook")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res1.returncode == 0
    assert "Skill is valid!" in res1.stdout

    # Test scripts/quick_validate.py on valid fixture
    res2 = subprocess.run(
        [sys.executable, "scripts/quick_validate.py", str(FIXTURES_DIR / "valid-playbook")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res2.returncode == 0
    assert "Skill is valid!" in res2.stdout

    # Test scripts/quick_validate.py on invalid fixture
    res3 = subprocess.run(
        [sys.executable, "scripts/quick_validate.py", str(FIXTURES_DIR / "invalid-unknown-field")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res3.returncode == 1
    assert "Unexpected key(s) in SKILL.md frontmatter: unexpectedProperty" in res3.stdout


def test_validate_skills_integration():
    # Valid playbook passes validate_skills.py
    errors, _ = validate_skills.validate_skill(FIXTURES_DIR / "valid-playbook")
    assert errors == []

    # Invalid unknown field is rejected by validate_skills.py
    errors, _ = validate_skills.validate_skill(FIXTURES_DIR / "invalid-unknown-field")
    assert any("unexpectedProperty" in err for err in errors)

    # Ordinary skill with playbook fields is rejected by validate_skills.py
    errors, _ = validate_skills.validate_skill(
        FIXTURES_DIR / "invalid-ordinary-with-playbook-fields"
    )
    assert any("class" in err for err in errors)
