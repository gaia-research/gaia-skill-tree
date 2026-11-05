"""Strict core/fault/accounting tests; no network other than disposable local Git."""

from __future__ import annotations

import copy
import os
import pickle
import threading
from dataclasses import asdict, replace

import pytest

from gaia_cli.steward import ledger
from gaia_cli.steward.prmaintenance import coordination as core
from .coordination_helpers import (
    FakeServices, NAMESPACE, clone, coordinator, evidence, git, prepared, proof, seed, subject,
)


@pytest.fixture
def fixture(tmp_path, monkeypatch):
    return seed(tmp_path, monkeypatch)


def test_canonical_ref_only_no_file_or_legacy_fallback(fixture, tmp_path):
    remote, binding, first, second = fixture
    with pytest.raises(core.CoordinationError):
        core.PrWriteCoordinator(ledger.FileLedgerStore(tmp_path / "unused"), binding, FakeServices())
    with pytest.raises(core.CoordinationError):
        core.PrWriteCoordinator(ledger.GitRefLedgerStore(first), binding, FakeServices())
    with pytest.raises(core.CoordinationError):
        coordinator(first, replace(binding, canonicalUrl="https://elsewhere.invalid/repo.git"))
    before = git(remote, "show-ref")
    coord = coordinator(first, binding)
    assert coord.inspect()["operations"] == {}
    assert git(remote, "show-ref") == before
    assert not (tmp_path / "unused").exists()


def test_missing_ref_and_missing_pinned_genesis_never_bootstrap(fixture):
    remote, binding, first, second = fixture
    with pytest.raises(core.CoordinationError, match="genesis/history"):
        coordinator(first, replace(binding, genesis="d" * 40)).inspect()
    with pytest.raises(core.CoordinationError, match="genesis/history"):
        coordinator(first, replace(binding, historyPin="e" * 40)).inspect()
    git(remote, "update-ref", "-d", f"refs/heads/{core.REF}")
    with pytest.raises(core.CoordinationError, match="missing provisioned"):
        coordinator(first, binding).reserve(subject(), proof(), "run", "owner", "reserve")
    assert git(remote, "for-each-ref", "refs/heads") == ""


@pytest.mark.parametrize("corruption", ["namespace", "schema", "extra", "legacy", "history", "generation", "nonfinite"])
def test_malformed_nested_state_or_history_fails_closed(fixture, corruption):
    remote, binding, first, second = fixture
    coord = coordinator(first, binding)
    prepared(coord)
    document, tip = coord.store.load()
    payload = document["operations"][core.KEY]
    if corruption == "namespace":
        payload["namespace"]["repositoryId"] = "wrong-immutable-id"
    elif corruption == "schema":
        payload["schemaVersion"] = "unsupported"
    elif corruption == "extra":
        payload["events"][0]["args"]["proof"]["verification"]["callerApproval"] = True
    elif corruption == "legacy":
        document["runs"] = {"legacy": {"runId": "legacy"}}
    elif corruption == "history":
        payload["events"][0]["args"]["proof"]["justification"] = "rewritten durable proof"
    elif corruption == "generation":
        document["generation"] = 100
    elif corruption == "nonfinite":
        payload["events"][0]["time"]["lower"] = float("nan")
        with pytest.raises(ledger.LedgerUnavailable):
            coord.store.compare_and_swap(tip, document, "bad")
        return
    coord.store.compare_and_swap(tip, document, "intentionally invalid fixture history")
    with pytest.raises(core.CoordinationError):
        coordinator(second, binding).inspect()


def test_reset_non_descendant_and_rewind_seen_history_fail_closed(fixture):
    remote, binding, first, second = fixture
    coord = coordinator(first, binding)
    prepared(coord)
    coord.inspect()
    git(remote, "update-ref", f"refs/heads/{core.REF}", binding.genesis)
    with pytest.raises(core.CoordinationError, match="reset/non-descendant"):
        coord.inspect()
    # An unrelated well-formed genesis is not the pinned one, even cold.
    document, _ = coord.store.load()
    document["generation"] = 0
    blob = coord.store.plumb(["hash-object", "-w", "--stdin"], stdin=ledger.serialize(document))
    tree = coord.store.plumb(["mktree"], stdin=f"100644 blob {blob}\tledger.json\n".encode())
    other = coord.store.plumb(["commit-tree", tree, "-m", "unrelated genesis"], identity=True)
    git(remote, "fetch", str(first), other)
    git(remote, "update-ref", f"refs/heads/{core.REF}", other)
    with pytest.raises(core.CoordinationError, match="genesis/history"):
        coordinator(second, binding).inspect()


def test_identity_immutable_bindings_and_stable_replay(fixture):
    remote, binding, first, second = fixture
    coord = coordinator(first, binding)
    token = prepared(coord)
    resumed = coordinator(second, binding)
    replay = resumed.reserve(subject(), proof(), "stable-run", "owner-1", "reserve-1")
    assert replay.status == core.CommitStatus.ALREADY and replay.token == token
    with pytest.raises(core.Refused):
        resumed.reserve(subject(), proof(), "new-run-cannot-reset", "other-owner", "different-id")
    altered = proof()
    altered["authority"] += " caller revision"
    with pytest.raises(core.CoordinationError):
        resumed.reserve(subject(), altered, "stable-run", "owner-1", "reserve-1")
    with pytest.raises(core.Refused, match="different immutable command"):
        resumed.cancelPrepared(token, "not the reserve command", "reserve-1")
    assert core.logicalId(NAMESPACE, subject()) == token.operationId
    assert core.logicalId(NAMESPACE, subject(action="close")) != token.operationId
    assert core.logicalId(replace(NAMESPACE, epoch="f" * 32), subject()) != token.operationId


@pytest.mark.parametrize("action,number", [("merge", 1), ("close", 1), ("merge", 2), ("close", 2)])
def test_one_slot_excludes_same_and_different_pr_actions(fixture, action, number):
    _, binding, first, second = fixture
    prepared(coordinator(first, binding))
    candidate = subject(number, action)
    with pytest.raises(core.Refused):
        coordinator(second, binding).reserve(candidate, proof(candidate), "another-run", "owner", "other-reserve")


def test_preparation_takeover_fences_old_owner_but_claim_never_expires(fixture):
    _, binding, first, second = fixture
    services = FakeServices()
    coord = coordinator(first, binding, services)
    token = prepared(coord)
    services.now = core.TimeBounds(10121, 10121, "fixture-authoritative-clock")
    adopted = coord.takeover(token, "new-owner", "takeover").token
    assert adopted.fence > token.fence and adopted.attemptId == token.attemptId
    with pytest.raises(core.Refused):
        coord.invoke(token, "stale-claim")
    services.response = "lost"
    coord.invoke(adopted, "claim")
    services.now = core.TimeBounds(999999, 999999, "fixture-authoritative-clock")
    with pytest.raises(core.Refused):
        coord.takeover(adopted, "third-owner", "bad-takeover")
    with pytest.raises(core.Refused):
        coord.cancelPrepared(adopted, "local run superseded", "bad-cancel")
    assert coord.recover(token.operationId).state == "quarantined"
    tip = coord.store.remoteTip()
    assert coord.recover(token.operationId).status == core.CommitStatus.ALREADY
    assert coord.store.remoteTip() == tip
    assert len(services.invocations) == len(services.effects) == 1


@pytest.mark.parametrize("kind", ["reserve", "intent", "takeover", "cancel", "claim", "unknown", "quarantine", "complete", "merge-terminal"])
@pytest.mark.parametrize("fault", ["ack-loss", "conflict"])
def test_every_transition_ack_loss_and_cas_retry(fixture, monkeypatch, kind, fault):
    _, binding, first, second = fixture
    services = FakeServices()
    coord = coordinator(first, binding, services)
    original = coord.store.compare_and_swap
    injected = []

    def faulty(expected, document, message):
        if message.split()[1] == kind and not injected:
            injected.append(True)
            if fault == "conflict":
                raise ledger.LedgerConflict("injected failed snapshot")
            original(expected, document, message)
            raise ledger.LedgerUnavailable("push accepted, acknowledgement lost")
        return original(expected, document, message)

    monkeypatch.setattr(coord.store, "compare_and_swap", faulty)
    result = coord.reserve(subject(), proof(), "stable-run", "owner-1", "reserve-1")
    token = result.token
    if kind != "reserve":
        result = coord.recordIntent(token, core.exactRequest(NAMESPACE, subject()), "intent-1")
    if kind == "takeover":
        services.now = core.TimeBounds(10121, 10121, "fixture-authoritative-clock")
        result = coord.takeover(token, "new-owner", "takeover")
    elif kind == "cancel":
        result = coord.cancelPrepared(token, "safe unsent", "cancel")
    elif kind in {"claim", "unknown", "quarantine", "complete", "merge-terminal"}:
        services.response = "effect" if kind in {"claim", "complete"} else "lost"
        result = coord.invoke(token, "claim")
        if kind in {"quarantine", "merge-terminal"}:
            services.observed = ("observed-terminal", "merged") if kind == "merge-terminal" else None
            result = coord.recover(token.operationId)
    assert injected == [True]
    assert result.status == (core.CommitStatus.ALREADY if fault == "ack-loss" else core.CommitStatus.NEW)
    state = coordinator(second, binding).inspect()
    assert len(state["operations"]) == 1
    events = coord._load()[0]["operations"][core.KEY]["events"]
    assert sum(event["kind"] == kind for event in events) == 1
    expectedInvocations = int(kind in {"claim", "unknown", "quarantine", "complete", "merge-terminal"})
    if kind == "claim" and fault == "ack-loss":
        expectedInvocations = 0
        assert state["activeOperationId"] == token.operationId
        # Copied token and restarted claimant cannot manufacture a grant.
        restarted = coordinator(second, binding, FakeServices())
        assert restarted.invoke(token, "claim").status == core.CommitStatus.ALREADY
        assert restarted.services.invocations == []
    assert len(services.invocations) == len(services.effects) == expectedInvocations
    assert core.usage(state, services.now, "stable-run", "merge")[0] == (0 if kind == "cancel" else 1)


def test_unresolved_push_never_grants_or_initializes(fixture, monkeypatch):
    _, binding, first, second = fixture
    services = FakeServices()
    coord = coordinator(first, binding, services)
    token = prepared(coord)
    def unavailable(*args):
        raise ledger.LedgerUnavailable("transport unavailable before/after unknown push")
    monkeypatch.setattr(coord.store, "compare_and_swap", unavailable)
    result = coord.invoke(token, "claim")
    assert result.status == core.CommitStatus.UNRESOLVED
    assert coordinator(second, binding).inspect()["operations"][token.operationId]["state"] == "intent"
    assert services.invocations == services.effects == []


def test_process_local_grant_cannot_copy_serialize_reuse_or_cross_thread(fixture, monkeypatch):
    _, binding, first, second = fixture
    services = FakeServices()
    coord = coordinator(first, binding, services)
    other = coordinator(second, binding)
    token = prepared(coord)
    consume = coord._consume
    checked = []

    def checkedConsume(grant, operation):
        for copier in (copy.copy, copy.deepcopy, pickle.dumps):
            with pytest.raises(TypeError):
                copier(grant)
        with pytest.raises(core.Refused):
            other._consume(grant, operation)
        failures = []
        def threadConsume():
            try:
                consume(grant, operation)
            except core.Refused:
                failures.append(True)
        thread = threading.Thread(target=threadConsume)
        thread.start()
        thread.join(5)
        assert not thread.is_alive() and failures == [True]
        forged = core._Grant(operation)
        with pytest.raises(core.Refused):
            consume(forged, operation)
        consume(grant, operation)
        with pytest.raises(core.Refused):
            consume(grant, operation)
        checked.append(True)

    monkeypatch.setattr(coord, "_consume", checkedConsume)
    assert coord.invoke(token, "claim").state == "completed-effect"
    assert checked == [True]
    assert len(services.invocations) == len(services.effects) == 1
    assert coord.invoke(token, "claim").status == core.CommitStatus.ALREADY
    assert len(services.invocations) == 1


def test_quotas_count_rejections_and_resume_run_and_only_cancel_refunds(fixture):
    _, binding, first, second = fixture
    services = FakeServices()
    coord = coordinator(first, binding, services)
    firstToken = prepared(coord, 1)
    coord.cancelPrepared(firstToken, "unsent", "cancel")
    services.response = "reject"
    coord.invoke(prepared(coord, 2), "claim-2")
    coord.invoke(prepared(coord, 3), "claim-3")
    assert len(services.invocations) == 2 and services.effects == []
    with pytest.raises(core.Refused, match="ceiling"):
        prepared(coordinator(second, binding), 4)
    # Both action-specific run ceilings remain 2, combined hourly cap is shared.
    for number in (5, 6):
        coord.invoke(prepared(coord, number, "close"), f"claim-{number}")
    with pytest.raises(core.Refused, match="ceiling"):
        prepared(coord, 7, "close")
    state = coord.inspect()
    assert core.usage(state, services.now, "stable-run", "merge") == (2, 4)
    assert core.usage(state, services.now, "stable-run", "close") == (2, 4)


def test_hourly_last_token_unknown_pinned_and_exact_expiry_boundary(fixture):
    _, binding, first, second = fixture
    services = FakeServices()
    services.caps = core.Limits(writesPerHour=1)
    coord = coordinator(first, binding, services)
    coord.invoke(prepared(coord), "claim-1")
    services.now = core.TimeBounds(13600, 13610, "fixture-authoritative-clock")
    with pytest.raises(core.Refused, match="ceiling"):
        prepared(coord, 2, run="another-stable-run")
    services.now = core.TimeBounds(13601, 13611, "fixture-authoritative-clock")
    services.response = "lost"
    token = prepared(coord, 2, run="another-stable-run")
    coord.invoke(token, "claim-2")
    services.now = core.TimeBounds(999999, 999999, "fixture-authoritative-clock")
    with pytest.raises(core.Refused, match="global critical slot"):
        prepared(coord, 3, run="third-run")
    state = coord.inspect()
    assert state["activeOperationId"] == token.operationId
    assert core.usage(state, services.now, "third-run", "merge")[1] == 1


@pytest.mark.parametrize("bad", [None, core.TimeBounds(10001, 10000, "clock"), core.TimeBounds(10000, 10031, "clock"),
                                 core.TimeBounds(9999, 10000, "clock"), core.TimeBounds(10000, 9999, "clock"),
                                 core.TimeBounds(True, 10000, "clock")])
def test_missing_invalid_regressing_clock_fails_admission_and_expiry_closed(fixture, bad):
    _, binding, first, second = fixture
    services = FakeServices()
    coord = coordinator(first, binding, services)
    token = prepared(coord)
    coord.cancelPrepared(token, "unsent", "cancel")
    tip = coord.store.remoteTip()
    services.now = bad
    with pytest.raises(core.CoordinationError):
        prepared(coord, 2, run="fresh-run")
    assert coord.store.remoteTip() == tip


def test_lowered_caps_block_claim_and_caller_cannot_raise_hard_ceiling(fixture):
    _, binding, first, second = fixture
    services = FakeServices()
    coord = coordinator(first, binding, services)
    token = prepared(coord)
    services.caps = core.Limits(mergesPerRun=0)
    with pytest.raises(core.Refused, match="ceiling"):
        coord.invoke(token, "claim")
    services.caps = core.Limits(mergesPerRun=3)
    with pytest.raises(core.CoordinationError):
        coord.invoke(token, "claim")
    assert services.invocations == []


@pytest.mark.parametrize("action", ["merge", "close"])
def test_lost_response_negative_or_closed_observations_do_not_settle(fixture, action):
    _, binding, first, second = fixture
    services = FakeServices()
    services.response = "lost"
    coord = coordinator(first, binding, services)
    token = prepared(coord, action=action)
    coord.invoke(token, "claim")
    # Open/closed GETs are both inconclusive; no independent merge fact.
    assert coord.recover(token.operationId).state == "quarantined"
    for _ in range(3):
        assert coord.recover(token.operationId).status == core.CommitStatus.ALREADY
    assert len(services.invocations) == len(services.effects) == 1
    assert core.usage(coord.inspect(), services.now, "stable-run", action) == (1, 1)
    with pytest.raises(core.Refused):
        coord.invoke(token, "new-claim")


def test_independent_matching_merge_settles_but_forged_stale_and_close_facts_do_not(fixture):
    _, binding, first, second = fixture
    services = FakeServices()
    services.response = "lost"
    coord = coordinator(first, binding, services)
    token = prepared(coord)
    coord.invoke(token, "claim")
    operation = coord.inspect()["operations"][token.operationId]
    stale = evidence(operation, "observed-terminal", "merged")
    stale["requestDigest"] = "0" * 64
    services.observation = lambda operation: stale
    with pytest.raises(core.CoordinationError, match="exact invocation"):
        coord.recover(token.operationId)
    services.observation = lambda operation: evidence(operation, "observed-terminal", "closed")
    with pytest.raises(core.CoordinationError, match="absorbing"):
        coord.recover(token.operationId)
    services.observation = lambda operation: evidence(operation, "observed-terminal", "merged")
    assert coord.recover(token.operationId).state == "observed-terminal"
    assert coord.inspect()["activeOperationId"] is None
    assert core.usage(coord.inspect(), services.now, "stable-run", "merge") == (1, 1)
    assert len(services.invocations) == 1


def test_authentic_close_completion_after_reopen_retires_sender_not_replay(fixture):
    _, binding, first, second = fixture
    services = FakeServices()
    services.response = "reopened"
    coord = coordinator(first, binding, services)
    token = prepared(coord, action="close")
    result = coord.invoke(token, "claim")
    assert result.state == "completed-effect"
    operation = coordinator(second, binding).inspect()["operations"][token.operationId]
    assert operation["evidence"]["observedState"] == "reopened"
    assert operation["request"] == {"method": "PATCH", "path": "/repos/example/project/pulls/1", "body": {"state": "closed"}}
    assert coord.invoke(token, "claim").status == core.CommitStatus.ALREADY
    assert len(services.invocations) == len(services.effects) == 1
    with pytest.raises(core.Refused):
        prepared(coord, action="close", run="new-run-not-lifecycle")


def test_proof_and_request_must_be_exact_and_durable_before_invocation(fixture):
    _, binding, first, second = fixture
    coord = coordinator(first, binding)
    bad = proof()
    bad["verification"]["verifier"] = bad["verification"]["builder"]
    with pytest.raises(core.CoordinationError):
        coord.reserve(subject(), bad, "run", "owner", "reserve")
    token = coord.reserve(subject(), proof(), "run", "owner", "reserve").token
    with pytest.raises(core.Refused):
        coord.invoke(token, "no-intent")
    request = core.exactRequest(NAMESPACE, subject())
    request["body"]["sha"] = "d" * 40
    with pytest.raises(core.Refused):
        coord.recordIntent(token, request, "bad-intent")
    coord.services.authorized = False
    with pytest.raises(core.CoordinationError):
        coord.invoke(token, "stale-current-authority")
    assert coord.services.invocations == []


def test_finite_storage_admission_keeps_outcome_headroom_and_tombstones(fixture, monkeypatch):
    _, binding, first, second = fixture
    coord = coordinator(first, binding)
    token = prepared(coord)
    size = len(ledger.serialize(coord._load()[0]))
    monkeypatch.setattr(core, "MAX_BYTES", size + core.OUTCOME_HEADROOM)
    # Existing active operation can always record its bounded outcome.
    coord.invoke(token, "claim")
    tip = coord.store.remoteTip()
    with pytest.raises(core.Refused, match="headroom"):
        prepared(coord, 2, run="other-run")
    assert coord.store.remoteTip() == tip
    monkeypatch.setattr(core, "MAX_BYTES", 512 * 1024)
    monkeypatch.setattr(core, "MAX_OPERATIONS", 1)
    with pytest.raises(core.Refused, match="anti-replay"):
        prepared(coord, 3, run="third-run")
    assert token.operationId in coord.inspect()["operations"]
