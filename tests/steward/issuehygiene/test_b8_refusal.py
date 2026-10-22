"""Lane B8 H-3(a, c): an executor refusal settles its step, the pair is emitted again later, and three refusals
escalate to one Class C question. Pending closures count toward the hourly budget at emission time.

The driver tests use the scripted world from test_steward_drive. The end-to-end tests use the real CLI, runner,
ledger, closure script and sensor on a checkout built in a temporary directory with the offline fakes. Nothing
here reaches the network.
"""

from __future__ import annotations

import json

from gaia_cli.steward.issuehygiene.outcomes import RETRYLIMIT, failedAttempts, loadOutcomes
from gaia_cli.steward.issuehygiene.sensor import CENSUS_INPUT, IssueHygieneSensor
from scripts.steward_issue_close import main as closeMain
from scripts.steward_issue_census import writeAtomic
from tests.steward.issuehygiene.e_fakes import REPO
from tests.steward.issuehygiene.test_e_steward_full_e2e import (
    HOUR_ONE,
    closeActions,
    refuseNetwork,  # noqa: F401 - autouse: the offline steward tests must not reach the network
    setUpSteward,
)
from tests.steward.test_steward_drive import FakeWorld, closeAction, drive, makeDriver, view
from tests.steward.test_steward_drive_close import closeRecords, closeRoot

from gaia_cli.steward.clock import parseInstant


# --- the driver settles an exit-2 refusal as a refused outcome -------------------------------------------

def test_an_executor_refusal_is_recorded_as_a_refused_outcome_that_settles_the_step(tmp_path):
    root = closeRoot(tmp_path)
    reply = {"outcome": "refused", "reason": "item-changed", "key": "upstream-candidate:o/r:foo", "issue": 10}
    refused = drive.CommandResult(2, json.dumps(reply), "steward issue close refused: the closure's own proof changed")
    actions = [closeAction("close:abc:abcd1234", 10)]
    world = FakeWorld(root, [view("R1", actions), view("R1", [], "completed")], close=lambda argv: refused)
    driver = makeDriver(tmp_path, world, env={"GH_TOKEN": "t"})

    code = driver.drive()

    records = closeRecords(world)
    assert len(records) == 1, "the refusal is recorded, so the runner can settle the step"
    assert records[0]["outcome"] == "refused"
    assert records[0]["reason"] == "item-changed"
    assert records[0]["key"] == "upstream-candidate:o/r:foo" and records[0]["issue"] == 10
    assert records[0]["failure"]
    assert code == drive.EXITCOMPLETED, "a settled refusal no longer stalls the run"


def test_a_refusal_the_script_cannot_describe_is_still_recorded_with_a_generic_reason(tmp_path):
    root = closeRoot(tmp_path)
    refused = drive.CommandResult(2, "", "steward issue close refused: no reason")
    world = FakeWorld(root, [view("R1", [closeAction("close:abc:abcd1234", 10)]), view("R1", [], "completed")],
                      close=lambda argv: refused)
    driver = makeDriver(tmp_path, world, env={"GH_TOKEN": "t"})
    driver.drive()
    record = closeRecords(world)[0]
    assert record["outcome"] == "refused" and record["reason"] == "refused"


# --- end to end: the runner settles, re-emits, and escalates -------------------------------------------

def pendingCloses(view_: dict) -> list[dict]:
    return [a for a in closeActions(view_) if a["status"] == "pending"]


def refuseOrClose(steward, view_: dict, refuse: set[int]) -> dict:
    """Perform each pending closure with the real script: the pairs in ``refuse`` are refused by the gate, the rest close.

    Every outcome is recorded through ``gaia steward full record`` exactly as the driver records it, then the run is
    resumed, as the driver does. Returns the resumed run view.
    """
    runId = view_["runId"]
    for action in pendingCloses(view_):
        params = action["params"]
        stepId = action["stepId"]
        actionFile = steward.root / ".gaia/steward/drive/closures" / f"{runId}--{stepId.replace(':', '-')}.json"
        actionFile.parent.mkdir(parents=True, exist_ok=True)
        actionFile.write_text(json.dumps(params, indent=2, sort_keys=True), encoding="utf-8")
        code = closeMain(["--root", str(steward.root), "--action", str(actionFile), "--repo", REPO, "--run-id", runId],
                         forgeFactory=lambda repo, token: steward.forge)
        out = steward.capsys.readouterr()
        outcome = json.loads(out.out.strip().splitlines()[-1])
        if params["issue"] in refuse:
            assert code == 2 and outcome["outcome"] == "refused", (code, outcome)
            outcome = {**outcome, "key": params["key"], "issue": params["issue"]}
        else:
            assert code == 0 and outcome["outcome"] == "closed", outcome
        outcomeFile = steward.root / ".gaia/steward/drive/outcomes" / f"{runId}--{stepId.replace(':', '-')}.json"
        outcomeFile.parent.mkdir(parents=True, exist_ok=True)
        outcomeFile.write_text(json.dumps(outcome, indent=2, sort_keys=True), encoding="utf-8")
        recordCode, _ = steward.gaia("record", runId, stepId, "--input", str(outcomeFile), "--ledger", "local", "--json")
        assert recordCode == 0, steward.lastErr
    resumeCode, resumed = steward.resume(runId)
    assert resumeCode == 0, steward.lastErr
    return resumed


def retitle(steward, number: int, title: str) -> None:
    """A person edits the closure's own issue after emission; the next census shows it, the gate must refuse."""
    steward.gh.edit(number, title=title)
    writeAtomic(steward.root / CENSUS_INPUT, steward.gh.census(parseInstant(HOUR_ONE)))


def test_an_exit_two_refusal_settles_the_step_and_the_pair_is_emitted_again_and_closes(tmp_path, monkeypatch, capsys):
    steward, gh, picks = setUpSteward(tmp_path, monkeypatch, capsys, 1)
    number = picks[0]["number"]
    code, first = steward.run()
    assert code == 0 and [a["params"]["issue"] for a in pendingCloses(first)] == [number]
    retitle(steward, number, "[intake] renamed before the closure ran")
    resumed = refuseOrClose(steward, first, refuse={number})

    # The refused step is settled: its recorded outcome is the refusal with its reason code, and nothing of it is pending.
    (entry,) = [e for e in loadOutcomes(steward.root).values() if e["issue"] == number]
    assert entry["outcome"] == "refused" and entry["reason"] == "item-changed" and entry["attempts"] == 1
    assert gh.issues[number]["state"] == "open"

    # The refusal did not wedge the run: the pair is emitted again against the current census, and that closure runs.
    again = pendingCloses(resumed)
    assert [a["params"]["issue"] for a in again] == [number], "a refused pair is emitted again"
    refuseOrClose(steward, resumed, refuse=set())
    assert gh.issues[number]["state"] == "closed"


def test_three_refusals_stop_emission_and_escalate_one_class_c_question(tmp_path, monkeypatch, capsys):
    steward, gh, picks = setUpSteward(tmp_path, monkeypatch, capsys, 1)
    number = picks[0]["number"]
    code, view_ = steward.run()
    assert code == 0
    for round_ in range(RETRYLIMIT):
        assert [a["params"]["issue"] for a in pendingCloses(view_)] == [number], round_
        retitle(steward, number, f"[intake] renamed {round_}")
        view_ = refuseOrClose(steward, view_, refuse={number})
    (entry,) = [e for e in loadOutcomes(steward.root).values() if e["issue"] == number]
    assert failedAttempts(loadOutcomes(steward.root), entry["key"], number) == RETRYLIMIT
    assert pendingCloses(view_) == [], "a pair refused three times is not emitted again"

    code, last = steward.run()
    assert code == 0 and closeActions(last) == [], "a later run does not emit it either"

    scan = IssueHygieneSensor().scan_detailed(steward.root, HOUR_ONE)
    escalations = [obs for obs in scan.observations
                   if obs.kind == "issue_founder_decision" and obs.subject.id == "closure-refused"]
    assert len(escalations) == 1, "one Class C question for every refused pair"
    assert escalations[0].observed_state["affected"] == [number]
    assert escalations[0].observed_state["decisionTarget"] == "issue-question/closure-refused"
