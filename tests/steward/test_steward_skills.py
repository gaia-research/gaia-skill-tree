"""Inventory contract for the /gaia-steward-full skill family.

Each skill is checked against the live CLI and repository, not against prose:
every documented ``gaia steward`` command must parse with the real parser, every
referenced test file must exist, and the atomic skills must carry the machine-
checkable sections the family promises.
"""

from __future__ import annotations

import re
import shlex
from pathlib import Path

import pytest
import yaml

from gaia_cli.main import get_parser

ROOT = Path(__file__).resolve().parents[2]
ROOT_SKILL = "gaia-steward-full"
ATOMIC_SKILLS = (
    "gaia-steward-observe",
    "gaia-steward-triage",
    "gaia-steward-land",
    "gaia-steward-verify",
    "gaia-steward-retro",
    "gaia-steward-desk",
    "gaia-steward-issue-hygiene",
)
REUSED_SKILLS = (
    "gaia-steward-lane",
    "gaia-tm-inspect",
    "gaia-trace-timeline",
    "gaia-docs-sync",
    "ci-churn",
    "gaia-triage",
    "gaia-issue-resolver",
    "feature-pipeline",
)
ATOMIC_SECTIONS = (
    "Responsibility",
    "Input",
    "Output",
    "Authority ceiling",
    "Stop conditions",
    "Idempotency",
    "Failure states",
    "Validation",
    "Tests",
)
MODEL_IDENTIFIER = re.compile(r"\bclaude-(?:opus|sonnet|haiku|fable)-\d", re.IGNORECASE)
ALL_SKILLS = (ROOT_SKILL, *ATOMIC_SKILLS)


def _text(skill: str) -> str:
    return (ROOT / ".agents/skills" / skill / "SKILL.md").read_text(encoding="utf-8")


def _frontmatter(skill: str) -> dict:
    return yaml.safe_load(_text(skill).split("---", 2)[1])


def _code_lines(text: str) -> list[str]:
    lines: list[str] = []
    for block in re.findall(r"```(?:bash)?\n(.*?)```", text, re.DOTALL):
        lines.extend(line.strip() for line in block.splitlines() if line.strip())
    lines.extend(re.findall(r"`(gaia steward [^`]+)`", text))
    return lines


def _steward_commands(text: str) -> list[str]:
    return sorted({line for line in _code_lines(text) if line.startswith("gaia steward ")})


@pytest.mark.parametrize("skill", ALL_SKILLS)
def test_skill_is_mirrored_byte_for_byte(skill: str) -> None:
    canonical = ROOT / ".agents/skills" / skill / "SKILL.md"
    mirror = ROOT / ".claude/skills" / skill / "SKILL.md"
    assert mirror.read_bytes() == canonical.read_bytes()


@pytest.mark.parametrize("skill", ALL_SKILLS)
def test_frontmatter_names_the_skill(skill: str) -> None:
    frontmatter = _frontmatter(skill)
    assert frontmatter["name"] == skill
    assert len(str(frontmatter["description"])) <= 1024


@pytest.mark.parametrize("skill", ATOMIC_SKILLS)
def test_atomic_skill_declares_every_contract_section(skill: str) -> None:
    headings = re.findall(r"^## (.+)$", _text(skill), re.MULTILINE)
    assert headings == list(ATOMIC_SECTIONS)


@pytest.mark.parametrize("skill", ALL_SKILLS)
def test_documented_steward_commands_parse_with_the_live_cli(skill: str) -> None:
    commands = _steward_commands(_text(skill))
    assert commands, f"{skill} documents no gaia steward command"
    parser, _subparsers = get_parser()
    for command in commands:
        arguments = shlex.split(command)[1:]
        try:
            parser.parse_args(arguments)
        except SystemExit as exc:  # argparse rejects unknown verbs and flags
            pytest.fail(f"{skill}: `{command}` does not parse (exit {exc.code})")


@pytest.mark.parametrize("skill", ALL_SKILLS)
def test_referenced_paths_exist(skill: str) -> None:
    text = _text(skill)
    for path in sorted(set(re.findall(r"(?<![\w/.])((?:tests|scripts|founder)/[\w./-]+\.(?:py|json|md|yaml))", text))):
        assert (ROOT / path).is_file(), f"{skill} references missing {path}"


@pytest.mark.parametrize("skill", ALL_SKILLS)
def test_skill_carries_no_model_identifier(skill: str) -> None:
    assert not MODEL_IDENTIFIER.search(_text(skill))


def test_root_skill_routes_every_mode_and_reuses_existing_skills() -> None:
    text = _text(ROOT_SKILL)
    for mode in ("--observe", "--triage", "--routine N", "--debt ID", "--verify", "--retro", "--status", "--resume RUN", "--afk"):
        assert f"`{mode}`" in text, mode
    for skill in (*ATOMIC_SKILLS, *REUSED_SKILLS):
        assert f"`{skill}`" in text, skill
        assert (ROOT / ".agents/skills" / skill / "SKILL.md").is_file(), skill


def test_root_skill_stays_thin() -> None:
    assert len(_text(ROOT_SKILL).splitlines()) <= 160
