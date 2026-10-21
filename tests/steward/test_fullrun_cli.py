"""`gaia steward full`: argument parsing, exit codes, JSON shape, record input checks."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

import gaia_cli.steward.fullrun as fullrun
from gaia_cli.commands.steward import StewardCommand
from gaia_cli.main import get_parser, main
from gaia_cli.steward.controller import StewardController
from gaia_cli.steward.primitives import SensorUnavailable
from gaia_cli.steward.sensors import AgentSkillMirrorSensor

from tests.steward.test_fullrun import (
    INTEGRATION,
    StubSensor,
    git,
    makeFixture,
    makeRunner,
    fileStore,
)


def useSensors(monkeypatch: pytest.MonkeyPatch, sensors: list[Any]) -> None:
    monkeypatch.setattr(fullrun, "StewardController", lambda: StewardController(sensors=tuple(sensors)))


def runCli(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], repo: Path, *argv: str) -> tuple[int, str, str]:
    monkeypatch.setattr(sys, "argv", ["gaia", "--registry", str(repo), "steward", "full", *argv])
    code = 0
    try:
        main()
    except SystemExit as exc:
        code = int(exc.code or 0)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


@pytest.fixture(autouse=True)
def noIntegrationEnv(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GAIA_STEWARD_INTEGRATION_BRANCH", raising=False)


# --- parsing -------------------------------------------------------------------------


def test_run_arguments_parse_into_the_documented_fields() -> None:
    parser, _ = get_parser()
    args = parser.parse_args([
        "--registry", ".", "steward", "full", "run", "--triage", "--routine", "9", "--debt", "debt:x",
        "--afk", "--trigger", "scheduled", "--no-agents", "--ledger", "local",
        "--integration-branch", "dev/x", "--push", "--json",
    ])
    assert (args.steward_command, args.fullAction) == ("full", "run")
    assert args.triage is True and args.observe is False
    assert (args.routine, args.debt, args.afk, args.trigger) == ("9", "debt:x", True, "scheduled")
    assert (args.noAgents, args.ledger, args.integrationBranch, args.push, args.json) == (True, "local", "dev/x", True, True)
    assert StewardCommand._fullModeOf(args) == "triage"


def test_run_defaults_are_safe() -> None:
    parser, _ = get_parser()
    args = parser.parse_args(["--registry", ".", "steward", "full", "run"])
    assert (args.push, args.afk, args.noAgents, args.ledger, args.trigger) == (False, False, False, "auto", "manual")
    assert args.integrationBranch is None and args.resume is None
    assert StewardCommand._fullModeOf(args) == "full"


def test_mode_flags_are_mutually_exclusive() -> None:
    parser, _ = get_parser()
    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["--registry", ".", "steward", "full", "run", "--observe", "--retro"])
    assert exc.value.code == 2


def test_record_requires_an_input_file() -> None:
    parser, _ = get_parser()
    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["--registry", ".", "steward", "full", "record", "run-1", "step-1"])
    assert exc.value.code == 2
    args = parser.parse_args(["--registry", ".", "steward", "full", "record", "run-1", "step-1", "--input", "o.json"])
    assert (args.runId, args.stepId, args.input) == ("run-1", "step-1", "o.json")


def test_existing_subcommands_still_parse() -> None:
    parser, _ = get_parser()
    assert parser.parse_args(["--registry", ".", "steward", "scan", "--json"]).steward_command == "scan"
    assert parser.parse_args(["--registry", ".", "steward", "lane", "status"]).lane_action == "status"


# --- exit codes and JSON ----------------------------------------------------------------


def test_observe_json_shape_and_exit_zero(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    repo, _ = makeFixture(tmp_path)
    useSensors(monkeypatch, [StubSensor("repository-hygiene", "repository_hygiene", ["leak"])])

    code, out, err = runCli(monkeypatch, capsys, repo, "run", "--observe", "--ledger", "local", "--json")

    assert code == 0, err
    view = json.loads(out)
    assert view["schemaVersion"] == "steward-full-run-view-v1"
    assert view["status"] == "completed" and view["mode"] == "observe" and view["phase"] == "done"
    assert view["actions"] == [] and view["coverageUnknown"] == []
    assert view["ledger"] == {"transport": "local-file", "shared": False, "warning": "ledger_local_only"}
    assert {"observe", "reconcile"} <= set(view["summary"])
    assert view["summary"]["observe"]["openDebt"] == 1
    assert {"runId", "nextAction", "unresolvedWork", "notEvaluated", "desk"} <= set(view)
    assert (repo / ".gaia/steward/full/ledger.json").is_file()


def test_unknown_coverage_exits_three(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    repo, _ = makeFixture(tmp_path)
    useSensors(monkeypatch, [StubSensor("flaky", "registry_integrity_failed", raises=SensorUnavailable("nope"))])

    code, out, _err = runCli(monkeypatch, capsys, repo, "run", "--ledger", "local", "--json")

    assert code == 3
    view = json.loads(out)
    assert view["status"] == "blocked" and view["coverageUnknown"] == ["flaky"]


@pytest.mark.parametrize("mode", ["--observe", "--triage", "--verify", "--retro", None])
def test_unknown_coverage_blocks_every_mode_with_exit_three(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys, mode: str | None
) -> None:
    repo, _ = makeFixture(tmp_path)
    useSensors(monkeypatch, [
        StubSensor("good", "repository_hygiene", routines=(12,)),
        StubSensor("flaky", "registry_integrity_failed", routines=(7,), raises=SensorUnavailable("nope")),
    ])
    args = ["run", "--ledger", "local", "--json"] + ([mode] if mode else [])

    code, out, _err = runCli(monkeypatch, capsys, repo, *args)

    assert code == 3, mode
    view = json.loads(out)
    assert view["status"] == "blocked" and view["coverageUnknown"] == ["flaky"]
    assert view["actions"] == []


def test_human_output_is_a_concise_phase_summary_with_next_action(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    repo, _ = makeFixture(tmp_path)
    useSensors(monkeypatch, [StubSensor("repository-hygiene", "repository_hygiene")])

    code, out, _err = runCli(monkeypatch, capsys, repo, "run", "--ledger", "local")

    assert code == 0
    assert out.startswith("Gaia Steward full\n")
    for label in ("Run ", "Status ", "Ledger ", "Observed ", "Triage ", "Desk ", "Next "):
        assert any(line.startswith(label) for line in out.splitlines()), label
    assert "local only" in out
    assert len(out.splitlines()) < 25


def test_integration_branch_default_comes_from_the_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    repo, bare = makeFixture(tmp_path, mirrorDrift=True)
    useSensors(monkeypatch, [AgentSkillMirrorSensor()])

    # No target configured: the debt is blocked, nothing is pushed.
    code, out, _ = runCli(monkeypatch, capsys, repo, "run", "--push", "--ledger", "local", "--json")
    assert code == 0
    blocked = json.loads(out)
    assert blocked["summary"]["class_a"]["landings"][0]["reason"] == "landing target not configured"
    assert not [b for b in git(bare, "for-each-ref", "--format=%(refname:short)", "refs/heads").split() if b.startswith("steward/a/")]
    assert any(d["decisionId"] == "landing-target-not-configured" for d in blocked["desk"]["decisions"])

    monkeypatch.setenv("GAIA_STEWARD_INTEGRATION_BRANCH", INTEGRATION)
    code, out, _ = runCli(monkeypatch, capsys, repo, "run", "--push", "--ledger", "local", "--json")
    landed = json.loads(out)
    assert code == 0 and landed["status"] == "awaiting-action", landed
    assert [a["type"] for a in landed["actions"]] == ["forge.open_pr"]
    assert landed["actions"][0]["params"]["base"] == INTEGRATION


def test_second_invocation_while_a_run_is_live_exits_four_and_names_the_holder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    repo, _ = makeFixture(tmp_path)
    sensor = StubSensor("repository-hygiene", "repository_hygiene", ["leak"])
    first = makeRunner(repo, StewardCommand._fullStore(repo, "local", "origin"), [sensor], trigger="manual").start("full")
    assert first.status == "awaiting-action"
    useSensors(monkeypatch, [sensor])

    code, out, _ = runCli(monkeypatch, capsys, repo, "run", "--ledger", "local", "--json")

    assert code == 4, "observing-existing is neither success (0) nor refused input (2)"
    view = json.loads(out)
    assert view["status"] == "observing-existing" and view["holder"] == first.runId
    assert view["runId"] is None


# --- refusals (exit 2) -------------------------------------------------------------------


@pytest.mark.parametrize("extra", [["--routine", "0"], ["--routine", "19"], ["--resume", "run-x", "--observe"],
                                   ["--resume", "run-x", "--debt", "debt:x"]])
def test_bad_run_arguments_exit_two(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys, extra: list[str]) -> None:
    repo, _ = makeFixture(tmp_path)
    useSensors(monkeypatch, [])
    code, _out, err = runCli(monkeypatch, capsys, repo, "run", "--ledger", "local", *extra)
    assert code == 2 and "refused" in err


def test_resume_of_an_unknown_run_exits_two(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    repo, _ = makeFixture(tmp_path)
    useSensors(monkeypatch, [])
    code, _out, err = runCli(monkeypatch, capsys, repo, "run", "--ledger", "local", "--resume", "run-nope")
    assert code == 2 and "unknown run" in err


def startedBuild(repo: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Any, Any]:
    sensor = StubSensor("repository-hygiene", "repository_hygiene", ["leak"])
    view = makeRunner(repo, StewardCommand._fullStore(repo, "local", "origin"), [sensor]).start("full")
    useSensors(monkeypatch, [sensor])
    return view, sensor


def test_record_rejects_unreadable_and_non_object_input(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    repo, _ = makeFixture(tmp_path)
    view, _ = startedBuild(repo, monkeypatch)
    step = view.actions[0]["stepId"]

    code, _o, err = runCli(monkeypatch, capsys, repo, "record", view.runId, step, "--input", str(tmp_path / "missing.json"), "--ledger", "local")
    assert code == 2 and "cannot read outcome file" in err

    notObject = tmp_path / "list.json"
    notObject.write_text("[1, 2]", encoding="utf-8")
    code, _o, err = runCli(monkeypatch, capsys, repo, "record", view.runId, step, "--input", str(notObject), "--ledger", "local")
    assert code == 2 and "JSON object" in err

    broken = tmp_path / "broken.json"
    broken.write_text("{nope", encoding="utf-8")
    code, _o, err = runCli(monkeypatch, capsys, repo, "record", view.runId, step, "--input", str(broken), "--ledger", "local")
    assert code == 2


def test_record_refuses_invalid_outcomes_and_unknown_steps(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    repo, _ = makeFixture(tmp_path)
    view, _ = startedBuild(repo, monkeypatch)
    step = view.actions[0]["stepId"]
    outcome = tmp_path / "outcome.json"

    outcome.write_text(json.dumps({"agentId": "b", "model": "haiku", "effort": "default",
                                   "noChange": True, "summary": "nothing"}), encoding="utf-8")
    code, _o, err = runCli(monkeypatch, capsys, repo, "record", view.runId, step, "--input", str(outcome), "--ledger", "local")
    assert code == 2 and "effort" in err

    outcome.write_text(json.dumps({"agentId": "b", "model": "haiku", "effort": "high",
                                   "noChange": False, "summary": "x"}), encoding="utf-8")
    code, _o, err = runCli(monkeypatch, capsys, repo, "record", view.runId, step, "--input", str(outcome), "--ledger", "local")
    assert code == 2 and "diffPath" in err

    code, _o, err = runCli(monkeypatch, capsys, repo, "record", view.runId, "no-such-step", "--input", str(outcome), "--ledger", "local")
    assert code == 2 and "no action" in err

    code, _o, err = runCli(monkeypatch, capsys, repo, "record", "run-nope", step, "--input", str(outcome), "--ledger", "local")
    assert code == 2


def test_record_accepts_a_valid_no_change_build_and_returns_a_view(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    repo, _ = makeFixture(tmp_path)
    view, _ = startedBuild(repo, monkeypatch)
    step = view.actions[0]["stepId"]
    outcome = tmp_path / "outcome.json"
    outcome.write_text(json.dumps({"agentId": "b1", "model": "haiku", "effort": "medium",
                                   "noChange": True, "summary": "does not reproduce"}), encoding="utf-8")

    code, out, err = runCli(monkeypatch, capsys, repo, "record", view.runId, step, "--input", str(outcome), "--ledger", "local", "--json")

    assert code == 0, err
    payload = json.loads(out)
    assert payload["runId"] == view.runId and payload["actions"] == []
    assert "--resume" in payload["nextAction"]


# --- status -------------------------------------------------------------------------------


def test_status_json_and_human(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    repo, _ = makeFixture(tmp_path)
    view, _ = startedBuild(repo, monkeypatch)

    code, out, _ = runCli(monkeypatch, capsys, repo, "status", "--ledger", "local", "--json")
    assert code == 0
    status = json.loads(out)
    assert status["schemaVersion"] == "steward-full-status-v1"
    assert status["holder"] == view.runId and status["workCounts"] == {"building": 1}
    assert status["activeRuns"][0]["status"] == "awaiting-action"
    assert status["lane"]["counts"]["dispatched"] == 1
    assert status["ledger"]["shared"] is False

    code, out, _ = runCli(monkeypatch, capsys, repo, "status", "--ledger", "local")
    assert code == 0 and out.startswith("Gaia Steward full status")
    assert "Run lease" in out and "building 1" in out


def test_ledger_auto_prefers_the_shared_ref_when_the_remote_answers(tmp_path: Path) -> None:
    repo, _ = makeFixture(tmp_path)
    assert StewardCommand._fullStore(repo, "auto", "origin").transport == "git-ref"
    lonely = tmp_path / "lonely"
    lonely.mkdir()
    subprocess.run(["git", "init", "-q", str(lonely)], check=True)
    assert StewardCommand._fullStore(lonely, "auto", "origin").transport == "local-file"
    assert StewardCommand._fullStore(repo, "local", "origin").transport == "local-file"
    assert StewardCommand._fullStore(repo, "git", "origin").transport == "git-ref"


def test_the_runner_never_touches_a_real_ledger_ref(tmp_path: Path) -> None:
    repo, bare = makeFixture(tmp_path)
    store = fileStore(tmp_path)
    makeRunner(repo, store, [StubSensor("repository-hygiene", "repository_hygiene")]).start("observe")
    refs = git(bare, "for-each-ref", "--format=%(refname:short)", "refs/heads").split()
    assert not [r for r in refs if r.startswith("steward/")]


# --- D10: distinct exit codes, documented where an operator looks -------------------------


def test_run_help_documents_every_exit_code(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    repo, _ = makeFixture(tmp_path)
    code, out, _err = runCli(monkeypatch, capsys, repo, "run", "--help")
    assert code == 0
    assert "exit codes:" in out
    for line in ("0  completed", "1  failed", "2  refused input", "3  blocked", "4  observing-existing"):
        assert line in out, line


def test_exit_codes_are_distinct_for_every_outcome() -> None:
    from gaia_cli.steward.fullrun import RunView

    codes = {
        status: RunView(runId="r", mode="full", status=status, phase="done", nextAction="").exitCode
        for status in ("completed", "awaiting-action", "failed", "abandoned", "blocked", "observing-existing")
    }
    assert codes == {"completed": 0, "awaiting-action": 0, "failed": 1, "abandoned": 1,
                     "blocked": 3, "observing-existing": 4}


def test_conflicting_integration_branch_on_resume_exits_two(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    repo, _ = makeFixture(tmp_path)
    sensor = StubSensor("repository-hygiene", "repository_hygiene", ["leak"])
    view = makeRunner(repo, StewardCommand._fullStore(repo, "local", "origin"), [sensor]).start("full")
    useSensors(monkeypatch, [sensor])
    code, _out, err = runCli(monkeypatch, capsys, repo, "run", "--ledger", "local", "--resume", view.runId,
                             "--integration-branch", "dev/elsewhere")
    assert code == 2 and "refusing to resume" in err


def test_routine_placeholder_parses_but_a_non_number_is_refused_at_run_time(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    parser, _ = get_parser()
    args = parser.parse_args(["--registry", ".", "steward", "full", "run", "--triage", "--routine", "N", "--json"])
    assert args.routine == "N"
    repo, _ = makeFixture(tmp_path)
    useSensors(monkeypatch, [])
    code, _out, err = runCli(monkeypatch, capsys, repo, "run", "--ledger", "local", "--triage", "--routine", "N")
    assert code == 2 and "must be a number" in err


# --- D11: --retro prints the routine and sensor table for a person ----------------------------


def test_retro_human_output_prints_the_sensor_and_routine_tables(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    repo, _ = makeFixture(tmp_path)
    useSensors(monkeypatch, [
        StubSensor("detector-ok", "repository_hygiene", routines=(3,)),
        StubSensor("detector-dark", "registry_integrity_failed", routines=(3,), raises=SensorUnavailable("dark")),
        StubSensor("detector-solo", "repository_hygiene", routines=(5,)),
    ])

    code, out, _err = runCli(monkeypatch, capsys, repo, "run", "--retro", "--ledger", "local")

    assert code == 3, "unknown coverage blocks, in every mode"
    lines = out.splitlines()
    assert "Sensors" in lines and "Routines" in lines
    assert any(l.strip().startswith("detector-dark") and "unknown" in l for l in lines)
    assert any(l.strip().startswith("detector-ok") and "executed" in l for l in lines)
    three = next(l for l in lines if l.strip().startswith("3 ") and "detector-ok" in l)
    assert "partial" in three and "observed" not in three
    five = next(l for l in lines if l.strip().startswith("5 ") and "detector-solo" in l)
    assert "observed" in five
    routineRows = [l for l in lines if l.startswith("  ") and l.split()[:1] and l.split()[0].isnumeric()]
    assert len(routineRows) == 18


def test_a_clean_scheduled_run_prints_the_quiet_line_and_status_carries_the_desk(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    from gaia_cli.steward.desk import QUIET_LINE
    from gaia_cli.steward.primitives import SensorNotEvaluated

    repo, _bare = makeFixture(tmp_path)
    # A clean tree plus a driver input nobody supplied: shown in the receipt, nothing to act on.
    absent = StubSensor("ci-health", "ci_failure", raises=SensorNotEvaluated("no ci-runs.json supplied", input_absent=True))
    useSensors(monkeypatch, [StubSensor("repository-hygiene", "repository_hygiene"), absent])

    code, out, _err = runCli(monkeypatch, capsys, repo, "run", "--ledger", "git", "--trigger", "scheduled")
    assert code == 0, out
    assert QUIET_LINE in out.splitlines()

    code, out, _err = runCli(monkeypatch, capsys, repo, "run", "--observe", "--ledger", "git", "--trigger", "scheduled", "--json")
    view = json.loads(out)
    assert view["desk"]["quiet"] is True
    assert view["summary"]["observe"]["notEvaluated"] == [
        {"sensor": "ci-health", "reason": "no ci-runs.json supplied", "inputAbsent": True}
    ]

    code, out, _err = runCli(monkeypatch, capsys, repo, "status", "--ledger", "git", "--json")
    status = json.loads(out)
    assert code == 0 and status["desk"]["quiet"] is True and status["deskRunId"] == view["runId"]
    code, out, _err = runCli(monkeypatch, capsys, repo, "status", "--ledger", "git")
    assert out.rstrip("\n").endswith(QUIET_LINE)


def test_unknown_coverage_names_its_cause_in_the_run_and_on_the_desk(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    repo, _ = makeFixture(tmp_path)
    useSensors(monkeypatch, [StubSensor("broken", "repository_hygiene", raises=SensorUnavailable("required inventory is empty: registry/named"))])
    code, out, _err = runCli(monkeypatch, capsys, repo, "run", "--ledger", "local", "--json")
    view = json.loads(out)
    assert code == 3
    why = view["summary"]["observe"]["coverageUnknownReasons"]["broken"]
    assert why == "SensorUnavailable: required inventory is empty: registry/named"
    (operation,) = [op for op in view["desk"]["operations"] if op["kind"] == "coverage_unknown"]
    assert operation["detail"].endswith("Cause: " + why)
