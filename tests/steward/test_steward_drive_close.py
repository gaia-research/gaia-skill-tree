"""The driver's forge.close_issue owner and its census refresh (#2130, lane D2).

Reuses the scripted world from test_steward_drive: gaia, gh, git, the closure script and the
census collector are all fakes, so nothing here touches GitHub or a real run ledger.
"""

from __future__ import annotations

import json
from pathlib import Path

from tests.steward.test_steward_drive import (
    FakeWorld,
    closeAction,
    drive,
    makeDriver,
    makeRoot,
    ok,
    view,
)


def closeRecords(world: FakeWorld) -> list[dict]:
    return [payload for step, payload in world.recorded if step.startswith("close:")]


def test_closure_runs_the_script_and_records_its_outcome(tmp_path):
    root = makeRoot(tmp_path)
    runs = [view("R1", [closeAction()]), view("R1", [], "completed")]
    world = FakeWorld(root, runs)
    driver = makeDriver(tmp_path, world, env={"GH_TOKEN": "t"})

    code = driver.drive()

    assert code == drive.EXITCOMPLETED
    (call,) = world.closeCalls
    assert call[1].endswith("scripts/steward_issue_close.py")
    actionFile = Path(call[call.index("--action") + 1])
    assert actionFile.name == "R1--close-abc-abcd1234.json"
    params = json.loads(actionFile.read_text(encoding="utf-8"))
    assert params["issue"] == 10 and params["comment"].startswith("<!-- gaia-steward-closure:")
    (record,) = closeRecords(world)
    assert record["outcome"] == "closed" and record["commentId"] == 55
    assert world.agentCalls == []


def test_closure_without_a_token_is_not_run_and_exits_not_run(tmp_path):
    root = makeRoot(tmp_path)
    world = FakeWorld(root, [view("R1", [closeAction()])])
    driver = makeDriver(tmp_path, world, env={})

    code = driver.drive()

    assert code == drive.EXITNOTRUN == 5
    assert world.closeCalls == [] and world.recorded == []
    assert driver.unperformed[0]["reason"].startswith("no GH_TOKEN or GITHUB_TOKEN")


def test_blocked_closure_is_recorded_once_and_halts_the_run(tmp_path):
    root = makeRoot(tmp_path)
    blocked = ok(json.dumps({"outcome": "blocked", "key": "upstream-candidate:o/r:foo", "issue": 10,
                             "commentUrl": None, "commentId": None, "markerVerified": False,
                             "closedAt": None, "failure": "http-403"}))
    actions = [closeAction("close:abc:abcd1234", 10), closeAction("close:abc:abcd1234b", 11)]
    world = FakeWorld(root, [view("R1", actions)], close=lambda argv: blocked)
    driver = makeDriver(tmp_path, world, env={"GH_TOKEN": "t"})

    code = driver.drive()

    assert code == drive.EXITSTOPPED == 1
    assert len(world.closeCalls) == 1  # the second closure is never attempted
    assert driver.stopReason.startswith("forge.close_issue blocked at close:abc:abcd1234")
    assert closeRecords(world)[0]["outcome"] == "blocked"


def test_closure_script_without_an_outcome_is_a_failed_step_not_a_record(tmp_path):
    root = makeRoot(tmp_path)
    world = FakeWorld(root, [view("R1", [closeAction()])],
                      close=lambda argv: drive.CommandResult(3, "", "steward issue close blocked: no-token"))
    driver = makeDriver(tmp_path, world, env={"GH_TOKEN": "t"})

    code = driver.drive()

    assert world.recorded == []
    assert code == drive.EXITSTOPPED
    assert driver.failures == {"close:abc:abcd1234": drive.MAXFAILURESPERSTEP}
    assert "failed twice" in driver.stopReason


def test_census_is_refreshed_before_the_run_when_enabled(tmp_path):
    root = makeRoot(tmp_path)
    runs = [view("R1", [], "completed")]
    world = FakeWorld(root, runs)
    driver = makeDriver(tmp_path, world, census=True, repo="gaia-research/gaia-skill-tree")

    code = driver.drive()

    assert code == drive.EXITCOMPLETED
    (call,) = world.censusCalls
    assert call[call.index("--repo") + 1] == "gaia-research/gaia-skill-tree"
    assert driver.censusReport == {"state": "complete", "detail": "gaia-research/gaia-skill-tree census collected"}
    runIndex = next(i for i, c in enumerate(world.calls) if c[:6] == ["PY", "-m", "gaia_cli.main", "steward", "full", "run"])
    censusIndex = next(i for i, c in enumerate(world.calls) if len(c) > 1 and str(c[1]).endswith("steward_issue_census.py"))
    assert censusIndex < runIndex


def test_census_is_not_collected_by_default(tmp_path):
    root = makeRoot(tmp_path)
    world = FakeWorld(root, [view("R1", [], "completed")])
    driver = makeDriver(tmp_path, world)

    driver.drive()

    assert world.censusCalls == []
    assert driver.censusReport is None


def test_failed_census_removes_the_stale_input(tmp_path):
    root = makeRoot(tmp_path)
    target = root / ".gaia/steward/inputs/github-issues.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("{}", encoding="utf-8")
    world = FakeWorld(root, [view("R1", [], "completed")],
                      census=lambda argv: drive.CommandResult(2, "", "usage"))
    driver = makeDriver(tmp_path, world, census=True)

    driver.drive()

    assert not target.exists()
    assert driver.censusReport["state"] == "failed"


def test_incomplete_census_keeps_its_file_for_the_sensor_to_refuse(tmp_path):
    root = makeRoot(tmp_path)
    target = root / ".gaia/steward/inputs/github-issues.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('{"completeness": {}}', encoding="utf-8")
    world = FakeWorld(root, [view("R1", [], "completed")],
                      census=lambda argv: drive.CommandResult(3, "", "census INCOMPLETE"))
    driver = makeDriver(tmp_path, world, census=True)

    driver.drive()

    assert target.is_file()
    assert driver.censusReport["state"] == "incomplete"
