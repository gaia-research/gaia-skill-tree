"""Spawned concrete-service actors: independent stores, local fake HTTP forge.

No worktrees, inherited grant, real HTTPS endpoint, credentials or forge writes.
The fake HTTP server counts invocations AND effects, including response loss.
"""
from __future__ import annotations

import dataclasses
import http.client
import json
import multiprocessing
import os
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from gaia_cli.steward import ledger
from gaia_cli.steward.prmaintenance import coordination as core, executor as ex, gate, proofs
from . import helpers as h
from .coordination_helpers import assertIndependent
from .test_executor import Clock, world, prepare
from .test_coordination_processes import collectActors


class FixtureHttp:
    def __init__(self, port): self.port = port
    def request(self, method, path, body=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        try:
            connection.request(method, path, body=None if body is None else json.dumps(body),
                               headers={"Content-Type": "application/json"})
            response = connection.getresponse()
            return ex.HttpReply(response.status, {}, json.loads(response.read(2 * 1024 * 1024)))
        finally:
            connection.close()


@pytest.fixture(autouse=True)
def fastContentEngineProofs(monkeypatch):
    monkeypatch.setattr(proofs, "contentEngineProofs", lambda root, baseSha, headSha, label: [
        proofs.Proof("rendered-html", proofs.PASS, "ok"),
        proofs.Proof("index-rebuild", proofs.PASS, "ok"),
    ])


def concrete(root, storeRoot, binding, configured, port):
    transport = FixtureHttp(port)
    service = ex.ProductionServices(root, configured, transport, Clock(),
        lambda number: gate.Snapshot(**transport.request("GET", "/__snapshot").body),
        lambda: h.run(root, "rev-parse", "refs/remotes/origin/main"))
    return ex.Executor(core.PrWriteCoordinator(ledger.GitRefLedgerStore(storeRoot, ref=core.REF), binding, service))


def actor(root, storeRoot, binding, configured, port, operationId, barrier, output):
    proofs.contentEngineProofs = lambda root, baseSha, headSha, label: [
        proofs.Proof("rendered-html", proofs.PASS, "ok"),
        proofs.Proof("index-rebuild", proofs.PASS, "ok"),
    ]
    executor = concrete(root, storeRoot, binding, configured, port)
    original, waited = executor.coordinator.store.compare_and_swap, False
    def contend(expected, document, message):
        nonlocal waited
        if message.split()[1] == "claim" and not waited:
            waited = True
            barrier.wait(10)
        try:
            return original(expected, document, message)
        except ledger.LedgerConflict:
            output.put(("conflict", "claim"))
            raise
    executor.coordinator.store.compare_and_swap = contend
    enter = executor.coordinator._consumeAdapter
    def forkEntry(service, request, invocationId):
        # The winner is a fresh spawned actor: no inherited pytest watchdog.
        # Fork exactly while the concrete adapter's one-shot entry is live.
        child = os.fork()
        if child == 0:
            statusFile = root / f"child-{os.getpid()}.status"
            try:
                enter(service, request, invocationId)
            except core.Refused:
                statusFile.write_text("0")
                os._exit(0)
            except BaseException:
                statusFile.write_text("32")
                os._exit(32)
            statusFile.write_text("31")
            os._exit(31)
        statusFile = root / f"child-{child}.status"
        try:
            waited, status = os.waitpid(child, 0)
            assert waited == child and os.waitstatus_to_exitcode(status) == 0
        except ChildProcessError:
            pass
        if not statusFile.is_file() or statusFile.read_text().strip() != "0":
            raise RuntimeError(f"Child process {child} did not exit with code 0 (status: {statusFile.read_text() if statusFile.is_file() else 'missing'})")
        return enter(service, request, invocationId)
    executor.coordinator._consumeAdapter = forkEntry
    result = executor.execute(operationId)
    output.put(("result", result["state"]))
    output.put(("done", str(root)))


@pytest.mark.parametrize("lost", [False, True])
def test_spawned_concrete_executors_share_one_http_invocation_and_cold_recovery(tmp_path, monkeypatch, lost):
    fixture = world(tmp_path, monkeypatch)
    fx, forge, _, executor, _, _ = fixture
    operation = prepare(fixture)
    forge.lost = lost
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def dispatch(self):
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0")))) if self.headers.get("Content-Length") else None
            try:
                reply = (ex.HttpReply(200, {}, dataclasses.asdict(forge.snap)) if self.path == "/__snapshot"
                         else forge.request(self.command, self.path, body))
            except OSError:
                self.close_connection = True  # effect happened; no HTTP response
                return
            data = json.dumps(reply.body).encode()
            self.send_response(reply.status)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        do_GET = do_PUT = do_PATCH = dispatch
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    serving = threading.Thread(target=server.serve_forever, daemon=True)
    serving.start()
    roots = [tmp_path / "host-a", tmp_path / "host-b"]
    for root in roots:
        subprocess.run(["git", "clone", "--no-local", "--quiet", str(fx.root), str(root)], check=True, capture_output=True, timeout=30)
        assert not (root / ".gaia/steward/pr-maintenance/verifications.jsonl").exists()
    assertIndependent(*roots)
    first = executor.coordinator.store.repo_root
    second = first.parent / "second"
    assertIndependent(first, second)
    context = multiprocessing.get_context("spawn")
    barrier, output = context.Barrier(2), context.Queue()
    processes = [context.Process(target=actor, args=(root, storeRoot, executor.coordinator.binding,
                 executor.services.binding, server.server_port, operation["operationId"], barrier, output))
                 for root, storeRoot in zip(roots, (first, second))]
    try:
        for process in processes: process.start()
        messages = collectActors(processes, output)
        assert sum(kind == "conflict" for kind, _ in messages) == 1
        assert len(forge.invocations) == len(forge.effects) == 1
        # Original checkout and its local dispatch/verification files disappear.
        fx.root.rename(fx.root.with_name("original-checkout-gone"))
        cold = concrete(roots[1], second, executor.coordinator.binding, executor.services.binding, server.server_port)
        result = cold.recover(operation["operationId"])
        assert result["state"] == ("already-merged" if lost else "merged")
        assert result["evidenceSha256"] and result["mergeCommitSha"] == "d" * 40
        assert cold.execute(operation["operationId"])["state"] == result["state"]
        assert len(forge.invocations) == len(forge.effects) == 1
    finally:
        for process in processes:
            if process.is_alive(): process.terminate(); process.join(5)
        server.shutdown()
        server.server_close()
        serving.join(5)
