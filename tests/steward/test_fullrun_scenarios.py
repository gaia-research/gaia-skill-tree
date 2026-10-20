"""Acceptance scenarios for Steward Full, against fixture repos with real git.

Each scenario uses a local bare remote and, where it matters, both ledger
transports. No test touches a real origin or a real `steward/*` ref.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

import pytest

import gaia_cli.steward.fullrun as fullrun
from gaia_cli.steward.fullrun import RecordRefused
from gaia_cli.steward.ledger import GitRefLedgerStore
from gaia_cli.steward.lane import load_lane
from gaia_cli.steward.policy import StewardPolicy
from gaia_cli.steward.sensors import AgentSkillMirrorSensor
from gaia_cli.steward.primitives import SensorUnavailable

from tests.steward.test_fullrun import (
    BUILD,
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
