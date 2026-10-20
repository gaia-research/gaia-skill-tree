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
    fileStore,
    git,
    makeFixture,
    makeRunner,
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
    assert params["allowedModels"] == ["claude-haiku-5-5", "claude-sonnet-5-5"]
    assert params["effortRequired"] is True and params["base"] == INTEGRATION
    assert params["branch"].startswith("steward/b/repository-hygiene-")
    assert set(params["outputs"]) == {"diffPath", "proofPath"}
    prompt = (repo / params["promptPath"]).read_text()
    assert "Tree Keeper" in prompt
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
        runner.record(view.runId, build["stepId"], {**BUILD, "model": "claude-opus-5", "diffPath": str(diff), "proofPath": str(proof)})
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
    assert verify["params"]["allowedModels"] == ["claude-sonnet-5-5"]
    assert "scripts/fix.py" in (repo / verify["params"]["verifierPromptPath"]).read_text()

    # 5. the same agent may not judge its own work; a different one may.
    with pytest.raises(RecordRefused, match="independent"):
        runner.record(view.runId, verify["stepId"], {**VERIFY, "agentId": "builder-1"})
    with pytest.raises(RecordRefused, match="not permitted"):
        runner.record(view.runId, verify["stepId"], {**VERIFY, "model": "claude-haiku-5-5"})
    runner.record(view.runId, verify["stepId"], VERIFY)
    doc = ledgerOf(store)
    assert doc["work"][debtId]["state"] == "verified"
    entry = load_lane(doc["lane"], StewardPolicy.load(repo).lane).by_id(debtId)
    assert entry.state == "closed" and entry.last_verdict == "accept"
    assert "verifier-1" in entry.history[-1].reason

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
    run = doc["runs"][view.runId]
    assert run["modelIds"] == ["claude-haiku-5-5", "claude-sonnet-5-5"]
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
        root = Path(scratch)
        writeInheritedEvidenceRegistry(root)
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
