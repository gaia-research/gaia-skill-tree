from __future__ import annotations

import json
from pathlib import Path

import pytest

from gaia_cli.steward.primitives import SensorNotEvaluated, SensorUnavailable
from gaia_cli.steward.sensors_ci import (
    CiHealthSensor,
    CiWorkflowSensor,
    DependencyAdvisorySensor,
    SupplyChainSensor,
)
from tests.steward.sensor_fixtures import commit_all, make_repo, tree_digest, write_files


NOW = "2026-10-20T00:00:00Z"

CLEAN_WORKFLOW = """\
name: ci
on:
  pull_request:
permissions:
  contents: read
jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - run: echo ok
"""

PYPROJECT_CLEAN = """\
[project]
name = "demo"
version = "1.2.3"
license = {text = "MIT"}
dependencies = [
    "jinja2>=3.0",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
embeddings = [
    "numpy>=1.21.0",
]
"""

NPM_CLEAN = '{\n  "name": "demo",\n  "version": "1.2.3",\n  "license": "MIT"\n}\n'

CLEAN_SUPPLY = {
    "pyproject.toml": PYPROJECT_CLEAN,
    "packages/cli-npm/package.json": NPM_CLEAN,
    "LICENSE": "MIT License\n",
}


def _run_dict(observations):
    return [o.to_dict() for o in observations]


def _write_inputs(root: Path, name: str, payload) -> None:
    target = root / ".gaia" / "steward" / "inputs" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    text = payload if isinstance(payload, str) else json.dumps(payload)
    target.write_text(text, encoding="utf-8")


def _ci_runs(runs, **overrides):
    document = {
        "schemaVersion": "steward-ci-runs-v1",
        "repository": "gaia-research/gaia-skill-tree",
        "branch": "dev/example",
        "collectedAt": "2026-10-20T00:00:00Z",
        "runs": runs,
    }
    document.update(overrides)
    return document


def _run(workflow, conclusion, *, attempt=1, created="2026-10-19T10:00:00Z", sha="a" * 40):
    return {
        "workflow": workflow,
        "conclusion": conclusion,
        "headSha": sha,
        "runAttempt": attempt,
        "createdAt": created,
        "url": f"https://github.example.invalid/runs/{workflow}-{attempt}",
    }


# --- CiWorkflowSensor -------------------------------------------------------


def _workflow_repo(tmp_path: Path, body: str) -> Path:
    return make_repo(tmp_path / "repo", {".github/workflows/ci.yml": body})


def test_workflow_clean_repository_yields_no_observations(tmp_path: Path) -> None:
    root = _workflow_repo(tmp_path, CLEAN_WORKFLOW)
    assert CiWorkflowSensor().scan(root, NOW) == []


def test_workflow_real_defects_produce_exact_findings(tmp_path: Path) -> None:
    body = """\
name: bad
on:
  pull_request_target:
permissions: write-all
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@main
        with:
          ref: ${{ github.event.pull_request.head.sha }}
      - uses: some/action@master
"""
    root = _workflow_repo(tmp_path, body)
    observations = CiWorkflowSensor().scan(root, NOW)
    assert len(observations) == 1
    observation = observations[0]
    assert observation.kind == "workflow_hygiene"
    assert observation.subject.type == "workflow"
    assert observation.subject.id == ".github/workflows/ci.yml"
    assert observation.status == "drift"
    assert observation.confidence == 1.0
    findings = observation.observed_state["findings"]
    assert observation.observed_state["findingCount"] == 5
    assert findings == [
        {"rule": "branch-pinned-action", "detail": "$.jobs.build.steps[0].uses uses actions/checkout@main"},
        {"rule": "branch-pinned-action", "detail": "$.jobs.build.steps[1].uses uses some/action@master"},
        {"rule": "missing-timeout", "detail": "job build has no timeout-minutes"},
        {
            "rule": "pull-request-target-checkout",
            "detail": "job build step 0 checks out the pull request head under pull_request_target",
        },
        {"rule": "write-all-permissions", "detail": "$.permissions grants write-all"},
    ]


def test_workflow_missing_permissions_and_unparseable_are_findings(tmp_path: Path) -> None:
    root = make_repo(
        tmp_path / "repo",
        {
            ".github/workflows/a.yml": "on: push\njobs:\n  t:\n    runs-on: x\n    timeout-minutes: 5\n",
            ".github/workflows/b.yaml": "on: [push\njobs: {\n",
        },
    )
    observations = CiWorkflowSensor().scan(root, NOW)
    by_id = {o.subject.id: o for o in observations}
    assert set(by_id) == {".github/workflows/a.yml", ".github/workflows/b.yaml"}
    assert [f["rule"] for f in by_id[".github/workflows/a.yml"].observed_state["findings"]] == [
        "missing-permissions"
    ]
    broken = by_id[".github/workflows/b.yaml"].observed_state["findings"]
    assert [f["rule"] for f in broken] == ["unparseable-workflow"]
    assert "YAML parse error" in broken[0]["detail"]


def test_workflow_repeat_scan_is_identical(tmp_path: Path) -> None:
    root = make_repo(
        tmp_path / "repo",
        {
            ".github/workflows/a.yml": "on: push\njobs:\n  t:\n    runs-on: x\n",
            ".github/workflows/b.yml": "on: push\npermissions: write-all\njobs: {}\n",
        },
    )
    first = _run_dict(CiWorkflowSensor().scan(root, NOW))
    second = _run_dict(CiWorkflowSensor().scan(root, "2026-10-21T00:00:00Z"))
    assert [item["observedState"] for item in first] == [item["observedState"] for item in second]
    assert [item["subject"] for item in first] == [item["subject"] for item in second]


def test_workflow_missing_inventory_is_unavailable(tmp_path: Path) -> None:
    root = make_repo(tmp_path / "repo", {"README.md": "x\n"})
    with pytest.raises(SensorUnavailable):
        CiWorkflowSensor().scan(root, NOW)


def test_workflow_non_git_directory_is_unavailable(tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    (plain / ".github/workflows").mkdir(parents=True)
    (plain / ".github/workflows/ci.yml").write_text(CLEAN_WORKFLOW, encoding="utf-8")
    with pytest.raises(SensorUnavailable):
        CiWorkflowSensor().scan(plain, NOW)


def test_workflow_near_misses_are_not_findings(tmp_path: Path) -> None:
    body = """\
on:
  pull_request_target:
permissions:
  contents: read
jobs:
  release:
    uses: org/repo/.github/workflows/reusable.yml@v4
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
        with:
          ref: main
      - uses: actions/setup-python@v5
"""
    root = _workflow_repo(tmp_path, body)
    assert CiWorkflowSensor().scan(root, NOW) == []


def test_workflow_on_key_parsed_as_boolean_is_handled(tmp_path: Path) -> None:
    body = "on:\n  pull_request_target:\npermissions: {}\njobs:\n  b:\n    runs-on: x\n    timeout-minutes: 5\n    steps:\n      - uses: actions/checkout@v4\n        with:\n          ref: ${{ github.event.pull_request.head.ref }}\n"
    root = _workflow_repo(tmp_path, body)
    findings = CiWorkflowSensor().scan(root, NOW)[0].observed_state["findings"]
    assert [f["rule"] for f in findings] == ["pull-request-target-checkout"]


def test_workflow_nested_inert_directory_is_out_of_scope(tmp_path: Path) -> None:
    root = make_repo(
        tmp_path / "repo",
        {
            ".github/workflows/_disabled/old.yml": "on: push\njobs:\n  t:\n    runs-on: x\n",
            ".github/workflows/ci.yml": CLEAN_WORKFLOW,
        },
    )
    assert CiWorkflowSensor().scan(root, NOW) == []


def test_workflow_read_only(tmp_path: Path) -> None:
    root = _workflow_repo(tmp_path, "on: push\njobs: {}\n")
    before = tree_digest(root)
    CiWorkflowSensor().scan(root, NOW)
    assert tree_digest(root) == before


def test_workflow_recovery_removes_finding(tmp_path: Path) -> None:
    root = _workflow_repo(tmp_path, "on: push\njobs:\n  t:\n    runs-on: x\n")
    assert len(CiWorkflowSensor().scan(root, NOW)) == 1
    write_files(root, {".github/workflows/ci.yml": CLEAN_WORKFLOW})
    commit_all(root, "fix")
    assert CiWorkflowSensor().scan(root, NOW) == []


# --- CiHealthSensor ---------------------------------------------------------


def test_ci_health_absent_input_is_not_evaluated(tmp_path: Path) -> None:
    root = make_repo(tmp_path / "repo", {"README.md": "x\n"})
    with pytest.raises(SensorNotEvaluated):
        CiHealthSensor().scan(root, NOW)


def test_ci_health_non_git_directory_is_unavailable(tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    with pytest.raises(SensorUnavailable):
        CiHealthSensor().scan(plain, NOW)


def test_ci_health_latest_failure_is_exact_finding_with_churn(tmp_path: Path) -> None:
    root = make_repo(tmp_path / "repo", {"README.md": "x\n"})
    _write_inputs(
        root,
        "ci-runs.json",
        _ci_runs(
            [
                _run("tests", "success", created="2026-10-18T10:00:00Z"),
                _run("tests", "failure", created="2026-10-19T10:00:00Z", attempt=1, sha="b" * 40),
                _run("tests", "failure", created="2026-10-19T10:00:00Z", attempt=2, sha="b" * 40),
                _run("lint", "success", created="2026-10-19T11:00:00Z"),
            ]
        ),
    )
    observations = CiHealthSensor().scan(root, NOW)
    assert len(observations) == 1
    observation = observations[0]
    assert observation.kind == "ci_failure"
    assert observation.subject.type == "workflow-run"
    assert observation.subject.id == "tests"
    assert observation.observed_state["retryChurn"] == 1
    assert observation.observed_state["runCount"] == 3
    assert observation.observed_state["findingCount"] == 1
    finding = observation.observed_state["findings"][0]
    assert finding["conclusion"] == "failure"
    assert finding["headSha"] == "b" * 40
    assert finding["runAttempt"] == 2
    assert finding["url"] == "https://github.example.invalid/runs/tests-2"


def test_ci_health_all_green_is_zero_observations(tmp_path: Path) -> None:
    root = make_repo(tmp_path / "repo", {"README.md": "x\n"})
    _write_inputs(root, "ci-runs.json", _ci_runs([_run("tests", "success")]))
    assert CiHealthSensor().scan(root, NOW) == []


def test_ci_health_timed_out_and_startup_failure_count(tmp_path: Path) -> None:
    root = make_repo(tmp_path / "repo", {"README.md": "x\n"})
    _write_inputs(
        root,
        "ci-runs.json",
        _ci_runs([_run("a", "timed_out"), _run("b", "startup_failure"), _run("c", "cancelled")]),
    )
    ids = [o.subject.id for o in CiHealthSensor().scan(root, NOW)]
    assert ids == ["a", "b"]


def test_ci_health_repeat_and_recovery(tmp_path: Path) -> None:
    root = make_repo(tmp_path / "repo", {"README.md": "x\n"})
    _write_inputs(root, "ci-runs.json", _ci_runs([_run("tests", "failure")]))
    first = _run_dict(CiHealthSensor().scan(root, NOW))
    assert first == _run_dict(CiHealthSensor().scan(root, NOW))
    _write_inputs(
        root,
        "ci-runs.json",
        _ci_runs([_run("tests", "failure", created="2026-10-18T00:00:00Z"), _run("tests", "success", created="2026-10-19T00:00:00Z")]),
    )
    assert CiHealthSensor().scan(root, NOW) == []


@pytest.mark.parametrize(
    "payload",
    [
        "{not json",
        _ci_runs("not-a-list"),
        _ci_runs([_run("tests", "failure", attempt=True)]),
        _ci_runs([{"workflow": "tests"}]),
        _ci_runs([_run("tests", "failure", created="yesterday")]),
        {"schemaVersion": "steward-ci-runs-v0", "runs": []},
    ],
)
def test_ci_health_malformed_input_is_unavailable(tmp_path: Path, payload) -> None:
    root = make_repo(tmp_path / "repo", {"README.md": "x\n"})
    _write_inputs(root, "ci-runs.json", payload)
    with pytest.raises(SensorUnavailable):
        CiHealthSensor().scan(root, NOW)


def test_ci_health_oversized_input_is_unavailable(tmp_path: Path) -> None:
    root = make_repo(tmp_path / "repo", {"README.md": "x\n"})
    _write_inputs(root, "ci-runs.json", " " * (2 * 1024 * 1024 + 1))
    with pytest.raises(SensorUnavailable):
        CiHealthSensor().scan(root, NOW)


def test_ci_health_read_only(tmp_path: Path) -> None:
    root = make_repo(tmp_path / "repo", {"README.md": "x\n"})
    _write_inputs(root, "ci-runs.json", _ci_runs([_run("tests", "failure")]))
    before = tree_digest(root)
    CiHealthSensor().scan(root, NOW)
    assert tree_digest(root) == before


# --- SupplyChainSensor ------------------------------------------------------


def test_supply_clean_repository_yields_no_observations(tmp_path: Path) -> None:
    root = make_repo(tmp_path / "repo", CLEAN_SUPPLY)
    assert SupplyChainSensor().scan(root, NOW) == []


def test_supply_version_lockstep_drift_is_exact(tmp_path: Path) -> None:
    files = dict(CLEAN_SUPPLY)
    files["packages/cli-npm/package.json"] = NPM_CLEAN.replace("1.2.3", "1.2.4")
    root = make_repo(tmp_path / "repo", files)
    observations = SupplyChainSensor().scan(root, NOW)
    assert [o.kind for o in observations] == ["version_lockstep_drift"]
    observation = observations[0]
    assert observation.subject.type == "manifest-versions"
    assert observation.observed_state["versions"] == {"pyproject": "1.2.3", "cliNPM": "1.2.4"}
    assert observation.observed_state["findings"] == [
        {"rule": "version-mismatch", "detail": "pyproject.toml=1.2.3 packages/cli-npm/package.json=1.2.4"}
    ]


def test_supply_unpinned_dependency_is_exact_with_confidence(tmp_path: Path) -> None:
    pyproject = PYPROJECT_CLEAN.replace('"pyyaml>=6.0",', '"pyyaml>=6.0",\n    "requests",')
    root = make_repo(tmp_path / "repo", {**CLEAN_SUPPLY, "pyproject.toml": pyproject})
    observations = SupplyChainSensor().scan(root, NOW)
    assert [o.kind for o in observations] == ["dependency_pin_drift"]
    observation = observations[0]
    assert observation.subject.id == "python-dependencies"
    assert observation.confidence == 0.8
    assert observation.observed_state["findingCount"] == 1
    assert observation.observed_state["findings"][0]["requirement"] == "requests"
    assert observation.observed_state["findings"][0]["group"] == "dependencies"


def test_supply_license_drift_undeclared_and_mismatch(tmp_path: Path) -> None:
    pyproject = PYPROJECT_CLEAN.replace('license = {text = "MIT"}\n', "")
    root = make_repo(tmp_path / "repo", {**CLEAN_SUPPLY, "pyproject.toml": pyproject})
    observations = SupplyChainSensor().scan(root, NOW)
    assert [o.kind for o in observations] == ["license_metadata_drift"]
    assert observations[0].confidence == 0.9
    assert [f["rule"] for f in observations[0].observed_state["findings"]] == ["license-undeclared"]

    mismatch = {**CLEAN_SUPPLY, "packages/cli-npm/package.json": NPM_CLEAN.replace('"MIT"', '"Apache-2.0"')}
    root2 = make_repo(tmp_path / "repo2", mismatch)
    findings = SupplyChainSensor().scan(root2, NOW)[0].observed_state["findings"]
    assert findings == [
        {
            "rule": "license-mismatch",
            "detail": "pyproject declares MIT but packages/cli-npm/package.json declares Apache-2.0",
        }
    ]


def test_supply_license_classifier_counts_as_declared(tmp_path: Path) -> None:
    pyproject = (
        '[project]\nname = "demo"\nversion = "1.2.3"\n'
        'classifiers = ["License :: OSI Approved :: MIT License"]\n'
    )
    root = make_repo(tmp_path / "repo", {**CLEAN_SUPPLY, "pyproject.toml": pyproject})
    assert SupplyChainSensor().scan(root, NOW) == []


def test_supply_near_misses_are_not_findings(tmp_path: Path) -> None:
    pyproject = """\
[project]
name = "demo"
version = "1.2.3"
license = "MIT"
dependencies = [
    "pkg>=1",
    "pkg2==2.0.0",
    "pkg3[extra]~=3.1",
    "pkg4 @ https://example.invalid/pkg4-1.0.tar.gz",
    "pkg5 ; python_version < '3.11'",
]
"""
    root = make_repo(
        tmp_path / "repo",
        {
            "pyproject.toml": pyproject.replace("pkg5 ; python_version < '3.11'", "pkg5<2"),
            "packages/cli-npm/package.json": NPM_CLEAN,
            "LICENSE": "MIT\n",
        },
    )
    assert SupplyChainSensor().scan(root, NOW) == []


def test_supply_missing_pyproject_is_unavailable(tmp_path: Path) -> None:
    root = make_repo(tmp_path / "repo", {"packages/cli-npm/package.json": NPM_CLEAN})
    with pytest.raises(SensorUnavailable):
        SupplyChainSensor().scan(root, NOW)


def test_supply_non_git_directory_is_unavailable(tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    (plain / "pyproject.toml").write_text(PYPROJECT_CLEAN, encoding="utf-8")
    with pytest.raises(SensorUnavailable):
        SupplyChainSensor().scan(plain, NOW)


def test_supply_malformed_manifest_is_unavailable(tmp_path: Path) -> None:
    root = make_repo(tmp_path / "repo", {**CLEAN_SUPPLY, "pyproject.toml": "[project\n"})
    with pytest.raises(SensorUnavailable):
        SupplyChainSensor().scan(root, NOW)


def test_supply_read_only_and_recovery(tmp_path: Path) -> None:
    files = dict(CLEAN_SUPPLY)
    files["packages/cli-npm/package.json"] = NPM_CLEAN.replace("1.2.3", "9.9.9")
    root = make_repo(tmp_path / "repo", files)
    before = tree_digest(root)
    assert len(SupplyChainSensor().scan(root, NOW)) == 1
    assert tree_digest(root) == before
    write_files(root, {"packages/cli-npm/package.json": NPM_CLEAN})
    commit_all(root, "fix")
    assert SupplyChainSensor().scan(root, NOW) == []


# --- DependencyAdvisorySensor -----------------------------------------------


def _advisories(*dependencies):
    return {"dependencies": list(dependencies), "fixes": []}


def test_advisory_clean_inventory_yields_no_observations(tmp_path: Path) -> None:
    root = make_repo(tmp_path / "repo", {"README.md": "x\n"})
    _write_inputs(root, "advisories.json", _advisories({"name": "pyyaml", "version": "6.0", "vulns": []}))
    assert DependencyAdvisorySensor().scan(root, NOW) == []


def test_advisory_real_vulnerability_is_exact_finding(tmp_path: Path) -> None:
    root = make_repo(tmp_path / "repo", {"README.md": "x\n"})
    _write_inputs(
        root,
        "advisories.json",
        _advisories(
            {
                "name": "jinja2",
                "version": "3.0.0",
                "vulns": [
                    {"id": "PYSEC-2024-2", "fix_versions": ["3.1.5", "3.0.6"], "aliases": ["CVE-x"]},
                    {"id": "PYSEC-2024-1", "fix_versions": ["3.1.4"]},
                ],
            },
            {"name": "pyyaml", "version": "6.0", "vulns": []},
        ),
    )
    observations = DependencyAdvisorySensor().scan(root, NOW)
    assert len(observations) == 1
    observation = observations[0]
    assert observation.kind == "dependency_advisory"
    assert observation.subject.type == "python-package"
    assert observation.subject.id == "jinja2"
    assert observation.confidence == 1.0
    assert observation.observed_state["installedVersions"] == ["3.0.0"]
    assert observation.observed_state["findings"] == [
        {
            "rule": "known-vulnerability",
            "detail": "jinja2 3.0.0 is affected by PYSEC-2024-1",
            "vulnerabilityId": "PYSEC-2024-1",
            "installedVersion": "3.0.0",
            "fixVersions": ["3.1.4"],
        },
        {
            "rule": "known-vulnerability",
            "detail": "jinja2 3.0.0 is affected by PYSEC-2024-2",
            "vulnerabilityId": "PYSEC-2024-2",
            "installedVersion": "3.0.0",
            "fixVersions": ["3.0.6", "3.1.5"],
        },
    ]


def test_advisory_absent_input_is_not_evaluated(tmp_path: Path) -> None:
    root = make_repo(tmp_path / "repo", {"README.md": "x\n"})
    with pytest.raises(SensorNotEvaluated):
        DependencyAdvisorySensor().scan(root, NOW)


def test_advisory_non_git_directory_is_unavailable(tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    with pytest.raises(SensorUnavailable):
        DependencyAdvisorySensor().scan(plain, NOW)


@pytest.mark.parametrize(
    "payload",
    [
        "[not an object",
        {"fixes": []},
        {"dependencies": "nope"},
        {"dependencies": [{"name": "x", "vulns": []}]},
        {"dependencies": [{"name": "x", "version": "1", "vulns": [{"fix_versions": []}]}]},
        {"dependencies": [{"name": "x", "version": "1", "vulns": [{"id": "V", "fix_versions": "3"}]}]},
    ],
)
def test_advisory_malformed_input_is_unavailable(tmp_path: Path, payload) -> None:
    root = make_repo(tmp_path / "repo", {"README.md": "x\n"})
    _write_inputs(root, "advisories.json", payload)
    with pytest.raises(SensorUnavailable):
        DependencyAdvisorySensor().scan(root, NOW)


def test_advisory_repeat_read_only_and_recovery(tmp_path: Path) -> None:
    root = make_repo(tmp_path / "repo", {"README.md": "x\n"})
    _write_inputs(
        root,
        "advisories.json",
        _advisories({"name": "jinja2", "version": "3.0.0", "vulns": [{"id": "V1", "fix_versions": ["3.1.0"]}]}),
    )
    before = tree_digest(root)
    first = _run_dict(DependencyAdvisorySensor().scan(root, NOW))
    assert first == _run_dict(DependencyAdvisorySensor().scan(root, NOW))
    assert tree_digest(root) == before
    _write_inputs(root, "advisories.json", _advisories({"name": "jinja2", "version": "3.1.0", "vulns": []}))
    assert DependencyAdvisorySensor().scan(root, NOW) == []
