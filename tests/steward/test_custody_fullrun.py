"""Evidence custody through the Steward Full runner (issue #2448): real git, two "cloud" checkouts."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest

from gaia_cli.steward.fullrun import RecordRefused
from gaia_cli.steward.lane import load_lane
from gaia_cli.steward.ledger import GitRefLedgerStore
from gaia_cli.steward.policy import StewardPolicy

from tests.steward.test_fullrun import (
    BUILD,
    VERIFY,
    Clock,
    StubSensor,
    actionTypes,
    bareBranches,
    cloneOf,
    git,
    makeFixture,
    makeRunner,
    writeBuildArtifacts,
)

HYGIENE = "repository-hygiene"


def sensorFor() -> StubSensor:
    return StubSensor(HYGIENE, "repository_hygiene", ["leaked-artifact"])


def runnerOn(repo: Path, clock: Clock, **overrides: Any):
    return makeRunner(repo, GitRefLedgerStore(repo), [sensorFor()], clock=clock, **overrides)


def workOf(repo: Path) -> dict[str, Any]:
    document, _ = GitRefLedgerStore(repo).load()
    return document


def test_full_run_cloud_a_dispatches_and_builds_cloud_b_verifies_after_a_disappears(tmp_path: Path) -> None:
    repo, bare = makeFixture(tmp_path)
    clock = Clock()
    runnerA = runnerOn(repo, clock, evidence="git")
    view = runnerA.start("full")
    assert actionTypes(view) == ["agent.build"], view.to_dict()
    build = view.actions[0]
    debtId = build["params"]["debtId"]
    evidence = workOf(repo)["work"][debtId]["evidence"]
    assert evidence["dispatchBundle"], "dispatch authority is durable before any builder is told about the work"

    diff, proof = writeBuildArtifacts(repo)
    runnerA.record(view.runId, build["stepId"], {**BUILD, "diffPath": str(diff), "proofPath": str(proof)})
    evidence = workOf(repo)["work"][debtId]["evidence"]
    assert evidence["buildBundle"], "the builder's outcome is not accepted until its patch and proof are durable"
    assert "steward/evidence" in bareBranches(bare)

    shutil.rmtree(repo)  # cloud A's container is destroyed: no .gaia/steward receipts, diff or proof survive
    cloudB = cloneOf(bare, tmp_path / "cloudB")
    assert not (cloudB / ".gaia").exists()
    clock.advance(hours=2)  # A's run lease lapses with its work outstanding

    verifying = runnerOn(cloudB, clock, evidence="git").start("verify")
    assert actionTypes(verifying) == ["agent.verify"], verifying.to_dict()
    # The verifier prompt carries the ORIGINAL patch, restored from custody rather than re-rendered.
    prompt = (cloudB / verifying.actions[0]["params"]["verifierPromptPath"]).read_text()
    assert "scripts/fix.py" in prompt
    runnerOn(cloudB, clock, evidence="git").record(verifying.runId, verifying.actions[0]["stepId"], VERIFY)
    item = workOf(cloudB)["work"][debtId]
    assert item["state"] == "verified"
    assert item["evidence"]["buildBundle"] == evidence["buildBundle"]


def test_without_custody_a_missing_original_receipt_defers_and_never_redispatches(tmp_path: Path) -> None:
    repo, bare = makeFixture(tmp_path)
    clock = Clock()
    runnerA = runnerOn(repo, clock)  # custody off: the pre-#2448 path
    view = runnerA.start("full")
    build = view.actions[0]
    debtId = build["params"]["debtId"]
    diff, proof = writeBuildArtifacts(repo)
    runnerA.record(view.runId, build["stepId"], {**BUILD, "diffPath": str(diff), "proofPath": str(proof)})
    attemptsBefore = load_lane(workOf(repo)["lane"], StewardPolicy.load(repo).lane).by_id(debtId).attempts

    # Cloud B has the diff/proof (say they were copied across) but NOT the original dispatch receipt.
    cloudB = cloneOf(bare, tmp_path / "cloudB")
    (cloudB / ".gaia" / "inputs").mkdir(parents=True)
    for name in (diff.name, proof.name):
        shutil.copyfile(repo / ".gaia" / "inputs" / name, cloudB / ".gaia" / "inputs" / name)
    # the ledger records absolute paths from A; point B's copies where the ledger looks
    clock.advance(hours=2)
    view = runnerOn(cloudB, clock).start("verify")
    assert "agent.verify" not in actionTypes(view)
    assert "BLOCKED: provenance unavailable" in view.nextAction
    receipts = cloudB / ".gaia" / "steward" / "receipts"
    dispatched = [p for p in receipts.glob("steward-*.json") if '"action": "dispatch"' in p.read_text()] if receipts.is_dir() else []
    assert dispatched == [], "no new dispatch is issued to legitimize an old patch"
    after = workOf(cloudB)
    assert load_lane(after["lane"], StewardPolicy.load(cloudB).lane).by_id(debtId).attempts == attemptsBefore


def test_full_run_blocks_when_dispatch_cannot_be_made_durable(tmp_path: Path) -> None:
    repo, bare = makeFixture(tmp_path)
    git(repo, "remote", "add", "evidence-down", str(tmp_path / "nowhere.git"))
    view = makeRunner(repo, GitRefLedgerStore(repo), [sensorFor()], clock=Clock(),
                      evidence="git", evidence_remote="evidence-down").start("full")
    assert actionTypes(view) == []  # no builder is told about work whose authority could not be preserved
    assert view.status == "blocked", view.to_dict()
    assert "BLOCKED: provenance unavailable" in view.nextAction
    document, _ = GitRefLedgerStore(repo).load()
    assert document["work"] == {} or all(w["state"] != "building" for w in document["work"].values())
    assert "steward/evidence" not in bareBranches(bare)


def test_record_is_refused_while_custody_is_down_and_succeeds_once_repaired(tmp_path: Path) -> None:
    repo, bare = makeFixture(tmp_path)
    clock = Clock()
    runner = runnerOn(repo, clock, evidence="git")
    view = runner.start("full")
    build = view.actions[0]
    diff, proof = writeBuildArtifacts(repo)
    outcome = {**BUILD, "diffPath": str(diff), "proofPath": str(proof)}
    originalUrl = git(repo, "remote", "get-url", "origin")
    git(repo, "remote", "set-url", "origin", str(tmp_path / "nowhere.git"))
    with pytest.raises(RecordRefused, match="BLOCKED: provenance unavailable"):
        runner.record(view.runId, build["stepId"], outcome)
    git(repo, "remote", "set-url", "origin", originalUrl)
    runner.record(view.runId, build["stepId"], outcome)  # the step stayed pending, so recording again just works
    debtId = build["params"]["debtId"]
    assert GitRefLedgerStore(repo).load()[0]["work"][debtId]["evidence"]["buildBundle"]


def test_resumed_full_run_does_not_publish_or_dispatch_twice(tmp_path: Path) -> None:
    repo, bare = makeFixture(tmp_path)
    clock = Clock()
    runner = runnerOn(repo, clock, evidence="git")
    view = runner.start("full")
    commits = int(git(bare, "rev-list", "--count", "refs/heads/steward/evidence"))
    resumed = runner.resume(view.runId)
    assert actionTypes(resumed) == ["agent.build"]
    assert int(git(bare, "rev-list", "--count", "refs/heads/steward/evidence")) == commits


def test_quiet_day_with_custody_enabled_is_a_clean_noop(tmp_path: Path) -> None:
    repo, bare = makeFixture(tmp_path)
    quiet = StubSensor(HYGIENE, "repository_hygiene", [])
    view = makeRunner(repo, GitRefLedgerStore(repo), [quiet], clock=Clock(), evidence="git").start("full")
    assert view.status == "completed" and actionTypes(view) == []
    assert "steward/evidence" not in bareBranches(bare)
