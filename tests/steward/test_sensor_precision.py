"""Precision and redaction regressions for the Steward sensors.

A finding must never carry a value read from the repository, a driver input
that is stale or about another repository must observe nothing, and a sensor
must not report a pattern that is not a defect. Credentials in this file are
assembled at runtime so the secret-scan sensor finds no literal here.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from gaia_cli.main import main
from gaia_cli.steward.controller import StewardController
from gaia_cli.steward.policy import POLICY_RELATIVE_PATH
from gaia_cli.steward.primitives import SensorNotEvaluated, SensorUnavailable
from gaia_cli.steward.primitives.redact import describe_value, fingerprint, scrub
from gaia_cli.steward.sensors_ci import (
    CiHealthSensor,
    CiWorkflowSensor,
    DependencyAdvisorySensor,
    SupplyChainSensor,
)
from gaia_cli.steward.sensors_contracts import SchemaValiditySensor, TimelineCausalitySensor
from gaia_cli.steward.sensors_tests import TestHistorySensor, TestIsolationSensor
from tests.steward.sensor_fixtures import commit_all, make_repo, set_mtime, write_files
from tests.steward.test_cli import _clean_cli_repo
from tests.steward.test_sensors_ci import CLEAN_SUPPLY, NOW, _advisories, _ci_runs, _run, _write_inputs

REPO_ROOT = Path(__file__).resolve().parents[2]
START = datetime(2026, 10, 20, tzinfo=timezone.utc)


def _key() -> str:
    return "AKIA" + "Q" * 16


def _stamp(value: datetime) -> str:
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


# ---------------------------------------------------------------- redaction


def test_describe_value_reports_type_length_and_fingerprint_only() -> None:
    shown = describe_value(_key())
    assert _key() not in shown
    assert shown == f"<str length=20 sha256={fingerprint(_key())}>"
    assert len(fingerprint(_key())) == 12


def test_scrub_replaces_credential_shaped_substrings_only() -> None:
    scrubbed = scrub(f"tests/test_x.py::test[{_key()}]")
    assert _key() not in scrubbed
    assert scrubbed.startswith("tests/test_x.py::test[<aws-access-key-id sha256=")
    assert scrub("tests/test_x.py::test_plain") == "tests/test_x.py::test_plain"


def _plant(root: Path) -> None:
    key = _key()
    named = (
        "---\nid: fixture/example\nname: example\ncontributor: fixture\ntimeline:\n"
        f"  - action: created\n    timestamp: {key}\n"
        '  - action: updated\n    timestamp: "2026-01-02T00:00:00Z"\n'
        "---\n# Example\n"
    )
    schema = json.dumps(
        {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {"a": {"type": "integer", "minimum": key}},
        },
        sort_keys=True,
    )
    write_files(
        root,
        {
            "registry/named/fixture/example.md": named,
            "registry/schema/leaky.schema.json": schema,
            "src/gaia_cli/data/registry/schema/leaky.schema.json": schema,
        },
    )
    commit_all(root, "plant")


def test_planted_credential_never_reaches_stdout_debt_or_receipts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _clean_cli_repo(tmp_path)
    _plant(tmp_path)
    monkeypatch.setattr(sys, "argv", ["gaia", "--registry", str(tmp_path), "steward", "scan", "--json"])

    main()

    stdout = capsys.readouterr().out
    payload = json.loads(stdout)
    drift = {item["kind"] for item in payload["observations"] if item["status"] == "drift"}
    # The test is only meaningful if both sensors really reported the planted value.
    assert {"timeline_causality_drift", "schema_contract_drift"} <= drift
    state = tmp_path / ".gaia" / "steward"
    files = [path for path in state.rglob("*") if path.is_file()]
    assert (state / "debt.json") in files
    assert any(path.parent.name == "receipts" for path in files)
    artifacts = [stdout] + [path.read_text(encoding="utf-8") for path in files]
    assert not [text for text in artifacts if _key() in text]
    # The credential scanner may fingerprint it, never print it.
    assert any(item["kind"] == "credential_leak" for item in payload["observations"])


def test_timeline_unparseable_timestamp_is_described_not_echoed(tmp_path: Path) -> None:
    repo = make_repo(
        tmp_path / "repo",
        {
            "registry/named/o/a.md": (
                f"---\nid: o/a\ntimeline:\n  - action: x\n    timestamp: {_key()}\n---\n"
            )
        },
    )
    (observation,) = TimelineCausalitySensor().scan(repo, NOW)
    detail = observation.observed_state["findings"][0]["detail"]
    assert _key() not in json.dumps(observation.to_dict())
    assert f"sha256={fingerprint(_key())}" in detail
    assert "length=20" in detail


def test_schema_invalid_reports_keyword_and_path_not_the_instance(tmp_path: Path) -> None:
    schema = json.dumps({"type": "object", "properties": {"a": {"type": "integer", "minimum": _key()}}})
    repo = make_repo(tmp_path / "repo", {"registry/schema/s.json": schema})
    (observation,) = SchemaValiditySensor().scan(repo, NOW)
    (finding,) = observation.observed_state["findings"]
    assert _key() not in json.dumps(observation.to_dict())
    assert finding == {"rule": "invalid-schema", "detail": "keyword type fails at /properties/a/minimum"}


def test_workflow_and_manifest_echoes_are_scrubbed(tmp_path: Path) -> None:
    workflow = (
        "name: ci\non: push\npermissions:\n  contents: read\njobs:\n"
        f"  build:\n    runs-on: x\n    timeout-minutes: 5\n    steps:\n      - uses: owner/{_key()}@main\n"
    )
    repo = make_repo(tmp_path / "repo", {".github/workflows/ci.yml": workflow})
    (observation,) = CiWorkflowSensor().scan(repo, NOW)
    assert _key() not in json.dumps(observation.to_dict())


def test_pyproject_requirement_and_version_echoes_are_redacted(tmp_path: Path) -> None:
    files = dict(CLEAN_SUPPLY)
    files["pyproject.toml"] = files["pyproject.toml"].replace('"pyyaml>=6.0",', f'"pyyaml>=6.0", "{_key()}",')
    files["packages/cli-npm/package.json"] = '{"name": "demo", "version": "%s", "license": "MIT"}\n' % _key()
    repo = make_repo(tmp_path / "repo", files)
    serialized = json.dumps([o.to_dict() for o in SupplyChainSensor().scan(repo, NOW)])
    assert _key() not in serialized
    assert "version-mismatch" in serialized


def test_test_history_never_echoes_run_ids_or_shas(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo", {"tests/test_a.py": "def test_a():\n    pass\n"})
    runs = [
        {"runId": _key(), "sha": "abc", "results": {"tests/test_a.py::test_a": "passed"}},
        {"runId": "r2", "sha": "abc", "results": {"tests/test_a.py::test_a": "failed"}},
    ]
    path = repo / ".gaia/steward/inputs/test-history.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"schemaVersion": "steward-test-history-v1", "runs": runs}))
    set_mtime(path, NOW)
    serialized = json.dumps([o.to_dict() for o in TestHistorySensor().scan(repo, NOW)])
    assert _key() not in serialized
    assert "<aws-access-key-id sha256=" in serialized

    runs.append({"runId": _key(), "sha": "abd", "results": {}})
    path.write_text(json.dumps({"schemaVersion": "steward-test-history-v1", "runs": runs}))
    set_mtime(path, NOW)
    with pytest.raises(SensorUnavailable) as raised:
        TestHistorySensor().scan(repo, NOW)
    assert _key() not in str(raised.value)


def test_ci_runs_malformed_values_are_described_not_echoed(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo", {"README.md": "x\n"})
    bad = _run("tests", "failure")
    bad["headSha"] = _key()
    _write_inputs(repo, "ci-runs.json", _ci_runs([bad]))
    with pytest.raises(SensorUnavailable) as raised:
        CiHealthSensor().scan(repo, NOW)
    assert _key() not in str(raised.value)
    assert "sha256=" in str(raised.value)


# ------------------------------------------------ driver input freshness etc.

DAY = timedelta(days=1)


def _at(offset: timedelta) -> str:
    return _stamp(START + offset)


def _history_payload(passed_and_failed: bool) -> dict:
    second = "failed" if passed_and_failed else "passed"
    return {
        "schemaVersion": "steward-test-history-v1",
        "runs": [
            {"runId": "r1", "sha": "abc", "results": {"tests/test_a.py::test_a": "passed"}},
            {"runId": "r2", "sha": "abc", "results": {"tests/test_a.py::test_a": second}},
        ],
    }


# (sensor factory, input file name, failing payload, healthy payload)
DRIVEN = {
    "ci-health": (
        CiHealthSensor,
        "ci-runs.json",
        lambda when: _ci_runs([_run("tests", "failure")], collectedAt=when),
        lambda when: _ci_runs([_run("tests", "success")], collectedAt=when),
    ),
    "dependency-advisory": (
        DependencyAdvisorySensor,
        "advisories.json",
        lambda when: {
            **_advisories({"name": "jinja2", "version": "3.0.0", "vulns": [{"id": "V1", "fix_versions": ["3.1.0"]}]}),
            "collectedAt": when,
        },
        lambda when: {
            **_advisories({"name": "jinja2", "version": "3.1.0", "vulns": []}),
            "collectedAt": when,
        },
    ),
    "test-history": (
        TestHistorySensor,
        "test-history.json",
        lambda when: {**_history_payload(True), "collectedAt": when},
        lambda when: {**_history_payload(False), "collectedAt": when},
    ),
}


def _driven_repo(tmp_path: Path) -> Path:
    root = make_repo(tmp_path / "repo", {POLICY_RELATIVE_PATH.as_posix(): (REPO_ROOT / POLICY_RELATIVE_PATH).read_text()})
    return root


@pytest.mark.parametrize("name", sorted(DRIVEN))
def test_stale_or_future_input_is_not_evaluated(tmp_path: Path, name: str) -> None:
    factory, filename, failing, _ = DRIVEN[name]
    root = _driven_repo(tmp_path)
    for when in (_at(-8 * DAY), _at(DAY)):
        _write_inputs(root, filename, failing(when))
        with pytest.raises(SensorNotEvaluated, match="stale input"):
            factory().scan(root, NOW)
    # Exactly inside the bound is still evaluated.
    _write_inputs(root, filename, failing(_at(-6 * DAY)))
    assert factory().scan(root, NOW)


@pytest.mark.parametrize("name", ["dependency-advisory", "test-history"])
def test_untimestamped_input_is_dated_by_its_file(tmp_path: Path, name: str) -> None:
    factory, filename, failing, _ = DRIVEN[name]
    root = _driven_repo(tmp_path)
    payload = failing(_at(timedelta(0)))
    del payload["collectedAt"]
    for offset, expected in ((-8 * DAY, True), (-1 * DAY, False)):
        _write_inputs(root, filename, payload)
        set_mtime(root / ".gaia/steward/inputs" / filename, _at(offset))
        if expected:
            with pytest.raises(SensorNotEvaluated, match="stale input"):
                factory().scan(root, NOW)
        else:
            assert factory().scan(root, NOW)


def _controller_scan(root: Path, controller: StewardController):
    return controller.scan(root)


class Clock:
    def __init__(self) -> None:
        self.now = START

    def __call__(self) -> datetime:
        self.now += timedelta(minutes=1)
        return self.now


@pytest.mark.parametrize("name", sorted(DRIVEN))
def test_fresh_healthy_input_resolves_its_own_previous_debt(tmp_path: Path, name: str) -> None:
    factory, filename, failing, healthy = DRIVEN[name]
    root = _driven_repo(tmp_path)
    sensor = factory()
    assert sensor.resolution_scope == "exhaustive"
    controller = StewardController(sensors=[sensor], clock=Clock())

    _write_inputs(root, filename, failing(_at(timedelta(0))))
    first = controller.scan(root)
    assert [d.kind for d in first.open_debts]
    assert first.receipt.not_evaluated == ()

    _write_inputs(root, filename, healthy(_at(timedelta(minutes=5))))
    second = controller.scan(root)
    assert second.open_debts == ()
    assert {d.resolution for d in second.debts} == {"condition_not_reobserved"}
    assert second.receipt.debt_resolved


@pytest.mark.parametrize("name", sorted(DRIVEN))
def test_missing_or_stale_input_sweeps_nothing(tmp_path: Path, name: str) -> None:
    factory, filename, failing, healthy = DRIVEN[name]
    root = _driven_repo(tmp_path)
    controller = StewardController(sensors=[factory()], clock=Clock())
    _write_inputs(root, filename, failing(_at(timedelta(0))))
    opened = {d.id for d in controller.scan(root).open_debts}
    assert opened

    # Stale healthy input: not evaluated, so the debt it would resolve stays open.
    _write_inputs(root, filename, healthy(_at(-30 * DAY)))
    stale = controller.scan(root)
    assert {d.id for d in stale.open_debts} == opened
    assert [item["sensor"] for item in stale.receipt.not_evaluated] == [name]
    assert "stale input" in stale.receipt.not_evaluated[0]["reason"]
    assert stale.receipt.debt_resolved == ()

    # Missing input: the same.
    (root / ".gaia/steward/inputs" / filename).unlink()
    missing = controller.scan(root)
    assert {d.id for d in missing.open_debts} == opened
    assert [item["sensor"] for item in missing.receipt.not_evaluated] == [name]
    assert missing.receipt.debt_resolved == ()
    assert not any(item.kind == "sensor_coverage_unknown" for item in missing.observations)


def test_unavailable_input_still_sweeps_nothing(tmp_path: Path) -> None:
    factory, filename, failing, _ = DRIVEN["ci-health"]
    root = _driven_repo(tmp_path)
    controller = StewardController(sensors=[factory()], clock=Clock())
    _write_inputs(root, filename, failing(_at(timedelta(0))))
    opened = {d.id for d in controller.scan(root).open_debts}
    _write_inputs(root, filename, "{not json")
    broken = controller.scan(root)
    assert opened <= {d.id for d in broken.open_debts}
    assert broken.receipt.coverage_unknown == ("ci-health",)


# --------------------------------------------------------- ci-runs identity


def _origin(root: Path, url: str) -> None:
    subprocess.run(["git", "-C", str(root), "remote", "add", "origin", url], check=True)


@pytest.mark.parametrize(
    "url",
    [
        "https://github.com/gaia-research/gaia-skill-tree.git",
        "git@github.com:Gaia-Research/gaia-skill-tree.git",
        "ssh://git@github.com/gaia-research/gaia-skill-tree",
        "http://local_proxy@127.0.0.1:41405/git/gaia-research/gaia-skill-tree",
    ],
)
def test_ci_runs_repository_matching_origin_is_evaluated(tmp_path: Path, url: str) -> None:
    root = make_repo(tmp_path / "repo", {"README.md": "x\n"})
    _origin(root, url)
    _write_inputs(root, "ci-runs.json", _ci_runs([_run("tests", "failure")]))
    (observation,) = CiHealthSensor().scan(root, NOW)
    assert observation.provenance["repositoryCheck"] == "origin-match"
    assert observation.provenance["repository"] == "gaia-research/gaia-skill-tree"
    assert observation.provenance["branch"] == "dev/example"


def test_ci_runs_for_another_repository_is_not_evaluated(tmp_path: Path) -> None:
    root = make_repo(tmp_path / "repo", {"README.md": "x\n"})
    _origin(root, "https://github.com/someone/fork.git")
    _write_inputs(root, "ci-runs.json", _ci_runs([_run("tests", "failure")]))
    with pytest.raises(SensorNotEvaluated, match="another repository"):
        CiHealthSensor().scan(root, NOW)


def test_ci_runs_without_a_determinable_origin_records_it_in_provenance(tmp_path: Path) -> None:
    root = make_repo(tmp_path / "repo", {"README.md": "x\n"})
    _write_inputs(root, "ci-runs.json", _ci_runs([_run("tests", "failure")]))
    (observation,) = CiHealthSensor().scan(root, NOW)
    assert observation.provenance["repositoryCheck"] == "origin-unknown"
    # A local-path remote is not a URL; it is "unknown", never a mismatch.
    _origin(root, str(tmp_path / "elsewhere"))
    (observation,) = CiHealthSensor().scan(root, NOW)
    assert observation.provenance["repositoryCheck"] == "origin-unknown"


@pytest.mark.parametrize(
    "overrides",
    [{"repository": ""}, {"repository": "not-owner-name"}, {"branch": ""}, {"branch": "has space"}, {"repository": 7}],
)
def test_ci_runs_repository_and_branch_must_be_plain_non_empty_strings(tmp_path: Path, overrides: dict) -> None:
    root = make_repo(tmp_path / "repo", {"README.md": "x\n"})
    _write_inputs(root, "ci-runs.json", _ci_runs([_run("tests", "failure")], **overrides))
    with pytest.raises(SensorUnavailable):
        CiHealthSensor().scan(root, NOW)


def test_ci_health_groups_by_workflow_path_then_id_then_name(tmp_path: Path) -> None:
    root = make_repo(tmp_path / "repo", {"README.md": "x\n"})
    runs = [
        {**_run("CI", "failure"), "workflowPath": ".github/workflows/a.yml"},
        {**_run("CI", "success", created="2026-10-19T12:00:00Z"), "workflowPath": ".github/workflows/b.yml"},
        {**_run("Deploy", "failure"), "workflowId": 42},
        {**_run("Deploy", "success", created="2026-10-18T10:00:00Z"), "workflowId": 43},
        _run("plain", "failure"),
    ]
    _write_inputs(root, "ci-runs.json", _ci_runs(runs))
    ids = sorted(o.subject.id for o in CiHealthSensor().scan(root, NOW))
    # Two workflows that share a display name stay separate.
    assert ids == [".github/workflows/a.yml", "id:42", "plain"]


def test_ci_health_one_group_when_the_name_is_the_only_identity(tmp_path: Path) -> None:
    root = make_repo(tmp_path / "repo", {"README.md": "x\n"})
    _write_inputs(
        root,
        "ci-runs.json",
        _ci_runs([_run("tests", "failure", created="2026-10-18T10:00:00Z"), _run("tests", "success")]),
    )
    assert CiHealthSensor().scan(root, NOW) == []


# ---------------------------------------------------------------- pip-audit

# Captured from `pip-audit --format json --local -o FILE` (pip-audit 2.10.1) in an
# environment with one editable local package: descriptions are shortened, nothing else.
REAL_PIP_AUDIT = (
    '{"dependencies": [{"name": "certifi", "version": "2026.10.19", "vulns": []}, '
    '{"name": "jinja2", "version": "3.0.0", "vulns": ['
    '{"id": "PYSEC-2026-1473", "fix_versions": ["3.1.3"], "aliases": ["CVE-2024-22195", "GHSA-h5c8-rqwp-cp95"], '
    '"description": "The `xmlattr` filter in affected versions of Jinja accepts k"}, '
    '{"id": "PYSEC-2026-1474", "fix_versions": ["3.1.4"], "aliases": ["CVE-2024-34064", "GHSA-h75v-3vvj-5mfj"], '
    '"description": "The `xmlattr` filter in affected versions of Jinja accepts k"}]}, '
    '{"name": "wbtiny", "skip_reason": "Dependency not found on PyPI and could not be audited: wbtiny (0.1)"}], '
    '"fixes": []}'
)


def test_real_pip_audit_output_is_accepted_and_skipped_entries_are_recorded(tmp_path: Path) -> None:
    root = make_repo(tmp_path / "repo", {"README.md": "x\n"})
    _write_inputs(root, "advisories.json", REAL_PIP_AUDIT)
    (observation,) = DependencyAdvisorySensor().scan(root, NOW)
    assert observation.subject.id == "jinja2"
    assert observation.observed_state["findingCount"] == 2
    assert observation.provenance["notAuditedCount"] == 1
    assert observation.provenance["notAudited"] == [
        {
            "name": "wbtiny",
            "reason": "Dependency not found on PyPI and could not be audited: wbtiny (0.1)",
        }
    ]
    assert observation.provenance["dependenciesAudited"] == 2
    assert observation.provenance["freshnessSource"] == "file-mtime"


def test_skipped_dependency_alone_is_clean_not_an_error(tmp_path: Path) -> None:
    root = make_repo(tmp_path / "repo", {"README.md": "x\n"})
    _write_inputs(root, "advisories.json", {"dependencies": [{"name": "local", "skip_reason": "editable"}], "fixes": []})
    assert DependencyAdvisorySensor().scan(root, NOW) == []


def test_unaudited_third_party_package_is_a_reported_skip(tmp_path: Path) -> None:
    # A package vulnerable yesterday and unauditable today must not be swept as fixed.
    root = make_repo(tmp_path / "repo", {"README.md": "x\n", "pyproject.toml": '[project]\nname = "Own_Pkg"\n'})
    _write_inputs(
        root,
        "advisories.json",
        {
            "dependencies": [
                {"name": "own-pkg", "skip_reason": "editable"},
                {"name": "jinja2", "skip_reason": "Dependency not found on PyPI"},
            ],
            "fixes": [],
        },
    )
    result = DependencyAdvisorySensor().scan_detailed(root, NOW)
    assert result.observations == ()
    assert [entry["subjectId"] for entry in result.skipped] == ["jinja2"]


def test_own_editable_project_skip_keeps_the_sweep_exhaustive(tmp_path: Path) -> None:
    root = make_repo(tmp_path / "repo", {"README.md": "x\n", "pyproject.toml": '[project]\nname = "gaia-cli"\n'})
    _write_inputs(root, "advisories.json", {"dependencies": [{"name": "gaia_cli", "skip_reason": "editable"}], "fixes": []})
    assert DependencyAdvisorySensor().scan_detailed(root, NOW).skipped == ()


def test_registry_schema_violation_never_echoes_the_value() -> None:
    from jsonschema import Draft7Validator

    from gaia_cli.steward.sensors import schemaViolation

    planted = "AKIA" + "Q" * 16
    (error,) = Draft7Validator({"properties": {"id": {"type": "integer"}}}).iter_errors({"id": planted})
    described = schemaViolation(error)
    assert described == "schema /id: type violation"
    assert planted not in described


@pytest.mark.parametrize(
    "dependency",
    [
        {"name": "x", "skip_reason": 7},
        {"name": "x"},
        {"skip_reason": "no name"},
    ],
)
def test_malformed_skip_entries_remain_unavailable(tmp_path: Path, dependency: dict) -> None:
    root = make_repo(tmp_path / "repo", {"README.md": "x\n"})
    _write_inputs(root, "advisories.json", {"dependencies": [dependency], "fixes": []})
    with pytest.raises(SensorUnavailable):
        DependencyAdvisorySensor().scan(root, NOW)


# ----------------------------------------------------- workflow permissions

WORKFLOW_HEAD = "name: ci\non: push\n"
JOB = "  {name}:\n    runs-on: x\n    timeout-minutes: 5\n{perm}    steps:\n      - run: echo\n"


def _workflow(top: str, jobs: list[tuple[str, bool]]) -> str:
    body = "".join(JOB.format(name=name, perm="    permissions:\n      contents: read\n" if scoped else "") for name, scoped in jobs)
    return WORKFLOW_HEAD + top + "jobs:\n" + body


def _permission_findings(tmp_path: Path, text: str) -> list[dict]:
    root = make_repo(tmp_path / "repo", {".github/workflows/ci.yml": text})
    return [f for o in CiWorkflowSensor().scan(root, NOW) for f in o.observed_state["findings"] if f["rule"] == "missing-permissions"]


def test_job_level_permissions_on_every_job_are_not_a_gap(tmp_path: Path) -> None:
    assert _permission_findings(tmp_path, _workflow("", [("a", True), ("b", True)])) == []


def test_top_level_permissions_cap_unscoped_jobs(tmp_path: Path) -> None:
    assert _permission_findings(tmp_path, _workflow("permissions:\n  contents: read\n", [("a", False)])) == []


def test_a_job_without_permissions_and_no_top_level_is_flagged(tmp_path: Path) -> None:
    (finding,) = _permission_findings(tmp_path, _workflow("", [("a", True), ("b", False)]))
    assert finding["detail"] == "no top-level permissions key and no job-level permissions on job b"


def test_every_live_missing_permissions_false_positive_is_gone() -> None:
    names = [
        "auto-triage", "branch-scope", "docs-cohesion", "labels-sync", "meta-guard",
        "pr-author-identity", "pr-first-time-contributor", "verify-evidence",
    ]
    live = {o.subject.id: o for o in CiWorkflowSensor().scan(REPO_ROOT, NOW)}
    for name in names:
        observation = live.get(f".github/workflows/{name}.yml")
        rules = {f["rule"] for f in observation.observed_state["findings"]} if observation else set()
        assert "missing-permissions" not in rules, name


# ------------------------------------------------------------ chdir restore


def _isolation(tmp_path: Path, body: str) -> list[dict]:
    root = make_repo(tmp_path / "repo", {"tests/test_a.py": body})
    return [f for o in TestIsolationSensor().scan(root, NOW) for f in o.observed_state["findings"] if f["pattern"] == "chdir"]


RESTORED = {
    "try-finally": (
        "import os\n\n\ndef test_a(tmp_path):\n    orig = os.getcwd()\n    try:\n        os.chdir(tmp_path)\n"
        "    finally:\n        os.chdir(orig)\n"
    ),
    "unittest-teardown": (
        "import os\nimport unittest\n\n\nclass T(unittest.TestCase):\n    def setUp(self):\n"
        "        self.orig = os.getcwd()\n        os.chdir('/')\n\n    def tearDown(self):\n        os.chdir(self.orig)\n"
    ),
    "fixture-yield": (
        "import os\nimport pytest\n\n\n@pytest.fixture\ndef cwd(tmp_path):\n    orig = os.getcwd()\n"
        "    os.chdir(tmp_path)\n    yield\n    os.chdir(orig)\n"
    ),
    "add-cleanup": (
        "import os\nimport unittest\n\n\nclass T(unittest.TestCase):\n    def test_a(self):\n"
        "        self.addCleanup(os.chdir, os.getcwd())\n        os.chdir('/')\n"
    ),
}


@pytest.mark.parametrize("shape", sorted(RESTORED))
def test_restored_chdir_is_not_flagged(tmp_path: Path, shape: str) -> None:
    assert _isolation(tmp_path, RESTORED[shape]) == []


UNRESTORED = {
    "bare": "import os\n\n\ndef test_a(tmp_path):\n    os.chdir(tmp_path)\n",
    "try-without-restore": (
        "import os\n\n\ndef test_a(tmp_path):\n    try:\n        os.chdir(tmp_path)\n    finally:\n        print('x')\n"
    ),
    "teardown-that-does-not-chdir": (
        "import os\nimport unittest\n\n\nclass T(unittest.TestCase):\n    def setUp(self):\n"
        "        os.chdir('/')\n\n    def tearDown(self):\n        pass\n"
    ),
    "fixture-without-restore": (
        "import os\nimport pytest\n\n\n@pytest.fixture\ndef cwd(tmp_path):\n    os.chdir(tmp_path)\n    yield\n"
    ),
}


@pytest.mark.parametrize("shape", sorted(UNRESTORED))
def test_unrestored_chdir_is_still_flagged(tmp_path: Path, shape: str) -> None:
    assert len(_isolation(tmp_path, UNRESTORED[shape])) == 1


def test_live_restored_chdirs_are_gone() -> None:
    live = {o.subject.id: o for o in TestIsolationSensor().scan(REPO_ROOT, NOW)}
    for path, lines in (
        ("tests/test_named_skills.py", {147, 150}),
        ("tests/test_packaging.py", {278, 282}),
        ("tests/test_push.py", {185, 193}),
    ):
        flagged = {f["line"] for f in live[path].observed_state["findings"]} if path in live else set()
        assert not (lines & flagged), path


# ---------------------------------------------------- supply chain: dynamic


def _supply(tmp_path: Path, pyproject: str) -> list:
    files = {**CLEAN_SUPPLY, "pyproject.toml": pyproject}
    return SupplyChainSensor().scan(make_repo(tmp_path / "repo", files), NOW)


def test_dynamic_dependencies_are_reported_not_ignored(tmp_path: Path) -> None:
    pyproject = '[project]\nname = "demo"\nversion = "1.2.3"\nlicense = {text = "MIT"}\ndynamic = ["dependencies"]\n'
    (observation,) = _supply(tmp_path, pyproject)
    assert observation.kind == "dependency_pin_drift"
    (finding,) = observation.observed_state["findings"]
    assert finding["rule"] == "dynamic-dependencies"
    assert observation.confidence == 0.8


def test_dynamic_optional_dependencies_and_license_are_reported(tmp_path: Path) -> None:
    pyproject = (
        '[project]\nname = "demo"\nversion = "1.2.3"\ndynamic = ["optional-dependencies", "license"]\n'
        'dependencies = ["pyyaml>=6.0"]\n'
    )
    kinds = {o.kind: o.observed_state["findings"][0]["rule"] for o in _supply(tmp_path, pyproject)}
    assert kinds == {
        "dependency_pin_drift": "dynamic-dependencies",
        "license_metadata_drift": "license-dynamic",
    }


def test_static_dependencies_with_dynamic_unrelated_fields_stay_clean(tmp_path: Path) -> None:
    pyproject = PYPROJECT_STATIC_PLUS_DYNAMIC
    assert _supply(tmp_path, pyproject) == []


PYPROJECT_STATIC_PLUS_DYNAMIC = (
    '[project]\nname = "demo"\nversion = "1.2.3"\nlicense = {text = "MIT"}\n'
    'dynamic = ["readme"]\ndependencies = ["pyyaml>=6.0"]\n'
)


def test_malformed_dynamic_field_is_unavailable(tmp_path: Path) -> None:
    with pytest.raises(SensorUnavailable):
        _supply(tmp_path, '[project]\nname = "demo"\nversion = "1"\ndynamic = "dependencies"\n')


# ------------------------------------------------------------ nits


def test_test_history_requires_a_git_worktree(tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    with pytest.raises(SensorUnavailable):
        TestHistorySensor().scan(plain, NOW)
    shutil.rmtree(plain)
