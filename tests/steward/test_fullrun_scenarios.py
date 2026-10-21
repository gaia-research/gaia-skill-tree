"""Acceptance scenarios for Steward Full, against fixture repos with real git.

Each scenario uses a local bare remote and, where it matters, both ledger
transports. No test touches a real origin or a real `steward/*` ref.
"""

from __future__ import annotations

import json
import tempfile
import threading
from pathlib import Path
from typing import Any

import pytest
import yaml

import gaia_cli.steward.fullrun as fullrun
from gaia_cli.steward.fullrun import RecordRefused
from gaia_cli.steward.ledger import GitRefLedgerStore
from gaia_cli.steward.lane import load_lane
from gaia_cli.steward.policy import StewardPolicy
from gaia_cli.steward.sensors import AgentSkillMirrorSensor, TrustCalibrationDriftSensor
from gaia_cli.steward.primitives import SensorUnavailable

from tests.steward.sensor_fixtures import make_repo
from tests.steward.test_fullrun import (
    BUILD,
    Clock,
    INTEGRATION,
    VERIFY,
    StubSensor,
    actionTypes,
    bareBranches,
    cloneOf,
    commitAll,
    drive,
    editLedger,
    fileStore,
    git,
    makeFixture,
    makeRunner,
    pinMaxInFlight,
    write,
    writeBuildArtifacts,
)

HYGIENE = "repository-hygiene"


def ledgerOf(store: Any) -> dict[str, Any]:
    document, _version = store.load()
    return document


def stewardRefs(bare: Path) -> list[str]:
    return [b for b in bareBranches(bare) if b.startswith("steward/a/")]


# --- A: clean repository ---------------------------------------------------------


@pytest.mark.parametrize("transport", ["file", "git"])
def test_scenario_a_clean_repo_is_quiet_with_zero_everything(tmp_path: Path, transport: str) -> None:
    repo, bare = makeFixture(tmp_path)
    store = fileStore(tmp_path) if transport == "file" else GitRefLedgerStore(repo, "origin")
    runner = makeRunner(repo, store, [AgentSkillMirrorSensor()], trigger="scheduled")

    view = runner.start("full")

    assert view.status == "completed", view.to_dict()
    assert view.actions == []
    assert view.coverageUnknown == []
    doc = ledgerOf(store)
    run = doc["runs"][view.runId]
    assert run["branches"] == [] and run["pullRequests"] == []
    assert run["modelIds"] == [] and run["agentAssignments"] == []
    assert run["tokensIn"] == 0 and run["costUsd"] == 0
    assert doc["work"] == {}
    assert doc["leases"] == {}, "a finished run releases the run lease"
    assert stewardRefs(bare) == []
    assert view.desk is not None and view.desk["decisions"] == []
    if transport == "git":
        assert view.desk["quiet"] is True and view.desk["operations"] == [], view.desk
        assert "steward/ledger" in bareBranches(bare)
    else:
        # A local-only ledger is not quiet: the desk says so, and says nothing else.
        assert [op["kind"] for op in view.desk["operations"]] == ["ledger_local_only"]
        assert view.ledger["shared"] is False


# --- B: deterministic mirror drift -> Class A landing branch -----------------------


def mergeIntoIntegration(repo: Path, branch: str) -> str:
    """Play the forge: merge the landing branch into the integration branch, update the checkout."""

    git(repo, "fetch", "-q", "origin")
    git(repo, "checkout", "-q", "-B", INTEGRATION, f"origin/{INTEGRATION}")
    git(repo, "merge", "-q", "--no-ff", "-m", "merge steward branch", f"origin/{branch}")
    git(repo, "push", "-q", "origin", INTEGRATION)
    return git(repo, "rev-parse", "HEAD")


@pytest.mark.parametrize("transport", ["file", "git"])
def test_scenario_b_mirror_drift_lands_on_a_branch_and_resolves_after_merge(
    tmp_path: Path, transport: str
) -> None:
    repo, bare = makeFixture(tmp_path, mirrorDrift=True)
    store = fileStore(tmp_path) if transport == "file" else GitRefLedgerStore(repo, "origin")
    runner = makeRunner(repo, store, [AgentSkillMirrorSensor()])

    view = runner.start("full")

    assert view.status == "awaiting-action", view.to_dict()
    branches = stewardRefs(bare)
    assert len(branches) == 1 and branches[0].startswith("steward/a/agent-skill-mirror-drift-")
    assert [a["type"] for a in view.actions] == ["forge.open_pr"]
    params = view.actions[0]["params"]
    assert params["head"] == branches[0] and params["base"] == INTEGRATION
    assert params["ifExists"] == "record-existing" and params["idempotencyKey"] == branches[0]
    assert (repo / params["bodyPath"]).is_file()
    # The landing branch is based on the integration branch and touches only the mirror.
    changed = git(bare, "diff", "--name-only", f"{INTEGRATION}..{branches[0]}").splitlines()
    assert changed == [".claude/skills/x/SKILL.md"]
    # The caller's checkout was never touched.
    assert (repo / ".claude/skills/x/SKILL.md").read_text() == "# x stale\n"

    doc = ledgerOf(store)
    (item,) = doc["work"].values()
    assert item["state"] == "proposed" and item["branch"] == branches[0] and item["authority"] == "A"
    assert doc["runs"][view.runId]["branches"][0]["pushed"] is True

    # The driver opens the PR and reports it; the run completes without opening a second branch.
    recorded = runner.record(view.runId, view.actions[0]["stepId"],
                             {"pullRequest": {"number": 7, "url": "https://example.invalid/pr/7"}})
    assert recorded.actions == []
    resumed = runner.resume(view.runId)
    assert resumed.status == "completed", resumed.to_dict()
    assert stewardRefs(bare) == branches
    item = next(iter(ledgerOf(store)["work"].values()))
    assert item["state"] == "proposed", "an unmerged proposal is never claimed resolved"
    assert any("awaiting merge" in n["note"] for n in item["notes"])
    assert item["pullRequest"]["number"] == 7

    # Merge into the integration branch; a verify-mode run re-observes on that head.
    mergedSha = mergeIntoIntegration(repo, branches[0])
    again = runner.start("verify")
    assert again.status == "completed", again.to_dict()
    item = next(iter(ledgerOf(store)["work"].values()))
    assert item["state"] == "resolved"
    assert [h["to"] for h in item["history"]][-1] == "resolved"
    assert again.summary["reobserve"]["resolvedWork"] == [item["debtId"]]
    assert git(repo, "rev-parse", "HEAD") == mergedSha


# --- C: Class B routed debt, independent verification, integration ---------------------


def hygieneRunner(tmp_path: Path, subjects: list[str] | None = None, **overrides: Any):
    repo, bare = makeFixture(tmp_path)
    sensor = StubSensor(HYGIENE, "repository_hygiene", subjects if subjects is not None else ["leaked-artifact"])
    store = overrides.pop("store", None) or fileStore(tmp_path)
    return repo, bare, sensor, store, makeRunner(repo, store, [sensor], **overrides)


def test_scenario_c_class_b_build_verify_integrate_land_and_resolve(tmp_path: Path) -> None:
    repo, bare, sensor, store, runner = hygieneRunner(tmp_path)

    view = runner.start("full")

    # 1. one agent.build, nothing else, and the run waits for it.
    assert view.status == "awaiting-action", view.to_dict()
    assert actionTypes(view) == ["agent.build"]
    build = view.actions[0]
    params = build["params"]
    assert params["allowedModels"] == ["haiku", "sonnet"]
    assert params["effortRequired"] is True and params["base"] == INTEGRATION
    assert params["branch"].startswith("steward/b/repository-hygiene-")
    assert set(params["outputs"]) == {"diffPath", "proofPath"}
    prompt = (repo / params["promptPath"]).read_text()
    assert "Tree Keeper" in prompt
    # The builder is told what to hand back and where, in the shape verification reads.
    handoff = prompt.split("## Steward hand-off", 1)[1]
    assert "steward-proof-transcript-v1" in handoff and "contractIndex" in handoff
    assert params["outputs"]["diffPath"] in handoff and params["outputs"]["proofPath"] in handoff
    assert f"`{params['branch']}`, created from `{INTEGRATION}`" in handoff
    assert "Independent review is not yours to obtain" in handoff
    doc = ledgerOf(store)
    debtId = params["debtId"]
    assert doc["work"][debtId]["state"] == "building"
    lane = load_lane(doc["lane"], StewardPolicy.load(repo).lane)
    assert lane.by_id(debtId).state == "dispatched" and lane.by_id(debtId).attempts == 1
    assert stewardRefs(bare) == [], "Class B never creates a landing branch"

    # 2. a second invocation sees the holder and does nothing.
    other = makeRunner(repo, store, [sensor]).start("full")
    assert other.status == "observing-existing" and other.holder == view.runId
    assert sensor.scans == 2  # the first run's observe and the dispatch's own scan; none for `other`

    # 3. the builder's outcome is validated, then recorded.
    diff, proof = writeBuildArtifacts(repo)
    with pytest.raises(RecordRefused, match="diffPath"):
        runner.record(view.runId, build["stepId"], {**BUILD})
    with pytest.raises(RecordRefused, match="effort"):
        runner.record(view.runId, build["stepId"], {**BUILD, "effort": "default", "diffPath": str(diff), "proofPath": str(proof)})
    with pytest.raises(RecordRefused, match="not permitted"):
        runner.record(view.runId, build["stepId"], {**BUILD, "model": "opus", "diffPath": str(diff), "proofPath": str(proof)})
    built = {**BUILD, "diffPath": str(diff), "proofPath": str(proof)}
    runner.record(view.runId, build["stepId"], built)
    again = runner.record(view.runId, build["stepId"], built)  # an identical retry is harmless
    assert again.actions == []
    with pytest.raises(RecordRefused, match="already"):
        runner.record(view.runId, build["stepId"], {**built, "summary": "something else"})

    # 4. resume: mechanical verification passes, so exactly one agent.verify is emitted.
    verifying = runner.resume(view.runId)
    assert verifying.status == "awaiting-action", verifying.to_dict()
    assert actionTypes(verifying) == ["agent.verify"]
    verify = verifying.actions[0]
    assert verify["params"]["forbiddenAgentIds"] == ["builder-1"]
    assert verify["params"]["allowedModels"] == ["sonnet"]
    assert "scripts/fix.py" in (repo / verify["params"]["verifierPromptPath"]).read_text()

    # 5. the same agent may not judge its own work; a different one may.
    with pytest.raises(RecordRefused, match="independent"):
        runner.record(view.runId, verify["stepId"], {**VERIFY, "agentId": "builder-1"})
    with pytest.raises(RecordRefused, match="not permitted"):
        runner.record(view.runId, verify["stepId"], {**VERIFY, "model": "haiku"})
    runner.record(view.runId, verify["stepId"], VERIFY)
    doc = ledgerOf(store)
    assert doc["work"][debtId]["state"] == "verified"
    entry = load_lane(doc["lane"], StewardPolicy.load(repo).lane).by_id(debtId)
    # Verified is not integrated: the lane slot stays occupied until the lead has decided.
    assert entry.state == "dispatched" and entry.attempts == 1

    # 6. the lead integrates; the work lands.
    integrating = runner.resume(view.runId)
    assert actionTypes(integrating) == ["lead.integrate"], integrating.to_dict()
    integrate = integrating.actions[0]
    assert integrate["params"]["branch"] == params["branch"]
    with pytest.raises(RecordRefused, match="by"):
        runner.record(view.runId, integrate["stepId"], {"decision": "integrate"})
    runner.record(view.runId, integrate["stepId"], {
        "decision": "integrate", "by": "lead", "pullRequest": {"number": 9}, "mergedSha": "a" * 40})
    done = runner.resume(view.runId)
    assert done.status == "completed", done.to_dict()
    doc = ledgerOf(store)
    assert doc["work"][debtId]["state"] == "landed"
    entry = load_lane(doc["lane"], StewardPolicy.load(repo).lane).by_id(debtId)
    assert entry.state == "closed" and entry.last_verdict == "accept"
    assert "lead" in entry.history[-1].reason and "verifier-1" in entry.history[-1].reason
    run = doc["runs"][view.runId]
    assert run["modelIds"] == ["haiku", "sonnet"]
    assert run["thinkingEfforts"] == ["high"]
    assert run["tokensIn"] == 1200 and run["tokensOut"] == 300 and run["costUsd"] == 0.01
    assert [a["role"] for a in run["agentAssignments"]] == ["builder", "verifier"]
    assert run["decisions"][-1]["by"] == "lead"
    assert doc["leases"] == {}

    # 7. landed is not resolved: the debt is still observed, so the work says why.
    still = runner.start("verify")
    assert still.status == "completed"
    item = ledgerOf(store)["work"][debtId]
    assert item["state"] == "landed"
    assert any("does not contain it yet" in n["note"] for n in item["notes"])

    # 8. only after the condition is observed healthy does it become resolved.
    sensor.heal("leaked-artifact")
    final = runner.start("verify")
    assert final.status == "completed"
    assert ledgerOf(store)["work"][debtId]["state"] == "resolved"


def test_scenario_c_mechanical_reject_returns_the_debt_and_attempts_are_bounded(tmp_path: Path) -> None:
    repo, _bare, sensor, store, runner = hygieneRunner(tmp_path)
    policy = StewardPolicy.load(repo)
    view = runner.start("full")
    build = view.actions[0]
    debtId = build["params"]["debtId"]
    diff, proof = writeBuildArtifacts(repo, proofExit=1)  # failing proof
    runner.record(view.runId, build["stepId"], {**BUILD, "diffPath": str(diff), "proofPath": str(proof)})

    result = runner.resume(view.runId)

    doc = ledgerOf(store)
    assert result.status == "completed", result.to_dict()
    assert result.actions == [], "a mechanical reject spends no verifier"
    assert doc["work"][debtId]["state"] == "blocked"
    assert any("proof commands exited non-zero" in h["reason"] for h in doc["work"][debtId]["history"])
    entry = load_lane(doc["lane"], policy.lane).by_id(debtId)
    assert entry.last_verdict == "reject" and entry.attempts == 1
    assert entry.state in {"queued", "escalated"}
    assert not (doc["runs"][view.runId]["actions"][0]["status"] == "pending")


# --- D: Class C goes to the desk; unrelated A and B work still proceeds ----------------


def test_scenario_d_class_c_debt_reaches_the_desk_and_executes_nothing(tmp_path: Path) -> None:
    repo, bare = makeFixture(tmp_path, mirrorDrift=True)
    mapping = StubSensor("discovery-generic-mapping", "generic_mapping", ["candidate-1"],
                         extra={"decisionTarget": "alpha-skill"})
    hygiene = StubSensor(HYGIENE, "repository_hygiene", ["leaked-artifact"])
    store = fileStore(tmp_path)
    runner = makeRunner(repo, store, [AgentSkillMirrorSensor(), mapping, hygiene])

    view = runner.start("full")

    assert view.status == "awaiting-action", view.to_dict()
    assert sorted(actionTypes(view)) == ["agent.build", "forge.open_pr"]
    triage = view.summary["triage"]
    assert triage["counts"] == {"A": 1, "B": 1, "B-report-only": 0, "C": 1}
    (cDebt,) = triage["classC"]
    doc = ledgerOf(store)
    assert cDebt not in doc["work"], "nothing is created, dispatched or landed for a Class C debt"
    assert load_lane(doc["lane"], StewardPolicy.load(repo).lane).by_id(cDebt) is None
    assert len(stewardRefs(bare)) == 1, "only the unrelated mirror drift got a branch"
    # The debt is on the desk as a decision for a person, never as an operation.
    desk = view.desk
    assert desk is not None and desk["quiet"] is False
    assert any(cDebt in d["debtIds"] for d in desk["decisions"]), desk["decisions"]
    assert all(cDebt not in op["subject"] for op in desk["operations"])
    assert not any(a["debtId"] == cDebt for a in doc["runs"][view.runId]["actions"])


# --- E: a broken sensor ------------------------------------------------------------------


def test_scenario_e_broken_sensor_reports_unknown_and_refuses_to_act(tmp_path: Path) -> None:
    repo, bare = makeFixture(tmp_path, mirrorDrift=True)
    hygiene = StubSensor(HYGIENE, "repository_hygiene", ["leaked-artifact"])
    broken = StubSensor("flaky-surface", "registry_integrity_failed")
    store = fileStore(tmp_path)
    runner = makeRunner(repo, store, [AgentSkillMirrorSensor(), hygiene, broken])
    first = runner.start("observe")  # establishes pre-existing open debt
    assert first.status == "completed" and first.coverageUnknown == []

    broken.raises = SensorUnavailable("surface cannot be read completely")
    view = runner.start("full")

    assert view.status == "blocked" and view.exitCode == 3, view.to_dict()
    assert view.coverageUnknown == ["flaky-surface"]
    assert view.actions == []
    assert view.summary["class_a"]["status"] == "blocked"
    assert "coverage is unknown" in view.summary["class_a"]["reason"]
    assert view.summary["class_b"]["status"] == "blocked"
    doc = ledgerOf(store)
    assert doc["work"] == {}
    assert stewardRefs(bare) == []
    assert doc["lane"] is None or load_lane(doc["lane"], StewardPolicy.load(repo).lane).in_flight == ()
    assert [op["kind"] for op in view.desk["operations"]].count("coverage_unknown") == 1
    assert doc["leases"] == {}
    # The pre-existing debt is retained, still open, not silently resolved.
    state = json.loads((repo / ".gaia/steward/debt.json").read_text())
    openKinds = sorted(d["kind"] for d in state["debts"] if d["status"] == "open")
    assert "agent_skill_mirror_drift" in openKinds and "repository_hygiene" in openKinds


# --- F: crash and resume --------------------------------------------------------------------


class Crash(BaseException):
    """Stands in for a killed process; not an Exception, so nothing swallows it."""


def crashAt(monkeypatch: pytest.MonkeyPatch, point: str) -> None:
    def hook(name: str) -> None:
        if name == point:
            raise Crash(name)

    monkeypatch.setattr(fullrun, "_checkpoint", hook)


def uncrash(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fullrun, "_checkpoint", lambda name: None)


def onlyRunId(store: Any) -> str:
    (runId,) = ledgerOf(store)["runs"]
    return runId


def openPrActions(store: Any) -> list[dict[str, Any]]:
    return [a for run in ledgerOf(store)["runs"].values() for a in run["actions"] if a["type"] == "forge.open_pr"]


@pytest.mark.parametrize("point", ["class_a.intent", "class_a.executed"])
@pytest.mark.parametrize("transport", ["file", "git"])
def test_scenario_f_class_a_crash_resumes_with_one_branch_and_one_pr_action(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, point: str, transport: str
) -> None:
    repo, bare = makeFixture(tmp_path, mirrorDrift=True)
    store = fileStore(tmp_path) if transport == "file" else GitRefLedgerStore(repo, "origin")
    crashAt(monkeypatch, point)
    with pytest.raises(Crash):
        makeRunner(repo, store, [AgentSkillMirrorSensor()]).start("full")
    runId = onlyRunId(store)
    run = ledgerOf(store)["runs"][runId]
    assert [s["status"] for s in run["steps"] if s["kind"] == "landing"] == ["intent"], "intent was recorded first"
    assert len(stewardRefs(bare)) == (0 if point == "class_a.intent" else 1)
    assert openPrActions(store) == []

    uncrash(monkeypatch)
    view = makeRunner(repo, store, [AgentSkillMirrorSensor()]).resume(runId)  # a brand new process

    assert view.status == "awaiting-action", view.to_dict()
    assert len(stewardRefs(bare)) == 1, "the idempotent landing never makes a second branch"
    assert len(openPrActions(store)) == 1 and actionTypes(view) == ["forge.open_pr"]
    (item,) = ledgerOf(store)["work"].values()
    assert item["state"] == "proposed" and item["branch"] == stewardRefs(bare)[0]
    # A third pass changes nothing.
    again = makeRunner(repo, store, [AgentSkillMirrorSensor()]).resume(runId)
    assert len(stewardRefs(bare)) == 1 and len(openPrActions(store)) == 1
    assert actionTypes(again) == ["forge.open_pr"]


@pytest.mark.parametrize("point", ["class_b.rendered", "class_b.dispatched"])
def test_scenario_f_class_b_crash_resumes_with_exactly_one_dispatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, point: str
) -> None:
    repo, _bare, sensor, store, _runner = hygieneRunner(tmp_path)
    crashAt(monkeypatch, point)
    with pytest.raises(Crash):
        makeRunner(repo, store, [sensor]).start("full")
    runId = onlyRunId(store)

    uncrash(monkeypatch)
    view = makeRunner(repo, store, [sensor]).resume(runId)

    assert view.status == "awaiting-action", view.to_dict()
    assert actionTypes(view) == ["agent.build"]
    doc = ledgerOf(store)
    builds = [a for a in doc["runs"][runId]["actions"] if a["type"] == "agent.build"]
    assert len(builds) == 1
    lane = load_lane(doc["lane"], StewardPolicy.load(repo).lane)
    (entry,) = lane.entries
    assert entry.state == "dispatched" and entry.attempts == 1 and len(lane.in_flight) == 1
    # Resuming again cannot dispatch a second time.
    makeRunner(repo, store, [sensor]).resume(runId)
    lane = load_lane(ledgerOf(store)["lane"], StewardPolicy.load(repo).lane)
    assert lane.entries[0].attempts == 1


def test_scenario_f_expired_lease_is_abandoned_and_its_work_adopted_not_duplicated(tmp_path: Path) -> None:
    clock = Clock()
    repo, _bare, sensor, store, _ = hygieneRunner(tmp_path)
    first = makeRunner(repo, store, [sensor], clock=clock).start("full")
    assert actionTypes(first) == ["agent.build"]
    debtId = first.actions[0]["params"]["debtId"]
    assert makeRunner(repo, store, [sensor], clock=clock).start("full").status == "observing-existing"

    clock.advance(hours=2)  # the lease (1800s) expires with the build still outstanding
    second = makeRunner(repo, store, [sensor], clock=clock).start("full")

    doc = ledgerOf(store)
    assert doc["runs"][first.runId]["status"] == "abandoned"
    assert [w["debtId"] for w in second.unresolvedWork] == [debtId]
    assert second.unresolvedWork[0]["state"] == "building"
    assert len(doc["work"]) == 1
    lane = load_lane(doc["lane"], StewardPolicy.load(repo).lane)
    assert lane.by_id(debtId).attempts == 1, "the adopted dispatch is not dispatched again"
    # The adopted build is re-offered under the new run, against the same dispatch.
    assert actionTypes(second) == ["agent.build"]
    assert second.actions[0]["params"]["dispatchId"] == first.actions[0]["params"]["dispatchId"]
    assert second.status == "awaiting-action"


# --- G: two runners, one lease -------------------------------------------------------------------


def test_scenario_g_concurrent_runners_exactly_one_holds_the_run_lease(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, bare = makeFixture(tmp_path)
    clone = cloneOf(bare, tmp_path / "clone2")
    sensors = {"a": StubSensor(HYGIENE, "repository_hygiene"), "b": StubSensor(HYGIENE, "repository_hygiene")}
    runners = {
        "a": makeRunner(repo, GitRefLedgerStore(repo, "origin"), [sensors["a"]], trigger="manual"),
        "b": makeRunner(clone, GitRefLedgerStore(clone, "origin"), [sensors["b"]], trigger="manual"),
    }
    barrier = threading.Barrier(2)
    release, results, errors = threading.Event(), {}, []

    def hook(name: str) -> None:  # the winner parks here, still holding the lease
        if name == "phase:reconcile":
            assert release.wait(60)

    monkeypatch.setattr(fullrun, "_checkpoint", hook)

    def go(name: str) -> None:
        try:
            barrier.wait(30)
            results[name] = runners[name].start("observe")
        except BaseException as exc:  # noqa: BLE001 - surface thread failures in the test
            errors.append(exc)
            results.setdefault(name, None)

    threads = [threading.Thread(target=go, args=(n,)) for n in runners]
    for thread in threads:
        thread.start()
    deadline = 60.0
    while len(results) < 1 and deadline > 0:  # the loser returns while the winner is parked
        threading.Event().wait(0.05)
        deadline -= 0.05
    loserName = next(iter(results))
    release.set()
    for thread in threads:
        thread.join(60)
    assert not errors, errors
    winnerName = "a" if loserName == "b" else "b"
    loser, winner = results[loserName], results[winnerName]

    assert loser.status == "observing-existing" and winner.status == "completed"
    assert loser.holder == winner.runId and loser.runId is None
    assert loser.holderPhase in {"reconcile", "observe"}
    document, _ = GitRefLedgerStore(repo, "origin").load()
    assert list(document["runs"]) == [winner.runId], "the loser created no run"
    assert document["work"] == {} and document["leases"] == {}
    assert sensors[loserName].scans == 0, "the loser did no scanning"
    assert sensors[winnerName].scans == 1


# --- H: historical regression #2114 ------------------------------------------------------------------


def writeInheritedEvidenceRegistry(root: Path) -> None:
    """A named 3-star skill whose grade is B only through its generic parent's evidence."""

    write(root / "registry/nodes/basic/gen-skill.json", json.dumps({
        "id": "gen-skill", "type": "basic", "prerequisites": [], "derivatives": [],
        "evidence": [
            {"type": "github-stars-own", "grade": "A", "source": "https://example.invalid/gen/stargazers", "stars": 200},
            {"type": "repo-own", "grade": "B", "source": "https://example.invalid/gen", "commits": 20, "contributors": 3},
        ],
    }))
    frontmatter = {
        "id": "acme/thing", "status": "named", "genericSkillRef": "gen-skill", "level": "3★",
        "evidence": [{"type": "repo-own", "grade": "C", "source": "https://example.invalid/thing/blob/main/SKILL.md",
                      "commits": 3, "contributors": 1}],
    }
    write(root / "registry/named/acme/thing.md", "---\n" + yaml.safe_dump(frontmatter, sort_keys=False) + "---\n")



def sensorStillUsesEmptyContext() -> bool:
    """True while TrustCalibrationDriftSensor scores against an empty context map (#2114)."""

    with tempfile.TemporaryDirectory() as scratch:
        root = make_repo(Path(scratch) / "probe", {"README.md": "probe\n"})  # sensors read git's inventory
        writeInheritedEvidenceRegistry(root)
        commitAll(root, "registry with inherited evidence")
        return bool(TrustCalibrationDriftSensor().scan(root, "2026-10-20T00:00:00Z"))


@pytest.mark.xfail(
    strict=True,
    condition=sensorStillUsesEmptyContext(),
    reason="#2114: TrustCalibrationDriftSensor still scores with an empty context map; fixed by "
           "feat/steward-full-correctness. The probe flips this test to a normal one once that merges.",
)
def test_scenario_h_inherited_evidence_keeps_a_correct_stored_rank_unflagged(tmp_path: Path) -> None:
    repo, _bare = makeFixture(tmp_path)
    writeInheritedEvidenceRegistry(repo)
    commitAll(repo, "registry with inherited evidence")
    store = fileStore(tmp_path)
    runner = makeRunner(repo, store, [TrustCalibrationDriftSensor()])

    view = runner.start("full")

    assert view.status == "completed", view.to_dict()
    assert view.actions == []
    doc = ledgerOf(store)
    assert [w for w in doc["work"].values() if w["kind"] == "trust_calibration_drift"] == []
    state = json.loads((repo / ".gaia/steward/debt.json").read_text())
    assert [d for d in state["debts"] if d["kind"] == "trust_calibration_drift"] == []
    assert view.summary["triage"]["counts"]["B"] == 0


# --- C (continued): the shared lane's caps hold across runs -----------------------------------


def test_scenario_c_cooldown_then_attempt_ceiling_escalate_to_the_desk(tmp_path: Path) -> None:
    clock = Clock()
    repo, _bare, sensor, store, _ = hygieneRunner(tmp_path)
    policy = StewardPolicy.load(repo)
    attempts = []

    def failingAttempt() -> Any:
        runner = makeRunner(repo, store, [sensor], clock=clock)
        view = runner.start("full")
        attempts.append(view)
        build = view.actions[0]
        diff, proof = writeBuildArtifacts(repo, f"try{len(attempts)}", proofExit=1)
        runner.record(view.runId, build["stepId"], {**BUILD, "agentId": f"builder-{len(attempts)}",
                                                    "diffPath": str(diff), "proofPath": str(proof)})
        return runner.resume(view.runId)

    first = failingAttempt()
    debtId = attempts[0].actions[0]["params"]["debtId"]
    assert first.status == "completed"

    # Inside the cooldown the lane hands out nothing, and says why.
    clock.advance(minutes=5)
    cooling = makeRunner(repo, store, [sensor], clock=clock).start("full")
    assert cooling.status == "completed" and cooling.actions == []
    assert "cooldown" in cooling.summary["class_b"]["reason"]

    # After it, the second (last permitted) attempt is dispatched against the SAME shared lane...
    clock.advance(hours=2)
    second = failingAttempt()
    entry = load_lane(ledgerOf(store)["lane"], policy.lane).by_id(debtId)
    assert entry.attempts == 2 and entry.state == "escalated"
    assert ledgerOf(store)["work"][debtId]["state"] == "escalated"
    # ...and its rejection leaves the agent lane for the founder's desk.
    assert second.desk is not None
    assert any(d["source"] == "escalated-lane" and debtId in d["debtIds"] for d in second.desk["decisions"])

    # Escalated work is never re-dispatched.
    clock.advance(hours=5)
    after = makeRunner(repo, store, [sensor], clock=clock).start("full")
    assert after.actions == [] and ledgerOf(store)["work"][debtId]["state"] == "escalated"


def test_scenario_c_no_change_build_is_confirmed_by_an_independent_verifier(tmp_path: Path) -> None:
    repo, _bare, sensor, store, runner = hygieneRunner(tmp_path)
    view = runner.start("full")
    build = view.actions[0]
    debtId = build["params"]["debtId"]
    runner.record(view.runId, build["stepId"], {**BUILD, "noChange": True, "summary": "BUILDER-NARRATIVE-ZZ"})

    verifying = runner.resume(view.runId)

    assert actionTypes(verifying) == ["agent.verify"]
    prompt = (repo / verifying.actions[0]["params"]["verifierPromptPath"]).read_text()
    assert "BUILDER-NARRATIVE-ZZ" not in prompt, "the verifier never sees the builder's narrative"
    assert "leaked-artifact" in prompt, "but it does see the sensor's finding"
    assert "no-change claim" in prompt
    runner.record(view.runId, verifying.actions[0]["stepId"], VERIFY)
    done = runner.resume(view.runId)
    assert done.status == "completed" and done.actions == []
    assert ledgerOf(store)["work"][debtId]["state"] == "no_change"

    # A no_change item is held out of re-dispatch even while the sensor keeps reporting it,
    # and resolves only once the sensor reports the condition healthy.
    held = runner.start("full")
    assert held.status == "completed", held.to_dict()
    assert held.actions == []
    sensor.heal("leaked-artifact")
    runner.start("verify")
    assert ledgerOf(store)["work"][debtId]["state"] == "resolved"


def test_scenario_c_lead_hold_keeps_work_verified_and_reject_blocks_it(tmp_path: Path) -> None:
    repo, _bare, sensor, store, runner = hygieneRunner(tmp_path)
    view = runner.start("full")
    build = view.actions[0]
    debtId = build["params"]["debtId"]
    diff, proof = writeBuildArtifacts(repo)
    runner.record(view.runId, build["stepId"], {**BUILD, "diffPath": str(diff), "proofPath": str(proof)})
    verifying = runner.resume(view.runId)
    runner.record(view.runId, verifying.actions[0]["stepId"], VERIFY)
    integrating = runner.resume(view.runId)
    step = integrating.actions[0]["stepId"]

    runner.record(view.runId, step, {"decision": "hold", "by": "lead"})
    held = runner.resume(view.runId)
    assert held.status == "completed" and held.actions == []
    assert ledgerOf(store)["work"][debtId]["state"] == "verified"

    # The next run re-offers the integration decision rather than forgetting verified work.
    again = runner.start("verify")
    assert actionTypes(again) == ["lead.integrate"]
    runner.record(again.runId, again.actions[0]["stepId"], {"decision": "reject", "by": "lead"})
    assert ledgerOf(store)["work"][debtId]["state"] == "blocked"


def test_scenario_c_verdicts_are_refused_for_the_wrong_step(tmp_path: Path) -> None:
    repo, _bare, _sensor, _store, runner = hygieneRunner(tmp_path)
    view = runner.start("full")
    build = view.actions[0]
    with pytest.raises(RecordRefused, match="no action"):
        runner.record(view.runId, "verify:nothing", VERIFY)
    # A verify outcome cannot be recorded against a build step's id.
    with pytest.raises(RecordRefused):
        runner.record(view.runId, build["stepId"], VERIFY)


# =====================================================================================
# Review fixes D1-D11, and the mutation-killing tests the review asked for
# =====================================================================================


def builds(doc: dict[str, Any]) -> list[dict[str, Any]]:
    """Every live (not superseded) agent.build action across all runs."""

    return [a for run in doc["runs"].values() for a in run["actions"]
            if a["type"] == "agent.build" and a["status"] != "superseded"]


def toPendingVerify(runner: Any, view: Any, repo: Path, name: str = "pv") -> Any:
    """Record a good build for the pending agent.build and resume to the agent.verify."""

    diff, proof = writeBuildArtifacts(repo, name)
    runner.record(view.runId, view.actions[0]["stepId"], {**BUILD, "diffPath": str(diff), "proofPath": str(proof)})
    return runner.resume(view.runId)


# --- D1: Class B has the same target floor as landing ---------------------------------


@pytest.mark.parametrize("target", [None, "main", "master", "no-such-branch", "origin/main"])
def test_scenario_d1_class_b_refuses_a_target_that_landing_would_refuse(tmp_path: Path, target: str | None) -> None:
    repo, _bare, _sensor, store, runner = hygieneRunner(tmp_path, integration_branch=target)

    view = runner.start("full")

    assert view.status == "completed" and view.actions == [], view.to_dict()
    assert view.summary["class_b"]["status"] == "blocked" and view.summary["class_b"]["floor"] is False
    doc = ledgerOf(store)
    assert doc["work"] == {}, "nothing was dispatched"
    assert doc["lane"] is None or not [e for e in doc["lane"]["entries"] if e["state"] == "dispatched"]
    decisions = doc["runs"][view.runId]["decisions"]
    assert any(d["type"] == "landing-target" for d in decisions), decisions
    assert any(d["decisionId"] == "landing-target-not-configured" for d in view.desk["decisions"])


def test_scenario_d1_verify_mode_emits_nothing_without_a_valid_target(tmp_path: Path) -> None:
    clock = Clock()
    repo, _bare, sensor, store, runner = hygieneRunner(tmp_path, clock=clock)
    view = runner.start("full")
    verifying = toPendingVerify(runner, view, repo)
    assert actionTypes(verifying) == ["agent.verify"]

    clock.advance(hours=2)
    refused = makeRunner(repo, store, [sensor], clock=clock, integration_branch="main").start("verify")

    assert refused.actions == [], refused.to_dict()
    assert refused.summary["verify"]["status"] == "blocked"
    assert next(iter(ledgerOf(store)["work"].values()))["state"] == "building"


def test_scenario_d1_a_valid_target_passes_the_same_floor(tmp_path: Path) -> None:
    repo, _bare, _sensor, store, runner = hygieneRunner(tmp_path)
    view = runner.start("full")
    assert actionTypes(view) == ["agent.build"]
    assert ledgerOf(store)["runs"][view.runId]["floor"] == {"ok": True, "branch": INTEGRATION, "reason": None}


# --- D2/D5: lead rejection counts, and verified work occupies a slot ---------------------


def test_scenario_d2_lead_rejection_cannot_bypass_cooldown_or_the_attempt_ceiling(tmp_path: Path) -> None:
    clock = Clock()
    repo, _bare, sensor, store, _ = hygieneRunner(tmp_path, ["only"], clock=clock)
    policy = StewardPolicy.load(repo)
    views = []
    for cycle in range(4):
        runner = makeRunner(repo, store, [sensor], clock=clock)
        view = runner.start("full")
        if view.actions:
            view = drive(runner, view, repo, integrate="reject", builderId=f"b{cycle}", verifierId=f"v{cycle}")
        views.append(view)
        clock.advance(seconds=1)  # not even close to the 3600s cooldown...
        if cycle == 1:
            clock.advance(hours=2)  # ...until after the second cycle

    doc = ledgerOf(store)
    assert len(builds(doc)) == 2, "two attempts, never more"
    assert "cooldown" in views[1].summary["class_b"]["reason"], views[1].summary["class_b"]
    (debtId,) = doc["work"]
    entry = load_lane(doc["lane"], policy.lane).by_id(debtId)
    assert entry.attempts == 2 and entry.state == "escalated"
    assert doc["work"][debtId]["state"] == "escalated"
    assert views[3].actions == [] and views[3].summary["class_b"]["dispatched"] is None
    assert any(d["source"] == "escalated-lane" and debtId in d["debtIds"] for d in views[2].desk["decisions"])


def test_scenario_d2_the_first_lead_rejection_requeues_with_a_cooldown(tmp_path: Path) -> None:
    clock = Clock()
    repo, _bare, sensor, store, runner = hygieneRunner(tmp_path, ["only"], clock=clock)
    view = drive(runner, runner.start("full"), repo, integrate="reject")
    doc = ledgerOf(store)
    (debtId,) = doc["work"]
    entry = load_lane(doc["lane"], StewardPolicy.load(repo).lane).by_id(debtId)
    assert doc["work"][debtId]["state"] == "blocked"
    assert (entry.state, entry.attempts, entry.last_verdict) == ("queued", 1, "reject")
    assert view.status == "completed"


def test_scenario_d5_verified_but_unintegrated_work_holds_the_only_slot(tmp_path: Path) -> None:
    repo, _bare, sensor, store, runner = hygieneRunner(tmp_path, ["a", "b"])
    pinMaxInFlight(repo, 1)  # this scenario is about the single slot; the shipped lane has two
    first = drive(runner, runner.start("full"), repo, integrate="hold")
    assert first.status == "completed"
    (verified,) = [w for w in ledgerOf(store)["work"].values() if w["state"] == "verified"]

    second_runner = makeRunner(repo, store, [sensor])
    second = second_runner.start("full")
    assert "agent.build" not in actionTypes(second), second.to_dict()
    assert "maxInFlight" in second.summary["class_b"]["reason"]
    drive(second_runner, second, repo, integrate="hold")  # settle: the lead holds again

    # Even with the shared lane wiped, the work items themselves still count.
    editLedger(store, lambda doc: doc.update(lane=None))
    third = makeRunner(repo, store, [sensor]).start("full")
    assert "agent.build" not in actionTypes(third)
    assert "not integrated" in third.summary["class_b"]["reason"]
    assert ledgerOf(store)["work"][verified["debtId"]]["state"] == "verified"


def test_the_shipped_lane_keeps_two_debts_in_flight_across_runs_and_refuses_the_third(tmp_path: Path) -> None:
    """Concurrency 2, end to end: each run still dispatches at most one build (maxDispatchesPerRun 1)."""

    repo, _bare, sensor, store, runner = hygieneRunner(tmp_path, ["a", "b", "c"])
    assert StewardPolicy.load(repo).lane.max_in_flight == 2, "this test is about the shipped two-slot lane"

    first_view = runner.start("full")
    assert actionTypes(first_view) == ["agent.build"], first_view.to_dict()
    first_debt = first_view.actions[0]["params"]["debtId"]
    drive(runner, first_view, repo, integrate="hold")  # verified, held by the lead: still in flight

    second_runner = makeRunner(repo, store, [sensor])
    second_view = second_runner.start("full")
    assert actionTypes(second_view) == ["agent.build"], "the second slot is free, so the lane hands out a second debt"
    second_debt = second_view.actions[0]["params"]["debtId"]
    assert second_debt != first_debt
    drive(second_runner, second_view, repo, integrate="hold")

    doc = ledgerOf(store)
    for run_id in (first_view.runId, second_view.runId):
        runBuilds = [a for a in doc["runs"][run_id]["actions"] if a["type"] == "agent.build"]
        assert len(runBuilds) == 1, "maxDispatchesPerRun is 1 for each run"
    lane = load_lane(doc["lane"], StewardPolicy.load(repo).lane)
    assert {first_debt, second_debt} == {e.debt_id for e in lane.in_flight}

    third_view = makeRunner(repo, store, [sensor]).start("full")
    assert "agent.build" not in actionTypes(third_view), third_view.to_dict()
    assert "maxInFlight" in third_view.summary["class_b"]["reason"]
    assert len(builds(ledgerOf(store))) == 2, "the refused third debt was never dispatched"


# --- D3: a deferred verification is never "nothing further" and cannot deadlock the lane ------


def test_scenario_d3_deferred_verification_is_awaiting_action_then_escalates_after_24h(tmp_path: Path) -> None:
    clock = Clock()
    repo, _bare, sensor, store, runner = hygieneRunner(tmp_path, ["a", "b"], clock=clock)
    pinMaxInFlight(repo, 1)  # one slot: the second debt must wait behind the stuck dispatch
    view = runner.start("full")
    first = view.actions[0]["params"]["debtId"]
    diff, proof = writeBuildArtifacts(repo, "d1")
    runner.record(view.runId, view.actions[0]["stepId"], {**BUILD, "diffPath": str(diff), "proofPath": str(proof)})
    diff.unlink()  # the builder's artifact is gone

    deferred = runner.resume(view.runId)

    assert deferred.status == "awaiting-action" and deferred.exitCode == 0
    assert "nothing further" not in deferred.nextAction and "deferred" in deferred.nextAction
    assert deferred.actions == [], "no driver action exists for it, yet the run is not finished"
    assert any(op["kind"] == "failed_dispatch" and first in op["subject"] for op in deferred.desk["operations"])
    assert ledgerOf(store)["leases"] == {}, "the lease is not held for work nobody can finish"

    for _ in range(2):  # the same state keeps being reported, never silently completed
        clock.advance(hours=3)
        again = makeRunner(repo, store, [sensor], clock=clock).start("full")
        assert again.status == "awaiting-action", again.to_dict()
        assert "agent.build" not in actionTypes(again) and "maxInFlight" in again.summary["class_b"]["reason"]

    clock.advance(hours=20)  # more than 24h since the dispatch
    freed = makeRunner(repo, store, [sensor], clock=clock).start("full")

    doc = ledgerOf(store)
    assert doc["work"][first]["state"] == "escalated"
    assert "24h" in doc["work"][first]["history"][-1]["reason"]
    entry = load_lane(doc["lane"], StewardPolicy.load(repo).lane).by_id(first)
    assert entry.state == "escalated"
    assert actionTypes(freed) == ["agent.build"], "the freed lane dispatched the other debt"
    assert freed.actions[0]["params"]["debtId"] != first


def test_scenario_d3_building_inside_24h_is_not_escalated(tmp_path: Path) -> None:
    clock = Clock()
    repo, _bare, sensor, store, runner = hygieneRunner(tmp_path, ["a"], clock=clock)
    view = runner.start("full")
    clock.advance(hours=23)
    again = makeRunner(repo, store, [sensor], clock=clock).start("full")
    debtId = view.actions[0]["params"]["debtId"]
    assert ledgerOf(store)["work"][debtId]["state"] == "building"
    assert actionTypes(again) == ["agent.build"], "re-offered under the adopting run, not escalated"


# --- D4 ------------------------------------------------------------------------------------


def test_scenario_d4_unknown_coverage_blocks_even_an_observe_run(tmp_path: Path) -> None:
    repo, _bare = makeFixture(tmp_path)
    broken = StubSensor("flaky", "registry_integrity_failed", raises=SensorUnavailable("nope"))
    view = makeRunner(repo, fileStore(tmp_path), [broken]).start("observe")
    assert view.status == "blocked" and view.exitCode == 3 and view.coverageUnknown == ["flaky"]
    assert ledgerOf(fileStore(tmp_path))["leases"] == {}


# --- D6: a debt that is gone takes its work with it -----------------------------------------


def test_scenario_d6_blocked_work_resolves_when_the_debt_is_observed_resolved(tmp_path: Path) -> None:
    clock = Clock()
    repo, _bare, sensor, store, runner = hygieneRunner(tmp_path, ["a"], clock=clock)
    view = runner.start("full")
    diff, proof = writeBuildArtifacts(repo, "s1", proofExit=1)
    runner.record(view.runId, view.actions[0]["stepId"], {**BUILD, "diffPath": str(diff), "proofPath": str(proof)})
    runner.resume(view.runId)
    (debtId,) = ledgerOf(store)["work"]
    assert ledgerOf(store)["work"][debtId]["state"] == "blocked"

    sensor.heal("a")  # a human fixed the condition
    clock.advance(hours=5)
    final = makeRunner(repo, store, [sensor], clock=clock).start("full")

    doc = ledgerOf(store)
    assert doc["work"][debtId]["state"] == "resolved"
    assert "resolved by observation" in doc["work"][debtId]["history"][-1]["reason"]
    assert final.summary["reobserve"]["resolvedWork"] == [debtId]
    assert final.status == "completed" and final.desk["decisions"] == []
    assert not [op for op in final.desk["operations"] if op["kind"] == "failed_dispatch"]
    entry = load_lane(doc["lane"], StewardPolicy.load(repo).lane).by_id(debtId)
    assert entry is None or not entry.live


def test_scenario_d6_escalated_work_resolves_and_leaves_the_desk(tmp_path: Path) -> None:
    clock = Clock()
    repo, _bare, sensor, store, _ = hygieneRunner(tmp_path, ["only"], clock=clock)
    for cycle in range(2):
        runner = makeRunner(repo, store, [sensor], clock=clock)
        drive(runner, runner.start("full"), repo, integrate="reject", builderId=f"b{cycle}", verifierId=f"v{cycle}")
        clock.advance(hours=2)
    (debtId,) = ledgerOf(store)["work"]
    assert ledgerOf(store)["work"][debtId]["state"] == "escalated"
    escalated = makeRunner(repo, store, [sensor], clock=clock).start("triage")
    assert any(d["source"] == "escalated-lane" for d in escalated.desk["decisions"])

    sensor.heal("only")
    cleared = makeRunner(repo, store, [sensor], clock=clock).start("verify")

    assert ledgerOf(store)["work"][debtId]["state"] == "resolved"
    assert cleared.desk["decisions"] == [], cleared.desk["decisions"]


def test_scenario_d6_work_is_never_resolved_without_the_debt_being_observed_resolved(tmp_path: Path) -> None:
    repo, _bare = makeFixture(tmp_path)
    store = fileStore(tmp_path)
    for index, state in enumerate(("building", "blocked", "landed", "no_change", "verified", "escalated")):
        debtId = f"debt:never-seen:{index}"
        editLedger(store, lambda doc, d=debtId, s=state: doc["work"].update({d: {
            "debtId": d, "state": s, "authority": "B", "kind": "repository_hygiene", "history": [], "notes": []}}))
    view = makeRunner(repo, store, [StubSensor(HYGIENE, "repository_hygiene")]).start("verify")
    assert view.summary["reobserve"]["resolvedWork"] == []
    states = {w["state"] for w in ledgerOf(store)["work"].values()}
    assert states == {"building", "blocked", "landed", "no_change", "verified", "escalated"}


def test_scenario_m12_coverage_unknown_resolves_nothing(tmp_path: Path) -> None:
    repo, _bare = makeFixture(tmp_path)
    store = fileStore(tmp_path)
    hygiene = StubSensor(HYGIENE, "repository_hygiene", ["x"])
    flaky = StubSensor("flaky", "registry_integrity_failed")
    runner = makeRunner(repo, store, [hygiene, flaky])
    (debtId,) = runner.start("triage").summary["triage"]["classB"]
    editLedger(store, lambda doc: doc["work"].update({debtId: {
        "debtId": debtId, "state": "landed", "authority": "B", "kind": "repository_hygiene", "history": [], "notes": []}}))
    hygiene.heal("x")
    flaky.raises = SensorUnavailable("went dark")

    view = makeRunner(repo, store, [hygiene, flaky]).start("verify")

    assert view.status == "blocked"
    item = ledgerOf(store)["work"][debtId]
    assert item["state"] == "landed", "the debt is gone, but the re-observation was incomplete"
    assert any("coverage is unknown" in n["note"] for n in item["notes"])

    flaky.raises = None  # coverage restored: now the very same evidence resolves it
    makeRunner(repo, store, [hygiene, flaky]).start("verify")
    assert ledgerOf(store)["work"][debtId]["state"] == "resolved"


# --- D7 -------------------------------------------------------------------------------------


def test_scenario_d7_resume_uses_the_recorded_branch_and_refuses_a_conflicting_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, bare = makeFixture(tmp_path, mirrorDrift=True)
    store = fileStore(tmp_path)
    crashAt(monkeypatch, "phase:class_a")
    with pytest.raises(Crash):
        makeRunner(repo, store, [AgentSkillMirrorSensor()]).start("full")
    runId = onlyRunId(store)
    uncrash(monkeypatch)

    with pytest.raises(fullrun.FullRunError, match="refusing to resume"):
        makeRunner(repo, store, [AgentSkillMirrorSensor()], integration_branch="dev/other").resume(runId)
    assert not stewardRefs(bare)

    view = makeRunner(repo, store, [AgentSkillMirrorSensor()], integration_branch=None).resume(runId)  # env var unset here
    assert view.status == "awaiting-action", view.to_dict()
    assert view.actions[0]["params"]["base"] == INTEGRATION
    assert len(stewardRefs(bare)) == 1


def test_scenario_d7_a_run_started_without_a_target_cannot_be_resumed_into_one(tmp_path: Path) -> None:
    repo, _bare, sensor, store, runner = hygieneRunner(tmp_path, integration_branch=None)
    view = runner.start("full")
    editLedger(store, lambda doc: doc["runs"][view.runId].update(status="active"))
    with pytest.raises(fullrun.FullRunError, match="refusing to resume"):
        makeRunner(repo, store, [sensor]).resume(view.runId)


# --- D8: attempts bind step ids, idempotency keys and recorded outcomes -------------------------


def test_scenario_d8_a_stale_attempt_cannot_stand_in_for_the_current_build(tmp_path: Path) -> None:
    clock = Clock()
    repo, _bare, sensor, store, _ = hygieneRunner(tmp_path, ["only"], clock=clock)
    mk = lambda: makeRunner(repo, store, [sensor], clock=clock)  # noqa: E731
    r1 = mk()
    v1 = r1.start("full")
    old = v1.actions[0]                                  # attempt 1, run 1 (never performed)
    clock.advance(hours=2)
    r2 = mk()
    v2 = r2.start("full")                                # adopts attempt 1 under run 2
    assert ledgerOf(store)["runs"][v1.runId]["actions"][0]["status"] == "superseded"
    diff, proof = writeBuildArtifacts(repo, "a1", proofExit=1)
    r2.record(v2.runId, v2.actions[0]["stepId"], {**BUILD, "agentId": "builder-A1", "diffPath": str(diff), "proofPath": str(proof)})
    r2.resume(v2.runId)                                  # mechanical reject: blocked, cooldown
    clock.advance(hours=2)
    r3 = mk()
    v3 = r3.start("full")                                # attempt 2
    new = v3.actions[0]

    assert new["params"]["attempt"] == 2 and old["params"]["attempt"] == 1
    assert new["stepId"] != old["stepId"] and new["idempotencyKey"] != old["idempotencyKey"]
    assert new["params"]["dispatchId"] == old["params"]["dispatchId"]  # same debt and rule, different attempt
    good, goodProof = writeBuildArtifacts(repo, "stale")
    with pytest.raises(RecordRefused, match="superseded"):
        r3.record(v1.runId, old["stepId"], {**BUILD, "agentId": "builder-STALE", "diffPath": str(good), "proofPath": str(goodProof)})
    r3.record(v3.runId, new["stepId"], {**BUILD, "agentId": "builder-REAL", "diffPath": str(good), "proofPath": str(goodProof)})
    (item,) = ledgerOf(store)["work"].values()
    assert item["build"]["agentId"] == "builder-REAL" and item["build"]["attempt"] == 2


def test_scenario_d8_outcomes_for_another_attempt_are_refused_even_on_a_live_step(tmp_path: Path) -> None:
    repo, _bare, sensor, store, runner = hygieneRunner(tmp_path)
    view = runner.start("full")
    (debtId,) = ledgerOf(store)["work"]
    diff, proof = writeBuildArtifacts(repo, "att")
    editLedger(store, lambda doc: doc["work"][debtId].update(attempt=2))
    with pytest.raises(RecordRefused, match="attempt"):
        runner.record(view.runId, view.actions[0]["stepId"], {**BUILD, "diffPath": str(diff), "proofPath": str(proof)})
    editLedger(store, lambda doc: doc["work"][debtId].update(attempt=1))
    verifying = toPendingVerify(runner, view, repo, "att2")
    editLedger(store, lambda doc: doc["work"][debtId].update(attempt=2))
    with pytest.raises(RecordRefused, match="earlier attempt"):
        runner.record(view.runId, verifying.actions[0]["stepId"], VERIFY)


# --- D9: identity is compared canonically -------------------------------------------------------


@pytest.mark.parametrize("spelling", ["builder-1 ", " builder-1", "Builder-1", "BUILDER-1", "builder-1​",
                                      "ｂuilder-1", "builder-1\t"])
def test_scenario_d9_a_builder_cannot_verify_its_own_work_by_respelling_its_id(tmp_path: Path, spelling: str) -> None:
    repo, _bare, _sensor, store, runner = hygieneRunner(tmp_path)
    view = runner.start("full")
    verifying = toPendingVerify(runner, view, repo)
    with pytest.raises(RecordRefused, match="independent"):
        runner.record(view.runId, verifying.actions[0]["stepId"], {**VERIFY, "agentId": spelling})
    runner.record(view.runId, verifying.actions[0]["stepId"], {**VERIFY, "agentId": "someone-else"})
    assert next(iter(ledgerOf(store)["work"].values()))["state"] == "verified"


# --- D11 (runner side) ---------------------------------------------------------------------------


def test_scenario_d11_a_routine_with_mixed_detector_states_is_partial(tmp_path: Path) -> None:
    repo, _bare = makeFixture(tmp_path)
    ok = StubSensor("detector-ok", "repository_hygiene", routines=(3,))
    broken = StubSensor("detector-broken", "registry_integrity_failed", routines=(3,), raises=SensorUnavailable("dark"))
    only = StubSensor("detector-solo", "repository_hygiene", routines=(5,))
    view = makeRunner(repo, fileStore(tmp_path), [ok, broken, only]).start("retro")
    routines = {r["routine"]: r for r in view.summary["retro"]["routines"]}
    assert routines[3]["state"] == "partial", routines[3]
    assert routines[5]["state"] == "observed"
    assert {d["sensor"]: d["state"] for d in routines[3]["detectors"]} == {"detector-ok": "executed", "detector-broken": "unknown"}


# =====================================================================================
# Mutation-killing tests
# =====================================================================================


def test_m15_a_run_that_lost_its_lease_stops_writing(tmp_path: Path) -> None:
    clock = Clock()
    repo, _bare = makeFixture(tmp_path)
    store = fileStore(tmp_path)
    first = makeRunner(repo, store, [StubSensor(HYGIENE, "repository_hygiene", ["leak"])], clock=clock, holder="A")
    second = makeRunner(repo, store, [StubSensor(HYGIENE, "repository_hygiene", ["leak"])], clock=clock, holder="B")
    seen: dict[str, Any] = {}

    def hook(name: str) -> None:
        if name == "phase:class_b" and not seen:
            seen["parked"] = True
            clock.advance(hours=2)  # A's lease expires while it is parked...
            seen["second"] = second.start("full")  # ...and B takes the ledger over.

    fullrun._checkpoint = hook
    try:
        viewA = first.start("full")
    finally:
        fullrun._checkpoint = lambda name: None

    doc = ledgerOf(store)
    runA = doc["runs"][viewA.runId]
    assert viewA.status == "abandoned" and "lease" in viewA.error
    assert runA["status"] == "abandoned" and runA["phase"] == "class_b", "A wrote nothing after losing the lease"
    assert doc["leases"]["run"]["holder"] == seen["second"].runId, "A did not release or take B's lease"
    assert [a["type"] for a in seen["second"].actions] == ["agent.build"]
    assert len(builds(doc)) == 1
    (entry,) = load_lane(doc["lane"], StewardPolicy.load(repo).lane).entries
    assert entry.attempts == 1


def test_m30_a_failed_run_releases_its_lease(tmp_path: Path) -> None:
    repo, _bare = makeFixture(tmp_path)
    store = fileStore(tmp_path)

    class Exploding:
        sensors: tuple = ()

        def scan(self, root: Path) -> Any:
            raise RuntimeError("scan blew up")

    config = fullrun.FullRunConfig(repo_root=repo, store=store, integration_branch=INTEGRATION,
                                   controller_factory=Exploding)
    view = fullrun.FullRunner(config).start("observe")

    assert view.status == "failed" and view.exitCode == 1 and "scan blew up" in view.error
    assert ledgerOf(store)["leases"] == {}, "a dead run must not hold the ledger"
    again = makeRunner(repo, store, [StubSensor(HYGIENE, "repository_hygiene")]).start("observe")
    assert again.status == "completed", "the next run is not locked out"


def test_m33_a_vanished_debt_frees_its_lane_slot(tmp_path: Path) -> None:
    clock = Clock()
    repo, _bare, sensor, store, runner = hygieneRunner(tmp_path, ["a"], clock=clock)
    view = runner.start("full")
    debtId = view.actions[0]["params"]["debtId"]
    sensor.heal("a")
    clock.advance(hours=2)

    makeRunner(repo, store, [sensor], clock=clock).start("verify")

    doc = ledgerOf(store)
    lane = load_lane(doc["lane"], StewardPolicy.load(repo).lane)
    assert lane.in_flight == (), "the slot held by the vanished debt was freed"
    assert lane.by_id(debtId).state == "closed"
    assert doc["work"][debtId]["state"] == "resolved"


def test_m28_active_work_is_not_landed_again(tmp_path: Path) -> None:
    repo, bare = makeFixture(tmp_path, mirrorDrift=True)
    store = fileStore(tmp_path)
    runner = makeRunner(repo, store, [AgentSkillMirrorSensor()])
    first = runner.start("full")
    runner.record(first.runId, first.actions[0]["stepId"], {"pullRequest": {"number": 3}})
    assert runner.resume(first.runId).status == "completed"

    second = makeRunner(repo, store, [AgentSkillMirrorSensor()]).start("full")

    (debtId,) = ledgerOf(store)["work"]
    assert debtId in second.summary["triage"]["skippedActive"]
    assert second.summary["class_a"]["landings"] == []
    assert second.actions == [] and second.status == "completed"
    assert len(openPrActions(store)) == 1 and len(stewardRefs(bare)) == 1


def test_m19_a_pull_request_action_goes_stale_once_the_pull_request_is_known(tmp_path: Path) -> None:
    repo, _bare = makeFixture(tmp_path, mirrorDrift=True)
    store = fileStore(tmp_path)
    runner = makeRunner(repo, store, [AgentSkillMirrorSensor()])
    view = runner.start("full")
    assert actionTypes(view) == ["forge.open_pr"]
    (debtId,) = ledgerOf(store)["work"]
    editLedger(store, lambda doc: doc["work"][debtId].update(pullRequest={"number": 1}))

    resumed = runner.resume(view.runId)

    assert resumed.status == "completed" and resumed.actions == []
    assert ledgerOf(store)["runs"][view.runId]["actions"][0]["status"] == "superseded"


def test_m20_an_integrate_action_goes_stale_once_the_work_has_moved_on(tmp_path: Path) -> None:
    repo, _bare, _sensor, store, runner = hygieneRunner(tmp_path)
    view = runner.start("full")
    verifying = toPendingVerify(runner, view, repo)
    runner.record(view.runId, verifying.actions[0]["stepId"], VERIFY)
    integrating = runner.resume(view.runId)
    assert actionTypes(integrating) == ["lead.integrate"]
    (debtId,) = ledgerOf(store)["work"]
    editLedger(store, lambda doc: doc["work"][debtId].update(state="landed"))

    resumed = runner.resume(view.runId)

    assert resumed.status == "completed" and resumed.actions == []
    integrate = [a for a in ledgerOf(store)["runs"][view.runId]["actions"] if a["type"] == "lead.integrate"]
    assert [a["status"] for a in integrate] == ["superseded"]


def test_m21_a_verify_action_goes_stale_once_the_work_has_moved_on(tmp_path: Path) -> None:
    repo, _bare, _sensor, store, runner = hygieneRunner(tmp_path)
    view = runner.start("full")
    verifying = toPendingVerify(runner, view, repo)
    assert actionTypes(verifying) == ["agent.verify"]
    (debtId,) = ledgerOf(store)["work"]
    editLedger(store, lambda doc: doc["work"][debtId].update(state="escalated"))

    resumed = runner.resume(view.runId)

    assert resumed.status == "completed" and resumed.actions == []
    verify = [a for a in ledgerOf(store)["runs"][view.runId]["actions"] if a["type"] == "agent.verify"]
    assert [a["status"] for a in verify] == ["superseded"]


def test_m24_resolution_requires_the_debt_to_be_observed_resolved(tmp_path: Path) -> None:
    """A still-open debt never resolves its work, whatever state the work is in."""

    repo, _bare, sensor, store, runner = hygieneRunner(tmp_path, ["a"])
    drive(runner, runner.start("full"), repo, integrate="integrate")
    (debtId,) = ledgerOf(store)["work"]
    assert ledgerOf(store)["work"][debtId]["state"] == "landed"
    again = makeRunner(repo, store, [sensor]).start("verify")  # the sensor still reports the finding
    assert ledgerOf(store)["work"][debtId]["state"] == "landed"
    assert again.summary["reobserve"]["resolvedWork"] == []
    for state in ("building", "blocked", "verified", "escalated", "no_change"):
        editLedger(store, lambda doc, s=state: doc["work"][debtId].update(state=s))
        makeRunner(repo, store, [sensor]).start("verify")
        assert ledgerOf(store)["work"][debtId]["state"] == state, state


def helperTwoDebts(tmp_path: Path, **overrides: Any) -> tuple[Path, Any, StubSensor, StubSensor, Any]:
    repo, _bare = makeFixture(tmp_path)
    hygiene = StubSensor(HYGIENE, "repository_hygiene", ["h"], routines=(12,))
    knowledge = StubSensor("knowledge-contradiction", "knowledge_contradiction", ["k"], routines=(17,))
    store = fileStore(tmp_path)
    return repo, store, hygiene, knowledge, lambda: makeRunner(repo, store, [hygiene, knowledge], **overrides)


def test_m03_the_debt_filter_dispatches_only_the_named_debt(tmp_path: Path) -> None:
    repo, store, hygiene, knowledge, mk = helperTwoDebts(tmp_path)
    ids = mk().start("triage").summary["triage"]["classB"]
    assert len(ids) == 2
    for chosen in ids:  # whichever the lane would rank first, the filter decides
        base = tmp_path / chosen.split(":")[1]
        base.mkdir()
        repo2, store2, h2, k2, mk2 = helperTwoDebts(base)
        view = mk2().start("full", debt=chosen)
        assert [a["params"]["debtId"] for a in view.actions] == [chosen], (chosen, view.to_dict())


def test_m03_the_routine_filter_dispatches_only_that_routines_debt(tmp_path: Path) -> None:
    for routine, kind in ((12, "repository_hygiene"), (17, "knowledge_contradiction")):
        base = tmp_path / f"r{routine}"
        base.mkdir()
        repo, store, hygiene, knowledge, mk = helperTwoDebts(base)
        view = mk().start("full", routine=routine)
        (action,) = view.actions
        assert action["params"]["debtId"].startswith(f"debt:{kind}:"), (routine, action["params"]["debtId"])


def test_m03_held_work_is_never_chosen_by_the_lane(tmp_path: Path) -> None:
    repo, bare, sensor, store, runner = hygieneRunner(tmp_path, ["a", "b"])
    first, second = sorted(runner.start("triage").summary["triage"]["classB"])
    editLedger(store, lambda doc: doc["work"].update({first: {
        "debtId": first, "state": "no_change", "authority": "B", "kind": "repository_hygiene",
        "history": [], "notes": []}}))

    view = makeRunner(repo, store, [sensor]).start("full")

    assert [a["params"]["debtId"] for a in view.actions] == [second], "the lowest id was held, so it is skipped"
    assert view.summary["triage"]["held"] == [first]


def test_m01_m02_dispatch_cap_and_pending_build_guard(tmp_path: Path) -> None:
    repo, _bare, sensor, store, _ = hygieneRunner(tmp_path, ["a", "b"])
    pinMaxInFlight(repo, 2)  # the lane could take a second dispatch; only the per-run cap forbids it
    runner = makeRunner(repo, store, [sensor])
    view = runner.start("full")
    assert actionTypes(view) == ["agent.build"]

    # M02: resuming while the build is still outstanding must stay parked in class_b, not move on.
    parked = runner.resume(view.runId)
    assert parked.phase == "class_b" and parked.status == "awaiting-action"
    assert "reobserve" not in parked.summary and actionTypes(parked) == ["agent.build"]

    # M01: with the build recorded, the per-run cap (1) stops a second dispatch.
    verifying = toPendingVerify(runner, view, repo)
    assert actionTypes(verifying) == ["agent.verify"], verifying.to_dict()
    doc = ledgerOf(store)
    assert len(builds(doc)) == 1
    assert sum(e["attempts"] for e in doc["lane"]["entries"]) == 1
    assert verifying.summary["class_b"]["status"] == "ok" and "maxDispatchesPerRun" in verifying.summary["class_b"]["reason"]


def test_class_a_no_change_is_retried_when_the_integration_base_later_gains_the_drift(tmp_path: Path) -> None:
    # Rehearsal B: the drift reached main, the integration branch already matched canonical,
    # so the landing was no_change. When the integration branch later gains the drift, the
    # next run must land it instead of holding the stale no_change forever.
    repo, bare = makeFixture(tmp_path, mirrorDrift=True)
    fixer = cloneOf(bare, tmp_path / "fixer")
    git(fixer, "checkout", "-q", INTEGRATION)
    write(fixer / ".claude/skills/x/SKILL.md", "# x canonical\n")
    commitAll(fixer, "integration already canonical")
    git(fixer, "push", "-q", "origin", INTEGRATION)
    store = fileStore(tmp_path)

    first = makeRunner(repo, store, [AgentSkillMirrorSensor()]).start("full")
    (item,) = ledgerOf(store)["work"].values()
    assert item["state"] == "no_change", first.to_dict()
    assert stewardRefs(bare) == []

    git(bare, "update-ref", f"refs/heads/{INTEGRATION}", "refs/heads/main")
    second = makeRunner(repo, store, [AgentSkillMirrorSensor()]).start("full")
    (item,) = ledgerOf(store)["work"].values()
    assert item["state"] == "proposed", second.to_dict()
    assert len(stewardRefs(bare)) == 1
