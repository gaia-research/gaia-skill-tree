from __future__ import annotations

import json
from pathlib import Path

import pytest

from gaia_cli.steward.primitives import SensorNotEvaluated
from gaia_cli.steward.sensors_ci import DependencyAdvisorySensor
from scripts.steward_collect_advisories import InputError, convert, main
from tests.steward.sensor_fixtures import make_repo

NOW = "2026-10-20T00:00:00Z"
REPO = "gaia-research/gaia-skill-tree"


def _pip_audit(*dependencies, fixes=None) -> dict:
    return {"dependencies": list(dependencies), "fixes": fixes if fixes is not None else []}


JINJA = {
    "name": "jinja2",
    "version": "3.0.0",
    "vulns": [{"id": "PYSEC-2024-1", "fix_versions": ["3.1.4"], "aliases": ["CVE-x"], "description": "d"}],
}
CLEAN = {"name": "pyyaml", "version": "6.0", "vulns": []}
SKIPPED = {"name": "private-lib", "skip_reason": "Dependency not found on PyPI and could not be audited"}


def _install(root: Path, document: dict) -> None:
    target = root / ".gaia" / "steward" / "inputs" / "advisories.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(document), encoding="utf-8")


def test_converted_input_is_read_by_the_dependency_advisory_sensor(tmp_path: Path) -> None:
    root = make_repo(tmp_path / "repo", {"README.md": "x\n"})
    _install(root, convert(_pip_audit(JINJA, CLEAN), repository=REPO, collected_at=NOW))

    observations = DependencyAdvisorySensor().scan(root, NOW)

    assert [(o.kind, o.subject.id, o.status) for o in observations] == [
        ("dependency_advisory", "jinja2", "drift"),
    ]
    assert observations[0].observed_state["findings"][0]["vulnerabilityId"] == "PYSEC-2024-1"
    assert observations[0].provenance["freshnessSource"] == "collectedAt"


def test_clean_inventory_is_accepted_and_yields_nothing(tmp_path: Path) -> None:
    root = make_repo(tmp_path / "repo", {"README.md": "x\n"})
    _install(root, convert(_pip_audit(CLEAN), repository=REPO, collected_at=NOW))
    assert DependencyAdvisorySensor().scan(root, NOW) == []


def test_skipped_dependency_is_reported_as_not_audited_not_as_clean(tmp_path: Path) -> None:
    root = make_repo(tmp_path / "repo", {"README.md": "x\n"})
    _install(root, convert(_pip_audit(SKIPPED, CLEAN), repository=REPO, collected_at=NOW))

    scan = DependencyAdvisorySensor().scan_detailed(root, NOW)

    assert scan.observations == ()
    assert [(item["subjectId"], item["reason"]) for item in scan.skipped] == [
        ("private-lib", "not audited by pip-audit"),
    ]


def test_vulnerability_keeps_only_the_fields_the_sensor_reads() -> None:
    document = convert(_pip_audit(JINJA), repository=REPO, collected_at=NOW)
    assert document["dependencies"] == [
        {
            "name": "jinja2",
            "version": "3.0.0",
            "vulns": [{"id": "PYSEC-2024-1", "fix_versions": ["3.1.4"]}],
        }
    ]
    assert document["collectedAt"] == NOW
    assert document["repository"] == REPO


def test_missing_fix_versions_defaults_to_an_empty_list() -> None:
    dependency = {"name": "x", "version": "1.0", "vulns": [{"id": "V1"}]}
    document = convert(_pip_audit(dependency), repository=REPO, collected_at=NOW)
    assert document["dependencies"][0]["vulns"] == [{"id": "V1", "fix_versions": []}]


@pytest.mark.parametrize(
    "raw",
    [
        [],
        {"fixes": []},
        {"dependencies": "nope"},
        {"dependencies": [42]},
        {"dependencies": [{"version": "1", "vulns": []}]},
        {"dependencies": [{"name": "x", "version": "1"}]},
        {"dependencies": [{"name": "x", "vulns": []}]},
        {"dependencies": [{"name": "x", "version": "1", "vulns": [{"fix_versions": []}]}]},
        {"dependencies": [{"name": "x", "version": "1", "vulns": [{"id": "V", "fix_versions": "3"}]}]},
        {"dependencies": [{"name": "x", "skip_reason": 7}]},
        {"dependencies": [], "fixes": "none"},
    ],
)
def test_malformed_pip_audit_output_is_refused(raw) -> None:
    with pytest.raises(InputError):
        convert(raw, repository=REPO, collected_at=NOW)


def test_repository_must_be_owner_and_name(tmp_path: Path) -> None:
    source = tmp_path / "pip-audit.json"
    source.write_text(json.dumps(_pip_audit(CLEAN)), encoding="utf-8")
    output = tmp_path / "advisories.json"

    assert main([str(source), "--repository", "not a repo", "--output", str(output)]) == 1
    assert not output.exists()


def test_cli_writes_the_driver_input_and_the_sensor_accepts_it(tmp_path: Path) -> None:
    root = make_repo(tmp_path / "repo", {"README.md": "x\n"})
    source = tmp_path / "pip-audit.json"
    source.write_text(json.dumps(_pip_audit(JINJA, SKIPPED)), encoding="utf-8")
    output = root / ".gaia" / "steward" / "inputs" / "advisories.json"

    assert main([str(source), "--repository", REPO, "--output", str(output)]) == 0

    written = json.loads(output.read_text(encoding="utf-8"))
    # Freshness is read from the document's own stamp, so observe at that instant.
    observations = DependencyAdvisorySensor().scan(root, written["collectedAt"])
    assert [o.subject.id for o in observations] == ["jinja2"]


def test_cli_refused_input_leaves_the_previous_output_untouched(tmp_path: Path) -> None:
    source = tmp_path / "pip-audit.json"
    output = tmp_path / "advisories.json"
    output.write_text('{"previous": true}\n', encoding="utf-8")
    source.write_text("{", encoding="utf-8")

    assert main([str(source), "--repository", REPO, "--output", str(output)]) == 1
    assert output.read_text(encoding="utf-8") == '{"previous": true}\n'


def test_cli_leaves_no_staging_file_behind(tmp_path: Path) -> None:
    source = tmp_path / "pip-audit.json"
    source.write_text(json.dumps(_pip_audit(CLEAN)), encoding="utf-8")
    output_dir = tmp_path / "inputs"

    assert main([str(source), "--repository", REPO, "--output", str(output_dir / "advisories.json")]) == 0
    assert sorted(path.name for path in output_dir.iterdir()) == ["advisories.json"]


def test_collector_refusal_never_becomes_a_sensor_clean_run(tmp_path: Path) -> None:
    # A refused transform writes nothing, so the sensor still reports the input as absent.
    root = make_repo(tmp_path / "repo", {"README.md": "x\n"})
    source = tmp_path / "pip-audit.json"
    source.write_text(json.dumps({"dependencies": "nope"}), encoding="utf-8")
    output = root / ".gaia" / "steward" / "inputs" / "advisories.json"

    assert main([str(source), "--repository", REPO, "--output", str(output)]) == 1
    with pytest.raises(SensorNotEvaluated):
        DependencyAdvisorySensor().scan(root, NOW)
