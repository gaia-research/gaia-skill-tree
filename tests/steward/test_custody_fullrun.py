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


# ---------------------------------------------------------------------------
# Codex finding 1: lost builder prompts come from the ORIGINAL dispatch, never a new one
# ---------------------------------------------------------------------------

from gaia_cli.steward.fullrun import HANDOFFHEADING  # noqa: E402
from gaia_cli.steward.policy import POLICY_RELATIVE_PATH  # noqa: E402

NARROWED = (
    "      allowedPaths:\n        - tests/steward/**\n      allowedCommands:\n        - git status --short"
)
ORIGINAL = (
    "      allowedPaths:\n        - scripts/**\n        - tests/steward/**\n      allowedCommands:\n        - git status --short"
)


def narrowPolicy(repo: Path) -> None:
    policy = repo / POLICY_RELATIVE_PATH
    text = policy.read_text()
    assert ORIGINAL in text
    policy.write_text(text.replace(ORIGINAL, NARROWED, 1))


def dispatchReceipts(repo: Path) -> list[str]:
    receipts = repo / ".gaia" / "steward" / "receipts"
    if not receipts.is_dir():
        return []
    return sorted(p.name for p in receipts.glob("steward-*.json") if '"action": "dispatch"' in p.read_text())


def body(prompt: str) -> str:
    return prompt.split(HANDOFFHEADING, 1)[0]


def test_ordinary_resume_restores_the_original_prompt_even_after_policy_and_debt_change(tmp_path: Path) -> None:
    repo, bare = makeFixture(tmp_path)
    clock = Clock()
    runner = runnerOn(repo, clock, evidence="git")
    view = runner.start("full")
    action = view.actions[0]
    promptPath = repo / action["params"]["promptPath"]
    original = promptPath.read_text()
    debtId = action["params"]["debtId"]
    receiptsBefore = dispatchReceipts(repo)
    evidenceBefore = int(git(bare, "rev-list", "--count", "refs/heads/steward/evidence"))
    attemptsBefore = load_lane(workOf(repo)["lane"], StewardPolicy.load(repo).lane).by_id(debtId).attempts

    promptPath.unlink()  # the container lost its ignored .gaia/ prompt
    narrowPolicy(repo)  # policy moved on between sessions

    resumed = runnerOn(repo, clock, evidence="git")
    resumedView = resumed.resume(view.runId)
    assert actionTypes(resumedView) == ["agent.build"], resumedView.to_dict()
    assert promptPath.read_text() == original, "the builder gets exactly the envelope it was dispatched under"
    assert "- `scripts/**`" in original and "- `scripts/**`" in promptPath.read_text()
    assert dispatchReceipts(repo) == receiptsBefore, "no new dispatch receipt was minted"
    assert int(git(bare, "rev-list", "--count", "refs/heads/steward/evidence")) == evidenceBefore
    lane = load_lane(workOf(repo)["lane"], StewardPolicy.load(repo).lane)
    assert lane.by_id(debtId).attempts == attemptsBefore == 1


def test_negative_control_without_custody_a_lost_prompt_is_re_rendered_from_todays_policy(tmp_path: Path) -> None:
    """Documents the defect this guards against: the pre-custody path mints a new dispatch under changed policy."""

    repo, _bare = makeFixture(tmp_path)
    clock = Clock()
    runner = runnerOn(repo, clock)
    view = runner.start("full")
    promptPath = repo / view.actions[0]["params"]["promptPath"]
    original = promptPath.read_text()
    receiptsBefore = dispatchReceipts(repo)
    promptPath.unlink()
    narrowPolicy(repo)
    runnerOn(repo, clock).resume(view.runId)
    assert promptPath.read_text() != original
    assert "- `scripts/**`" not in promptPath.read_text(), "the re-rendered envelope silently lost an authorized path"
    assert dispatchReceipts(repo) != receiptsBefore


def test_adoption_after_the_original_container_disappears_uses_the_original_dispatch(tmp_path: Path) -> None:
    repo, bare = makeFixture(tmp_path)
    clock = Clock()
    view = runnerOn(repo, clock, evidence="git").start("full")
    action = view.actions[0]
    debtId = action["params"]["debtId"]
    original = (repo / action["params"]["promptPath"]).read_text()
    evidenceBefore = int(git(bare, "rev-list", "--count", "refs/heads/steward/evidence"))

    shutil.rmtree(repo)  # cloud A is gone, and its run lease lapses
    cloudB = cloneOf(bare, tmp_path / "cloudB")
    narrowPolicy(cloudB)
    clock.advance(hours=2)

    second = runnerOn(cloudB, clock, evidence="git").start("full")
    assert actionTypes(second) == ["agent.build"], second.to_dict()
    adopted = second.actions[0]
    assert adopted["params"]["dispatchId"] == action["params"]["dispatchId"]
    adoptedPrompt = (cloudB / adopted["params"]["promptPath"]).read_text()
    assert body(adoptedPrompt) == body(original), "adoption restores the original envelope, not today's"
    assert "- `scripts/**`" in adoptedPrompt
    assert dispatchReceipts(cloudB) == [], "the adopting container never issued a dispatch"
    assert int(git(bare, "rev-list", "--count", "refs/heads/steward/evidence")) == evidenceBefore
    document = workOf(cloudB)
    assert load_lane(document["lane"], StewardPolicy.load(cloudB).lane).by_id(debtId).attempts == 1
    assert document["work"][debtId]["evidence"]["dispatchBundle"]


def test_lost_prompt_with_unavailable_custody_blocks_without_redispatching_then_recovers(tmp_path: Path) -> None:
    repo, bare = makeFixture(tmp_path)
    git(repo, "remote", "add", "evcustody", str(bare))
    clock = Clock()
    view = runnerOn(repo, clock, evidence="git", evidence_remote="evcustody").start("full")
    action = view.actions[0]
    promptPath = repo / action["params"]["promptPath"]
    original = promptPath.read_text()
    promptPath.unlink()
    git(repo, "remote", "set-url", "evcustody", str(tmp_path / "nowhere.git"))
    narrowPolicy(repo)

    blocked = runnerOn(repo, clock, evidence="git", evidence_remote="evcustody").resume(view.runId)
    assert not promptPath.exists(), "no substitute prompt is written"
    assert "BLOCKED: provenance unavailable" in blocked.nextAction
    receiptsAfterBlock = dispatchReceipts(repo)
    pending = [a for a in workOf(repo)["runs"][view.runId]["actions"] if a["status"] == "pending"]
    assert pending and pending[0].get("recoveryBlocked")

    # Repair the transport. The SAME run resumes, restores the original prompt and drops the block.
    git(repo, "remote", "set-url", "evcustody", str(bare))
    healed = runnerOn(repo, clock, evidence="git", evidence_remote="evcustody").resume(view.runId)
    assert actionTypes(healed) == ["agent.build"], healed.to_dict()
    assert promptPath.read_text() == original
    assert "BLOCKED" not in healed.nextAction
    assert dispatchReceipts(repo) == receiptsAfterBlock


def test_adoption_with_unavailable_custody_is_blocked_and_never_falls_back_to_a_new_dispatch(tmp_path: Path) -> None:
    repo, bare = makeFixture(tmp_path)
    clock = Clock()
    view = runnerOn(repo, clock, evidence="git").start("full")
    debtId = view.actions[0]["params"]["debtId"]
    shutil.rmtree(repo)
    cloudB = cloneOf(bare, tmp_path / "cloudB")
    git(cloudB, "remote", "add", "evcustody", str(tmp_path / "nowhere.git"))  # custody unreachable from B
    narrowPolicy(cloudB)
    clock.advance(hours=2)
    second = runnerOn(cloudB, clock, evidence="git", evidence_remote="evcustody").start("full")
    assert "agent.build" not in actionTypes(second)
    assert second.status == "blocked", second.to_dict()
    assert "BLOCKED: provenance unavailable" in second.nextAction
    assert dispatchReceipts(cloudB) == [], "no new dispatch was issued in place of the unreachable original"
    document = workOf(cloudB)
    assert load_lane(document["lane"], StewardPolicy.load(cloudB).lane).by_id(debtId).attempts == 1
