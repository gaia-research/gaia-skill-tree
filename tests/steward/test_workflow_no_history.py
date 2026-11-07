"""Workflow-timeout route: the no-history default and the narrow no_change release (#2283).

Decision steward-workflow-timeout-no-history-2283 (R4): a job whose read history
has no successful run gets a deterministic, conservative timeout from its own
steps; unreadable history still stops. Decision
steward-workflow-timeout-no-history-release-2283: exactly the named (run, build
step) pairs held as no_change may be released once, append-only.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import gaia_cli.steward.fullrun as fullrun
from gaia_cli.steward.fullrun import RecordRefused
from gaia_cli.steward.policy import StewardPolicy
from gaia_cli.steward.workflowproof import (
    NO_HISTORY_BASE_MINUTES,
    _main,
    history_timeout,
    no_history_timeout,
    prove_workflow_edit,
)
from tests.steward.test_fullrun import BUILD, VERIFY, actionTypes
from tests.steward.test_fullrun_scenarios import hygieneRunner, ledgerOf

REPO_ROOT = Path(__file__).resolve().parents[2]
RULING = "steward-workflow-timeout-no-history-release-2283"


# --- the value rules ---------------------------------------------------------


@pytest.mark.parametrize(
    "seconds, expected",
    [
        ([3, 4, 14], 5),  # auto-triage siblings: seconds-long jobs get the 5-minute floor
        ([600, 900], 30),  # p95 = 900 s -> 2 x 15 = 30 > 1.5 x 15
        ([60] * 20, 5),
        ([14400], 360),  # capped at the platform maximum
    ],
)
def test_history_rule(seconds: list[float], expected: int) -> None:
    assert history_timeout(seconds) == expected


def test_history_rule_never_applies_without_history() -> None:
    with pytest.raises(ValueError):
        history_timeout([])


def test_the_batch_9_jobs_get_their_documented_defaults() -> None:
    # auto-label-bot-prs.yml label-bots: one github-script call, never executed.
    assert no_history_timeout("api-script", declared_wait_seconds=0, longest_observed_seconds=None) == 10
    # auto-triage.yml auto-merge: gh/jq steps, declared poll 60 rounds x 10 s.
    assert no_history_timeout("api-script", declared_wait_seconds=600, longest_observed_seconds=None) == 30


def test_never_shorter_than_any_observed_execution() -> None:
    # The job once ran 30 minutes (and failed): 1.5 x 30 = 45 beats the 10-minute base.
    assert no_history_timeout("api-script", declared_wait_seconds=0, longest_observed_seconds=1800) == 45


@pytest.mark.parametrize(
    "step_class, wait, observed",
    [
        ("deploy", 0, None),  # not one of the three classes
        ("install-build-test", 1200, None),  # 30 + 40 = 70 > 60
        ("api-script", 0, 3000),  # 1.5 x 50 = 75 > 60: needs real history
        ("api-script", -1, None),
        ("api-script", 0, -5),
    ],
)
def test_no_default_means_stop(step_class: str, wait: float, observed: float | None) -> None:
    assert no_history_timeout(step_class, declared_wait_seconds=wait, longest_observed_seconds=observed) is None


def test_defaults_stay_inside_the_floor_and_ceiling() -> None:
    for step_class in NO_HISTORY_BASE_MINUTES:
        for wait in (0, 60, 300, 600, 900):
            value = no_history_timeout(step_class, declared_wait_seconds=wait, longest_observed_seconds=None)
            assert value is None or (10 <= value <= 60 and value % 5 == 0)


def test_cli_prints_the_value_or_stops(capsys: pytest.CaptureFixture[str]) -> None:
    assert _main(["no-history", "--class", "api-script", "--declared-wait-seconds", "600"]) == 0
    assert capsys.readouterr().out.strip() == "30"
    assert _main(["no-history", "--class", "install-build-test", "--declared-wait-seconds", "1200"]) == 3
    assert "no default" in capsys.readouterr().out
    assert _main(["history", "--successful-seconds", "3", "4", "14"]) == 0
    assert capsys.readouterr().out.strip() == "5"


# --- the envelope is unchanged: out-of-envelope edits are still rejected ----

LABEL_BOTS = (
    "name: Auto-label bot PRs\n"
    "on:\n  pull_request:\n    types: [opened]\n"
    "jobs:\n"
    "  label-bots:\n"
    "    runs-on: ubuntu-latest\n"
    "    steps:\n"
    "      - uses: actions/github-script@v7\n"
)


def _insert(line: str, at: int = 7) -> tuple:
    return ((at, 0, (("+", line, False),)),)


def test_the_no_history_value_passes_the_structural_proof() -> None:
    assert prove_workflow_edit(LABEL_BOTS, _insert("    timeout-minutes: 10")) == []


@pytest.mark.parametrize(
    "line",
    [
        "    timeout-minutes: 10 # no-history default",  # comment
        "    timeout-minutes: 0",
        "    timeout-minutes: 361",
        "    timeout-minutes: '10'",
        "      timeout-minutes: 10",  # wrong indentation (not the job's own key)
    ],
)
def test_out_of_envelope_insertions_are_still_rejected(line: str) -> None:
    assert prove_workflow_edit(LABEL_BOTS, _insert(line)) != []


def test_policy_carries_the_no_history_contract() -> None:
    rule = StewardPolicy.load(REPO_ROOT).dispatch_rule_for("workflow_hygiene")
    assert rule is not None
    assert any("workflowproof no-history" in command for command in rule.allowed_commands)
    assert any("no-history default" in condition for condition in rule.stop_conditions)
    assert any("no-history" in item for item in rule.proof)
    assert rule.allowed_paths == (".github/workflows/*.yml",)


# --- the narrow release of a held no_change ---------------------------------


def _held(tmp_path: Path):
    repo, _bare, sensor, store, runner = hygieneRunner(tmp_path)
    view = runner.start("full")
    build = view.actions[0]
    runner.record(view.runId, build["stepId"], {**BUILD, "noChange": True, "summary": "stopped: no history"})
    verifying = runner.resume(view.runId)
    runner.record(view.runId, verifying.actions[0]["stepId"], VERIFY)
    runner.resume(view.runId)
    debtId = build["params"]["debtId"]
    assert ledgerOf(store)["work"][debtId]["state"] == "no_change"
    return repo, store, runner, view.runId, build["stepId"], debtId


def _record(repo: Path, lines: list[str], **overrides: Any) -> None:
    record = {
        "schemaVersion": "steward-decision-v1",
        "id": RULING,
        "status": "decided",
        "resolution": "standing-authority-r4",
        "decision": "Release the named no_change builds?",
        "whyItMatters": "The route gap is fixed.",
        "evidence": lines,
        "recommended": "Release once.",
        "alternative": "Keep held.",
        "unblocks": "Rebuild.",
        "links": [],
        **overrides,
    }
    path = repo / "founder/steward/decisions" / f"{RULING}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record), encoding="utf-8")


def test_release_returns_exactly_that_build_to_the_queue_once_and_keeps_history(tmp_path: Path) -> None:
    repo, store, runner, runId, stepId, debtId = _held(tmp_path)
    _record(repo, [f"releaseNoChange {runId} {stepId}"])
    runner.release_no_change(runId, stepId, ruling=RULING)
    doc = ledgerOf(store)
    item = doc["work"][debtId]
    assert item["state"] == "queued"
    assert item["history"][-1]["from"] == "no_change" and RULING in item["history"][-1]["reason"]
    (kept,) = item["releasedBuilds"]
    assert kept["build"]["noChange"] is True and kept["verification"]["verdict"] == "accept"
    assert [entry["stepId"] for entry in doc["runs"][runId]["releases"]] == [stepId]
    # Consumed once.
    with pytest.raises(RecordRefused, match="consumed once|not held"):
        runner.release_no_change(runId, stepId, ruling=RULING)
    # The next run re-offers it to the lane like any queued work.
    again = runner.start("full")
    assert actionTypes(again) == ["agent.build"]
    assert again.actions[0]["params"]["debtId"] == debtId


def test_release_refuses_an_unpinned_record(tmp_path: Path) -> None:
    repo, _store, runner, runId, stepId, _debtId = _held(tmp_path)
    with pytest.raises(RecordRefused, match="not a recognized"):
        runner.release_no_change(runId, stepId, ruling="steward-anything-else")


@pytest.mark.parametrize(
    "lines, overrides, message",
    [
        ([], {}, "does not name"),
        (["releaseNoChange run-other build:x:1"], {}, "does not name"),
        (None, {"status": "open"}, "not decided"),
        (None, {"extraKey": True}, "malformed"),
    ],
)
def test_release_refuses_a_record_that_does_not_bind_this_step(
    tmp_path: Path, lines, overrides: dict, message: str
) -> None:
    repo, store, runner, runId, stepId, debtId = _held(tmp_path)
    _record(repo, lines if lines is not None else [f"releaseNoChange {runId} {stepId}"], **overrides)
    with pytest.raises(RecordRefused, match=message):
        runner.release_no_change(runId, stepId, ruling=RULING)
    assert ledgerOf(store)["work"][debtId]["state"] == "no_change"


def test_release_refuses_a_missing_record_and_a_non_build_step(tmp_path: Path) -> None:
    repo, _store, runner, runId, stepId, _debtId = _held(tmp_path)
    with pytest.raises(RecordRefused, match="missing"):
        runner.release_no_change(runId, stepId, ruling=RULING)
    verifyStep = stepId.replace("build:", "verify:")
    _record(repo, [f"releaseNoChange {runId} {verifyStep}"])
    with pytest.raises(RecordRefused, match="not a build action"):
        runner.release_no_change(runId, verifyStep, ruling=RULING)


def test_release_refuses_work_whose_no_change_came_from_a_different_build(tmp_path: Path) -> None:
    repo, store, runner, runId, stepId, debtId = _held(tmp_path)
    _record(repo, [f"releaseNoChange {runId} {stepId}"])

    def swap(doc: dict[str, Any]) -> None:
        doc["work"][debtId]["build"]["dispatchId"] = "dispatch-somebody-else"

    from tests.steward.test_fullrun import editLedger

    editLedger(store, swap)
    with pytest.raises(RecordRefused, match="not the outcome of"):
        runner.release_no_change(runId, stepId, ruling=RULING)


def test_the_shipped_release_record_names_exactly_the_two_batch_9_steps() -> None:
    record = json.loads((REPO_ROOT / f"founder/steward/decisions/{RULING}.json").read_text(encoding="utf-8"))
    bindings = [line for line in record["evidence"] if line.startswith(fullrun.NOCHANGERELEASEPREFIX)]
    assert bindings == [
        "releaseNoChange run-20261107T164134Z-574a6b71 build:2933fea8b223:1",
        "releaseNoChange run-20261107T164134Z-574a6b71 build:55b938d79131:1",
    ]
    assert RULING in fullrun.NOCHANGERELEASERULINGS and len(fullrun.NOCHANGERELEASERULINGS) == 1
