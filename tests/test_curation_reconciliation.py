import copy
import hashlib
import json
import threading
import time

import pytest

from gaia_cli.curation.fanout import reconcileFanout, runFanout, shardFor
from gaia_cli.curation.reconciliation import canonicalJson, freezeInventory, reconcileInventory, sha256

GENERIC = [{"id": "animation-design", "kind": "generic", "name": "Animation Design"}]


def _snapshot(options):
    return {
        "capturedAt": "2026-01-01T00:00:00Z",
        "command": "gaia dev list --generic --json",
        "generics": copy.deepcopy(GENERIC),
        "contentSha256": sha256(canonicalJson(GENERIC)),
        "mappingOptionsSha256": sha256(canonicalJson(options)),
    }


def packet(row, *, identity=None, source_digest=None, revision=None, proposal=None, snapshot=None):
    cid = row["candidateId"]
    options = [{"genericId": "animation-design", "rationale": "Exact capability match.", "similarity": 0.9, "matchTier": "strong"}]
    decision = {"value": "MAP", "reasonCode": "MAP_EXISTING_GENERIC", "genericId": "animation-design"}
    if proposal is not None:
        decision = {"value": "NEW_GENERIC", "reasonCode": "NEW_GENERIC_PROPOSAL", "proposal": proposal}
    snap = snapshot or _snapshot(options)
    return {
        "contractVersion": "discovery-packet-v2",
        "candidateId": cid,
        "namedIdentity": identity or row["namedIdentity"],
        "lifecycle": ["discovered", "fetched", "parsed", "normalized", "deduped", "mapped", "review-ready"],
        "source": {
            "canonicalUrl": row["canonicalUrl"], "hostRepository": "https://example.test/repo",
            "sourceLane": "source-repository", "fetchedAt": "2026-01-01T00:00:00Z",
            "commitSha": row["sourceRevision"] if revision is None else revision,
            "contentSha256": source_digest or row["sourceDigest"],
            "frontmatter": {"name": "Animation", "description": "A complete animation skill for testing."},
        },
        "normalized": {"name": "Animation", "description": "A complete animation skill for testing."},
        "exactDedupe": {"matched": False, "matchedCandidateId": None, "matchedCanonicalUrl": None},
        "mappingOptions": options,
        "genericSnapshot": snap,
        "decision": decision,
        "flags": [],
    }


def inventory(count=12, *, revision=True):
    entries = []
    for i in range(count):
        cid = f"candidate-{i:02d}"
        entries.append({
            "candidateId": cid,
            "namedIdentity": f"author/animation-{i:02d}",
            "sourceRevision": f"revision-{i}" if revision else None,
            "freshnessRequired": not revision,
            "sourceDigest": hashlib.sha256(f"source-{i}".encode()).hexdigest(),
            "canonicalUrl": f"https://example.test/{i}/SKILL.md",
            "packetInput": {"packet": {"genericSnapshot": _snapshot([{"genericId": "animation-design", "rationale": "Exact capability match.", "similarity": 0.9, "matchTier": "strong"}])}, "immutable": {"source": i}},
        })
    return freezeInventory(entries)


def receipt(row, outcome="review-ready", *, packet_data=None, proposed=None, attempt=1, **extra):
    data = packet_data if packet_data is not None else canonicalJson(packet(row))
    return {
        "candidateId": row["candidateId"], "taskId": row["taskId"],
        "attempt": attempt, "inputDigest": row["inputDigest"],
        "outputDigest": sha256(data), "packetHash": sha256(data),
        "packetBytes": data, "packetPath": f"packets/{row['candidateId']}.json",
        "proposedGeneric": proposed or {"decision": "MAP", "genericId": "animation-design"},
        "outcome": outcome, **extra,
    }


def test_conserves_named_rows_with_shared_generic_and_retains_provenance():
    frozen = inventory()
    receipts = [receipt(row) for row in frozen["candidates"]]
    report = reconcileInventory(frozen, receipts)
    assert report["accounted"] and report["counts"]["review-ready"] == 12
    assert len({row["namedIdentity"] for row in report["decisions"]}) == 12
    assert all(row["packetDigest"] == row["outputDigest"] for row in report["decisions"])
    assert all(row["taskId"] and row["attempt"] == 1 and row["proposedGeneric"] for row in report["decisions"])
    assert report["humanApproved"] is False


def test_freeze_detaches_packet_input_and_requires_exact_lowercase_identity():
    candidate = {"candidateId": "c", "namedIdentity": "owner/my-skill", "sourceRevision": "rev",
                 "sourceDigest": "a" * 64, "canonicalUrl": "https://example.test/SKILL.md", "packetInput": {"nested": [1]}}
    frozen = freezeInventory([candidate])
    candidate["packetInput"]["nested"].append(2)
    assert frozen["candidates"][0]["packetInput"] == {"nested": [1]}
    for identity in ("Owner/name", "owner/Bad", "owner/name/extra", "owner/" ):
        with pytest.raises(ValueError, match="identity"):
            freezeInventory([{**candidate, "namedIdentity": identity}])


def test_unresolved_revision_requires_freshness_and_is_not_invented():
    frozen = inventory(1, revision=False)
    row = frozen["candidates"][0]
    assert row["sourceRevision"] is None and row["freshnessRequired"] is True
    assert reconcileInventory(frozen, [receipt(row)])["decisions"][0]["outcome"] == "review-ready"
    with pytest.raises(ValueError, match="freshnessRequired"):
        freezeInventory([{**row, "freshnessRequired": False}])


def test_packet_candidate_named_source_revision_digest_and_proposal_are_bound():
    frozen = inventory(1)
    row = frozen["candidates"][0]
    attacks = [
        packet(row, identity="other/identity"),
        packet(row, source_digest="f" * 64),
        packet(row, revision="other-revision"),
    ]
    for forged in attacks:
        decision = reconcileInventory(frozen, [receipt(row, packet_data=canonicalJson(forged))])["decisions"][0]
        assert decision["outcome"] == "deferred"
        assert decision["reason"]
    forged = receipt(row, proposed={"decision": "MAP", "genericId": "other-generic"})
    assert reconcileInventory(frozen, [forged])["decisions"][0]["outcome"] == "deferred"


def test_rejects_incomplete_or_untrusted_snapshot_and_does_not_require_human_review():
    frozen = inventory(1)
    row = frozen["candidates"][0]
    incomplete = {"contractVersion": "discovery-packet-v2", "candidateId": row["candidateId"]}
    result = reconcileInventory(frozen, [receipt(row, packet_data=canonicalJson(incomplete))])
    assert result["decisions"][0]["outcome"] == "deferred"
    # The valid packet fixture has no l4Resolution/humanReview, yet is review-ready.
    assert reconcileInventory(frozen, [receipt(row)])["counts"]["review-ready"] == 1


def test_exact_duplicate_requires_different_surviving_target_and_source_proof():
    frozen = inventory(2)
    first = frozen["candidates"][0]
    self_proof = {"targetNamedIdentity": first["namedIdentity"], "canonicalUrl": first["canonicalUrl"]}
    assert reconcileInventory(frozen, [receipt(first, "proven-duplicate", duplicateProof=self_proof)])["decisions"][0]["outcome"] == "deferred"
    missing_target = {"targetNamedIdentity": "author/not-present", "canonicalUrl": first["canonicalUrl"]}
    assert reconcileInventory(frozen, [receipt(first, "proven-duplicate", duplicateProof=missing_target)])["decisions"][0]["outcome"] == "deferred"
    target = frozen["candidates"][1]
    valid = {"targetNamedIdentity": target["namedIdentity"], "canonicalUrl": target["canonicalUrl"]}
    proven = reconcileInventory(frozen, [receipt(first, "proven-duplicate", duplicateProof=valid)])
    assert proven["decisions"][0]["outcome"] == "proven-duplicate"
    assert proven["decisions"][0]["duplicateProof"] == valid


def test_unknown_receipts_and_competing_attempts_are_reported_order_independently():
    frozen = inventory(1)
    row = frozen["candidates"][0]
    a, b = receipt(row), receipt(row, attempt=2)
    unknown = receipt({**row, "candidateId": "unknown"})
    one = reconcileInventory(frozen, [a, b, unknown])
    two = reconcileInventory(frozen, [unknown, b, a])
    assert one == two
    assert one["unknownReceipts"][0]["reason"] == "receipt references unknown candidate"
    assert one["decisions"][0]["outcome"] == "deferred"
    assert "multiple attempts" in one["decisions"][0]["reason"]


def test_conflicting_generic_definitions_reject_all_regardless_order():
    frozen = inventory(2)
    proposals = [
        {"name": "Motion", "description": "A precise motion capability definition.", "type": "basic"},
        {"name": "Motion", "description": "A different motion capability definition.", "type": "basic"},
    ]
    receipts = []
    for row, proposal in zip(frozen["candidates"], proposals):
        pkt = packet(row, proposal=proposal)
        receipts.append(receipt(row, proposed={"decision": "NEW_GENERIC", "proposal": proposal}, packet_data=canonicalJson(pkt)))
    one = reconcileInventory(frozen, receipts)
    two = reconcileInventory(frozen, reversed(receipts))
    assert one == two
    assert [r["outcome"] for r in one["decisions"]] == ["rejected", "rejected"]
    assert all("conflicting full definitions" in r["reason"] for r in one["decisions"])


def test_missing_receipts_are_deferred_without_loss():
    report = reconcileInventory(inventory(), [])
    assert report["accounted"] and report["counts"]["deferred"] == 12
    assert all(row["reason"] for row in report["decisions"])


def test_fanout_retries_worker_exceptions_and_is_completion_order_independent():
    frozen = inventory(4)
    calls = {}
    def worker(row, attempt):
        cid = row["candidateId"]
        calls[cid] = calls.get(cid, 0) + 1
        if cid.endswith("02") and attempt == 1:
            raise RuntimeError("transient")
        return receipt(row)
    result = runFanout(frozen, worker, maxWorkers=3, maxAttempts=2)
    assert len(result["receipts"]) == 4 and calls["candidate-02"] == 2
    assert reconcileInventory(frozen, result["receipts"])["counts"]["review-ready"] == 4
    assert result["attemptBudget"] == 8 and result["budgetUnit"] == "candidate-tasks"


def test_deterministically_invalid_receipt_is_not_retried_and_errors_reconcile():
    frozen = inventory(1)
    calls = []
    def worker(row, attempt):
        calls.append(attempt)
        return receipt(row, packet_data=canonicalJson({"contractVersion": "discovery-packet-v2", "candidateId": row["candidateId"]}))
    result = runFanout(frozen, worker, maxAttempts=4)
    assert calls == [1]
    assert reconcileFanout(frozen, result)["decisions"][0]["reason"]


def test_budget_counts_candidate_tasks_and_missing_worker_errors_survive():
    frozen = inventory(12)
    result = runFanout(frozen, lambda row, attempt: receipt(row), maxTasks=5, maxAttempts=3)
    assert len(result["receipts"]) == 5
    assert result["attemptBudget"] == 15
    report = reconcileFanout(frozen, result)
    assert report["counts"]["deferred"] == 7
    assert all("budget exhausted" in row["reason"] for row in report["decisions"] if row["outcome"] == "deferred")
    missing = runFanout(inventory(2), None)
    assert all(row["reason"] == "worker unavailable" for row in reconcileFanout(inventory(2), missing)["decisions"])


def test_prior_deferred_receipt_is_redispatched_but_valid_receipt_is_retained():
    frozen = inventory(2)
    row0, row1 = frozen["candidates"]
    prior = [receipt(row0, "deferred", reason="temporary"), receipt(row1)]
    seen = []
    result = runFanout(frozen, lambda row, attempt: (seen.append((row["candidateId"], attempt)) or receipt(row)), priorReceipts=prior)
    assert seen == [(row0["candidateId"], 1)]
    assert len(result["receipts"]) == 2


def test_prior_receipt_attempts_and_receipt_order_conflict_are_deterministic():
    frozen = inventory(1)
    row = frozen["candidates"][0]
    one, two = receipt(row), receipt(row, attempt=2)
    assert reconcileInventory(frozen, [one, two]) == reconcileInventory(frozen, [two, one])


def test_timeout_late_worker_cannot_change_reconciled_snapshot():
    frozen = inventory(1)
    row = frozen["candidates"][0]
    late = []
    gate = threading.Event()
    def worker(task, attempt):
        gate.wait(0.15)
        late.append(receipt(row))
        return receipt(row)
    result = runFanout(frozen, worker, timeoutSeconds=0.01)
    before = reconcileFanout(frozen, result)
    gate.set()
    time.sleep(0.2)
    assert late
    assert before == reconcileFanout(frozen, result)
    assert before["decisions"][0]["outcome"] == "deferred"


def test_inventory_digest_detects_mutation():
    frozen = inventory(1)
    frozen["candidates"][0]["namedIdentity"] = "changed/name"
    with pytest.raises(ValueError, match="inventory digest"):
        reconcileInventory(frozen, [])


def test_stable_sharding_and_safe_packet_path():
    ids = [f"candidate-{i}" for i in range(20)]
    assert {cid: shardFor(cid, 7) for cid in ids} == {cid: shardFor(cid, 7) for cid in reversed(ids)}
    frozen = inventory(1)
    row = frozen["candidates"][0]
    bad = receipt(row)
    bad.pop("packetBytes")
    bad["packetPath"] = "../escape.json"
    assert reconcileInventory(frozen, [bad])["decisions"][0]["outcome"] == "deferred"
