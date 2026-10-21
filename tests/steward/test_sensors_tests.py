"""Contract tests for the test-portfolio, test-isolation and test-history sensors."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from gaia_cli.steward import sensors_tests
from gaia_cli.steward.primitives.files import SensorNotEvaluated, SensorUnavailable
from gaia_cli.steward.sensors_tests import (
    TestHistorySensor,
    TestIsolationSensor,
    TestPortfolioSensor,
)
from tests.steward.sensor_fixtures import commit_all, make_repo, set_mtime, tree_digest, write_files

NOW = "2026-10-20T00:00:00Z"

PYPROJECT = """[tool.pytest.ini_options]
markers = [
    "slow: slow test",
    "integration(level): spawns things",
]
"""
CLEAN_TEST = "def test_ok():\n    assert True\n"
HISTORY_PATH = ".gaia/steward/inputs/test-history.json"


def kinds(observations):
    return sorted((o.kind, o.subject.id) for o in observations)


def findings(observations, kind):
    (obs,) = [o for o in observations if o.kind == kind]
    return obs.observed_state["findings"]


def repo(tmp_path: Path, files: dict[str, str], *, pyproject: str | None = PYPROJECT) -> Path:
    content = {"tests/test_clean.py": CLEAN_TEST, **files}
    if pyproject is not None:
        content["pyproject.toml"] = pyproject
    return make_repo(tmp_path / "repo", content)


# ---------------------------------------------------------------- portfolio

def test_portfolio_clean_repo_has_no_drift(tmp_path):
    root = repo(tmp_path, {})
    assert TestPortfolioSensor().scan(root, NOW) == []


def test_shadowed_test_module_scope(tmp_path):
    root = repo(
        tmp_path,
        {"tests/test_dup.py": "def test_a():\n    pass\n\n\ndef test_a():\n    pass\n"},
    )
    result = TestPortfolioSensor().scan(root, NOW)
    assert kinds(result) == [("shadowed_test", "tests/test_dup.py")]
    assert findings(result, "shadowed_test") == [{"name": "test_a", "scope": "module", "lines": [1, 5]}]
    assert result[0].confidence == 1.0
    assert result[0].subject.type == "test-file"


def test_shadowed_test_class_scope(tmp_path):
    source = (
        "class TestThing:\n"
        "    def test_x(self):\n        pass\n\n"
        "    def test_x(self):\n        pass\n"
    )
    root = repo(tmp_path, {"tests/test_cls.py": source})
    result = TestPortfolioSensor().scan(root, NOW)
    assert findings(result, "shadowed_test") == [
        {"name": "test_x", "scope": "TestThing", "lines": [2, 5]}
    ]


def test_same_name_in_different_classes_and_helpers_is_fine(tmp_path):
    source = (
        "class TestA:\n    def test_x(self):\n        pass\n\n"
        "class TestB:\n    def test_x(self):\n        pass\n\n"
        "def test_x():\n    pass\n\n"
        "def helper():\n    pass\n\n"
        "def helper():\n    pass\n"
    )
    root = repo(tmp_path, {"tests/test_ok.py": source})
    assert TestPortfolioSensor().scan(root, NOW) == []


def test_conditional_definitions_are_not_shadowing(tmp_path):
    source = "import sys\nif sys.platform == 'win32':\n    def test_a():\n        pass\nelse:\n    def test_a():\n        pass\n"
    root = repo(tmp_path, {"tests/test_cond.py": source})
    assert TestPortfolioSensor().scan(root, NOW) == []


def test_unregistered_marker_in_decorator_pytestmark_and_param(tmp_path):
    source = (
        "import pytest\n"
        "pytestmark = pytest.mark.ghost\n\n"
        "@pytest.mark.phantom\n"
        "def test_a():\n    pass\n\n"
        "@pytest.mark.parametrize('v', [pytest.param(1, marks=pytest.mark.wraith)])\n"
        "def test_b(v):\n    pass\n\n"
        "@pytest.mark.slow\n@pytest.mark.skip\n"
        "def test_c():\n    pass\n"
    )
    root = repo(tmp_path, {"tests/test_marks.py": source})
    result = TestPortfolioSensor().scan(root, NOW)
    assert kinds(result) == [("unregistered_marker", "tests/test_marks.py")]
    names = [item["name"] for item in findings(result, "unregistered_marker")]
    assert names == ["ghost", "phantom", "wraith"]
    assert result[0].confidence == 1.0


def test_marker_registered_in_conftest_or_with_args_is_fine(tmp_path):
    conftest = (
        "def pytest_configure(config):\n"
        "    config.addinivalue_line('markers', 'gpu: needs a gpu')\n"
    )
    source = (
        "import pytest\nfrom pytest import mark\n\n"
        "@pytest.mark.gpu\n@pytest.mark.integration\n@mark.slow\n"
        "def test_a():\n    pass\n"
    )
    root = repo(tmp_path, {"tests/conftest.py": conftest, "tests/test_m.py": source})
    assert TestPortfolioSensor().scan(root, NOW) == []


def test_aliased_pytest_and_from_import_mark_detected(tmp_path):
    source = "import pytest as pt\nfrom pytest import mark\n\n@pt.mark.alpha\n@mark.beta\ndef test_a():\n    pass\n"
    root = repo(tmp_path, {"tests/test_alias.py": source})
    names = [i["name"] for i in findings(TestPortfolioSensor().scan(root, NOW), "unregistered_marker")]
    assert names == ["alpha", "beta"]


def test_empty_test_module(tmp_path):
    root = repo(tmp_path, {"tests/test_empty.py": "import os\n\nVALUE = 1\n"})
    result = TestPortfolioSensor().scan(root, NOW)
    assert kinds(result) == [("empty_test_module", "tests/test_empty.py")]
    assert result[0].confidence == 0.7
    assert findings(result, "empty_test_module")[0]["dynamicGenerationHint"] is False


def test_empty_test_module_with_class_without_methods(tmp_path):
    root = repo(tmp_path, {"tests/test_cls.py": "class TestNothing:\n    value = 1\n"})
    assert kinds(TestPortfolioSensor().scan(root, NOW)) == [("empty_test_module", "tests/test_cls.py")]


def test_generated_tests_lower_confidence(tmp_path):
    root = repo(tmp_path, {"tests/test_gen.py": "from helpers import *\n"})
    result = TestPortfolioSensor().scan(root, NOW)
    assert result[0].confidence == 0.5
    assert findings(result, "empty_test_module")[0]["dynamicGenerationHint"] is True


def test_helper_modules_and_imported_tests_are_not_empty(tmp_path):
    root = repo(
        tmp_path,
        {
            "tests/helpers.py": "VALUE = 1\n",
            "tests/__init__.py": "",
            "tests/test_reexport.py": "from tests.test_clean import test_ok\n",
            "tests/test_assigned.py": "def _f():\n    pass\n\ntest_it = _f\n",
        },
    )
    assert TestPortfolioSensor().scan(root, NOW) == []


def test_portfolio_syntax_error_file_is_skipped_with_count(tmp_path):
    root = repo(
        tmp_path,
        {
            "tests/test_broken.py": "def test_a(:\n",
            "tests/test_dup.py": "def test_a():\n    pass\n\ndef test_a():\n    pass\n",
        },
    )
    result = TestPortfolioSensor().scan(root, NOW)
    assert kinds(result) == [("shadowed_test", "tests/test_dup.py")]
    assert result[0].provenance["skipped"] == {"syntax-error": 1}


def test_portfolio_repeat_invocation_is_identical(tmp_path):
    root = repo(
        tmp_path,
        {
            "tests/test_dup.py": "import pytest\n@pytest.mark.zzz\ndef test_a():\n    pass\n\ndef test_a():\n    pass\n",
            "tests/test_empty.py": "X = 1\n",
        },
    )
    first = [o.to_dict() for o in TestPortfolioSensor().scan(root, NOW)]
    second = [o.to_dict() for o in TestPortfolioSensor().scan(root, NOW)]
    assert first == second and len(first) == 3


def test_portfolio_missing_inventory_is_unavailable(tmp_path):
    root = make_repo(tmp_path / "repo", {"pyproject.toml": PYPROJECT, "src/a.py": "x = 1\n"})
    with pytest.raises(SensorUnavailable):
        TestPortfolioSensor().scan(root, NOW)


def test_portfolio_non_git_directory_is_unavailable(tmp_path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_a.py").write_text(CLEAN_TEST)
    (tmp_path / "pyproject.toml").write_text(PYPROJECT)
    with pytest.raises(SensorUnavailable):
        TestPortfolioSensor().scan(tmp_path, NOW)


def test_portfolio_truncated_inventory_is_unavailable(tmp_path, monkeypatch):
    root = repo(tmp_path, {"tests/test_two.py": CLEAN_TEST})
    original = sensors_tests.tracked_files
    monkeypatch.setattr(
        sensors_tests, "tracked_files", lambda *a, **k: original(*a, **{**k, "max_files": 1})
    )
    with pytest.raises(SensorUnavailable):
        TestPortfolioSensor().scan(root, NOW)


def test_portfolio_missing_or_bad_pyproject_is_unavailable(tmp_path):
    root = repo(tmp_path, {}, pyproject=None)
    with pytest.raises(SensorUnavailable):
        TestPortfolioSensor().scan(root, NOW)
    bad = repo(tmp_path / "bad", {}, pyproject="[tool.pytest\nnot toml")
    with pytest.raises(SensorUnavailable):
        TestPortfolioSensor().scan(bad, NOW)


def test_portfolio_is_read_only(tmp_path):
    root = repo(tmp_path, {"tests/test_dup.py": "def test_a():\n    pass\n\ndef test_a():\n    pass\n"})
    before = tree_digest(root)
    TestPortfolioSensor().scan(root, NOW)
    assert tree_digest(root) == before


def test_portfolio_recovery_when_defect_fixed(tmp_path):
    root = repo(tmp_path, {"tests/test_dup.py": "def test_a():\n    pass\n\ndef test_a():\n    pass\n"})
    assert TestPortfolioSensor().scan(root, NOW)
    write_files(root, {"tests/test_dup.py": "def test_a():\n    pass\n\ndef test_b():\n    pass\n"})
    commit_all(root)
    assert TestPortfolioSensor().scan(root, NOW) == []


def test_portfolio_contract_attributes():
    sensor = TestPortfolioSensor()
    assert (sensor.id, sensor.routine_ids, sensor.resolution_scope) == ("test-portfolio", (4,), "exhaustive")


# ---------------------------------------------------------------- isolation

def isolation(tmp_path: Path, source: str, name: str = "tests/test_iso.py"):
    root = repo(tmp_path, {name: source})
    return TestIsolationSensor().scan(root, NOW)


def patterns(result):
    return [(f["pattern"], f["line"]) for f in result[0].observed_state["findings"]]


def test_isolation_clean_repo_has_no_drift(tmp_path):
    assert isolation(tmp_path, CLEAN_TEST) == []


def test_isolation_sleep_chdir_environ(tmp_path):
    source = (
        "import os, time\n"
        "from time import sleep\n\n"
        "def test_a():\n"
        "    time.sleep(2)\n"
        "    sleep(1.5)\n"
        "    os.chdir('/')\n"
        "    os.environ['X'] = '1'\n"
        "    os.environ.update({'Y': '2'})\n"
    )
    result = isolation(tmp_path, source)
    assert kinds(result) == [("test_isolation_risk", "tests/test_iso.py")]
    assert patterns(result) == [
        ("sleep", 5), ("sleep", 6), ("chdir", 7), ("environ-mutation", 8), ("environ-mutation", 9),
    ]
    assert result[0].confidence == 0.6
    assert set(result[0].observed_state["findings"][0]) == {"line", "pattern", "detail"}


def test_isolation_near_misses_are_clean(tmp_path):
    source = (
        "import os, time\n"
        "from unittest import mock\n\n"
        "def test_a(monkeypatch, tmp_path):\n"
        "    time.sleep(0)\n"
        "    time.sleep(0.01)\n"
        "    time.sleep(some_var())\n"
        "    monkeypatch.setenv('X', '1')\n"
        "    monkeypatch.chdir(tmp_path)\n"
        "    with mock.patch.dict(os.environ, {'A': 'b'}):\n"
        "        pass\n"
        "    value = os.environ['HOME']\n"
        "    value = os.environ.get('X')\n"
    )
    assert isolation(tmp_path, source) == []


def test_isolation_network_without_mocking_is_flagged(tmp_path):
    source = (
        "import requests\nimport socket\nimport urllib.request\nfrom http.client import HTTPConnection\n\n"
        "def test_a():\n"
        "    requests.get('https://example.com')\n"
        "    urllib.request.urlopen('https://example.com')\n"
        "    socket.create_connection(('example.com', 80))\n"
        "    HTTPConnection('example.com')\n"
    )
    result = isolation(tmp_path, source)
    assert [p for p, _ in patterns(result)] == ["network"] * 4


@pytest.mark.parametrize(
    "mocking",
    [
        "from unittest import mock\n",
        "import responses\n",
        "import respx\n",
        "def test_b(monkeypatch):\n    pass\n",
    ],
)
def test_isolation_mocked_network_is_not_flagged(tmp_path, mocking):
    source = f"import requests\n{mocking}\ndef test_a():\n    requests.get('https://example.com')\n"
    assert isolation(tmp_path, source) == []


def test_isolation_loopback_network_is_not_flagged(tmp_path):
    source = "import requests\n\ndef test_a():\n    requests.get('http://127.0.0.1:8000/x')\n"
    assert isolation(tmp_path, source) == []


def test_isolation_home_write(tmp_path):
    source = (
        "from pathlib import Path\nimport os\n\n"
        "def test_a():\n"
        "    (Path.home() / 'x.txt').write_text('x')\n\n"
        "def test_b():\n"
        "    p = os.path.expanduser('~/y')\n"
        "    os.makedirs(p)\n\n"
        "def test_read_only():\n"
        "    assert Path.home().exists()\n"
    )
    result = isolation(tmp_path, source)
    assert patterns(result) == [("home-write", 5), ("home-write", 8)]


def test_isolation_home_write_redirected_is_clean(tmp_path):
    source = (
        "from pathlib import Path\n\n"
        "def test_a(monkeypatch, tmp_path):\n"
        "    monkeypatch.setenv('HOME', str(tmp_path))\n"
        "    (Path.home() / 'x.txt').write_text('x')\n"
    )
    assert isolation(tmp_path, source) == []


def test_isolation_ignores_non_test_modules(tmp_path):
    source = "import time\n\ndef helper():\n    time.sleep(5)\n"
    assert isolation(tmp_path, source, name="tests/helpers.py") == []


def test_isolation_syntax_error_skipped(tmp_path):
    root = repo(
        tmp_path,
        {
            "tests/test_broken.py": "def (:\n",
            "tests/test_iso.py": "import time\n\ndef test_a():\n    time.sleep(3)\n",
        },
    )
    result = TestIsolationSensor().scan(root, NOW)
    assert kinds(result) == [("test_isolation_risk", "tests/test_iso.py")]
    assert result[0].provenance["skipped"] == {"syntax-error": 1}


def test_isolation_repeat_invocation_is_identical(tmp_path):
    root = repo(tmp_path, {"tests/test_iso.py": "import time\n\ndef test_a():\n    time.sleep(3)\n"})
    first = [o.to_dict() for o in TestIsolationSensor().scan(root, NOW)]
    assert first == [o.to_dict() for o in TestIsolationSensor().scan(root, NOW)]
    assert len(first) == 1


def test_isolation_missing_inventory_is_unavailable(tmp_path):
    root = make_repo(tmp_path / "repo", {"src/a.py": "x = 1\n"})
    with pytest.raises(SensorUnavailable):
        TestIsolationSensor().scan(root, NOW)


def test_isolation_non_git_directory_is_unavailable(tmp_path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_a.py").write_text(CLEAN_TEST)
    with pytest.raises(SensorUnavailable):
        TestIsolationSensor().scan(tmp_path, NOW)


def test_isolation_truncated_inventory_is_unavailable(tmp_path, monkeypatch):
    root = repo(tmp_path, {"tests/test_two.py": CLEAN_TEST})
    original = sensors_tests.tracked_files
    monkeypatch.setattr(
        sensors_tests, "tracked_files", lambda *a, **k: original(*a, **{**k, "max_files": 1})
    )
    with pytest.raises(SensorUnavailable):
        TestIsolationSensor().scan(root, NOW)


def test_isolation_is_read_only(tmp_path):
    root = repo(tmp_path, {"tests/test_iso.py": "import time\n\ndef test_a():\n    time.sleep(3)\n"})
    before = tree_digest(root)
    TestIsolationSensor().scan(root, NOW)
    assert tree_digest(root) == before


def test_isolation_recovery_when_defect_fixed(tmp_path):
    root = repo(tmp_path, {"tests/test_iso.py": "import time\n\ndef test_a():\n    time.sleep(3)\n"})
    assert TestIsolationSensor().scan(root, NOW)
    write_files(root, {"tests/test_iso.py": "def test_a(monkeypatch):\n    monkeypatch.setattr('time.sleep', lambda s: None)\n"})
    commit_all(root)
    assert TestIsolationSensor().scan(root, NOW) == []


def test_isolation_contract_attributes():
    sensor = TestIsolationSensor()
    assert (sensor.id, sensor.routine_ids, sensor.resolution_scope) == ("test-isolation", (5,), "exhaustive")


# ------------------------------------------------------------------ history

def history(root: Path, runs, *, schema: str = "steward-test-history-v1") -> None:
    path = root / HISTORY_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schemaVersion": schema, "runs": runs}), encoding="utf-8")
    set_mtime(path, NOW)


def run(run_id: str, sha: str, **results: str) -> dict:
    return {"runId": run_id, "sha": sha, "results": {f"tests/test_a.py::{k}": v for k, v in results.items()}}


def test_history_absent_is_not_evaluated(tmp_path):
    root = repo(tmp_path, {})
    with pytest.raises(SensorNotEvaluated, match="no test history supplied"):
        TestHistorySensor().scan(root, NOW)


def test_history_flaky_same_sha(tmp_path):
    root = repo(tmp_path, {})
    history(root, [run("r1", "abc", test_x="passed"), run("r2", "abc", test_x="failed"),
                   run("r3", "abc", test_x="passed")])
    result = TestHistorySensor().scan(root, NOW)
    assert kinds(result) == [("flaky_test", "tests/test_a.py::test_x")]
    assert result[0].subject.type == "test-node"
    assert result[0].confidence == 0.9
    assert result[0].observed_state["findings"] == [
        {"sha": "abc", "passedRuns": ["r1", "r3"], "failedRuns": [{"runId": "r2", "status": "failed"}]}
    ]


def test_history_error_counts_as_failure(tmp_path):
    root = repo(tmp_path, {})
    history(root, [run("r1", "abc", test_x="passed"), run("r2", "abc", test_x="error")])
    assert len(TestHistorySensor().scan(root, NOW)) == 1


def test_history_near_misses(tmp_path):
    root = repo(tmp_path, {})
    history(
        root,
        [
            # fixed by a later commit: not flaky
            run("r1", "aaa", test_fixed="failed"), run("r2", "bbb", test_fixed="passed"),
            # always failing
            run("r3", "aaa", test_broken="failed"), run("r4", "aaa", test_broken="failed"),
            # skipped then passed on same sha
            run("r5", "aaa", test_skip="skipped"), run("r6", "aaa", test_skip="passed"),
            # always passing
            run("r7", "aaa", test_ok="passed"), run("r8", "aaa", test_ok="passed"),
        ],
    )
    assert TestHistorySensor().scan(root, NOW) == []


def test_history_repeat_invocation_is_identical(tmp_path):
    root = repo(tmp_path, {})
    history(root, [run("r1", "abc", test_x="passed", test_y="passed"),
                   run("r2", "abc", test_x="failed", test_y="failed")])
    first = [o.to_dict() for o in TestHistorySensor().scan(root, NOW)]
    assert first == [o.to_dict() for o in TestHistorySensor().scan(root, NOW)]
    assert len(first) == 2


@pytest.mark.parametrize(
    "payload",
    [
        "not json",
        json.dumps([]),
        json.dumps({"schemaVersion": "other", "runs": []}),
        json.dumps({"schemaVersion": "steward-test-history-v1", "runs": "x"}),
        json.dumps({"schemaVersion": "steward-test-history-v1", "runs": [{"runId": "r", "sha": "s", "results": {"t": "weird"}}]}),
        json.dumps({"schemaVersion": "steward-test-history-v1", "runs": [{"runId": "", "sha": "s", "results": {}}]}),
        json.dumps({"schemaVersion": "steward-test-history-v1", "runs": [
            {"runId": "r", "sha": "s", "results": {}}, {"runId": "r", "sha": "s", "results": {}}]}),
    ],
)
def test_history_malformed_is_unavailable(tmp_path, payload):
    root = repo(tmp_path, {})
    path = root / HISTORY_PATH
    path.parent.mkdir(parents=True)
    path.write_text(payload, encoding="utf-8")
    with pytest.raises(SensorUnavailable):
        TestHistorySensor().scan(root, NOW)


def test_history_oversized_is_unavailable(tmp_path, monkeypatch):
    root = repo(tmp_path, {})
    history(root, [run("r1", "abc", test_x="passed")])
    monkeypatch.setattr(sensors_tests, "_HISTORY_LIMIT_BYTES", 10)
    with pytest.raises(SensorUnavailable):
        TestHistorySensor().scan(root, NOW)


def test_history_too_many_runs_is_unavailable(tmp_path, monkeypatch):
    root = repo(tmp_path, {})
    history(root, [run("r1", "abc", test_x="passed"), run("r2", "abc", test_x="passed")])
    monkeypatch.setattr(sensors_tests, "_HISTORY_MAX_RUNS", 1)
    with pytest.raises(SensorUnavailable):
        TestHistorySensor().scan(root, NOW)


def test_history_is_read_only_and_recovers(tmp_path):
    root = repo(tmp_path, {})
    history(root, [run("r1", "abc", test_x="passed"), run("r2", "abc", test_x="failed")])
    before = tree_digest(root)
    assert TestHistorySensor().scan(root, NOW)
    assert tree_digest(root) == before
    history(root, [run("r1", "abc", test_x="passed"), run("r2", "abc", test_x="passed")])
    assert TestHistorySensor().scan(root, NOW) == []


def test_history_contract_attributes():
    sensor = TestHistorySensor()
    assert (sensor.id, sensor.routine_ids) == ("test-history", (5,))
    assert sensor.resolution_scope == "exhaustive"
    assert sensor.driver_inputs == (HISTORY_PATH,)
