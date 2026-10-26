"""Actual domain receipt-port integration. All authorities are TEST-only memory.

Unlike the synthetic watch fixtures, these exercise open/close/history validation
through gaia_cli.challengeDomain and the production bridge's fail-closed seam.
"""
from dataclasses import replace
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]
for path in (ROOT, ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from test_challenge_domain import opened, proof, resolve_close
from gaia_cli.steward.ledger import FileLedgerStore
from scripts.upstream_watcher.admission import DomainChallengeAdmissionResolver
from scripts.upstream_watcher.challenge_watch import (
    ChallengeComparator, ChallengeTarget, WatchLedger, run_challenge_watch,
)
from scripts.upstream_watcher.transport import SimulatedTransport, VirtualClock


def domain_fixture():
    challenge, receipts = opened(subject_id="pbakaus/impeccable", comparator="competitor/rival@v1")
    lookup = {challenge.challenge_id: challenge}
    adapter = DomainChallengeAdmissionResolver(
        challenge_lookup=lookup.__getitem__, receipt_resolver=receipts,
        targets={challenge.subject_id: ChallengeTarget(challenge.subject_id, "pbakaus", "impeccable",
                                                     challenge.pinned_version, challenge.pinned_sha)},
        comparators={challenge.comparator: ChallengeComparator(challenge.comparator, "competitor", "rival",
                                                               True, pinned_version="v1")},
    )
    return challenge, receipts, lookup, adapter


def execute(tmp_path, raw, adapter=None, at="2026-10-26T00:00:00Z"):
    transport = SimulatedTransport()
    transport.register_probe("https://github.com/pbakaus/impeccable", status_code=200)
    transport.register_release("pbakaus", "impeccable", tag="new-version")
    result = run_challenge_watch(
        challenges=raw, admission_resolver=adapter, transport=transport, clock=VirtualClock(at),
        shared_store=FileLedgerStore(tmp_path / "operations.json"), packets_dir=tmp_path / "packets",
    )
    return result, transport


def test_domain_open_and_receipt_authorized_closure_not_caller_status(tmp_path):
    challenge, receipts, lookup, adapter = domain_fixture()
    raw = [{"challengeId": challenge.challenge_id}]
    result, transport = execute(tmp_path, raw, adapter)
    assert result.active_count == 1
    assert result.packets
    assert len(transport.recorded_requests) == 7
    closure = resolve_close(challenge, proof(challenge), receipts)
    assert closure.challenge.resolved
    lookup[challenge.challenge_id] = closure.challenge
    result, transport = execute(tmp_path, raw, adapter, at="2026-10-28T00:00:00Z")
    assert result.resolved_count == 1
    assert result.active_count == 0
    assert transport.recorded_requests == []
    assert [p.trigger_type for p in result.packets] == ["returned_to_routine"]
    assert result.packets[0].canonical_mutation is None
    # A stale lookup cannot reactivate a terminal immutable challenge identity.
    lookup[challenge.challenge_id] = challenge
    result, transport = execute(tmp_path, raw, adapter, at="2026-10-29T00:00:00Z")
    assert transport.recorded_requests == []
    assert result.packets == []
    assert result.active_count == 0
    assert result.resolved_count == 1
    state = WatchLedger(shared_store=FileLedgerStore(tmp_path / "operations.json"))
    assert state.challenges[challenge.challenge_id]["targeted_monitoring"] == "returned_to_routine"


@pytest.mark.parametrize("attack", ["missing", "context", "independence", "history", "output"])
def test_domain_revalidates_full_receipts_on_every_cached_run(tmp_path, attack):
    challenge, receipts, _, adapter = domain_fixture()
    raw = [{"challengeId": challenge.challenge_id}]
    execute(tmp_path, raw, adapter)
    receipt = receipts.receipts["open-receipt"]
    if attack == "missing":
        receipts.receipts.clear()
    else:
        changes = {
            "context": {"context_digest": "wrong-context"},
            "independence": {"builder_id": receipt.verifier_id},
            "history": {"method_version": "different-history"},
            "output": {"output_digest": "different-output"},
        }[attack]
        receipts.receipts["open-receipt"] = replace(receipt, **changes)
    result, transport = execute(tmp_path, [], adapter, at="2026-10-27T00:00:00Z")
    assert result.active_count == result.resolved_count == 0
    assert result.rejected_unverified_count == 1
    assert result.packets == []
    assert transport.recorded_requests == []


@pytest.mark.parametrize("raw", [
    {"challengeId": "native-lead", "packetType": "challenger-lead-v1", "status": "verified-pending"},
    {"challengeId": "experiment", "approvedBy": "founder", "independentlyVerified": True},
    {"challengeId": "missing-domain-challenge"},
])
def test_native_leads_experiments_and_inline_flags_never_admitted(tmp_path, raw):
    _, _, _, adapter = domain_fixture()
    result, transport = execute(tmp_path, [raw], adapter)
    assert result.active_count == result.resolved_count == 0
    assert result.rejected_unverified_count == 1
    assert result.packets == []
    assert transport.recorded_requests == []
    state = WatchLedger(shared_store=FileLedgerStore(tmp_path / "operations.json"))
    assert state.inputs == []
    assert state.observations == {}
    assert state.challenges == {}


def test_without_domain_port_even_real_receipt_reference_is_unavailable(tmp_path):
    challenge, _, _, _ = domain_fixture()
    result, transport = execute(tmp_path, [{"challengeId": challenge.challenge_id}])
    assert result.unavailable_count == 1
    assert result.active_count == result.resolved_count == 0
    assert transport.recorded_requests == []


def test_domain_repository_context_is_bound_not_selected_from_manifest(tmp_path):
    challenge, _, _, adapter = domain_fixture()
    adapter.targets = {challenge.subject_id: ChallengeTarget(challenge.subject_id, "wrong", "repo", "wrong", "sha")}
    result, transport = execute(tmp_path, [{"challengeId": challenge.challenge_id}], adapter)
    assert result.rejected_unverified_count == 1
    assert not transport.recorded_requests
