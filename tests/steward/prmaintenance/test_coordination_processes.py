"""Spawned OS actors, independent --no-local clones, real local bare Git CAS.

Barriers select races, not sleeps. Both INVOCATIONS and effects are asserted.
HOME/config/protocols are isolated by the administrative fixture. Nothing can
contact a real forge; FakeServices is the only mutation adapter.
"""

from __future__ import annotations

import multiprocessing
import os
import time
import pytest

from gaia_cli.steward import ledger
from gaia_cli.steward.prmaintenance import coordination as core
from .coordination_helpers import (
    FakeServices, NAMESPACE, assertIndependent, clone, coordinator, git, prepared, proof, seed, subject,
)


def raceActor(path, binding, beforeCas, afterReserve, output, candidate, runId, caps, wallOffset):
    # Local wall clock differences must have no effect on authoritative budgets.
    time.time = lambda: wallOffset
    services = FakeServices(queue=output)
    services.caps = caps
    coord = coordinator(path, binding, services)
    original = coord.store.compare_and_swap
    rendezvoused = False

    def raceCas(expected, document, message):
        nonlocal rendezvoused
        if message.split()[1] == "reserve" and not rendezvoused:
            rendezvoused = True
            beforeCas.wait(10)
        try:
            return original(expected, document, message)
        except ledger.LedgerConflict:
            output.put(("conflict", str(path)))
            raise

    coord.store.compare_and_swap = raceCas
    token = None
    try:
        result = coord.reserve(candidate, proof(candidate), runId, str(path.name), f"reserve-{path.name}")
        token = result.token
        output.put(("admitted", token))
    except core.Refused as exc:
        output.put(("refused", str(exc)))
    # Keep the winner's preparation active until the loser has reloaded.
    afterReserve.wait(10)
    if token is not None:
        coord.recordIntent(token, core.exactRequest(NAMESPACE, candidate), f"intent-{path.name}")
        result = coord.invoke(token, f"claim-{path.name}")
        output.put(("result", result.state))
    output.put(("done", os.getpid()))


def collectActors(processes, output):
    messages = []
    done = 0
    try:
        while done < len(processes):
            message = output.get(timeout=15)
            messages.append(message)
            done += message[0] == "done"
        for process in processes:
            process.join(10)
            assert not process.is_alive()
            assert process.exitcode == 0
    finally:
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join(5)
    return messages


@pytest.mark.parametrize("secondAction,secondNumber", [("merge", 1), ("close", 1), ("merge", 2), ("close", 2)])
def test_real_cas_race_excludes_same_different_pr_and_actions(tmp_path, monkeypatch, secondAction, secondNumber):
    remote, binding, first, second = seed(tmp_path, monkeypatch)
    context = multiprocessing.get_context("spawn")
    beforeCas, afterReserve = context.Barrier(2), context.Barrier(2)
    output = context.Queue()
    processes = [context.Process(target=raceActor, args=(
        path, binding, beforeCas, afterReserve, output, candidate, "same-stable-run", core.Limits(), wallOffset))
        for path, candidate, wallOffset in [(first, subject(), -999999), (second, subject(secondNumber, secondAction), 99999999999)]]
    for process in processes:
        process.start()
    messages = collectActors(processes, output)
    assert sum(kind == "admitted" for kind, _ in messages) == 1
    assert sum(kind == "refused" for kind, _ in messages) == 1
    assert sum(kind == "conflict" for kind, _ in messages) == 1
    invocations = [value for kind, value in messages if kind == "invocation"]
    effects = [value for kind, value in messages if kind == "effect"]
    assert len(invocations) == len(effects) == 1 and invocations == effects
    third = clone(tmp_path, remote, "cold-third")
    assertIndependent(first, third)
    state = coordinator(third, binding).inspect()
    assert state["activeOperationId"] is None and len(state["operations"]) == 1
    assert core.usage(state, core.TimeBounds(10000, 10000, "authoritative"), "same-stable-run", "merge")[1] == 1


@pytest.mark.parametrize("quota", ["hour", "run"])
def test_two_processes_cannot_spend_last_run_or_hour_token(tmp_path, monkeypatch, quota):
    remote, binding, first, second = seed(tmp_path, monkeypatch)
    services = FakeServices()
    services.caps = core.Limits(writesPerHour=2) if quota == "hour" else core.Limits()
    coord = coordinator(first, binding, services)
    coord.invoke(prepared(coord, 90, run="resumed-run"), "claim-90")
    context = multiprocessing.get_context("spawn")
    beforeCas, afterReserve, output = context.Barrier(2), context.Barrier(2), context.Queue()
    processes = [context.Process(target=raceActor, args=(
        path, binding, beforeCas, afterReserve, output, subject(number),
        "different-run" if quota == "hour" else "resumed-run", services.caps, wallOffset))
        for path, number, wallOffset in [(first, 1, -99999), (second, 2, 9999999999)]]
    for process in processes:
        process.start()
    messages = collectActors(processes, output)
    assert sum(kind == "invocation" for kind, _ in messages) == 1
    assert sum(kind == "effect" for kind, _ in messages) == 1
    assert sum(kind == "admitted" for kind, _ in messages) == 1
    state = coordinator(second, binding).inspect()
    assert len(state["operations"]) == 2
    assert core.usage(state, services.now, "resumed-run", "merge") == ((1 if quota == "hour" else 2), 2)
    with pytest.raises(core.Refused, match="ceiling"):
        prepared(coord, 3, run="third-distinct-run" if quota == "hour" else "resumed-run")


class SharedClockServices(FakeServices):
    def __init__(self, authoritativeTime, output, counts):
        super().__init__(queue=output)
        self.authoritativeTime = authoritativeTime
        self.counts = counts
        self.response = "reopened"

    def invoke(self, request, invocationId):
        with self.counts.get_lock():
            self.counts[0] += 1
        response = super().invoke(request, invocationId)
        with self.counts.get_lock():
            self.counts[1] += 1
        return response

    def clock(self):
        instant = self.authoritativeTime.value
        return core.TimeBounds(instant, instant, "fixture-authoritative-clock")


def pausedClaimActor(path, binding, output, resume, authoritativeTime, counts):
    services = SharedClockServices(authoritativeTime, output, counts)
    coord = coordinator(path, binding, services)
    token = prepared(coord, action="close")
    consume = coord._consume

    def pausedConsume(grant, operation):
        output.put(("paused", token))
        assert resume.wait(10)
        consume(grant, operation)

    coord._consume = pausedConsume
    result = coord.invoke(token, "claim")
    output.put(("result", result.state))
    output.put(("done", os.getpid()))


@pytest.mark.parametrize("terminate", [False, True])
def test_paused_claim_restart_and_cold_recovery_never_grant_again(tmp_path, monkeypatch, terminate):
    remote, binding, first, second = seed(tmp_path, monkeypatch)
    context = multiprocessing.get_context("spawn")
    output, resume, authoritativeTime = context.Queue(), context.Event(), context.Value("q", 10000)
    counts = context.Array("q", [0, 0])
    process = context.Process(target=pausedClaimActor, args=(first, binding, output, resume, authoritativeTime, counts))
    process.start()
    try:
        kind, token = output.get(timeout=15)
        assert kind == "paused"
        services = FakeServices(now=999999)
        authoritativeTime.value = 999999
        other = coordinator(second, binding, services)
        assert other.inspect()["operations"][token.operationId]["state"] == "possibly-sent"
        assert other.recover(token.operationId).state == "quarantined"
        third = clone(tmp_path, remote, "after-claim-cold-host")
        restartedServices = FakeServices(now=999999)
        restarted = coordinator(third, binding, restartedServices)
        assert restarted.invoke(token, "claim").status == core.CommitStatus.ALREADY
        with pytest.raises(core.Refused):
            restarted.invoke(token, "new-claim-from-copied-token")
        with pytest.raises(core.Refused):
            restarted.takeover(token, "new-owner", "takeover")
        assert restartedServices.invocations == restartedServices.effects == []
        assert core.usage(restarted.inspect(), restartedServices.now, "stable-run", "close") == (1, 1)
        if terminate:
            process.terminate()
            process.join(10)
            assert not process.is_alive() and process.exitcode != 0
            assert restarted.recover(token.operationId).status == core.CommitStatus.ALREADY
            assert restarted.inspect()["activeOperationId"] == token.operationId
            # Shared process counters prove both zero invocations and zero effects.
            assert list(counts) == [0, 0]
        else:
            resume.set()
            messages = collectActors([process], output)
            assert sum(kind == "invocation" for kind, _ in messages) == 1
            assert sum(kind == "effect" for kind, _ in messages) == 1
            assert ("result", "completed-effect") in messages
            assert list(counts) == [1, 1]
            operation = restarted.inspect()["operations"][token.operationId]
            assert operation["evidence"]["observedState"] == "reopened"
            assert operation["state"] == "completed-effect"
            assert restarted.inspect()["activeOperationId"] is None
    finally:
        if process.is_alive():
            process.terminate()
            process.join(5)


def forkActor(path, binding, output):
    # Spawn first so this fork occurs without pytest-timeout's watchdog thread.
    services = FakeServices()
    coord = coordinator(path, binding, services)
    token = prepared(coord)
    consume = coord._consume
    checked = []

    def forkConsume(grant, operation):
        child = os.fork()
        if child == 0:
            statusFile = path / f"child-{os.getpid()}.status"
            try:
                try:
                    consume(grant, operation)
                except core.Refused:
                    pass
                else:
                    statusFile.write_text("21")
                    os._exit(21)
                try:
                    coord.invoke(token, "forked-replay")
                except core.Refused:
                    statusFile.write_text("0")
                    os._exit(0)
                statusFile.write_text("22")
                os._exit(22)
            except BaseException:
                statusFile.write_text("23")
                os._exit(23)
        statusFile = path / f"child-{child}.status"
        try:
            waited, status = os.waitpid(child, 0)
            assert waited == child and os.waitstatus_to_exitcode(status) == 0
        except ChildProcessError:
            pass
        if not statusFile.is_file() or statusFile.read_text().strip() != "0":
            raise RuntimeError(f"Child process {child} did not exit with code 0 (status: {statusFile.read_text() if statusFile.is_file() else 'missing'})")
        checked.append(True)
        consume(grant, operation)

    coord._consume = forkConsume
    assert coord.invoke(token, "claim").state == "completed-effect"
    assert checked == [True]
    assert len(services.invocations) == len(services.effects) == 1
    output.put(("counts", (len(services.invocations), len(services.effects))))
    output.put(("done", os.getpid()))


def test_actual_fork_cannot_consume_or_invoke_inherited_grant(tmp_path, monkeypatch):
    _, binding, first, second = seed(tmp_path, monkeypatch)
    context = multiprocessing.get_context("spawn")
    output = context.Queue()
    process = context.Process(target=forkActor, args=(first, binding, output))
    process.start()
    assert ("counts", (1, 1)) in collectActors([process], output)


def takeoverActor(path, binding, token, barrier, output, takeover):
    services = FakeServices(now=10121 if takeover else 10000, queue=output)
    services.response = "lost"
    coord = coordinator(path, binding, services)
    original = coord.store.compare_and_swap
    rendezvoused = False

    def raceCas(expected, document, message):
        nonlocal rendezvoused
        if not rendezvoused:
            rendezvoused = True
            barrier.wait(10)
        return original(expected, document, message)

    coord.store.compare_and_swap = raceCas
    try:
        result = coord.takeover(token, "new-owner", "takeover") if takeover else coord.invoke(token, "claim")
        output.put(("result", ("takeover" if takeover else "claim", result.state)))
    except core.CoordinationError as exc:
        output.put(("refused", str(exc)))
    output.put(("done", os.getpid()))


def test_real_preparation_takeover_races_claim_without_two_senders(tmp_path, monkeypatch):
    _, binding, first, second = seed(tmp_path, monkeypatch)
    token = prepared(coordinator(first, binding))
    context = multiprocessing.get_context("spawn")
    barrier, output = context.Barrier(2), context.Queue()
    processes = [context.Process(target=takeoverActor, args=(path, binding, token, barrier, output, takeover))
                 for path, takeover in [(first, False), (second, True)]]
    for process in processes:
        process.start()
    messages = collectActors(processes, output)
    assert sum(kind == "refused" for kind, _ in messages) == 1
    results = [value for kind, value in messages if kind == "result"]
    assert len(results) == 1
    invocations = sum(kind == "invocation" for kind, _ in messages)
    effects = sum(kind == "effect" for kind, _ in messages)
    state = coordinator(second, binding).inspect()
    operation = state["operations"][token.operationId]
    if results[0][0] == "takeover":
        assert invocations == effects == 0
        assert operation["fence"] > token.fence and operation["state"] == "intent"
    else:
        assert invocations == effects == 1
        assert operation["fence"] == token.fence and operation["state"] == "unknown"
    assert state["activeOperationId"] == token.operationId
