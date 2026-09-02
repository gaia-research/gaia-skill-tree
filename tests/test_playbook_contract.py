from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from scripts import check_playbook_contract as contract


ROOT = Path(__file__).resolve().parents[1]


def playbook(**updates):
    value = {
        "name": "fixture-playbook",
        "description": "A fixture agent playbook.",
        "playbookVersion": 1,
        "class": "B",
        "objective": "Produce a bounded result.",
        "capability": "Apply bounded repository judgment.",
        "preconditions": ["the fixture exists"],
        "steps": [
            {
                "id": "inspect",
                "run": "gaia dev list --generic --json > {snapshot}",
                "proves": "snapshot captured",
            }
        ],
        "stopConditions": ["send an ambiguous result to the founder queue"],
        "proof": ["the snapshot exists"],
        "done": "A reviewable result exists.",
    }
    value.update(updates)
    return value


def write_skill(root: Path, data: dict, name: str = "fixture") -> Path:
    target = root / ".agents" / "skills" / name / "SKILL.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"---\n{yaml.safe_dump(data, sort_keys=False)}---\n\n# Fixture\n", encoding="utf-8")
    return target


@pytest.fixture
def fixture_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(contract, "SCHEMA_PATH", ROOT / "founder/steward/playbook.schema.json")
    return tmp_path


def errors_for(root: Path):
    return contract.validate_repository(root)[2]


def test_non_playbook_is_skipped_untouched(fixture_repo: Path):
    write_skill(fixture_repo, {"name": "ordinary", "description": "Not opted in."})
    scanned, opted_in, errors = contract.validate_repository(fixture_repo)
    assert (scanned, opted_in, errors) == (1, 0, [])


def test_frontmatter_is_parsed_before_opt_in_is_decided(fixture_repo: Path):
    target = fixture_repo / ".agents/skills/ordinary/SKILL.md"
    target.parent.mkdir(parents=True)
    target.write_text("---\nname: [unterminated\n", encoding="utf-8")
    scanned, opted_in, errors = contract.validate_repository(fixture_repo)
    assert (scanned, opted_in) == (1, 0)
    assert any("frontmatter" in error for error in errors)


def test_quoted_playbook_version_key_cannot_bypass_validation(fixture_repo: Path):
    target = write_skill(fixture_repo, playbook())
    content = target.read_text(encoding="utf-8")
    target.write_text(content.replace("playbookVersion:", '"playbookVersion":'), encoding="utf-8")
    scanned, opted_in, errors = contract.validate_repository(fixture_repo)
    assert (scanned, opted_in, errors) == (1, 1, [])


def test_schema_failures_are_reported_with_skill_path(fixture_repo: Path):
    invalid = playbook()
    del invalid["objective"]
    invalid["class"] = "D"
    write_skill(fixture_repo, invalid)
    errors = errors_for(fixture_repo)
    assert any(".agents/skills/fixture/SKILL.md" in error for error in errors)
    assert any("'objective' is a required property" in error for error in errors)
    assert any("class" in error and "not one of" in error for error in errors)


def test_duplicate_step_ids_are_rejected(fixture_repo: Path):
    data = playbook()
    data["steps"].append(deepcopy(data["steps"][0]))
    write_skill(fixture_repo, data)
    assert any("step inspect: duplicate step id" in error for error in errors_for(fixture_repo))


@pytest.mark.parametrize(
    "command",
    [
        "gaia dev list --generic --named",
        "gaia dev evidence {skill_id} {source_url} --type repo-own --commits {commit_count}",
        "gaia dev evidence {skill_id} {source_url} --commits={commit_count}",
        "gaia dev prefill {candidate_id} --name {candidate_name} --description {candidate_description} --url {source_url} --source-lane {source_lane} --json > {packet}",
        "gaia dev list --generic --json > {snapshot}",
        "gaia dev list --generic --json >> generated-output/snapshot.json",
        "python3 scripts/validate_skills.py --fixture {fixture_path}",
    ],
)
def test_valid_command_spines(command: str):
    contract.validate_run(command, ROOT)


@pytest.mark.parametrize(
    ("command", "message"),
    [
        ("gaia dev add fixture --type invented", "invalid choice"),
        ("gaia unknown-verb", "invalid choice"),
        ("gaia dev list --unknown-flag", "unrecognized arguments"),
        ("gaia dev fuse", "required"),
        ("gaia dev fuse fixture --type basic", "unrecognized arguments"),
        ("python3 scripts/does_not_exist.py", "does not exist"),
        ("python3 scripts/../pyproject.toml", "stay within scripts"),
    ],
)
def test_invalid_commands_have_actionable_errors(command: str, message: str):
    with pytest.raises(contract.CommandContractError, match=message):
        contract.validate_run(command, ROOT)


@pytest.mark.parametrize(
    "command",
    [
        "PATH=/tmp gaia dev list --generic",
        "PYTHONPATH=src gaia dev list --generic",
        "LD_LIBRARY_PATH=/tmp gaia dev list --generic",
        "GAIA_HOME={gaia_home} gaia dev list --generic",
    ],
)
def test_environment_assignments_are_rejected(command: str):
    with pytest.raises(contract.CommandContractError, match="environment assignment.*not allowed"):
        contract.validate_run(command, ROOT)


@pytest.mark.parametrize(
    "command",
    [
        "gaia dev list --gen",
        "gaia dev list --descr",
        "gaia --reg registry dev list --generic",
    ],
)
def test_argparse_option_abbreviations_are_rejected(command: str):
    with pytest.raises(contract.CommandContractError):
        contract.validate_run(command, ROOT)


@pytest.mark.parametrize(
    "command",
    [
        "gaia dev list --generic | tee out.json",
        "gaia dev list --generic && gaia dev list --named",
        "gaia dev list --generic ; gaia dev list --named",
        "gaia dev list --generic $(whoami)",
        "gaia dev list --generic `whoami`",
        "gaia dev list --generic <(python3 scripts/validate_skills.py)",
        "gaia dev list --generic &",
        "gaia dev list --generic > one.json extra",
        "gaia dev list --generic > one.json > two.json",
        "gaia dev list --generic 2> errors.log",
        "gaia dev evidence {Bad_Name} source",
    ],
)
def test_forbidden_shell_forms_are_rejected(command: str):
    with pytest.raises(contract.CommandContractError):
        contract.validate_run(command, ROOT)


@pytest.mark.parametrize(
    ("capability", "term"),
    [
        ("Ask Hermes to classify the input.", "hermes"),
        ("Use Copilot to inspect it.", "copilot"),
        ("Route this judgment to Opus.", "opus"),
        ("Route this judgment to Sonnet.", "sonnet"),
        ("Route this judgment to Haiku.", "haiku"),
        ("Select a model for this judgment.", "model"),
        ("Execute this in a harness.", "harness"),
        ("Use an LLM to decide.", "llm"),
        ("Use the ultra tier for this judgment.", "ultra"),
    ],
)
def test_capability_cannot_encode_routing_authority(
    fixture_repo: Path, capability: str, term: str
):
    write_skill(fixture_repo, playbook(capability=capability))
    errors = errors_for(fixture_repo)
    assert any("forbidden routing term" in error and term in error for error in errors)


@pytest.mark.parametrize(
    "capability",
    [
        "Continue reviewing until the bounded proof is complete.",
        "Perform a meta analysis of the declared proof.",
        "Compare registry metadata against the declared contract.",
    ],
)
def test_capability_allows_ordinary_continue_and_meta_words(
    fixture_repo: Path, capability: str
):
    write_skill(fixture_repo, playbook(capability=capability))
    assert errors_for(fixture_repo) == []


def test_valid_playbook_passes_repository_validation(fixture_repo: Path):
    write_skill(fixture_repo, playbook())
    scanned, opted_in, errors = contract.validate_repository(fixture_repo)
    assert (scanned, opted_in, errors) == (1, 1, [])


def test_workflow_triggers_for_all_playbook_contract_inputs():
    workflow = yaml.load(
        (ROOT / ".github/workflows/validate.yml").read_text(encoding="utf-8"),
        Loader=yaml.BaseLoader,
    )
    required = {
        ".agents/skills/**",
        ".claude/skills/**",
        "src/gaia_cli/**",
        "founder/steward/PLAYBOOKS.md",
        "founder/steward/playbook.schema.json",
        "scripts/**",
        "tests/**",
        ".github/workflows/validate.yml",
    }
    for event in ("push", "pull_request"):
        assert required <= set(workflow["on"][event]["paths"])
