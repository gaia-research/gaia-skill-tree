from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import pytest

from gaia_cli.steward.sensors_tests import TestHistorySensor
from scripts import steward_collect_test_history as collector
from scripts.steward_collect_test_history import InputError, build, caseId, main, readJunit, render
from tests.steward.sensor_fixtures import make_repo

NOW = "2026-10-20T00:00:00Z"

JUNIT = """<?xml version="1.0" encoding="utf-8"?>
<testsuites><testsuite name="pytest" tests="6">
<testcase classname="tests.steward.test_probe" name="test_ok" time="0.0"/>
<testcase classname="tests.steward.test_probe" name="test_bad" time="0.0"><failure message="x">boom</failure></testcase>
<testcase classname="tests.steward.test_probe" name="test_err" time="0.0"><error message="x">boom</error></testcase>
<testcase classname="tests.steward.test_probe" name="test_skip" time="0.0"><skipped type="pytest.skip" message="x">x</skipped></testcase>
<testcase classname="tests.steward.test_probe" name="test_param[a-b]" time="0.0"/>
<testcase classname="tests.steward.test_probe.TestGroup" name="test_inner" time="0.0"/>
</testsuite></testsuites>
"""


def writeJunit(path: Path, body: str = JUNIT) -> Path:
    path.write_text(body, encoding="utf-8")
    return path


def makeRun(runid: str, results: dict[str, str] | None = None, sha: str = "a" * 40) -> dict:
    return {"runId": runid, "sha": sha, "results": results if results is not None else {"t.py::x": "passed"}}


def testJunitMapsToPytestNodeIdsAndStatuses(tmp_path: Path) -> None:
    results = readJunit(writeJunit(tmp_path / "junit.xml"))

    assert results == {
        "tests/steward/test_probe.py::test_ok": "passed",
        "tests/steward/test_probe.py::test_bad": "failed",
        "tests/steward/test_probe.py::test_err": "error",
        "tests/steward/test_probe.py::test_skip": "skipped",
        "tests/steward/test_probe.py::test_param[a-b]": "passed",
        "tests/steward/test_probe.py::TestGroup::test_inner": "passed",
    }


def testRerunAttemptsDoNotCountAsTheOutcome() -> None:
    body = (
        '<testsuite><testcase classname="tests.test_flaky" name="test_once">'
        "<rerunFailure>first try</rerunFailure></testcase></testsuite>"
    )
    case = next(ET.fromstring(body).iter("testcase"))
    assert collector.caseStatus(case) == "passed"


def testCaseIdRefusesAClassnameWithNoTestModule() -> None:
    with pytest.raises(InputError):
        caseId("helpers.common", "test_x")


def testCollectionSkippedModuleIsAModuleRecordNotMalformed(tmp_path: Path) -> None:
    """A module skipped at collection (importorskip) has no classname.

    pytest reports it as classname="" with the dotted module path as the name.
    Refusing it made the whole history collection fail whenever an optional
    dependency was absent, leaving the flake detector permanently not evaluated.
    """

    body = (
        '<?xml version="1.0" encoding="utf-8"?><testsuites><testsuite name="pytest">'
        '<testcase classname="" name="tests.test_optional" time="0.0">'
        '<skipped type="pytest.skip" message="collection skipped">x</skipped></testcase>'
        '<testcase classname="tests.steward.test_probe" name="test_ok" time="0.0"/>'
        "</testsuite></testsuites>"
    )

    results = readJunit(writeJunit(tmp_path / "junit.xml", body))

    assert results == {
        "tests/test_optional.py": "skipped",
        "tests/steward/test_probe.py::test_ok": "passed",
    }
    assert caseId("", "tests.test_optional") == "tests/test_optional.py"
    with pytest.raises(InputError):
        caseId("", "not a module")
    with pytest.raises(InputError):
        caseId("", "helpers.common")


def testMergeAppendsNewRunsAndReplacesTheSameRunId() -> None:
    history = {"schemaVersion": collector.SCHEMA, "runs": [makeRun("r1"), makeRun("r2", {"t.py::x": "failed"})]}

    document = build(history, [makeRun("r2", {"t.py::x": "passed"}), makeRun("r3")], repository=None, collected=NOW)

    assert [run["runId"] for run in document["runs"]] == ["r1", "r2", "r3"]
    assert document["runs"][1]["results"] == {"t.py::x": "passed"}
    assert document["collectedAt"] == NOW


def testCapDropsTheOldestRuns(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(collector, "RUNCAP", 3)
    incoming = [makeRun(f"r{index}") for index in range(5)]

    document = build(None, incoming, repository=None, collected=NOW)

    assert [run["runId"] for run in document["runs"]] == ["r2", "r3", "r4"]


def testResultCapDropsTheOldestRuns(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(collector, "RESULTCAP", 4)
    incoming = [makeRun("old", {f"a{i}.py::t": "passed" for i in range(2)}), makeRun("mid", {f"b{i}.py::t": "passed" for i in range(2)}), makeRun("new", {"c.py::t": "failed"})]

    document = build(None, incoming, repository=None, collected=NOW)

    assert [run["runId"] for run in document["runs"]] == ["mid", "new"]


def testRenderedFileStaysUnderTheSizeCap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(collector, "BYTECAP", 4000)
    incoming = [makeRun(f"r{index}", {f"tests/test_{index}.py::test_{n}": "passed" for n in range(20)}) for index in range(10)]

    text = render(build(None, incoming, repository=None, collected=NOW))

    assert len(text.encode("utf-8")) <= 4000
    assert json.loads(text)["runs"][-1]["runId"] == "r9"


def testNewestRunThatCannotFitIsRefused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(collector, "RESULTCAP", 1)
    with pytest.raises(InputError):
        build(None, [makeRun("big", {"a.py::t": "passed", "b.py::t": "passed"})], repository=None, collected=NOW)


@pytest.mark.parametrize(
    "bad",
    [
        [makeRun("r1"), makeRun("r1")],
        [{"runId": "", "sha": "a", "results": {}}],
        [{"runId": "r9", "sha": "a", "results": {"t.py::x": "weird"}}],
        [{"runId": "r9", "sha": "a", "results": []}],
    ],
)
def testInvalidRunsAreRefusedBeforeTheyReachTheFile(bad: list) -> None:
    with pytest.raises(InputError):
        build(None, bad, repository=None, collected=NOW)


def testRepositoryIsKeptFromTheHistoryWhenNotGiven() -> None:
    history = {"schemaVersion": collector.SCHEMA, "repository": "o/r", "runs": []}
    assert build(history, [makeRun("r1")], repository=None, collected=NOW)["repository"] == "o/r"
    assert build(history, [makeRun("r1")], repository="p/q", collected=NOW)["repository"] == "p/q"


def testCliRefusesToOverwriteAForeignHistory(tmp_path: Path) -> None:
    history = tmp_path / "test-history.json"
    foreign = json.dumps({"schemaVersion": "something-else", "runs": []})
    history.write_text(foreign, encoding="utf-8")
    junit = writeJunit(tmp_path / "junit.xml")

    assert main(["--run", "r1", "a" * 40, str(junit), "--history", str(history)]) == 1
    assert history.read_text(encoding="utf-8") == foreign


def testCliMalformedXmlWritesNothing(tmp_path: Path) -> None:
    history = tmp_path / "test-history.json"
    junit = tmp_path / "junit.xml"
    junit.write_text("<testsuite><testcase", encoding="utf-8")

    assert main(["--run", "r1", "a" * 40, str(junit), "--history", str(history)]) == 1
    assert not history.exists()


def testCliMergesTwoRunsAndTheSensorAcceptsTheFile(tmp_path: Path) -> None:
    root = make_repo(tmp_path / "repo", {"README.md": "x"})
    target = root / ".gaia/steward/inputs/test-history.json"
    sha = "b" * 40
    passing = JUNIT.replace(
        'name="test_bad" time="0.0"><failure message="x">boom</failure></testcase>',
        'name="test_bad" time="0.0"/>',
    )
    first = writeJunit(tmp_path / "first.xml", passing)
    second = writeJunit(tmp_path / "second.xml")

    assert main(["--run", "run-1", sha, str(first), "--repository", "o/r", "--history", str(target)]) == 0
    assert main(["--run", "run-2", sha, str(second), "--history", str(target)]) == 0

    document = json.loads(target.read_text(encoding="utf-8"))
    assert document["schemaVersion"] == "steward-test-history-v1"
    assert document["repository"] == "o/r"
    assert [run["runId"] for run in document["runs"]] == ["run-1", "run-2"]
    assert not list(target.parent.glob("*.tmp"))

    observed = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    flaky = TestHistorySensor().scan(root, observed)
    assert [observation.kind for observation in flaky] == ["flaky_test"]
    assert flaky[0].subject.id == "tests/steward/test_probe.py::test_bad"
