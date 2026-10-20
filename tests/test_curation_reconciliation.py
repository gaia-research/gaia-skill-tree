import hashlib
import json

import pytest

from gaia_cli.curation.fanout import runFanout, shardFor
from gaia_cli.curation.reconciliation import canonicalJson, freezeInventory, reconcileInventory, sha256


def inventory(count=12):
    return freezeInventory([
        {
            "candidateId": f"candidate-{i:02d}",
            "namedIdentity": f"author/animation-{i:02d}",
            "sourceRevision": f"commit-{i}",
            "sourceDigest": hashlib.sha256(f"source-{i}".encode()).hexdigest(),
            "canonicalUrl": f"https://example.test/{i}/SKILL.md",
            "packetInput": {"candidateId": f"candidate-{i:02d}", "body": f"source-{i}"},
        }
        for i in range(count)
    ])


def packet(cid):
    return {"contractVersion": "discovery-packet-v2", "candidateId": cid}


def receipt(row, outcome="review-ready", *, proposed=None, packet_data=None, **extra):
    packet_data = packet_data or canonicalJson(packet(row["candidateId"]))
    return {
        "candidateId": row["candidateId"], "taskId": row["taskId"],
        "attempt": 1, "inputDigest": row["inputDigest"],
        "outputDigest": sha256(packet_data), "packetHash": sha256(packet_data),
        "packetBytes": packet_data, "packetPath": f"packets/{row['candidateId']}.json",
        "proposedGeneric": proposed, "outcome": outcome, **extra,
    }


def test_freeze_and_reconcile_conserves_twelve_six_shared_generic_rows():
    frozen = inventory()
    shared = {"decision": "MAP", "genericId": "animation-design"}
    receipts = [receipt(row, proposed=shared) for row in frozen["candidates"]]
    report = reconcileInventory(frozen, receipts)
    assert report["accounted"] is True
    assert report["candidateCount"] == 12
    assert report["counts"]["review-ready"] == 12
    assert len({row["namedIdentity"] for row in report["decisions"]}) == 12
    assert all(row["outcome"] == "review-ready" for row in report["decisions"])
    assert report["humanApproved"] is False


def test_exact_duplicate_requires_source_proof():
    frozen = inventory(1)
    row = frozen["candidates"][0]
    unproven = reconcileInventory(frozen, [receipt(row, "proven-duplicate")])
    assert unproven["decisions"][0]["outcome"] == "deferred"
    proof = {"canonicalUrl": row["canonicalUrl"]}
    proven = reconcileInventory(frozen, [receipt(row, "proven-duplicate", duplicateProof=proof)])
    assert proven["decisions"][0]["outcome"] == "proven-duplicate"


def test_conflicting_full_generic_definitions_reject_all_regardless_order():
    frozen = inventory(2)
    proposals = [
        {"decision": "NEW_GENERIC", "genericId": "new-motion", "definition": {"name": "Motion", "description": "one"}},
        {"decision": "NEW_GENERIC", "genericId": "new-motion", "definition": {"name": "Motion", "description": "two"}},
    ]
    receipts = [receipt(row, proposed=proposal) for row, proposal in zip(frozen["candidates"], proposals)]
    one = reconcileInventory(frozen, receipts)
    two = reconcileInventory(frozen, reversed(receipts))
    assert [r["outcome"] for r in one["decisions"]] == ["rejected", "rejected"]
    assert one == two
    assert all("conflicting full definitions" in r["reason"] for r in one["decisions"])


def test_self_asserted_digest_and_wrong_task_are_not_trusted():
    frozen = inventory(1)
    row = frozen["candidates"][0]
    bad = receipt(row)
    bad["packetBytes"] = canonicalJson(packet("tampered"))
    report = reconcileInventory(frozen, [bad])
    assert report["decisions"][0]["outcome"] == "deferred"
    wrong_task = receipt(row)
    wrong_task["taskId"] = "someone-elses-task"
    assert reconcileInventory(frozen, [wrong_task])["decisions"][0]["outcome"] == "deferred"


def test_inventory_digest_detects_mutation():
    frozen = inventory(1)
    frozen["candidates"][0]["namedIdentity"] = "changed/name"
    with pytest.raises(ValueError, match="inventory digest"):
        reconcileInventory(frozen, [])


def test_missing_receipts_are_deferred_without_loss():
    report = reconcileInventory(inventory(), [])
    assert report["accounted"]
    assert report["counts"]["deferred"] == 12


def test_fanout_retries_and_is_completion_order_independent():
    frozen = inventory(4)
    calls = {}
    def worker(row, attempt):
        cid = row["candidateId"]
        calls[cid] = calls.get(cid, 0) + 1
        if cid.endswith("02") and attempt == 1:
            raise RuntimeError("transient")
        return receipt(row, outcome="review-ready")
    result = runFanout(frozen, worker, maxWorkers=3, maxAttempts=2)
    assert len(result["receipts"]) == 4
    assert calls["candidate-02"] == 2
    assert reconcileInventory(frozen, result["receipts"])["counts"]["review-ready"] == 4


def test_budget_exhaustion_and_missing_worker_defer_candidates():
    frozen = inventory(12)
    def worker(row, attempt):
        return receipt(row)
    result = runFanout(frozen, worker, maxTasks=5)
    assert len(result["receipts"]) == 5
    report = reconcileInventory(frozen, result["receipts"])
    assert report["counts"]["deferred"] == 7
    missing = runFanout(frozen, None)
    assert len(missing["errors"]) == 12
    assert reconcileInventory(frozen, missing["receipts"])["counts"]["deferred"] == 12


def test_partial_resume_skips_valid_prior_packets():
    frozen = inventory(3)
    prior = [receipt(frozen["candidates"][0])]
    seen = []
    result = runFanout(frozen, lambda row, attempt: (seen.append(row["candidateId"]) or receipt(row)), priorReceipts=prior)
    assert len(result["receipts"]) == 3
    assert set(seen) == {"candidate-01", "candidate-02"}


def test_stable_sharding_does_not_depend_on_order():
    ids = [f"candidate-{i}" for i in range(20)]
    assert {cid: shardFor(cid, 7) for cid in ids} == {cid: shardFor(cid, 7) for cid in reversed(ids)}


def test_safe_packet_path_rejects_traversal(tmp_path):
    frozen = inventory(1)
    row = frozen["candidates"][0]
    bad = receipt(row)
    bad.pop("packetBytes")
    bad["packetPath"] = "../escape.json"
    assert reconcileInventory(frozen, [bad], packetRoot=tmp_path)["decisions"][0]["outcome"] == "deferred"


def test_six_named_rows_are_never_collapsed_by_shared_mapping():
    frozen = inventory(6)
    receipts = [receipt(row, proposed={"decision": "MAP", "genericId": "animation-design"}) for row in frozen["candidates"]]
    report = reconcileInventory(frozen, receipts)
    assert [row["candidateId"] for row in report["decisions"]] == [f"candidate-{i:02d}" for i in range(6)]
    assert report["counts"]["review-ready"] == 6
