"""Regression tests for the independent whole-source review of Routine 19 (PR #2317 @ 85f37bfb).

Every test here turns a reviewer probe or a lead decision into behavior. Nothing talks to a real forge, clock or the
shared Steward ledger; coordination state lives in disposable bare remotes under ``tmp_path``.
"""
from __future__ import annotations

import json
import socket
import ssl
import subprocess
import threading
import time
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


def test_connect_failure_before_the_first_request_byte_is_provably_unsent(tmp_path, monkeypatch):
    fixture = world(tmp_path, monkeypatch)
    _, forge, clock, executor, _, _ = fixture
    operation = prepare(fixture)
    original = forge.request

    def dnsFailure(method, path, body=None):
        if method in {"PUT", "PATCH"}:
            raise core.NotSent("HTTPS invocation failed or response unavailable")
        return original(method, path, body)

    forge.request = dnsFailure
    result = executor.execute(operation["operationId"])
    assert result["coordinationState"] == "canceled-after-claim" and forge.invocations == []
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


def test_execute_reports_a_post_claim_ledger_failure_as_persistence_uncertainty(tmp_path, monkeypatch):
    fixture = world(tmp_path, monkeypatch)
    _, forge, _, executor, _, _ = fixture
    operation = prepare(fixture)
    coordinator = executor.coordinator
    real = coordinator.invoke

    def claimThenFail(token, transitionId):
        coordinator._transition("claim", token.operationId, {"token": core.asdict(token)}, transitionId)
        raise ledger.LedgerUnavailable("fixture: failure after the claim committed")

    coordinator.invoke = claimThenFail
    result = executor.execute(operation["operationId"])
    assert result["state"] == "possibly-sent" and result["uncertaintyCause"] == "persistence"
    assert forge.invocations == []
    coordinator.invoke = real


def test_a_failure_before_any_claim_is_a_refusal_not_uncertainty(tmp_path, monkeypatch):
    fixture = world(tmp_path, monkeypatch)
    _, forge, _, executor, _, _ = fixture
    operation = prepare(fixture)

    def refused(token, transitionId):
        raise ledger.LedgerUnavailable("fixture: refused before the claim")

    executor.coordinator.invoke = refused
    with pytest.raises(ledger.LedgerUnavailable):
        executor.execute(operation["operationId"])
    assert executor.coordinator.inspect()["operations"][operation["operationId"]]["state"] == "intent"


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


@pytest.mark.parametrize("scenario,code,state", [("merge", 0, "merged"), ("reject", 2, "failed"), ("unsent", 2, "failed")])
def test_execute_exit_codes_follow_the_settled_states(tmp_path, monkeypatch, capsys, scenario, code, state):
    fixture = world(tmp_path, monkeypatch)
    fx, forge, _, executor, _, _ = fixture
    operation = prepare(fixture)
    if scenario == "reject":
        forge.reject = True
    if scenario == "unsent":
        original = forge.request

        def refuse(method, path, body=None):
            if method in {"PUT", "PATCH"}:
                raise core.NotSent("HTTPS invocation failed or response unavailable")
            return original(method, path, body)

        forge.request = refuse
    monkeypatch.setattr(ex, "makeExecutor", lambda root: executor)
    exit_, output = run(executor, fx, ["execute", "--operation-id", operation["operationId"]], capsys)
    assert (exit_, output["state"]) == (code, state)


def test_abort_records_the_operator_reason_in_the_shared_cancel_event(tmp_path, monkeypatch, capsys):
    fixture = world(tmp_path, monkeypatch)
    fx, forge, _, executor, _, _ = fixture
    operation = prepare(fixture)
    monkeypatch.setattr(ex, "makeExecutor", lambda root: executor)
    code, output = run(executor, fx, ["abort", "--operation-id", operation["operationId"], "--reason", "drain test, run 7"], capsys)
    assert code == 0 and output["state"] == "aborted"
    events = executor.coordinator._payload(executor.coordinator._load()[0])["events"]
    cancel = next(event for event in events if event["kind"] == "cancel")
    assert cancel["args"]["reason"] == "operator abort: drain test, run 7"
    assert forge.invocations == []


@pytest.mark.parametrize("reason", ["", "   ", "x" * 257, "bad\nnewline", "café"])
def test_abort_refuses_unrecordable_reasons_and_changes_nothing(tmp_path, monkeypatch, capsys, reason):
    fixture = world(tmp_path, monkeypatch)
    fx, _, _, executor, _, _ = fixture
    operation = prepare(fixture)
    monkeypatch.setattr(ex, "makeExecutor", lambda root: executor)
    code, _ = run(executor, fx, ["abort", "--operation-id", operation["operationId"], "--reason", reason], capsys)
    assert code == 2
    assert executor.coordinator.inspect()["operations"][operation["operationId"]]["state"] == "intent"


# --- lease: 120 s window, takeover verb and its anti-replay consequence -----------------------------------------------


def test_takeover_verb_refuses_live_lease_then_moves_an_expired_one_and_the_old_token_is_dead(tmp_path, monkeypatch, capsys):
    fixture = world(tmp_path, monkeypatch)
    fx, forge, clock, executor, _, _ = fixture
    operation = prepare(fixture)
    monkeypatch.setattr(ex, "makeExecutor", lambda root: executor)
    stale = ex.tokenFrom(executor.coordinator.inspect()["operations"][operation["operationId"]])
    code, _ = run(executor, fx, ["takeover", "--operation-id", operation["operationId"]], capsys)
    assert code == 2  # lease (120 s) still live: nothing to take over
    clock.instant += 200
    with pytest.raises(core.Refused, match="preparation"):
        executor.execute(operation["operationId"])  # expired lease cannot claim; slot stays held, nothing was sent
    assert forge.invocations == []
    code, output = run(executor, fx, ["takeover", "--operation-id", operation["operationId"]], capsys)
    assert code == 0 and output["state"] == "intent"
    current = executor.coordinator.inspect()["operations"][operation["operationId"]]
    assert current["fence"] > stale.fence and current["takeovers"] == 1
    with pytest.raises(core.Refused, match="stale"):
        executor.coordinator.invoke(stale, "stale-claim")  # the previous owner can no longer claim
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


def test_total_deadline_aborts_a_slow_drip_response_and_is_not_not_sent(tmp_path, monkeypatch):
    cert, key = tmp_path / "slow.pem", tmp_path / "slow.key"
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
        listener.settimeout(5)
        try:
            raw, _ = listener.accept()
            with server.wrap_socket(raw, server_side=True) as tls:
                tls.settimeout(5)
                tls.recv(65536)
                tls.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 50\r\n\r\n")
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
    with pytest.raises(core.CoordinationError) as failure:
        transport.request("GET", "/slow")
    elapsed = time.monotonic() - started
    stop.set()
    thread.join(10)
    listener.close()
    assert not isinstance(failure.value, core.NotSent)  # bytes were written: never a provable no-send
    assert elapsed < 6, f"deadline did not bound the exchange ({elapsed:.1f}s)"
    assert len(wrote) < 50


@pytest.mark.parametrize("deadline", [0, -1, 121, True, "5"])
def test_invalid_deadlines_are_refused(deadline):
    with pytest.raises(core.CoordinationError, match="deadline"):
        ex.HttpsTransport("https://forge.invalid", "synthetic", context=ssl.create_default_context(), deadline=deadline)
