from __future__ import annotations

import json
from pathlib import Path

import pytest

from gaia_cli.steward.sensors_ci import CiHealthSensor
from scripts.steward_collect_ci_runs import InputError, convert, main
from tests.steward.sensor_fixtures import make_repo

NOW = "2026-10-20T00:00:00Z"


def _run(conclusion: str, *, status: str = "completed", attempt: int = 1, created: str = "2026-10-19T00:00:00Z") -> dict:
    return {
        "workflowName": "validate",
        "conclusion": conclusion,
        "status": status,
        "headSha": "a" * 40,
        "createdAt": created,
        "url": "https://github.com/o/r/actions/runs/1",
        "attempt": attempt,
    }


def test_converted_input_is_read_by_the_ci_health_sensor(tmp_path: Path) -> None:
    root = make_repo(tmp_path / "repo", {"README.md": "x"})
    document = convert(
        [_run("success", created="2026-10-18T00:00:00Z"), _run("failure")],
        repository="o/r", branch="main", collected_at=NOW,
    )
    target = root / ".gaia/steward/inputs/ci-runs.json"
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps(document), encoding="utf-8")

    observations = CiHealthSensor().scan(root, NOW)

    assert [o.status for o in observations] == ["drift"]
    assert observations[0].kind == "ci_failure"


def test_incomplete_runs_are_skipped_not_reported() -> None:
    document = convert(
        [_run("", status="in_progress"), _run("success")],
        repository="o/r", branch="main", collected_at=NOW,
    )
    assert [run["conclusion"] for run in document["runs"]] == ["success"]


@pytest.mark.parametrize(
    "raw",
    [{"not": "a list"}, [42], [dict(_run("success"), attempt=0)], [dict(_run("success"), url="")]],
)
def test_malformed_gh_output_is_refused(raw) -> None:
    with pytest.raises(InputError):
        convert(raw, repository="o/r", branch="main", collected_at=NOW)


def test_cli_writes_the_driver_input(tmp_path: Path) -> None:
    source = tmp_path / "runs.json"
    source.write_text(json.dumps([_run("success")]), encoding="utf-8")
    output = tmp_path / "ci-runs.json"

    assert main([str(source), "--repository", "o/r", "--branch", "main", "--output", str(output)]) == 0
    assert json.loads(output.read_text())["schemaVersion"] == "steward-ci-runs-v1"
    source.write_text("{", encoding="utf-8")
    assert main([str(source), "--repository", "o/r", "--branch", "main", "--output", str(output)]) == 1
