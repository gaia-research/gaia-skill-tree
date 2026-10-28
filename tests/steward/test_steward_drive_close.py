"""The driver's forge.close_issue owner and its census refresh (#2130, lane D2).

Reuses the scripted world from test_steward_drive: gaia, gh, git, the closure script and the
census collector are all fakes, so nothing here touches GitHub or a real run ledger.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

from tests.steward.test_steward_drive import (
    FakeWorld,
    closeAction,
    drive,
    makeDriver,
    makeRoot,
    ok,
    view,
)


def closeRoot(tmp_path):
    """A driver checkout whose POLICY is explicitly writable (the shipped policy is dry-run, B5).

    The driver checks ``issueHygiene.writesEnabled`` before each closure and fails closed without a policy.
    """
    root = makeRoot(tmp_path)
    policy = REPO_ROOT / "founder" / "steward" / "POLICY.yaml"
    target = root / "founder" / "steward" / "POLICY.yaml"
    target.parent.mkdir(parents=True, exist_ok=True)
    text = policy.read_text(encoding="utf-8")
    target.write_text(text.replace("writesEnabled: false", "writesEnabled: true", 1), encoding="utf-8")
    from tests.steward.issuehygiene.e_fakes import approveClosureFixture
    approveClosureFixture(root)
    return root


def closeRecords(world: FakeWorld) -> list[dict]:
    return [payload for step, payload in world.recorded if step.startswith("close:")]


def test_closure_runs_the_script_and_records_its_outcome(tmp_path):
    root = closeRoot(tmp_path)
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
    root = closeRoot(tmp_path)
    world = FakeWorld(root, [view("R1", [closeAction()])])
    driver = makeDriver(tmp_path, world, env={})

    code = driver.drive()

    assert code == drive.EXITNOTRUN == 5
    assert world.closeCalls == [] and world.recorded == []
    assert driver.unperformed[0]["reason"].startswith("no GH_TOKEN or GITHUB_TOKEN")


def test_blocked_closure_is_recorded_once_and_halts_the_run(tmp_path):
    root = closeRoot(tmp_path)
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


def test_executor_refusal_is_recorded_as_refused_and_settles_the_step_so_the_run_continues(tmp_path):
    """B8 H-3a: exit 2 from the executor gate is a refused outcome. It settles the step (no stall) and the pair may be
    emitted again later; three refusals escalate on the founder desk. Nothing is retried within the pass."""
    root = closeRoot(tmp_path)
    refused = drive.CommandResult(2, "", "steward issue close refused: maxClosuresPerRun reached for run R1")
    actions = [closeAction("close:abc:abcd1234", 10), closeAction("close:abc:abcd1234b", 11)]
    world = FakeWorld(root, [view("R1", actions), view("R1", [], "completed")], close=lambda argv: refused)
    driver = makeDriver(tmp_path, world, env={"GH_TOKEN": "t"})

    code = driver.drive()

    assert len(world.closeCalls) == 2  # a refusal does not stop the pass
    records = closeRecords(world)
    assert [record["outcome"] for record in records] == ["refused", "refused"]
    assert all(record["failure"].startswith("refused:") for record in records)
    assert driver.skipped == []
    assert code == drive.EXITCOMPLETED


def test_closure_script_without_an_outcome_is_a_failed_step_not_a_record(tmp_path):
    root = closeRoot(tmp_path)
    world = FakeWorld(root, [view("R1", [closeAction()])],
                      close=lambda argv: drive.CommandResult(3, "", "steward issue close blocked: no-token"))
    driver = makeDriver(tmp_path, world, env={"GH_TOKEN": "t"})

    code = driver.drive()

    assert world.recorded == []
    assert code == drive.EXITSTOPPED
    assert driver.failures == {"close:abc:abcd1234": drive.MAXFAILURESPERSTEP}
    assert "failed twice" in driver.stopReason


def test_census_is_refreshed_before_the_run_when_enabled(tmp_path):
    root = closeRoot(tmp_path)
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
    root = closeRoot(tmp_path)
    world = FakeWorld(root, [view("R1", [], "completed")])
    driver = makeDriver(tmp_path, world)

    driver.drive()

    assert world.censusCalls == []
    assert driver.censusReport is None


def test_failed_census_removes_the_stale_input(tmp_path):
    root = closeRoot(tmp_path)
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
    root = closeRoot(tmp_path)
    target = root / ".gaia/steward/inputs/github-issues.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('{"completeness": {}}', encoding="utf-8")
    world = FakeWorld(root, [view("R1", [], "completed")],
                      census=lambda argv: drive.CommandResult(3, "", "census INCOMPLETE"))
    driver = makeDriver(tmp_path, world, census=True)

    driver.drive()

    assert target.is_file()
    assert driver.censusReport["state"] == "incomplete"


def test_a_compact_closure_action_without_a_comment_is_performed(tmp_path):
    """B7 D5: actions carry identifiers and digests, not the closing comment; the driver must still perform them."""
    root = closeRoot(tmp_path)
    compact = closeAction()
    compact["params"] = {k: v for k, v in compact["params"].items() if k not in ("comment", "comments", "original")}
    runs = [view("R1", [compact]), view("R1", [], "completed")]
    world = FakeWorld(root, runs)
    driver = makeDriver(tmp_path, world, env={"GH_TOKEN": "t"})

    code = driver.drive()

    assert code == drive.EXITCOMPLETED
    assert len(world.closeCalls) == 1


def test_writes_off_at_closure_time_is_reported_as_writes_disabled_not_as_a_stall(tmp_path):
    """B7 D3: the runner cancels the pending closures and the driver says so."""
    root = closeRoot(tmp_path)
    target = root / "founder" / "steward" / "POLICY.yaml"
    target.write_text(target.read_text(encoding="utf-8").replace("writesEnabled: true", "writesEnabled: false", 1), encoding="utf-8")
    world = FakeWorld(root, [view("R1", [closeAction()]), view("R1", [], "completed")])
    driver = makeDriver(tmp_path, world, env={"GH_TOKEN": "t"})

    code = driver.drive()

    assert world.closeCalls == []
    assert code == drive.EXITSTOPPED
    assert driver.stopReason.startswith("writes disabled")
    assert "stalled" not in driver.stopReason
