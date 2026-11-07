"""Regression tests for the independent whole-source review of Routine 19 (PR #2317 @ 85f37bfb).

Every test here turns a reviewer probe or a lead decision into behavior. Nothing talks to a real forge, clock or the
shared Steward ledger; coordination state lives in disposable bare remotes under ``tmp_path``.
"""
from __future__ import annotations

import json
import socket
import ssl
import subprocess
import sys
from pathlib import Path

import pytest

from gaia_cli.steward import ledger
from gaia_cli.steward.prmaintenance import cli, coordination as core, executor as ex, gate
from . import helpers as h
from .coordination_helpers import FakeServices, NAMESPACE, coordinator, prepared, proof, seed, subject
from .test_executor import prepare, world


class UnsentServices(FakeServices):
    """Adapter that PROVES it never wrote a request byte."""

    def invoke(self, request, invocationId):
        raise core.NotSent("fixture adapter refused before any socket write")


class WroteThenFailedServices(FakeServices):
    """Adapter that failed without being able to prove anything about the wire."""

    def invoke(self, request, invocationId):
        self.invocations.append((request, invocationId))
        raise RuntimeError("fixture: unknown wire state")


# --- MAJOR liveness: claim pinned the slot although nothing was sent -------------------------------------------------


def test_claim_result_is_built_from_the_cas_so_a_post_claim_read_failure_cannot_wedge(tmp_path, monkeypatch):
    """Probe 1: the second inspect() used to fail after the claim and leave a possibly-sent slot forever."""
    _, binding, first, _ = seed(tmp_path, monkeypatch)
    services = FakeServices()
    coord = coordinator(first, binding, services)
    token = prepared(coord)
    real = coord.inspect
    reads = []

    def flaky():
        reads.append(1)
        if len(reads) > 1:
            raise ledger.LedgerUnavailable("ledger fetch failed: network blip after the claim")
        return real()

    coord.inspect = flaky
    result = coord.invoke(token, "claim-1")
    coord.inspect = real
    assert len(reads) == 1  # only the pre-claim read; no read sits between claim and send
    assert result.state == "completed-effect"
    assert len(services.invocations) == len(services.effects) == 1
    assert real()["activeOperationId"] is None


def test_adapter_that_proves_no_send_releases_the_slot_but_keeps_the_charge(tmp_path, monkeypatch):
    _, binding, first, _ = seed(tmp_path, monkeypatch)
    services = UnsentServices()
    coord = coordinator(first, binding, services)
    token = prepared(coord)
    result = coord.invoke(token, "claim-1")
    assert result.state == "canceled-after-claim"
    shared = coord.inspect()
    assert shared["activeOperationId"] is None and shared["operations"][token.operationId]["state"] == "canceled-after-claim"
    assert services.invocations == [] and services.effects == []
    # Never a refund: the attempt stays counted for the run and the hour.
    assert core.usage(shared, services.now, "stable-run", "merge") == (1, 1)
    # Never a replay: the same logical operation stays spent, recovery and cancel have nothing to act on.
    candidate = subject(1)
    with pytest.raises(core.Refused):
        coord.reserve(candidate, proof(candidate), "stable-run-2", "owner-x", "reserve-again")
    with pytest.raises(core.Refused, match="no outstanding sender"):
        coord.recover(token.operationId)
    with pytest.raises(core.Refused):
        coord.cancelPrepared(token, "late", "cancel-late")
    # The slot is genuinely free for a different subject.
    other = subject(2)
    assert coord.reserve(other, proof(other), "stable-run", "owner-2", "reserve-2").token is not None


def test_cancelled_claim_charge_expires_only_after_the_hour_like_a_completed_attempt(tmp_path, monkeypatch):
    _, binding, first, _ = seed(tmp_path, monkeypatch)
    services = UnsentServices()
    services.caps = core.Limits(writesPerHour=1)
    coord = coordinator(first, binding, services)
    coord.invoke(prepared(coord), "claim-1")
    other = subject(2)
    with pytest.raises(core.Refused, match="ceiling"):
        coord.reserve(other, proof(other), "later-run", "owner-2", "reserve-2")
    services.now = core.TimeBounds(10000 + 3601, 10000 + 3601, "fixture-authoritative-clock")
    assert coord.reserve(other, proof(other), "later-run", "owner-2", "reserve-2").token is not None


@pytest.mark.parametrize("services", [WroteThenFailedServices(), FakeServices()], ids=["unprovable-failure", "lost-after-write"])
def test_any_failure_after_possible_entry_stays_unsettled_never_cancelled(tmp_path, monkeypatch, services):
    _, binding, first, _ = seed(tmp_path, monkeypatch)
    services.response = "lost"
    coord = coordinator(first, binding, services)
    token = prepared(coord)
    result = coord.invoke(token, "claim-1")
    assert result.state == "unknown"
    shared = coord.inspect()
    assert shared["activeOperationId"] == token.operationId
    assert core.usage(shared, services.now, "stable-run", "merge") == (1, 1)


def test_failure_before_adapter_entry_is_a_proven_no_send(tmp_path, monkeypatch):
    _, binding, first, _ = seed(tmp_path, monkeypatch)
    services = FakeServices()
    coord = coordinator(first, binding, services)
    token = prepared(coord)

    def broken(grant, operation):
        raise core.Refused("fixture: control flow lost before adapter entry")

    coord._consume = broken
    assert coord.invoke(token, "claim-1").state == "canceled-after-claim"
    assert services.invocations == []
    assert coord.inspect()["activeOperationId"] is None


def test_unrecordable_cancellation_leaves_the_claim_outstanding(tmp_path, monkeypatch):
    _, binding, first, _ = seed(tmp_path, monkeypatch)
    services = FakeServices()
    coord = coordinator(first, binding, services)
    token = prepared(coord)
    real = coord.store.compare_and_swap

    def unavailable(*args, **kwargs):
        raise ledger.LedgerUnavailable("push failed")

    def refuse(request, invocationId):
        coord.store.compare_and_swap = unavailable
        raise core.NotSent("fixture adapter refused before any socket write")

    services.invoke = refuse
    result = coord.invoke(token, "claim-1")
    coord.store.compare_and_swap = real
    assert result.status == core.CommitStatus.UNRESOLVED
    shared = coord.inspect()
    assert shared["operations"][token.operationId]["state"] == "possibly-sent"
    assert shared["activeOperationId"] == token.operationId


# --- executor: live re-check and transport failures ------------------------------------------------------------------


def test_live_recheck_refusal_after_claim_is_provably_unsent(tmp_path, monkeypatch):
    fixture = world(tmp_path, monkeypatch)
    _, forge, clock, executor, _, _ = fixture
    operation = prepare(fixture)
    original = executor.services.authorize
    calls = []

    def flaky(namespace, candidate, binding):
        calls.append(1)
        if len(calls) > 1:  # pre-claim passes; the re-check immediately before the send is refused
            raise core.CoordinationError("kill switch engaged between claim and send")
        return original(namespace, candidate, binding)

    executor.services.authorize = flaky
    result = executor.execute(operation["operationId"])
    assert result["state"] == "failed" and result["coordinationState"] == "canceled-after-claim"
    assert "no request byte was sent" in result["reason"]
    assert forge.invocations == [] and forge.effects == []
    shared = executor.coordinator.inspect()
    assert shared["activeOperationId"] is None
    assert core.usage(shared, clock.sample(), "stable-run", "merge") == (1, 1)


def test_connect_failure_before_the_first_request_byte_is_provably_unsent(tmp_path, monkeypatch, capsys):
    fixture = world(tmp_path, monkeypatch)
    fx, forge, clock, executor, _, _ = fixture
    operation = prepare(fixture)
    original = forge.request

    def dnsFailure(method, path, body=None):
        if method in {"PUT", "PATCH"}:
            raise core.NotSent("HTTPS invocation failed or response unavailable")
        return original(method, path, body)

    forge.request = dnsFailure
    monkeypatch.setattr(ex, "makeExecutor", lambda root: executor)
    code, output = run(executor, fx, ["execute", "--operation-id", operation["operationId"]], capsys)
    assert code == 2 and (output["state"], output["coordinationState"]) == ("failed", "canceled-after-claim")
    assert forge.invocations == []
    assert executor.coordinator.inspect()["activeOperationId"] is None


def test_transport_failure_after_a_possible_write_stays_possibly_sent(tmp_path, monkeypatch):
    fixture = world(tmp_path, monkeypatch)
    _, forge, clock, executor, _, _ = fixture
    operation = prepare(fixture)
    original = forge.request

    def midWrite(method, path, body=None):
        if method in {"PUT", "PATCH"}:
            forge.invocations.append((method, path, body))
            raise core.CoordinationError("HTTPS invocation failed or response unavailable")  # not NotSent
        return original(method, path, body)

    forge.request = midWrite
    result = executor.execute(operation["operationId"])
    assert result["coordinationState"] == "unknown" and result["state"] == "unknown"
    assert executor.coordinator.inspect()["activeOperationId"] == operation["operationId"]


def test_production_adapter_reads_no_ledger_between_claim_and_send(tmp_path, monkeypatch):
    fixture = world(tmp_path, monkeypatch)
    _, forge, _, executor, _, _ = fixture
    operation = prepare(fixture)
    real = executor.coordinator.inspect
    reads = []

    def counting():
        reads.append(1)
        return real()

    executor.coordinator.inspect = counting
    executor.services.coordinator = executor.coordinator
    sent = []
    original = forge.request

    def watch(method, path, body=None):
        if method in {"PUT", "PATCH"}:
            sent.append(len(reads))
        return original(method, path, body)

    forge.request = watch
    assert executor.coordinator.invoke(ex.tokenFrom(real()["operations"][operation["operationId"]]), "sole").state == "completed-effect"
    # one pre-claim read inside invoke, one test-side read to build the token above is not counted (made before wrapping)
    assert sent == [1]


# --- CLI / executor error mapping ------------------------------------------------------------------------------------


def test_cli_maps_a_raw_ledger_failure_to_a_refusal_report(monkeypatch, tmp_path, capsys):
    """Probe 2: LedgerUnavailable used to escape cli.main as a traceback."""

    class Broken:
        def execute(self, operationId):
            raise ledger.LedgerUnavailable("ledger fetch failed: x")

    monkeypatch.setattr(ex, "makeExecutor", lambda root: Broken())
    code = cli.main(["--root", str(tmp_path), "--json", "execute", "--operation-id", "a" * 64])
    assert code == 2
    assert json.loads(capsys.readouterr().out)["refused"] == "shared-route-unavailable"


def test_gate_maps_a_raw_ledger_failure_to_a_refusal_report(monkeypatch, tmp_path, capsys):
    def broken(root):
        raise ledger.LedgerUnavailable("ledger fetch failed: x")

    monkeypatch.setattr(gate, "makeExecutor", broken)
    code = cli.main(["--root", str(tmp_path), "--json", "gate-merge", "--repo", h.REPO, "--number", "1", "--head", "a" * 40,
                     "--run-id", "run", "--producer", "weekly-content-engine"])
    assert code == 2
    assert json.loads(capsys.readouterr().out)["refused"] == "shared-route-unavailable"


def test_ledger_failure_maps_to_refusal_before_the_claim_and_to_persistence_uncertainty_after_it(tmp_path, monkeypatch):
    fixture = world(tmp_path, monkeypatch)
    _, forge, _, executor, _, _ = fixture
    operation = prepare(fixture)
    coordinator = executor.coordinator
    real = coordinator.invoke

    def refused(token, transitionId):
        raise ledger.LedgerUnavailable("fixture: refused before the claim")

    coordinator.invoke = refused
    with pytest.raises(ledger.LedgerUnavailable):
        executor.execute(operation["operationId"])
    assert coordinator.inspect()["operations"][operation["operationId"]]["state"] == "intent"

    def claimThenFail(token, transitionId):
        coordinator._transition("claim", token.operationId, {"token": core.asdict(token)}, transitionId)
        raise ledger.LedgerUnavailable("fixture: failure after the claim committed")

    coordinator.invoke = claimThenFail
    result = executor.execute(operation["operationId"])
    assert result["state"] == "possibly-sent" and result["uncertaintyCause"] == "persistence"
    assert forge.invocations == []
    coordinator.invoke = real


# --- documented report shapes and exit codes, asserted from behavior -------------------------------------------------


UNKNOWN_SHAPE = {"operationId", "state", "coordinationState", "repo", "runId", "number", "headSha", "action", "evidenceSha256"}
UNCERTAIN_SHAPE = {"operationId", "state", "coordinationState", "uncertaintyCause", "evidenceSha256", "repo", "runId",
                   "number", "headSha", "action", "reason"}


def run(executor, fx, args, capsys):
    code = cli.main(["--root", str(fx.root), "--json", *args])
    return code, json.loads(capsys.readouterr().out)


def test_lost_response_report_is_the_store_unknown_shape_with_no_cause(tmp_path, monkeypatch, capsys):
    fixture = world(tmp_path, monkeypatch)
    fx, forge, _, executor, _, _ = fixture
    operation = prepare(fixture)
    forge.lost = True
    monkeypatch.setattr(ex, "makeExecutor", lambda root: executor)
    code, output = run(executor, fx, ["execute", "--operation-id", operation["operationId"]], capsys)
    assert code == 2 and set(output) == UNKNOWN_SHAPE
    assert output["state"] == "unknown" and output["coordinationState"] == "unknown" and output["evidenceSha256"] is None


def test_unauthenticated_reply_report_is_the_possibly_sent_shape_with_a_cause(tmp_path, monkeypatch, capsys):
    fixture = world(tmp_path, monkeypatch, "close")
    fx, forge, _, executor, _, _ = fixture
    operation = prepare(fixture)
    original = forge.request
    forge.request = lambda method, path, body=None: ex.HttpReply(502, {}, {}) if method == "PATCH" else original(method, path, body)
    monkeypatch.setattr(ex, "makeExecutor", lambda root: executor)
    code, output = run(executor, fx, ["execute", "--operation-id", operation["operationId"]], capsys)
    assert code == 2 and set(output) == UNCERTAIN_SHAPE
    assert output["state"] == "possibly-sent" and output["coordinationState"] == "unavailable"
    assert output["uncertaintyCause"] in ex.UNCERTAINTY_CAUSES and output["evidenceSha256"] is None


def test_abort_refuses_unrecordable_reasons_then_records_the_operator_reason(tmp_path, monkeypatch, capsys):
    fixture = world(tmp_path, monkeypatch)
    fx, forge, _, executor, _, _ = fixture
    operation = prepare(fixture)
    monkeypatch.setattr(ex, "makeExecutor", lambda root: executor)
    for reason in ("", "   ", "x" * 257, "bad\nnewline", "caf\u00e9"):
        code, _ = run(executor, fx, ["abort", "--operation-id", operation["operationId"], "--reason", reason], capsys)
        assert code == 2
        assert executor.coordinator.inspect()["operations"][operation["operationId"]]["state"] == "intent"
    code, output = run(executor, fx, ["abort", "--operation-id", operation["operationId"], "--reason", "drain test, run 7"], capsys)
    assert code == 0 and output["state"] == "aborted"
    events = executor.coordinator._payload(executor.coordinator._load()[0])["events"]
    cancel = next(event for event in events if event["kind"] == "cancel")
    assert cancel["args"]["reason"] == "operator abort: drain test, run 7"
    assert forge.invocations == []


# --- inspection / prepared / unresolved report shapes (not only freshly entered invocation failures) ----------------


def bareExecutor(tmp_path, monkeypatch, services=None):
    """Executor over a real coordinator on a disposable remote, with no production services."""
    _, binding, first, _ = seed(tmp_path, monkeypatch)
    services = services or FakeServices()
    coord = coordinator(first, binding, services)
    return ex.Executor(coord), coord, services


@pytest.mark.parametrize("target", ["possibly-sent", "quarantined", "unknown"])
def test_execute_on_a_persisted_unsettled_sender_is_an_inspection_report_without_a_cause(tmp_path, monkeypatch, target):
    services = FakeServices()
    executor, coord, _ = bareExecutor(tmp_path, monkeypatch, services)
    token = prepared(coord)
    if target == "unknown":
        services.response = "lost"
        coord.invoke(token, "claim-1")
    else:
        coord._transition("claim", token.operationId, {"token": core.asdict(token)}, "claim-1")  # a restarted claim
        if target == "quarantined":
            coord.recover(token.operationId)
    report = executor.execute(token.operationId)
    assert report["state"] == target and report["coordinationState"] == target
    assert "uncertaintyCause" not in report and "commitStatus" not in report and report["evidenceSha256"] is None
    assert len(services.invocations) == (1 if target == "unknown" else 0)  # inspection never enters the adapter


def test_execute_reports_an_unresolved_claim_with_the_observed_prepared_state(tmp_path, monkeypatch):
    executor, coord, services = bareExecutor(tmp_path, monkeypatch)
    token = prepared(coord)
    coord.invoke = lambda token_, transitionId: core.Result(core.CommitStatus.UNRESOLVED, token_.operationId)
    report = executor.execute(token.operationId)
    assert report["state"] == "intent" and report["commitStatus"] == "unresolved"
    assert "uncertaintyCause" not in report and services.invocations == []


# --- takeover reports success only when the record shows the new owner under a newer fence ------------------------


def expired(services):
    services.now = core.TimeBounds(services.now.upper + 200, services.now.upper + 200, "fixture-authoritative-clock")


@pytest.mark.parametrize("fake,flag", [(core.CommitStatus.UNRESOLVED, "unresolved"), (core.CommitStatus.ALREADY, "not-taken-over")])
def test_takeover_does_not_report_success_after_an_unresolved_or_no_op_transition(tmp_path, monkeypatch, capsys, fake, flag):
    executor, coord, services = bareExecutor(tmp_path, monkeypatch)
    token = prepared(coord)
    expired(services)
    before = coord.inspect()["operations"][token.operationId]
    coord.takeover = lambda token_, owner, transitionId: core.Result(fake, token_.operationId)  # nothing committed
    monkeypatch.setattr(ex, "makeExecutor", lambda root: executor)
    code = cli.main(["--root", str(tmp_path), "--json", "takeover", "--operation-id", token.operationId])
    output = json.loads(capsys.readouterr().out)
    assert code == 2 and output["commitStatus"] == flag and output["state"] == "intent"
    after = coord.inspect()["operations"][token.operationId]
    assert (after["ownerId"], after["fence"]) == (before["ownerId"], before["fence"])


def test_takeover_cli_exits_zero_only_when_the_new_owner_and_fence_are_committed(tmp_path, monkeypatch, capsys):
    executor, coord, services = bareExecutor(tmp_path, monkeypatch)
    token = prepared(coord)
    monkeypatch.setattr(ex, "makeExecutor", lambda root: executor)
    assert cli.main(["--root", str(tmp_path), "--json", "takeover", "--operation-id", token.operationId]) == 2  # lease live
    capsys.readouterr()
    expired(services)
    assert cli.main(["--root", str(tmp_path), "--json", "takeover", "--operation-id", token.operationId]) == 0
    output = json.loads(capsys.readouterr().out)
    assert "commitStatus" not in output
    after = coord.inspect()["operations"][token.operationId]
    assert after["fence"] > token.fence and after["ownerId"] != token.ownerId


# --- lease: 120 s window, takeover verb and its anti-replay consequence -----------------------------------------------


def test_takeover_verb_refuses_a_live_lease_then_moves_an_expired_one_and_the_send_proceeds(tmp_path, monkeypatch, capsys):
    fixture = world(tmp_path, monkeypatch)
    fx, forge, clock, executor, _, _ = fixture
    operation = prepare(fixture)
    monkeypatch.setattr(ex, "makeExecutor", lambda root: executor)
    before = executor.coordinator.inspect()["operations"][operation["operationId"]]
    code, _ = run(executor, fx, ["takeover", "--operation-id", operation["operationId"]], capsys)
    assert code == 2  # lease (120 s) still live: nothing to take over
    clock.instant += 200
    code, output = run(executor, fx, ["takeover", "--operation-id", operation["operationId"]], capsys)
    assert code == 0 and output["state"] == "intent"
    current = executor.coordinator.inspect()["operations"][operation["operationId"]]
    assert current["fence"] > before["fence"] and current["takeovers"] == 1 and current["ownerId"] != before["ownerId"]
    assert forge.invocations == []
    assert executor.execute(operation["operationId"])["state"] == "merged"
    assert len(forge.invocations) == len(forge.effects) == 1
    code, _ = run(executor, fx, ["takeover", "--operation-id", operation["operationId"]], capsys)
    assert code == 2  # a claimed/settled sender can never be taken over


def test_expired_unsent_preparation_can_be_aborted_but_the_subject_is_never_resubmittable(tmp_path, monkeypatch):
    """Probe 3: documented anti-replay consequence of the 120 s lease."""
    _, binding, first, _ = seed(tmp_path, monkeypatch)
    services = FakeServices()
    coord = coordinator(first, binding, services)
    token = prepared(coord)
    services.now = core.TimeBounds(services.now.lower + 200, services.now.lower + 200, "fixture-authoritative-clock")
    with pytest.raises(core.Refused):
        coord.invoke(token, "c1")
    coord.cancelPrepared(token, "expired", "cancel-1")
    candidate = subject(1)
    with pytest.raises(core.Refused):
        coord.reserve(candidate, proof(candidate), "run-new", "o", "reserve-new")
    assert coord.inspect()["activeOperationId"] is None  # the slot is free; only this exact subject is spent


def test_expired_lease_cannot_claim_and_a_takeover_kills_the_previous_token(tmp_path, monkeypatch):
    _, binding, first, _ = seed(tmp_path, monkeypatch)
    services = FakeServices()
    coord = coordinator(first, binding, services)
    stale = prepared(coord)
    services.now = core.TimeBounds(services.now.upper + 200, services.now.upper + 200, "fixture-authoritative-clock")
    with pytest.raises(core.Refused, match="preparation"):
        coord.invoke(stale, "expired-claim")  # an expired lease cannot claim: nothing was sent, the slot stays held
    assert services.invocations == [] and coord.inspect()["activeOperationId"] == stale.operationId
    fresh = coord.takeover(stale, "owner-new", "takeover-1").token
    assert fresh.fence > stale.fence and fresh.ownerId == "owner-new"
    with pytest.raises(core.Refused, match="stale"):
        coord.invoke(stale, "stale-claim")  # the previous owner can no longer claim
    assert coord.invoke(fresh, "fresh-claim").state == "completed-effect"
    assert len(services.invocations) == len(services.effects) == 1


def test_takeover_is_bounded_to_three_per_preparation(tmp_path, monkeypatch):
    _, binding, first, _ = seed(tmp_path, monkeypatch)
    services = FakeServices()
    coord = coordinator(first, binding, services)
    token = prepared(coord)
    for index in range(3):
        services.now = core.TimeBounds(services.now.upper + 200, services.now.upper + 200, "fixture-authoritative-clock")
        token = coord.takeover(token, f"owner-new-{index}", f"takeover-{index}").token
    services.now = core.TimeBounds(services.now.upper + 200, services.now.upper + 200, "fixture-authoritative-clock")
    with pytest.raises(core.Refused, match="bounded"):
        coord.takeover(token, "owner-new-3", "takeover-3")


# --- per-run ceiling cannot be evaded with a fresh run identifier ---------------------------------------------------


def test_fresh_run_ids_cannot_evade_the_per_action_hourly_ceiling(tmp_path, monkeypatch):
    """Probe 4: five merges with five distinct run ids used to complete in one hour (cap is 2)."""
    _, binding, first, _ = seed(tmp_path, monkeypatch)
    services = FakeServices()
    coord = coordinator(first, binding, services)
    done = 0
    for number in (1, 2):
        done += coord.invoke(prepared(coord, number, "merge", run=f"run-{number}"), f"claim-{number}").state == "completed-effect"
    assert done == 2
    with pytest.raises(core.Refused, match="ceiling"):
        prepared(coord, 3, "merge", run="run-3")
    # Closures are a separate action and keep their own ceiling of 2.
    for number in (4, 5):
        assert coord.invoke(prepared(coord, number, "close", run=f"run-{number}"), f"claim-{number}").state == "completed-effect"
    with pytest.raises(core.Refused, match="ceiling"):
        prepared(coord, 6, "close", run="run-6")
    assert len(services.effects) == 4


def test_ceiling_returns_only_after_completed_charges_age_past_the_hour(tmp_path, monkeypatch):
    _, binding, first, _ = seed(tmp_path, monkeypatch)
    services = FakeServices()
    coord = coordinator(first, binding, services)
    for number in (1, 2):
        coord.invoke(prepared(coord, number, "merge", run=f"run-{number}"), f"claim-{number}")
    services.now = core.TimeBounds(10000 + 3600, 10000 + 3600, "fixture-authoritative-clock")
    with pytest.raises(core.Refused, match="ceiling"):
        prepared(coord, 3, "merge", run="run-3")
    services.now = core.TimeBounds(10000 + 3601, 10000 + 3601, "fixture-authoritative-clock")
    assert prepared(coord, 3, "merge", run="run-3") is not None


# --- TLS: trust overrides refused, total deadline, pre-write failure classified ---------------------------------------


@pytest.mark.parametrize("name", ["SSL_CERT_FILE", "SSL_CERT_DIR"])
def test_ssl_trust_overrides_are_refused_like_git_overrides(monkeypatch, tmp_path, name):
    monkeypatch.setenv(name, str(tmp_path))
    with pytest.raises(core.CoordinationError, match="TLS trust overrides"):
        ex.HttpsTransport("https://forge.invalid", "synthetic")
    monkeypatch.delenv(name)
    transport = ex.HttpsTransport("https://forge.invalid", "synthetic")
    monkeypatch.setenv(name, str(tmp_path))
    with pytest.raises(core.CoordinationError, match="TLS trust overrides"):
        transport.request("GET", "/x")  # also checked at request time, not only at construction


def test_default_clock_transport_also_refuses_trust_overrides(monkeypatch, tmp_path):
    monkeypatch.setenv("SSL_CERT_FILE", str(tmp_path / "ca.pem"))
    with pytest.raises(core.CoordinationError, match="TLS trust overrides"):
        ex.BoundedClock({"url": "https://clock.invalid/v1", "maxSkewSeconds": 1, "precisionSeconds": 1, "maxRoundTripSeconds": 2})


def closedPort() -> int:
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    return port


def test_refused_connection_is_reported_as_not_sent(monkeypatch):
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)
    monkeypatch.delenv("SSL_CERT_DIR", raising=False)
    with pytest.raises(core.NotSent):
        ex.HttpsTransport(f"https://127.0.0.1:{closedPort()}", "synthetic").request("PUT", "/x", {"sha": "a" * 40})


def test_invalid_route_is_reported_as_not_sent(monkeypatch):
    with pytest.raises(core.NotSent):
        ex.HttpsTransport("https://forge.invalid", "synthetic").request("PUT", "//escape", {})


DRIP_PROBE = r"""
import socket, ssl, subprocess, sys, tempfile, threading, time
from pathlib import Path
sys.path.insert(0, sys.argv[1])
# http.client drops connection.sock on Connection: close and HTTP/1.0 while the body still reads the live descriptor.
HEADERS = {
    "persistent": b"HTTP/1.1 200 OK\r\nContent-Length: 50\r\n\r\n",
    "close": b"HTTP/1.1 200 OK\r\nConnection: close\r\nContent-Length: 50\r\n\r\n",
    "http10": b"HTTP/1.0 200 OK\r\nContent-Length: 50\r\n\r\n",
}
from gaia_cli.steward.prmaintenance import coordination as core, executor as ex
work = Path(tempfile.mkdtemp())
cert, key = work / "c.pem", work / "c.key"
subprocess.run(["openssl", "req", "-x509", "-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:prime256v1", "-nodes",
                "-keyout", str(key), "-out", str(cert), "-days", "1", "-subj", "/CN=127.0.0.1",
                "-addext", "subjectAltName=IP:127.0.0.1"], check=True, capture_output=True, timeout=60)
server = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
server.load_cert_chain(str(cert), str(key))
listener = socket.socket()
listener.bind(("127.0.0.1", 0))
listener.listen(1)
stop = threading.Event()
wrote = []
def drip():
    listener.settimeout(10)
    try:
        raw, _ = listener.accept()
        with server.wrap_socket(raw, server_side=True) as tls:
            tls.settimeout(10)
            tls.recv(65536)
            tls.sendall(HEADERS[sys.argv[2]])
            for _ in range(50):  # each byte well inside the per-operation socket timeout, total far beyond the deadline
                if stop.is_set():
                    return
                tls.sendall(b"x")
                wrote.append(1)
                time.sleep(0.4)
    except (OSError, ssl.SSLError):
        pass
thread = threading.Thread(target=drip, daemon=True)
thread.start()
context = ssl.create_default_context(cafile=str(cert))
transport = ex.HttpsTransport(f"https://127.0.0.1:{listener.getsockname()[1]}", "synthetic", context=context, deadline=1.0)
started = time.monotonic()
kind = "returned"
try:
    transport.request("GET", "/slow")
except core.NotSent:
    kind = "NotSent"
except core.CoordinationError:
    kind = "CoordinationError"
elapsed = time.monotonic() - started
stop.set()
thread.join(10)
print(kind, round(elapsed, 2), len(wrote))
"""


@pytest.mark.parametrize("mode", ["persistent", "close", "http10"])
def test_total_deadline_aborts_a_slow_drip_response_and_is_not_not_sent(tmp_path, mode):
    """Real TLS, separate interpreter. The closing modes used to defeat the watchdog (reviewer B1)."""
    script = tmp_path / "drip_probe.py"
    script.write_text(DRIP_PROBE)
    src = Path(__file__).resolve().parents[3] / "src"
    done = subprocess.run([sys.executable, "-I", str(script), str(src), mode], capture_output=True, text=True, timeout=45)
    assert done.returncode == 0, f"probe exit {done.returncode}: {done.stderr[-400:]}"
    kind, elapsed, wrote = done.stdout.split()
    assert kind == "CoordinationError", done.stdout  # bytes were written: never a provable no-send, and it did fail
    assert float(elapsed) < 6, f"deadline did not bound the {mode} exchange ({elapsed}s)"
    assert int(wrote) < 50


@pytest.mark.parametrize("deadline", [0, -1, 121, True, "5"])
def test_invalid_deadlines_are_refused(deadline):
    with pytest.raises(core.CoordinationError, match="deadline"):
        ex.HttpsTransport("https://forge.invalid", "synthetic", context=ssl.create_default_context(), deadline=deadline)
