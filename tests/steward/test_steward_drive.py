"""Tests for scripts/steward_drive.py: the unattended driver for `gaia steward full run`.

No network, no models, no real gaia/gh/git. Every external command goes through a
scripted fake runner that the driver receives by injection.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Callable

import pytest

REPO = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("steward_drive", REPO / "scripts" / "steward_drive.py")
drive = importlib.util.module_from_spec(SPEC)
sys.modules["steward_drive"] = drive
SPEC.loader.exec_module(drive)

from gaia_cli.steward.fullrun import BADEFFORTS  # noqa: E402

PY = "PY"
BASE = "dev/steward-x"
AGENTENV = {
    "STEWARD_AGENT_CMD": "fake-agent --model {model} --effort {effort} {prompt_path}",
    "STEWARD_SONNET_MODEL_ID": "sonnet-test-id",
    "STEWARD_HAIKU_MODEL_ID": "haiku-test-id",
}


def ok(stdout: str = "") -> drive.CommandResult:
    return drive.CommandResult(0, stdout, "")


class FakeWorld:
    """Scripted stand-in for gaia, gh, git and the agent command."""

    def __init__(self, root: Path, runs: list[tuple[int, Any]], *, records=None, status=None,
                 agent: Callable[..., drive.CommandResult] | None = None,
                 gh: Callable[[list[str]], drive.CommandResult] | None = None) -> None:
        self.root = root
        self.runs = list(runs)
        self.recordReplies = list(records or [])
        self.statusPayload = status or {}
        self.agentFn = agent or defaultAgent
        self.ghFn = gh or (lambda args: ok("[]"))
        self.calls: list[list[str]] = []
        self.recorded: list[tuple[str, dict[str, Any]]] = []
        self.agentCalls: list[list[str]] = []
        self.ghCalls: list[list[str]] = []

    def __call__(self, argv, *, cwd, timeout=None, env=None):
        argv = list(argv)
        self.calls.append(argv)
        if argv[:3] == [PY, "-m", "gaia_cli.main"]:
            verb = argv[5]
            if verb == "run":
                index = min(sum(1 for c in self.calls if isRun(c)) - 1, len(self.runs) - 1)
                code, payload = self.runs[index]
                return drive.CommandResult(code, json.dumps(payload) if payload is not None else "", "")
            if verb == "record":
                stepId = argv[7]
                payload = json.loads(Path(argv[argv.index("--input") + 1]).read_text(encoding="utf-8"))
                self.recorded.append((stepId, payload))
                code, body = self.recordReplies.pop(0) if self.recordReplies else (0, {"status": "awaiting-action"})
                text = json.dumps(body) if body is not None else ""
                return drive.CommandResult(code, text, "refused" if code == 2 else "")
            if verb == "status":
                return drive.CommandResult(0, json.dumps(self.statusPayload), "")
            raise AssertionError(f"unexpected gaia verb {verb}")
        if argv[0] == "gh":
            self.ghCalls.append(argv)
            return self.ghFn(argv[1:])
        if argv[0] == "git":
            return ok("diff --git a/x b/x\n+fix\n")
        self.agentCalls.append(argv)
        return self.agentFn(argv, cwd)


def defaultAgent(argv, cwd):
    prompt = next(t for t in argv if t.endswith(".prompt.md"))
    if "verify" in Path(prompt).name:
        return ok(json.dumps({"verdict": "accept", "rationale": "reproduces and is in scope"}))
    root = Path(cwd)
    (root / ".gaia/steward/full/R1").mkdir(parents=True, exist_ok=True)
    (root / ".gaia/steward/full/R1/build-abc.diff").write_text("diff --git a/x b/x\n+fix\n", encoding="utf-8")
    (root / ".gaia/steward/full/R1/build-abc.proof.json").write_text("{}", encoding="utf-8")
    return ok(json.dumps({"noChange": False, "summary": "fixed the mirror", "tokensIn": 10, "tokensOut": 5}))


def isRun(argv: list[str]) -> bool:
    return argv[:5] == [PY, "-m", "gaia_cli.main", "steward", "full"] and len(argv) > 5 and argv[5] == "run"


def makeRoot(tmp_path: Path) -> Path:
    root = tmp_path / "checkout"
    (root / ".gaia/steward/full/R1").mkdir(parents=True)
    (root / ".gaia/steward/full/R1/build-abc.prompt.md").write_text("# build\n", encoding="utf-8")
    (root / ".gaia/steward/full/R1/verify-abc.prompt.md").write_text("# verify\n", encoding="utf-8")
    (root / ".gaia/steward/full/R1/pr-body.md").write_text("body\n", encoding="utf-8")
    return root


def buildAction(stepId: str = "build:abc:1") -> dict[str, Any]:
    return {"stepId": stepId, "type": "agent.build", "debtId": "d1", "status": "pending", "params": {
        "debtId": "d1", "promptPath": ".gaia/steward/full/R1/build-abc.prompt.md",
        "allowedModels": ["haiku", "sonnet"], "base": BASE, "branch": "steward/b/x-abc", "attempt": 1,
        "outputs": {"diffPath": ".gaia/steward/full/R1/build-abc.diff",
                    "proofPath": ".gaia/steward/full/R1/build-abc.proof.json"},
    }}


def verifyAction(forbidden: list[str] | None = None) -> dict[str, Any]:
    return {"stepId": "verify:abc:1", "type": "agent.verify", "debtId": "d1", "status": "pending", "params": {
        "debtId": "d1", "verifierPromptPath": ".gaia/steward/full/R1/verify-abc.prompt.md",
        "forbiddenAgentIds": forbidden or [], "attempt": 1, "allowedModels": ["sonnet"],
    }}


def forgeAction(base: str = BASE, stepId: str = "open_pr:steward/a/x") -> dict[str, Any]:
    return {"stepId": stepId, "type": "forge.open_pr", "debtId": "d2", "status": "pending", "params": {
        "head": "steward/a/x", "base": base, "title": "chore(steward): repair x",
        "bodyPath": ".gaia/steward/full/R1/pr-body.md", "idempotencyKey": "steward/a/x",
        "ifExists": "record-existing",
    }}


def view(runId: str, actions: list[dict[str, Any]], status: str = "awaiting-action") -> tuple[int, dict]:
    code = 0 if status in ("awaiting-action", "completed") else 1
    return code, {"schemaVersion": "steward-full-run-view-v1", "runId": runId, "status": status,
                  "phase": "class_b", "actions": actions, "summary": {}, "ledger": {}}


def makeDriver(tmp_path: Path, world: FakeWorld, *, env=None, ready_which=None, **kw) -> Any:
    root = world.root
    options = drive.DriveOptions(root=root, integrationBranch=BASE, python=PY,
                                 reportPath=tmp_path / "report.json", **kw)
    return drive.Driver(options, runner=world, env=dict(AGENTENV if env is None else env),
                        which=ready_which or (lambda name: None))


# -- happy path ------------------------------------------------------------

def test_happy_path_build_verify_record(tmp_path):
    root = makeRoot(tmp_path)
    runs = [view("R1", [buildAction()]), view("R1", [verifyAction()]), view("R1", [], "completed")]
    world = FakeWorld(root, runs)
    driver = makeDriver(tmp_path, world)

    code = driver.drive()

    assert code == drive.EXITCOMPLETED
    assert [step for step, _ in world.recorded] == ["build:abc:1", "verify:abc:1"]
    builder = world.recorded[0][1]
    verifier = world.recorded[1][1]
    assert builder["model"] == "haiku" and builder["noChange"] is False
    assert builder["diffPath"] == ".gaia/steward/full/R1/build-abc.diff"
    assert verifier["model"] == "sonnet" and verifier["verdict"] == "accept"
    assert builder["agentId"].startswith("builder-") and verifier["agentId"].startswith("verifier-")


def test_builder_and_verifier_ids_differ(tmp_path):
    root = makeRoot(tmp_path)
    world = FakeWorld(root, [view("R1", [buildAction()]), view("R1", [verifyAction()]), view("R1", [], "completed")])
    makeDriver(tmp_path, world).drive()
    ids = [payload["agentId"] for _, payload in world.recorded]
    assert len(ids) == 2 and ids[0] != ids[1]


def test_efforts_are_explicit_and_never_default_or_inherit(tmp_path):
    root = makeRoot(tmp_path)
    world = FakeWorld(root, [view("R1", [buildAction()]), view("R1", [verifyAction()]), view("R1", [], "completed")])
    makeDriver(tmp_path, world).drive()
    for _, payload in world.recorded:
        assert payload["effort"].strip().lower() not in BADEFFORTS
    with pytest.raises(drive.DriverConfigError):
        makeDriver(tmp_path, FakeWorld(root, []), env={**AGENTENV, "STEWARD_BUILD_EFFORT": "inherit"})


def test_no_turn_limit_flag_is_passed(tmp_path):
    root = makeRoot(tmp_path)
    world = FakeWorld(root, [view("R1", [], "completed")])
    makeDriver(tmp_path, world).drive()
    flat = " ".join(" ".join(c) for c in world.calls)
    assert "max-turns" not in flat and "max_turns" not in flat


# -- verifier independence ---------------------------------------------------

def test_verifier_cannot_reuse_a_forbidden_id(tmp_path, monkeypatch):
    root = makeRoot(tmp_path)
    runs = [view("R1", [verifyAction(forbidden=["verifier-fixed"])])]
    world = FakeWorld(root, runs)
    driver = makeDriver(tmp_path, world)
    driver.newId = lambda prefix: f"{prefix}-fixed"

    code = driver.drive()

    assert code == drive.EXITSTOPPED
    assert world.agentCalls == []  # the verifier was never spawned
    assert world.recorded == []
    assert driver.failures == {"verify:abc:1": 2}
    assert "belongs to a builder" in driver.stopReason


def test_verifier_does_not_reuse_builder_id(tmp_path):
    root = makeRoot(tmp_path)
    verify = view("R1", [verifyAction()])
    world = FakeWorld(root, [view("R1", [buildAction()]), verify, verify])
    driver = makeDriver(tmp_path, world)
    driver.newId = lambda prefix: "shared"  # identical id for builder and verifier
    code = driver.drive()
    assert code == drive.EXITSTOPPED
    assert [step for step, _ in world.recorded] == ["build:abc:1"]
    assert driver.failures == {"verify:abc:1": 2}
    assert "belongs to a builder" in driver.stopReason


# -- unknown and refused actions -----------------------------------------------

def test_unknown_action_type_reported_not_executed(tmp_path):
    root = makeRoot(tmp_path)
    weird = {"stepId": "x:1", "type": "lead.frobnicate", "debtId": "d9", "status": "pending", "params": {}}
    world = FakeWorld(root, [view("R1", [weird])])
    driver = makeDriver(tmp_path, world)
    code = driver.drive()
    assert code == drive.EXITSTOPPED
    assert [u["type"] for u in driver.unknown] == ["lead.frobnicate"]
    assert world.recorded == [] and world.agentCalls == [] and world.ghCalls == []
    assert "stalled" in driver.stopReason


def test_base_main_refused_without_forge_calls(tmp_path):
    root = makeRoot(tmp_path)
    world = FakeWorld(root, [view("R1", [forgeAction(base="main")])])
    driver = makeDriver(tmp_path, world)
    code = driver.drive()
    assert code == drive.EXITSTOPPED
    assert world.ghCalls == [] and world.recorded == []
    assert any("protected" in r["reason"] for r in driver.refused)


def test_base_not_integration_branch_refused(tmp_path):
    root = makeRoot(tmp_path)
    world = FakeWorld(root, [view("R1", [forgeAction(base="dev/other")])])
    driver = makeDriver(tmp_path, world)
    assert driver.drive() == drive.EXITSTOPPED
    assert world.ghCalls == []


def test_refused_record_stops_after_second_refusal(tmp_path):
    root = makeRoot(tmp_path)
    world = FakeWorld(root, [view("R1", [forgeAction()])],
                      records=[(2, None), (2, None)],
                      gh=lambda args: ok("https://github.com/o/r/pull/9\n") if args[:2] == ["pr", "create"] else ok("[]"))
    driver = makeDriver(tmp_path, world)
    code = driver.drive()
    assert code == drive.EXITSTOPPED
    assert len(world.recorded) == 2
    assert "failed twice" in driver.stopReason


# -- forge and integrate ------------------------------------------------------

def test_forge_opens_draft_pr_into_integration_branch(tmp_path):
    root = makeRoot(tmp_path)
    world = FakeWorld(root, [view("R1", [forgeAction()]), view("R1", [], "completed")],
                      gh=lambda args: ok("https://github.com/o/r/pull/9\n") if args[:2] == ["pr", "create"] else ok("[]"))
    code = makeDriver(tmp_path, world).drive()
    assert code == drive.EXITCOMPLETED
    create = next(c for c in world.ghCalls if c[1:3] == ["pr", "create"])
    assert "--draft" in create and create[create.index("--base") + 1] == BASE
    assert create[create.index("--body-file") + 1].endswith("pr-body.md")
    assert world.recorded[0][1] == {"pullRequest": {"number": 9, "url": "https://github.com/o/r/pull/9"}, "merged": False}


def test_forge_is_idempotent_when_pr_exists(tmp_path):
    root = makeRoot(tmp_path)
    existing = json.dumps([{"number": 7, "url": "https://github.com/o/r/pull/7", "state": "OPEN",
                            "baseRefName": BASE, "headRefName": "steward/a/x"}])
    world = FakeWorld(root, [view("R1", [forgeAction()]), view("R1", [], "completed")],
                      gh=lambda args: ok(existing) if args[:2] == ["pr", "list"] else ok())
    assert makeDriver(tmp_path, world).drive() == drive.EXITCOMPLETED
    assert not any(c[1:3] == ["pr", "create"] for c in world.ghCalls)
    assert world.recorded[0][1]["pullRequest"]["number"] == 7


def integrateAction(base: str = BASE) -> dict[str, Any]:
    return {"stepId": "integrate:abc:1", "type": "lead.integrate", "debtId": "d1", "status": "pending", "params": {
        "debtId": "d1", "branch": "steward/b/x-abc", "base": base, "attempt": 1,
        "diffPath": ".gaia/steward/full/R1/build-abc.diff"}}


def test_integrate_merges_with_merge_commit_into_integration_branch(tmp_path):
    root = makeRoot(tmp_path)

    def gh(args):
        if args[:2] == ["pr", "list"]:
            return ok(json.dumps([{"number": 3, "url": "https://github.com/o/r/pull/3", "isDraft": False,
                                   "headRefOid": "abc123", "headRefName": "steward/b/x-abc",
                                   "baseRefName": BASE}]))
        if args[:2] == ["pr", "merge"]:
            return ok()
        if args[:2] == ["pr", "view"]:
            return ok("deadbeef\n")
        raise AssertionError(args)

    world = FakeWorld(root, [view("R1", [integrateAction()]), view("R1", [], "completed")], gh=gh)
    assert makeDriver(tmp_path, world).drive() == drive.EXITCOMPLETED
    merge = next(c for c in world.ghCalls if c[1:3] == ["pr", "merge"])
    assert "--merge" in merge and "--squash" not in merge
    assert merge[merge.index("--match-head-commit") + 1] == "abc123"
    assert world.recorded[0][1]["mergedSha"] == "deadbeef"


def test_integrate_ambiguous_records_nothing(tmp_path):
    root = makeRoot(tmp_path)
    two = json.dumps([{"number": 1, "url": "u1", "isDraft": False, "headRefOid": "a", "headRefName": "steward/b/x-abc", "baseRefName": BASE},
                      {"number": 2, "url": "u2", "isDraft": False, "headRefOid": "b", "headRefName": "steward/b/x-abc", "baseRefName": BASE}])
    world = FakeWorld(root, [view("R1", [integrateAction()])], gh=lambda args: ok(two))
    driver = makeDriver(tmp_path, world)
    assert driver.drive() == drive.EXITSTOPPED
    assert world.recorded == []
    assert not any(c[1:3] == ["pr", "merge"] for c in world.ghCalls)
    assert "ambiguous" in driver.skipped[0]["reason"]


def test_integrate_refuses_main(tmp_path):
    root = makeRoot(tmp_path)
    world = FakeWorld(root, [view("R1", [integrateAction(base="main")])])
    driver = makeDriver(tmp_path, world)
    assert driver.drive() == drive.EXITSTOPPED
    assert world.ghCalls == [] and world.recorded == []


# -- agents unavailable --------------------------------------------------------

def test_missing_credentials_runs_no_agents_and_exits_5_when_agent_work_is_pending(tmp_path):
    root = makeRoot(tmp_path)
    earlier = {"runs": [{"runId": "OLD", "actions": [
        {"stepId": "build:old:1", "type": "agent.build", "status": "pending"}]}]}
    world = FakeWorld(root, [view("R2", [buildAction()])], status=earlier)
    driver = makeDriver(tmp_path, world, env={"STEWARD_SONNET_MODEL_ID": "s"}, ready_which=lambda n: None)

    code = driver.drive()

    assert code == drive.EXITNOTRUN == 5
    runArgs = next(c for c in world.calls if isRun(c))
    assert "--no-agents" in runArgs
    assert world.agentCalls == [] and world.recorded == []
    assert {u["stepId"] for u in driver.unperformed} >= {"build:abc:1", "build:old:1"}
    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert report["agents"]["state"] == "NOT RUN"
    assert report["agents"]["reason"].startswith("no agent credentials")


def test_missing_credentials_with_no_agent_work_exits_zero_with_note(tmp_path):
    root = makeRoot(tmp_path)
    world = FakeWorld(root, [view("R1", [forgeAction()]), view("R1", [], "completed")],
                      gh=lambda args: ok("https://github.com/o/r/pull/9\n") if args[:2] == ["pr", "create"] else ok("[]"))
    driver = makeDriver(tmp_path, world, env={"STEWARD_SONNET_MODEL_ID": "s"})
    assert driver.drive() == drive.EXITCOMPLETED
    assert world.recorded and world.agentCalls == []
    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert report["agents"]["state"] == "NOT RUN" and report["exitCode"] == 0


def test_no_outcome_is_fabricated_when_agent_prints_nothing(tmp_path):
    root = makeRoot(tmp_path)
    silent = lambda argv, cwd: ok("no json here")
    world = FakeWorld(root, [view("R1", [buildAction()])], agent=silent)
    driver = makeDriver(tmp_path, world)
    assert driver.drive() == drive.EXITSTOPPED
    assert world.recorded == []
    assert "failed twice" in driver.stopReason
    assert driver.failures == {"build:abc:1": 2}


def test_builder_with_no_proof_is_not_recorded(tmp_path):
    root = makeRoot(tmp_path)

    def agent(argv, cwd):
        (Path(cwd) / ".gaia/steward/full/R1/build-abc.diff").write_text("diff\n", encoding="utf-8")
        return ok(json.dumps({"noChange": False, "summary": "s"}))

    world = FakeWorld(root, [view("R1", [buildAction()])], agent=agent)
    driver = makeDriver(tmp_path, world)
    assert driver.drive() == drive.EXITSTOPPED
    assert world.recorded == []
    assert "no proof transcript" in driver.stopReason


# -- reporting, flags and summary ----------------------------------------------

def test_report_and_markdown_summary_written(tmp_path, monkeypatch, capsys):
    root = makeRoot(tmp_path)
    summary = tmp_path / "summary.md"
    env = {**AGENTENV, "GITHUB_STEP_SUMMARY": str(summary)}
    world = FakeWorld(root, [view("R1", [buildAction()]), view("R1", [verifyAction()]), view("R1", [], "completed")])
    code = makeDriver(tmp_path, world, env=env).drive()
    assert code == drive.EXITCOMPLETED
    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert report["schemaVersion"] == "steward-drive-report-v1"
    assert [h["type"] for h in report["handled"]] == ["agent.build", "agent.verify"]
    assert report["tokens"]["in"] == 10 and report["tokens"]["out"] == 5
    assert "## Steward drive" in summary.read_text(encoding="utf-8")
    assert "## Steward drive" in capsys.readouterr().out


def test_no_push_flag_removes_push_from_runner_call(tmp_path):
    root = makeRoot(tmp_path)
    world = FakeWorld(root, [view("R1", [], "completed")])
    makeDriver(tmp_path, world, push=False).drive()
    runArgs = next(c for c in world.calls if isRun(c))
    assert "--push" not in runArgs
    assert runArgs[runArgs.index("--ledger") + 1] == "git"
    assert runArgs[runArgs.index("--integration-branch") + 1] == BASE


def test_runner_blocked_is_reported_not_retried(tmp_path):
    root = makeRoot(tmp_path)
    world = FakeWorld(root, [(3, {"status": "blocked", "runId": "R1", "actions": []})])
    driver = makeDriver(tmp_path, world)
    assert driver.drive() == drive.EXITBLOCKED == 3
    assert sum(1 for c in world.calls if isRun(c)) == 1


def test_integration_branch_must_be_dev(tmp_path, monkeypatch):
    code = drive.main(["--root", str(tmp_path), "--integration-branch", "main",
                       "--report", str(tmp_path / "r.json")])
    assert code == drive.EXITREFUSEDINPUT == 2


# -- engine mode (STEWARD_AGENT / STEWARD_VERIFIER_AGENT) ----------------------

ENGINEENV = {**AGENTENV, "GH_TOKEN": "token-test", "STEWARD_AGENT": "copilot"}


def readyWhich(name: str) -> str:
    return f"/usr/bin/{name}"


def adapterCalls(world: FakeWorld) -> list[list[str]]:
    return [c for c in world.agentCalls if "--engine" in c]


def dispatchOf(argv: list[str]) -> str:
    return argv[argv.index("--dispatch-id") + 1]


def gitCalls(world: FakeWorld) -> list[list[str]]:
    return [c for c in world.calls if c and c[0] == "git"]


def test_engine_copilot_builder_then_verifier_through_adapter(tmp_path):
    root = makeRoot(tmp_path)
    world = FakeWorld(root, [view("R1", [buildAction()]), view("R1", [verifyAction()]), view("R1", [], "completed")])
    driver = makeDriver(tmp_path, world, env=ENGINEENV, ready_which=readyWhich)

    assert driver.drive() == drive.EXITCOMPLETED

    builder, verifier = world.recorded[0][1], world.recorded[1][1]
    assert [step for step, _ in world.recorded] == ["build:abc:1", "verify:abc:1"]
    assert builder["model"] == "copilot" and verifier["model"] == "copilot"
    assert builder["agentId"] != verifier["agentId"]
    buildCall, verifyCall = adapterCalls(world)
    adapter = str(root / "scripts" / "steward_agent_dispatch.py")
    timeout = str(int(driver.options.agentTimeout))
    assert dispatchOf(buildCall).startswith("build-") and dispatchOf(verifyCall).startswith("verify-")
    assert buildCall == [PY, adapter, "--role", "build", "--engine", "copilot",
                         "--prompt-path", str(root / ".gaia/steward/full/R1/build-abc.prompt.md"),
                         "--dispatch-id", dispatchOf(buildCall), "--timeout", timeout,
                         "--base", BASE, "--branch", "steward/b/x-abc"]
    assert verifyCall == [PY, adapter, "--role", "verify", "--engine", "copilot",
                          "--prompt-path", str(root / ".gaia/steward/full/R1/verify-abc.prompt.md"),
                          "--dispatch-id", dispatchOf(verifyCall), "--timeout", timeout]


def test_engine_codex_builder_and_pi_verifier_recorded_by_engine(tmp_path):
    root = makeRoot(tmp_path)
    env = {**ENGINEENV, "STEWARD_AGENT": "codex", "STEWARD_VERIFIER_AGENT": "pi"}
    world = FakeWorld(root, [view("R1", [buildAction()]), view("R1", [verifyAction()]), view("R1", [], "completed")])
    driver = makeDriver(tmp_path, world, env=env, ready_which=readyWhich)

    assert driver.drive() == drive.EXITCOMPLETED

    assert world.recorded[0][1]["model"] == "codex"
    assert world.recorded[1][1]["model"] == "pi"
    buildCall, verifyCall = adapterCalls(world)
    assert buildCall[buildCall.index("--engine") + 1] == "codex"
    assert verifyCall[verifyCall.index("--engine") + 1] == "pi"


def test_engine_claude_keeps_sonnet_verifier_and_haiku_builder(tmp_path):
    root = makeRoot(tmp_path)
    env = {**ENGINEENV, "STEWARD_AGENT": "claude"}
    world = FakeWorld(root, [view("R1", [buildAction()]), view("R1", [verifyAction()]), view("R1", [], "completed")])
    driver = makeDriver(tmp_path, world, env=env, ready_which=readyWhich)

    assert driver.drive() == drive.EXITCOMPLETED

    assert world.recorded[0][1]["model"] == "haiku"
    assert world.recorded[1][1]["model"] == "sonnet"


def test_engine_builder_proof_is_written_and_diff_fetched_via_git(tmp_path):
    root = makeRoot(tmp_path)

    def agent(argv, cwd):
        if argv[argv.index("--role") + 1] == "build":
            return ok(json.dumps({"noChange": False, "summary": "fixed", "proof": {"transcript": "ran it"}}))
        return ok(json.dumps({"verdict": "accept", "rationale": "reproduces and is in scope"}))

    world = FakeWorld(root, [view("R1", [buildAction()]), view("R1", [verifyAction()]), view("R1", [], "completed")],
                      agent=agent)
    driver = makeDriver(tmp_path, world, env=ENGINEENV, ready_which=readyWhich)

    assert driver.drive() == drive.EXITCOMPLETED

    proof = json.loads((root / ".gaia/steward/full/R1/build-abc.proof.json").read_text(encoding="utf-8"))
    assert proof == {"transcript": "ran it"}
    assert (root / ".gaia/steward/full/R1/build-abc.diff").read_text(encoding="utf-8").startswith("diff --git")
    fetch = ["git", "fetch", "origin", BASE, "steward/b/x-abc"]
    diff = ["git", "diff", f"origin/{BASE}...origin/steward/b/x-abc"]
    assert fetch in gitCalls(world) and diff in gitCalls(world)
    assert gitCalls(world).index(fetch) < gitCalls(world).index(diff)
    assert world.recorded[0][1]["proofPath"] == ".gaia/steward/full/R1/build-abc.proof.json"


def test_engine_adapter_refusal_records_nothing_and_reports_stderr(tmp_path):
    root = makeRoot(tmp_path)

    def agent(argv, cwd):
        return drive.CommandResult(3, "", "gh: starting\ndispatch refused: 404\n")

    world = FakeWorld(root, [view("R1", [buildAction()])], agent=agent)
    driver = makeDriver(tmp_path, world, env=ENGINEENV, ready_which=readyWhich)

    assert driver.drive() == drive.EXITSTOPPED
    assert world.recorded == [] and driver.handled == []
    assert driver.failures == {"build:abc:1": 2}
    assert "dispatch refused: 404" in driver.stopReason
    assert not (root / ".gaia/steward/full/R1/build-abc.diff").exists()
    assert not (root / ".gaia/steward/full/R1/build-abc.proof.json").exists()


def test_unknown_engine_is_a_config_error(tmp_path):
    root = makeRoot(tmp_path)
    with pytest.raises(drive.DriverConfigError):
        makeDriver(tmp_path, FakeWorld(root, []), env={**ENGINEENV, "STEWARD_AGENT": "gemini"},
                   ready_which=readyWhich)
    with pytest.raises(drive.DriverConfigError):
        makeDriver(tmp_path, FakeWorld(root, []), env={**ENGINEENV, "STEWARD_AGENT": "copilot",
                                                        "STEWARD_VERIFIER_AGENT": "gemini"},
                   ready_which=readyWhich)


def test_engine_mode_without_gh_token_is_not_ready_and_runs_no_agents(tmp_path):
    root = makeRoot(tmp_path)
    world = FakeWorld(root, [view("R1", [buildAction()])])
    driver = makeDriver(tmp_path, world, env={**AGENTENV, "STEWARD_AGENT": "copilot"}, ready_which=readyWhich)

    assert driver.drive() == drive.EXITNOTRUN == 5
    assert "--no-agents" in next(c for c in world.calls if isRun(c))
    assert world.agentCalls == [] and world.recorded == []
    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert report["agents"]["state"] == "NOT RUN"
    assert "GH_TOKEN" in report["agents"]["reason"]


def test_engine_adapter_argv_never_carries_a_turn_limit(tmp_path):
    root = makeRoot(tmp_path)
    world = FakeWorld(root, [view("R1", [buildAction()]), view("R1", [verifyAction()]), view("R1", [], "completed")])
    makeDriver(tmp_path, world, env=ENGINEENV, ready_which=readyWhich).drive()
    calls = adapterCalls(world)
    assert len(calls) == 2
    for argv in calls:
        flags = [t for t in argv if t.startswith("--")]
        assert not any("turn" in f or "max" in f for f in flags), flags
