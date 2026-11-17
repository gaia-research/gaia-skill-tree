"""Durable evidence custody across ephemeral cloud environments (issue #2448).

Every test here uses real git: a bare remote stands in for GitHub and separate
clones stand in for separate cloud containers that share nothing but that remote.
"Cloud A disappears" is modelled by deleting its whole directory.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from gaia_cli.steward import custody as cu
from gaia_cli.steward import custody_ops as ops
from gaia_cli.steward.controller import StewardController
from gaia_cli.steward.custody import Custody, CustodyRefused, CustodyUnavailable
from gaia_cli.steward.models import Observation, Subject
from gaia_cli.steward.policy import POLICY_RELATIVE_PATH
from gaia_cli.steward.routing import render_dispatch
from gaia_cli.steward.verification import PROOF_TRANSCRIPT_SCHEMA

REPO_ROOT = Path(__file__).resolve().parents[2]
FROZEN = datetime(2026, 11, 13, tzinfo=timezone.utc)
LEAD = {"role": "lead", "agentId": "lead-test"}


class IntegritySensor:
    id = "registry-integrity"

    def __init__(self, count: int = 1) -> None:
        self.count = count

    def scan(self, root: Path, observed_at: str) -> list[Observation]:
        return [
            Observation(
                kind="registry_integrity_failed",
                subject=Subject("repository-surface", f"registry-nodes-{number}"),
                observed_at=observed_at, source=self.id, status="drift",
                current_state={"valid": True},
                observed_state={"violations": [{"path": f"registry/nodes/a{number}.json", "error": "boom"}]},
            )
            for number in range(self.count)
        ]


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.name=T", "-c", "user.email=t@example.com", "-c", "commit.gpgsign=false", *args],
        cwd=root, check=True, capture_output=True, text=True,
    ).stdout.strip()


def controller(count: int = 1) -> StewardController:
    return StewardController(sensors=[IntegritySensor(count)], clock=lambda: FROZEN)


def diffText(path: str = "scripts/fix.py") -> str:
    return (
        f"diff --git a/{path} b/{path}\nindex 1111111..2222222 100644\n--- a/{path}\n+++ b/{path}\n"
        "@@ -1 +1 @@\n-old line\n+new line\n"
    )


def transcript(items: int) -> str:
    return json.dumps({
        "schemaVersion": PROOF_TRANSCRIPT_SCHEMA,
        "entries": [
            {"contractIndex": index, "command": f"python scripts/validate.py # {index}", "exitCode": 0,
             "output": f"proof output {index}"}
            for index in range(1, items + 1)
        ],
    })


class World:
    """A bare remote plus the clones ("cloud containers") that share it."""

    def __init__(self, tmp: Path, count: int = 1) -> None:
        self.tmp = tmp
        self.remote = tmp / "remote.git"
        subprocess.run(["git", "init", "--bare", "-q", "-b", "main", str(self.remote)], check=True)
        self.cloudA = tmp / "cloudA"
        (self.cloudA / POLICY_RELATIVE_PATH).parent.mkdir(parents=True)
        shutil.copyfile(REPO_ROOT / POLICY_RELATIVE_PATH, self.cloudA / POLICY_RELATIVE_PATH)
        (self.cloudA / "scripts").mkdir()
        (self.cloudA / "scripts" / "fix.py").write_text("old line\n")
        git(self.cloudA, "init", "-q", "-b", "main")
        git(self.cloudA, "remote", "add", "origin", str(self.remote))
        git(self.cloudA, "add", "-A")
        git(self.cloudA, "commit", "-qm", "initial")
        git(self.cloudA, "push", "-q", "origin", "main")
        self.controller = controller(count)
        scan = self.controller.scan(self.cloudA)
        self.debts = sorted(debt.id for debt in scan.open_debts)

    def dispatch(self, debt: str | None = None) -> Any:
        return render_dispatch(self.cloudA, debt or self.debts[0], controller=self.controller)

    def clone(self, name: str) -> Path:
        target = self.tmp / name
        subprocess.run(["git", "clone", "-q", str(self.remote), str(target)], check=True)
        return target

    def custody(self, root: Path) -> Custody:
        return Custody.open(root)

    def evidenceCommits(self) -> int:
        return int(git(self.remote, "rev-list", "--count", "refs/heads/steward/evidence"))


@pytest.fixture
def world(tmp_path: Path) -> World:
    return World(tmp_path)


def publishDispatch(world: World, result: Any | None = None) -> tuple[cu.PublishResult, Any]:
    result = result or world.dispatch()
    published = ops.publishDispatch(
        world.cloudA, world.custody(world.cloudA), result.artifact.debt["id"], writer=LEAD,
        scanRaw=result.scan.receipt_path.read_bytes(), dispatchRaw=result.receipt_path.read_bytes(),
    )
    return published, result


def publishBuild(world: World, result: Any, *, diff: str | None = None, proof: str | None = None) -> cu.PublishResult:
    root = world.cloudA
    diffPath = root / "candidate.diff"
    proofPath = root / "proof.json"
    diffPath.write_text(diff if diff is not None else diffText())
    proofPath.write_text(proof if proof is not None else transcript(len(result.artifact.proof)))
    return ops.publishBuild(
        root, world.custody(root), result.artifact.debt["id"],
        writer=ops.writerRecord(role="builder", agentId="builder-1", model="haiku-5-5", effort="medium"),
        summary="fix", noChange=False, diffPath=diffPath, proofPath=proofPath,
    )


def corrupt(world: World, path: str, data: bytes) -> None:
    """Test-only: rewrite one path on the remote ref, simulating tampering at rest."""

    work = world.tmp / "tamper"
    shutil.rmtree(work, ignore_errors=True)
    subprocess.run(["git", "clone", "-q", "--branch", "steward/evidence", str(world.remote), str(work)], check=True)
    target = work / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    git(work, "add", "-A")
    git(work, "commit", "-qm", "tamper")
    git(work, "push", "-q", "origin", "HEAD:refs/heads/steward/evidence")


# ---------------------------------------------------------------------------
# The core guarantee: cloud A dispatches, terminates, cloud B verifies
# ---------------------------------------------------------------------------


def test_cloud_a_dispatches_terminates_and_cloud_b_verifies_the_original(world: World) -> None:
    published, result = publishDispatch(world)
    debt = result.artifact.debt["id"]
    originalDispatch = result.receipt_path.read_bytes()
    originalScan = result.scan.receipt_path.read_bytes()
    assert published.published and published.readBack
    build = publishBuild(world, result)
    assert build.published and build.readBack

    shutil.rmtree(world.cloudA)  # cloud A is gone, and so is its .gaia/steward/

    cloudB = world.clone("cloudB")
    assert not (cloudB / ".gaia").exists()
    verified = ops.verifyFromCustody(cloudB, world.custody(cloudB), debt, controller=world.controller)
    # Byte-for-byte the receipts cloud A issued, restored without re-rendering anything.
    restored = {p.name: p.read_bytes() for p in verified.restored.receiptPaths}
    assert restored[f"{result.receipt.run_id}.json"] == originalDispatch
    assert restored[f"{result.scan.receipt.run_id}.json"] == originalScan
    assert verified.result.artifact.verdict == "pending"  # machine never accepts
    assert verified.result.artifact.dispatch_id == result.artifact.dispatch_id

    verdict = ops.publishVerdict(
        cloudB, world.custody(cloudB), debt, receiptPath=verified.result.receipt_path,
        buildBundleId=verified.restored.build.bundle.bundleId, writer={"role": "mechanical"},
    )
    assert verdict.published and verdict.readBack

    cloudC = world.clone("cloudC")
    handoff = ops.readiness(world.custody(cloudC), debt)
    assert [b["kind"] for b in handoff["bundles"]] == ["dispatch", "build", "verdict"]
    assert handoff["mechanicalVerdict"] == "pending" and handoff["independentVerifierRequired"] is True
    assert handoff["sourceCommit"] == result.artifact.head_commit
    # PR-safe: ids and hashes only.
    assert "old line" not in json.dumps(handoff)


def test_restored_receipt_is_the_original_authority_not_todays_policy(world: World) -> None:
    published, result = publishDispatch(world)
    publishBuild(world, result)
    shutil.rmtree(world.cloudA)
    cloudB = world.clone("cloudB")
    policyFile = cloudB / POLICY_RELATIVE_PATH
    policyFile.write_text(policyFile.read_text().replace("      - scripts/**\n", ""))  # narrowed after dispatch
    verified = ops.verifyFromCustody(cloudB, world.custody(cloudB), result.artifact.debt["id"], controller=world.controller)
    assert verified.result.artifact.scope_valid and verified.result.artifact.verdict == "pending"


# ---------------------------------------------------------------------------
# Integrity: missing, altered, malformed
# ---------------------------------------------------------------------------


def test_altered_receipt_bytes_are_refused(world: World) -> None:
    published, result = publishDispatch(world)
    digest = published.objects["dispatch-receipt"]
    doctored = json.loads(result.receipt_path.read_bytes())
    doctored["artifact"]["allowedPaths"] = ["**"]  # widen the envelope after publication
    corrupt(world, cu.objectPath(digest), json.dumps(doctored).encode())
    cloudB = world.clone("cloudB")
    with pytest.raises(CustodyRefused, match="altered"):
        world.custody(cloudB).chain(result.artifact.debt["id"])


def test_missing_receipt_object_is_refused(world: World) -> None:
    published, result = publishDispatch(world)
    work = world.tmp / "rm"
    subprocess.run(["git", "clone", "-q", "--branch", "steward/evidence", str(world.remote), str(work)], check=True)
    (work / cu.objectPath(published.objects["dispatch-receipt"])).unlink()
    git(work, "add", "-A")
    git(work, "commit", "-qm", "drop")
    git(work, "push", "-q", "origin", "HEAD:refs/heads/steward/evidence")
    with pytest.raises(CustodyRefused, match="missing from custody"):
        world.custody(world.clone("cloudB")).chain(result.artifact.debt["id"])


def test_altered_manifest_no_longer_matches_its_bundle_id(world: World) -> None:
    published, result = publishDispatch(world)
    debt = result.artifact.debt["id"]
    path = cu.bundlePath(debt, published.bundleId)
    manifest = json.loads(world.custody(world.cloudA).store.readFile(world.custody(world.cloudA).store.snapshot(), path, limit=10**6))
    manifest["identity"]["sourceCommit"] = "0" * 40
    corrupt(world, path, json.dumps(manifest).encode())
    with pytest.raises(CustodyRefused, match="altered after publication"):
        world.custody(world.clone("cloudB")).chain(debt)


def test_missing_original_scan_is_refused_at_dispatch_time(world: World) -> None:
    result = world.dispatch()
    result.scan.receipt_path.unlink()  # the scan behind the dispatch is gone
    with pytest.raises(CustodyRefused, match="scan receipt"):
        ops.publishDispatch(world.cloudA, world.custody(world.cloudA), result.artifact.debt["id"], writer=LEAD)


def test_a_scan_that_is_not_the_one_behind_the_dispatch_is_refused(world: World) -> None:
    result = world.dispatch()
    otherScan = json.loads(result.scan.receipt_path.read_bytes())
    otherScan["runId"] = "steward-20260101T000000Z-deadbeefdeadbeef"
    with pytest.raises(CustodyRefused, match="not the scan this dispatch"):
        cu.dispatchBundle(
            debtId=result.artifact.debt["id"], scanRaw=json.dumps(otherScan).encode(),
            dispatchRaw=result.receipt_path.read_bytes(), writer=LEAD,
        )


def test_a_dispatch_edited_before_publication_is_refused(world: World) -> None:
    result = world.dispatch()
    doctored = json.loads(result.receipt_path.read_bytes())
    doctored["artifact"]["allowedPaths"] = ["**"]
    with pytest.raises(CustodyRefused, match="content hash"):
        cu.dispatchBundle(
            debtId=result.artifact.debt["id"], scanRaw=result.scan.receipt_path.read_bytes(),
            dispatchRaw=json.dumps(doctored).encode(), writer=LEAD,
        )


@pytest.mark.parametrize("proof,message", [
    ("", "missing or empty"),
    ("   \n", "missing or empty"),
    ("{not json", "not a valid steward-proof-transcript-v1"),
    ('{"schemaVersion": "wrong", "entries": []}', "not a valid steward-proof-transcript-v1"),
    ('{"schemaVersion": "steward-proof-transcript-v1", "entries": []}', "not a valid steward-proof-transcript-v1"),
])
def test_missing_empty_or_malformed_proof_is_refused(world: World, proof: str, message: str) -> None:
    _published, result = publishDispatch(world)
    with pytest.raises(CustodyRefused, match=message):
        publishBuild(world, result, proof=proof)


def test_a_proof_for_another_contract_is_stale_and_refused(world: World) -> None:
    _published, result = publishDispatch(world)
    tooMany = transcript(len(result.artifact.proof) + 3)  # indices outside this packet's proof contract
    with pytest.raises(CustodyRefused, match="outside the packet"):
        publishBuild(world, result, proof=tooMany)


def test_an_empty_or_hunkless_diff_is_refused(world: World) -> None:
    _published, result = publishDispatch(world)
    with pytest.raises(CustodyRefused, match="diff"):
        publishBuild(world, result, diff="")
    with pytest.raises(CustodyRefused, match="no hunks"):
        publishBuild(world, result, diff="just narrative\n")


def test_a_build_cannot_be_published_for_a_dispatch_that_was_never_made_durable(world: World) -> None:
    result = world.dispatch()  # dispatched locally only, never published
    with pytest.raises(CustodyRefused, match="no dispatch evidence bundle|no evidence has been published|does not exist"):
        publishBuild(world, result)


def test_wrong_baseline_is_refused_on_restore(world: World) -> None:
    published, result = publishDispatch(world)
    publishBuild(world, result)
    stranger = world.tmp / "stranger"  # a checkout of an unrelated history: cannot resolve the authorized baseline
    stranger.mkdir()
    git(stranger, "init", "-q", "-b", "main")
    (stranger / "x").write_text("x")
    (stranger / POLICY_RELATIVE_PATH).parent.mkdir(parents=True)
    shutil.copyfile(REPO_ROOT / POLICY_RELATIVE_PATH, stranger / POLICY_RELATIVE_PATH)
    git(stranger, "add", "-A")
    git(stranger, "commit", "-qm", "other history")
    git(stranger, "remote", "add", "origin", str(world.remote))
    with pytest.raises(CustodyRefused, match="baseline commit"):
        ops.restore(stranger, world.custody(stranger), result.artifact.debt["id"])


def test_a_newer_local_dispatch_cannot_stand_in_for_the_original(world: World) -> None:
    published, result = publishDispatch(world)
    publishBuild(world, result)
    debt = result.artifact.debt["id"]
    cloudB = world.clone("cloudB")
    # B re-dispatches the same debt locally under a later clock: a different, newer receipt.
    later = StewardController(sensors=[IntegritySensor(1)], clock=lambda: datetime(2026, 11, 14, tzinfo=timezone.utc))
    newer = render_dispatch(cloudB, debt, controller=later)
    assert newer.receipt.run_id != result.receipt.run_id
    with pytest.raises(CustodyRefused, match="newer dispatch receipt"):
        ops.verifyFromCustody(cloudB, world.custody(cloudB), debt, controller=later)


def test_restore_never_overwrites_a_different_local_receipt(world: World) -> None:
    published, result = publishDispatch(world)
    publishBuild(world, result)
    debt = result.artifact.debt["id"]
    cloudB = world.clone("cloudB")
    receipts = cloudB / ".gaia" / "steward" / "receipts"
    receipts.mkdir(parents=True)
    (receipts / f"{result.receipt.run_id}.json").write_text("{}")
    with pytest.raises(CustodyRefused, match="different bytes"):
        ops.restore(cloudB, world.custody(cloudB), debt)


# ---------------------------------------------------------------------------
# Interrupted persistence, concurrency, resume, quiet days
# ---------------------------------------------------------------------------


def test_interrupted_push_leaves_nothing_visible_and_is_recoverable(world: World, monkeypatch: pytest.MonkeyPatch) -> None:
    result = world.dispatch()
    custody = world.custody(world.cloudA)
    real = cu.GitEvidenceStore.publishTree
    monkeypatch.setattr(cu.GitEvidenceStore, "publishTree",
                        lambda *a, **k: (_ for _ in ()).throw(cu.LedgerUnavailable("connection reset")))
    with pytest.raises(CustodyUnavailable, match="connection reset"):
        ops.publishDispatch(world.cloudA, custody, result.artifact.debt["id"], writer=LEAD)
    assert custody.store.snapshot() is None  # nothing half-written is visible
    monkeypatch.setattr(cu.GitEvidenceStore, "publishTree", real)
    recovered = ops.publishDispatch(world.cloudA, custody, result.artifact.debt["id"], writer=LEAD)
    assert recovered.published and recovered.readBack


def test_push_that_lands_but_cannot_be_read_back_is_never_success_and_retry_is_idempotent(
    world: World, monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = world.dispatch()
    debt = result.artifact.debt["id"]
    custody = world.custody(world.cloudA)
    real = Custody.readBack
    monkeypatch.setattr(Custody, "readBack", lambda *a, **k: (_ for _ in ()).throw(CustodyUnavailable("fetch timed out")))
    with pytest.raises(CustodyUnavailable, match="timed out"):
        ops.publishDispatch(world.cloudA, custody, debt, writer=LEAD)
    commitsAfterFirst = world.evidenceCommits()
    monkeypatch.setattr(Custody, "readBack", real)
    again = ops.publishDispatch(world.cloudA, custody, debt, writer=LEAD)
    assert again.published is False and again.readBack is True  # found durable, re-verified, not duplicated
    assert world.evidenceCommits() == commitsAfterFirst


def test_resumed_run_does_not_duplicate_the_dispatch(world: World) -> None:
    first, result = publishDispatch(world)
    before = world.evidenceCommits()
    second, _ = publishDispatch(world, result)
    assert second.bundleId == first.bundleId and second.published is False
    assert world.evidenceCommits() == before
    held = world.custody(world.cloudA).bundles(world.custody(world.cloudA).store.snapshot(), result.artifact.debt["id"])
    assert len(held) == 1


def test_concurrent_writers_preserve_every_bundle(tmp_path: Path) -> None:
    world = World(tmp_path, count=4)
    bundles = []
    for debt in world.debts:
        result = world.dispatch(debt)
        bundle, objects = cu.dispatchBundle(
            debtId=debt, scanRaw=result.scan.receipt_path.read_bytes(),
            dispatchRaw=result.receipt_path.read_bytes(), writer=LEAD,
        )
        bundles.append((debt, bundle, objects))
    clones = [world.clone(f"writer{i}") for i in range(len(bundles))]
    errors: list[BaseException] = []
    barrier = threading.Barrier(len(bundles))

    def write(index: int) -> None:
        try:
            custody = Custody.open(clones[index])
            _debt, bundle, objects = bundles[index]
            barrier.wait()
            custody.publish(bundle, objects)
        except BaseException as exc:  # pragma: no cover - reported below
            errors.append(exc)

    threads = [threading.Thread(target=write, args=(i,)) for i in range(len(bundles))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert not errors, errors
    reader = Custody.open(world.clone("reader"))
    tip = reader.store.snapshot()
    for debt, bundle, _objects in bundles:
        assert [b.bundleId for b in reader.bundles(tip, debt)] == [bundle.bundleId]
        reader.loadAt(tip, bundle.bundleId, debt)
    # Fast-forward only: history is one linear chain with exactly one commit per writer.
    assert world.evidenceCommits() == len(bundles)


def test_quiet_day_is_a_genuine_noop(world: World) -> None:
    custody = world.custody(world.clone("cloudB"))
    assert custody.store.snapshot() is None
    assert custody.bundles(None, "debt:none") == []
    with pytest.raises(CustodyRefused, match="no evidence has been published|no evidence chain"):
        custody.chain("debt:none")


def test_a_genuine_no_change_build_is_recorded_without_a_diff(world: World) -> None:
    _published, result = publishDispatch(world)
    built = ops.publishBuild(
        world.cloudA, world.custody(world.cloudA), result.artifact.debt["id"],
        writer=ops.writerRecord(role="builder", agentId="b", model="haiku-5-5", effort="high"),
        summary="already fixed upstream", noChange=True, diffPath=None, proofPath=None,
    )
    assert built.published
    with pytest.raises(CustodyRefused, match="no change"):
        ops.verifyFromCustody(world.clone("cloudB"), world.custody(world.clone("cloudB2")), result.artifact.debt["id"],
                              controller=world.controller)


def test_ambiguous_builds_must_be_named(world: World) -> None:
    _published, result = publishDispatch(world)
    publishBuild(world, result)
    publishBuild(world, result, diff=diffText().replace("new line", "newer line"))
    with pytest.raises(CustodyRefused, match="evidence chains end"):
        world.custody(world.clone("cloudB")).chain(result.artifact.debt["id"])


def test_ready_refuses_an_incomplete_chain_and_a_non_pending_verdict(world: World) -> None:
    _published, result = publishDispatch(world)
    debt = result.artifact.debt["id"]
    with pytest.raises(CustodyRefused, match="incomplete"):
        ops.readiness(world.custody(world.cloudA), debt)
    publishBuild(world, result)
    with pytest.raises(CustodyRefused, match="incomplete"):
        ops.readiness(world.custody(world.cloudA), debt)


# ---------------------------------------------------------------------------
# Policy-shaped guards
# ---------------------------------------------------------------------------


def test_builder_and_verifier_writes_need_explicit_model_and_effort() -> None:
    with pytest.raises(CustodyRefused, match="explicit effort"):
        ops.writerRecord(role="builder", agentId="a", model="haiku-5-5", effort="default")
    with pytest.raises(CustodyRefused, match="explicit effort"):
        ops.writerRecord(role="verifier", agentId="a", model="sonnet-5-5", effort="inherit")
    with pytest.raises(CustodyRefused, match="name the model"):
        ops.writerRecord(role="builder", agentId="a", model=None, effort="high")


def test_mode_resolution_never_silently_downgrades() -> None:
    assert cu.requestedMode(None, {}) is None
    assert cu.requestedMode(None, {cu.ENVIRONMENT_VARIABLE: "git"}) == "git"
    assert cu.requestedMode("off", {cu.ENVIRONMENT_VARIABLE: "git"}) is None
    with pytest.raises(CustodyRefused, match="unknown evidence custody mode"):
        cu.requestedMode(None, {cu.ENVIRONMENT_VARIABLE: "s3"})


def test_the_evidence_ref_may_not_alias_the_ledger_ref(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path / "r")], check=True)
    with pytest.raises(CustodyRefused, match="ledger ref"):
        cu.GitEvidenceStore(tmp_path / "r", "origin", "steward/ledger")


def test_unreachable_remote_is_unavailable_not_empty(world: World) -> None:
    git(world.cloudA, "remote", "set-url", "origin", str(world.tmp / "nowhere.git"))
    with pytest.raises(CustodyUnavailable):
        world.custody(world.cloudA).store.snapshot()


def test_the_ledger_ref_is_untouched_by_custody(world: World) -> None:
    publishDispatch(world)
    heads = git(world.remote, "for-each-ref", "--format=%(refname)", "refs/heads")
    assert "refs/heads/steward/evidence" in heads and "refs/heads/steward/ledger" not in heads


# ---------------------------------------------------------------------------
# Codex finding 2: a verdict is bound to the exact build it judged
# ---------------------------------------------------------------------------


def secondBuild(world: World, result: Any, *, diff: str | None = None, proof: str | None = None) -> cu.PublishResult:
    """A different candidate under the SAME dispatch (a retry, or a hostile substitute)."""

    return publishBuild(world, result, diff=diff, proof=proof)


def verifyBuild(world: World, result: Any, buildBundleId: str, root: Path | None = None) -> Any:
    root = root or world.clone(f"verifier-{buildBundleId[:6]}")
    return ops.verifyFromCustody(
        root, world.custody(root), result.artifact.debt["id"], bundleId=buildBundleId, controller=world.controller,
    )


def test_a_pending_receipt_from_one_candidate_cannot_be_attached_to_another_under_the_same_dispatch(world: World) -> None:
    _published, result = publishDispatch(world)
    debt = result.artifact.debt["id"]
    buildA = publishBuild(world, result)
    buildB = secondBuild(world, result, diff=diffText().replace("new line", "a different line"))
    assert buildA.bundleId != buildB.bundleId
    verified = verifyBuild(world, result, buildA.bundleId)
    assert verified.result.artifact.verdict == "pending"
    cloud = world.clone("attacher")
    with pytest.raises(CustodyRefused, match="different candidate diff"):
        ops.publishVerdict(
            cloud, world.custody(cloud), debt, receiptPath=verified.result.receipt_path,
            buildBundleId=buildB.bundleId, writer={"role": "mechanical"},
        )
    # The same receipt IS accepted for the build it actually judged.
    ok = ops.publishVerdict(
        cloud, world.custody(cloud), debt, receiptPath=verified.result.receipt_path,
        buildBundleId=buildA.bundleId, writer={"role": "mechanical"},
    )
    assert ok.published


def test_a_receipt_for_a_different_proof_transcript_is_refused(world: World) -> None:
    _published, result = publishDispatch(world)
    debt = result.artifact.debt["id"]
    buildA = publishBuild(world, result)
    # Same diff, different (still valid) proof transcript.
    altered = json.loads(transcript(len(result.artifact.proof)))
    altered["entries"][0]["output"] = "different captured output"
    buildB = secondBuild(world, result, proof=json.dumps(altered))
    verified = verifyBuild(world, result, buildA.bundleId)
    cloud = world.clone("attacher")
    with pytest.raises(CustodyRefused, match="different proof transcript"):
        ops.publishVerdict(
            cloud, world.custody(cloud), debt, receiptPath=verified.result.receipt_path,
            buildBundleId=buildB.bundleId, writer={"role": "mechanical"},
        )


def test_a_receipt_for_another_debt_is_refused(tmp_path: Path) -> None:
    world = World(tmp_path, count=2)
    first, second = world.debts
    resultA = world.dispatch(first)
    resultB = world.dispatch(second)
    for result in (resultA, resultB):
        publishDispatch(world, result)
    buildA = publishBuild(world, resultA)
    buildB = publishBuild(world, resultB)
    verified = verifyBuild(world, resultA, buildA.bundleId)
    cloud = world.clone("attacher")
    with pytest.raises(CustodyRefused, match="different debt|different dispatch"):
        ops.publishVerdict(
            cloud, world.custody(cloud), second, receiptPath=verified.result.receipt_path,
            buildBundleId=buildB.bundleId, writer={"role": "mechanical"},
        )


def forgeVerdict(world: World, result: Any, *, receiptFrom: Any, onto: cu.PublishResult) -> cu.PublishResult:
    """Simulate a ref writer who bypasses the CLI: write a verdict bundle directly onto the remote."""

    debt = result.artifact.debt["id"]
    custody = world.custody(world.clone("forger"))
    commit, built = custody.select(debt, "build", bundleId=onto.bundleId)
    build = custody.loadAt(commit, built.bundleId, debt)
    receiptRaw = receiptFrom.result.receipt_path.read_bytes()
    art = cu.Artifact("verification-receipt", cu.sha256Hex(receiptRaw), len(receiptRaw), "forged.json")
    identity = {
        "kind": "verdict", "debtId": debt, "dispatchId": build.bundle.identity["dispatchId"],
        "dispatchReceiptId": build.bundle.identity["dispatchReceiptId"],
        "scanReceiptId": build.bundle.identity["scanReceiptId"],
        "sourceCommit": build.bundle.identity["sourceCommit"], "parent": build.bundle.bundleId,
        "verdict": "pending", "writer": {"role": "mechanical"},
        "binds": {"candidateDiff": build.bundle.artifacts["candidate-diff"]["sha256"],
                  "proofTranscript": build.bundle.artifacts["proof-transcript"]["sha256"],
                  "diffHash": "0" * 64, "transcriptHash": "0" * 64},
        "artifacts": {"verification-receipt": art.to_dict()},
    }
    return custody.publish(cu.makeBundle(identity, {"createdAt": cu.nowUtc()}), {art.sha256: receiptRaw})


def test_a_forged_verdict_is_refused_on_remote_retrieval_and_at_readiness(world: World) -> None:
    _published, result = publishDispatch(world)
    debt = result.artifact.debt["id"]
    buildA = publishBuild(world, result)
    buildB = secondBuild(world, result, diff=diffText().replace("new line", "a different line"))
    verifiedA = verifyBuild(world, result, buildA.bundleId)
    forged = forgeVerdict(world, result, receiptFrom=verifiedA, onto=buildB)  # bypasses publishVerdict entirely
    fresh = world.clone("reader")
    with pytest.raises(CustodyRefused, match="binding does not match|different candidate diff"):
        ops.readiness(world.custody(fresh), debt, bundleId=forged.bundleId)
    with pytest.raises(CustodyRefused, match="binding does not match|different candidate diff"):
        world.custody(fresh).chain(debt, forged.bundleId)
    # Restoring the same chain for verification is refused too, so a forged verdict is never trusted downstream.
    with pytest.raises(CustodyRefused, match="binding does not match|different candidate diff"):
        ops.restore(fresh, world.custody(fresh), debt, bundleId=forged.bundleId)


def test_a_verdict_bundle_whose_binding_fields_are_edited_is_refused(world: World) -> None:
    _published, result = publishDispatch(world)
    debt = result.artifact.debt["id"]
    built = publishBuild(world, result)
    verified = verifyBuild(world, result, built.bundleId)
    cloud = world.clone("pub")
    published = ops.publishVerdict(
        cloud, world.custody(cloud), debt, receiptPath=verified.result.receipt_path,
        buildBundleId=built.bundleId, writer={"role": "mechanical"},
    )
    path = cu.bundlePath(debt, published.bundleId)
    custody = world.custody(world.clone("r"))
    manifest = json.loads(custody.store.readFile(custody.store.snapshot(), path, limit=10**6))
    manifest["identity"]["binds"]["diffHash"] = "f" * 64
    corrupt(world, path, json.dumps(manifest).encode())
    with pytest.raises(CustodyRefused, match="altered after publication"):
        world.custody(world.clone("r2")).chain(debt)


def test_a_no_change_build_cannot_carry_a_mechanical_verdict(world: World) -> None:
    _published, result = publishDispatch(world)
    debt = result.artifact.debt["id"]
    real = publishBuild(world, result)
    verified = verifyBuild(world, result, real.bundleId)
    empty = ops.publishBuild(
        world.cloudA, world.custody(world.cloudA), debt,
        writer=ops.writerRecord(role="builder", agentId="b", model="haiku-5-5", effort="high"),
        summary="nothing to do", noChange=True, diffPath=None, proofPath=None,
    )
    cloud = world.clone("pub")
    with pytest.raises(CustodyRefused, match="no-change build"):
        ops.publishVerdict(
            cloud, world.custody(cloud), debt, receiptPath=verified.result.receipt_path,
            buildBundleId=empty.bundleId, writer={"role": "mechanical"},
        )


def test_the_genuine_chain_still_reaches_readiness_after_binding(world: World) -> None:
    _published, result = publishDispatch(world)
    debt = result.artifact.debt["id"]
    built = publishBuild(world, result)
    verified = verifyBuild(world, result, built.bundleId)
    cloud = world.clone("pub")
    ops.publishVerdict(
        cloud, world.custody(cloud), debt, receiptPath=verified.result.receipt_path,
        buildBundleId=built.bundleId, writer={"role": "mechanical"},
    )
    record = ops.readiness(world.custody(world.clone("reader")), debt)
    assert record["mechanicalVerdict"] == "pending" and record["independentVerifierRequired"] is True
    assert "not verified by this command" in record["writerAuthorization"]


# ---------------------------------------------------------------------------
# Codex finding 3: writer metadata is part of the identity; pins bind to authority recorded elsewhere
# ---------------------------------------------------------------------------


def test_writer_metadata_cannot_be_substituted_without_changing_the_bundle_id(world: World) -> None:
    published, result = publishDispatch(world)
    debt = result.artifact.debt["id"]
    path = cu.bundlePath(debt, published.bundleId)
    custody = world.custody(world.clone("r"))
    manifest = json.loads(custody.store.readFile(custody.store.snapshot(), path, limit=10**6))
    assert manifest["identity"]["writer"]["agentId"] == "lead-test"
    manifest["identity"]["writer"] = {"role": "lead", "agentId": "someone-else"}
    corrupt(world, path, json.dumps(manifest).encode())
    with pytest.raises(CustodyRefused, match="altered after publication"):
        world.custody(world.clone("r2")).chain(debt)


def test_the_build_summary_and_writer_are_authenticated_identity(world: World) -> None:
    _published, result = publishDispatch(world)
    one = publishBuild(world, result)
    other = ops.publishBuild(
        world.cloudA, world.custody(world.cloudA), result.artifact.debt["id"],
        writer=ops.writerRecord(role="builder", agentId="builder-2", model="haiku-5-5", effort="medium"),
        summary="fix", noChange=False, diffPath=world.cloudA / "candidate.diff", proofPath=world.cloudA / "proof.json",
    )
    assert one.bundleId != other.bundleId  # same bytes, different claimed writer => a different bundle


def completeChain(world: World) -> tuple[Any, str, cu.PublishResult, cu.PublishResult, cu.PublishResult]:
    _published, result = publishDispatch(world)
    debt = result.artifact.debt["id"]
    built = publishBuild(world, result)
    verified = verifyBuild(world, result, built.bundleId)
    cloud = world.clone("pub")
    verdict = ops.publishVerdict(
        cloud, world.custody(cloud), debt, receiptPath=verified.result.receipt_path,
        buildBundleId=built.bundleId, writer={"role": "mechanical"},
    )
    return result, debt, _published, built, verdict


def test_pins_accept_the_recorded_chain_and_refuse_a_substituted_one(world: World) -> None:
    result, debt, published, built, verdict = completeChain(world)
    reader = world.custody(world.clone("reader"))
    ok = ops.readiness(reader, debt, pinBundle=verdict.bundleId, pinCommit=verdict.commit)
    assert ok["bundles"][-1]["bundleId"] == verdict.bundleId
    with pytest.raises(CustodyRefused, match="not part of the custody chain"):
        ops.readiness(reader, debt, pinBundle="a" * 64)
    with pytest.raises(CustodyRefused, match="full 64-hex"):
        ops.readiness(reader, debt, pinBundle="abc")


def test_a_rewritten_history_is_detected_by_the_pinned_commit(world: World) -> None:
    result, debt, published, built, verdict = completeChain(world)
    pinned = verdict.commit
    # A ref writer force-pushes an unrelated root commit carrying the same files (history rewrite).
    work = world.tmp / "rewrite"
    subprocess.run(["git", "clone", "-q", "--branch", "steward/evidence", str(world.remote), str(work)], check=True)
    git(work, "checkout", "-q", "--orphan", "rewritten")
    git(work, "add", "-A")
    git(work, "commit", "-qm", "rewritten history")
    git(work, "push", "-q", "--force", "origin", "rewritten:refs/heads/steward/evidence")
    reader = world.custody(world.clone("reader"))
    # Content is intact, so without a pin the rewrite is invisible...
    assert ops.readiness(reader, debt)["mechanicalVerdict"] == "pending"
    # ...and with the commit recorded elsewhere it is caught.
    with pytest.raises(CustodyRefused, match="not an ancestor"):
        ops.readiness(world.custody(world.clone("reader2")), debt, pinCommit=pinned)


def test_the_ledger_recorded_dispatch_must_be_the_chains_dispatch(world: World) -> None:
    published, result = publishDispatch(world)
    debt = result.artifact.debt["id"]
    publishBuild(world, result)
    cloud = world.clone("cloudB")
    with pytest.raises(CustodyRefused, match="ledger recorded"):
        ops.restore(cloud, world.custody(cloud), debt, expectDispatchBundle="b" * 64)
    with pytest.raises(CustodyRefused, match="different dispatch"):
        ops.restore(cloud, world.custody(cloud), debt, expectDispatchId="dispatch-not-this-one")
    assert not (cloud / ".gaia" / "steward" / "receipts").exists(), "nothing is written before the binding is proven"


def test_original_prompt_is_restored_byte_for_byte_and_missing_prompt_is_refused(world: World) -> None:
    result = world.dispatch()
    debt = result.artifact.debt["id"]
    text = "# Tree Keeper dispatch\n\noriginal envelope text\n"
    withPrompt = ops.publishDispatch(
        world.cloudA, world.custody(world.cloudA), debt, writer=LEAD,
        scanRaw=result.scan.receipt_path.read_bytes(), dispatchRaw=result.receipt_path.read_bytes(), prompt=text,
    )
    cloud = world.clone("cloudB")
    restored = ops.originalPrompt(
        world.custody(cloud), debt, dispatchBundle=withPrompt.bundleId, dispatchId=result.artifact.dispatch_id,
    )
    assert restored == text
    with pytest.raises(CustodyRefused, match="different dispatch"):
        ops.originalPrompt(world.custody(cloud), debt, dispatchBundle=withPrompt.bundleId, dispatchId="dispatch-other")
    bare = ops.publishDispatch(
        world.cloudA, world.custody(world.cloudA), debt, writer={"role": "lead", "agentId": "other"},
        scanRaw=result.scan.receipt_path.read_bytes(), dispatchRaw=result.receipt_path.read_bytes(),
    )
    with pytest.raises(CustodyRefused, match="not preserved"):
        ops.originalPrompt(world.custody(cloud), debt, dispatchBundle=bare.bundleId, dispatchId=result.artifact.dispatch_id)


def test_a_legacy_verdict_without_binding_is_refused_with_a_clear_reason(world: World) -> None:
    _published, result = publishDispatch(world)
    debt = result.artifact.debt["id"]
    built = publishBuild(world, result)
    verified = verifyBuild(world, result, built.bundleId)
    custody = world.custody(world.clone("legacy"))
    commit, buildBundle = custody.select(debt, "build", bundleId=built.bundleId)
    build = custody.loadAt(commit, buildBundle.bundleId, debt)
    receiptRaw = verified.result.receipt_path.read_bytes()
    art = cu.Artifact("verification-receipt", cu.sha256Hex(receiptRaw), len(receiptRaw), "legacy.json")
    identity = {  # the pre-binding (v1) verdict shape: no writer, no binds
        "kind": "verdict", "debtId": debt, "dispatchId": build.bundle.identity["dispatchId"],
        "dispatchReceiptId": build.bundle.identity["dispatchReceiptId"],
        "scanReceiptId": build.bundle.identity["scanReceiptId"], "sourceCommit": build.bundle.identity["sourceCommit"],
        "parent": build.bundle.bundleId, "verdict": "pending", "artifacts": {"verification-receipt": art.to_dict()},
    }
    legacy = custody.publish(cu.makeBundle(identity, {"createdAt": cu.nowUtc()}), {art.sha256: receiptRaw})
    with pytest.raises(CustodyRefused, match="predates verdict binding"):
        ops.readiness(world.custody(world.clone("r")), debt, bundleId=legacy.bundleId)
    # The dispatch -> build chain it hangs from is still retrievable.
    assert ops.restore(world.clone("r2"), world.custody(world.clone("r3")), debt, bundleId=built.bundleId).build is not None
