"""Real coordinator + concrete production services, fixture-only forge/clock."""
from __future__ import annotations

import base64
import copy
import dataclasses
import json
import subprocess
from dataclasses import asdict
from urllib.parse import parse_qs, urlsplit

import pytest
import yaml

from gaia_cli.steward import ledger
from gaia_cli.steward.prmaintenance import coordination as core, executor as ex, gate, state
from gaia_cli.steward.prmaintenance.policy import WriteCoordination
from . import helpers as h
from .coordination_helpers import seed


class Clock:
    def __init__(self):
        self.instant = int(h.utc().timestamp())
    def sample(self):
        return core.TimeBounds(self.instant, self.instant, "authoritative-fixture-clock")


class Forge:
    def __init__(self, fx, snap):
        self.fx, self.snap = fx, snap
        self.tip = fx.base
        self.sources = {path: (fx.root / path).read_bytes() for path in gate.AUTHORITY_FILES}
        self.invocations, self.effects = [], []
        self.lost, self.reopen, self.reject = False, False, False
        self.fact = {"id": snap.row["number"], "state": "open", "merged": False, "head": {"sha": snap.row["headSha"]}}
        self.before = None
    def request(self, method, path, body=None):
        parsed = urlsplit(path)
        route = parsed.path
        if method in {"PUT", "PATCH"}:
            self.invocations.append((method, path, copy.deepcopy(body)))
            if self.before:
                self.before()
            if self.reject:
                return ex.HttpReply(409, {}, {"merged": False})
            self.effects.append(method)
            self.fact.update(state="closed", closed_at="2026-11-04T18:30:00Z")
            if method == "PUT":
                self.fact.update(merged=True, merge_commit_sha="d" * 40)
                response = {"merged": True, "sha": "d" * 40}
            else:
                response = copy.deepcopy(self.fact)
            if self.reopen:
                self.fact.update(state="open")
            if self.lost:
                raise OSError("synthetic lost response")
            return ex.HttpReply(200, {}, response)
        if method == "POST":
            raise OSError("synthetic receipt failure")
        prefix = f"/repos/{h.REPO}"
        if route == prefix:
            value = {"id": 42, "full_name": h.REPO}
        elif route == prefix + "/git/ref/heads/main":
            value = {"object": {"sha": self.tip}}
        elif route.startswith(prefix + "/contents/"):
            relative = route[len(prefix + "/contents/"):]
            assert parse_qs(parsed.query)["ref"] == [self.tip]
            value = {"encoding": "base64", "content": base64.b64encode(self.sources[relative]).decode()}
        elif route == prefix + "/pulls/2400":
            value = {"id": 2400, "merged": True, "head": {"sha": "e" * 40}}
        elif route == prefix + f"/pulls/{self.snap.row['number']}":
            value = copy.deepcopy(self.fact)
        elif route == prefix + "/commits/" + "d" * 40:
            value = {"parents": [{"sha": self.fx.base}, {"sha": self.snap.row["headSha"]}]}
        else:
            raise AssertionError("unexpected fixture-only route")
        return ex.HttpReply(200, {}, value)


def world(tmp_path, monkeypatch, action="merge"):
    namespace = core.Namespace("github.com", "42", h.REPO, "a" * 32)
    coordinationRoot = tmp_path / "coordination"
    coordinationRoot.mkdir(parents=True)
    remote, transportBinding, first, second = seed(coordinationRoot, monkeypatch, namespace)
    fx = h.makeRepo(tmp_path / "content", labels=("2026-42", "2026-43", "2026-44") if action == "close" else ("2026-42", "2026-43"))
    configured = WriteCoordination(core.SCHEMA, "github.com", "42", h.REPO, namespace.epoch,
                                   transportBinding.genesis, transportBinding.historyPin, f"https://github.com/{h.REPO}.git", "main",
                                   {"url": "https://clock.invalid/v1", "maxSkewSeconds": 1, "precisionSeconds": 1, "maxRoundTripSeconds": 2})
    path = fx.root / "founder/steward/POLICY.yaml"
    document = yaml.safe_load(path.read_text())
    document["prMaintenance"]["writeCoordination"] = asdict(configured)
    path.write_text(yaml.safe_dump(document, sort_keys=False))
    fx.base = fx.commit("disposable configured source")
    head = fx.head("2026-44")
    row = h.row(fx, head, "2026-44", prId="2270", repositoryId="42")
    closed = [{"number": 2400, "state": "closed", "mergedAt": "2026-11-04T17:00:00Z", "mergeCommitSha": "e" * 40,
               "headRef": "steward/b/replacement", "title": "fixture", "body": f"<!-- gaia-steward:replaces repo={h.REPO} pr=2270 -->"}] if action == "close" else []
    snap = gate.Snapshot(row, {"main": fx.base}, {"complete": True, "requiredChecks": h.REQUIRED}, [], closed)
    forge, clock = Forge(fx, snap), Clock()
    def make(root=fx.root, storeRoot=first):
        service = ex.ProductionServices(root, configured, forge, clock, lambda n: forge.snap)
        return ex.Executor(core.PrWriteCoordinator(ledger.GitRefLedgerStore(storeRoot, ref=core.REF), transportBinding, service))
    executor = make()
    monkeypatch.setattr(gate, "makeExecutor", lambda root: executor)
    verifier = {"agentId": "verifier", "profileId": "fixture", "effort": "xhigh"}
    state.appendRecord(fx.root, "dispatches", {"kind": "dispatch", "status": "started", "role": "verifier", "runId": "stable-run",
        "dispatchId": "dispatch", "agentId": "verifier", "effort": "xhigh", "builders": ["builder"],
        "envelope": {"subjects": [{"repo": h.REPO, "number": 2270, "headSha": head}]}})
    gate.recordVerification(fx.root, {"runId": "stable-run", "repo": h.REPO, "number": 2270, "action": action,
        "headSha": head, "baseSha": fx.base, "verdict": "pass", "verifier": verifier, "builders": ["builder"],
        "proofs": [{"name": "actual fixture validation", "state": "pass", "detail": "checked"}]}, h.utc())
    request = {"action": action, "repo": h.REPO, "number": 2270, "expectedHeadSha": head, "baseRef": "main", "producerId": "weekly-content-engine"}
    if action == "close":
        request.update(reason="label-already-published", replacement=2400)
    return fx, forge, clock, executor, request, lambda: make(storeRoot=second)


def prepare(world):
    fx, forge, clock, executor, request, cold = world
    fn = gate.gateMerge if request["action"] == "merge" else gate.gateClose
    return fn(fx.root, request, forge.snap, h.utc(), "stable-run")


@pytest.mark.parametrize("action", ["merge", "close"])
def test_concrete_services_full_sources_exact_sole_http_and_cold_truth(tmp_path, monkeypatch, action):
    fixture = world(tmp_path, monkeypatch, action)
    fx, forge, clock, executor, request, cold = fixture
    operation = prepare(fixture)
    assert operation["state"] == "intent" and forge.invocations == []
    result = executor.execute(operation["operationId"])
    assert result["state"] == ("merged" if action == "merge" else "closed")
    assert len(forge.invocations) == len(forge.effects) == 1
    method, path, body = forge.invocations[0]
    assert body == ({"sha": request["expectedHeadSha"], "merge_method": "merge"} if action == "merge" else {"state": "closed"})
    assert method == ("PUT" if action == "merge" else "PATCH")
    assert executor.execute(operation["operationId"])["state"] == result["state"]
    assert len(forge.invocations) == 1
    assert cold().recover(operation["operationId"])["state"] == result["state"]
    stored = executor.coordinator.inspect()["operations"][operation["operationId"]]
    for key, relative in zip(("policy", "producerRegistry", "authority"), gate.AUTHORITY_FILES):
        assert core.digest(stored["proof"][key]) == core.digest((fx.root / relative).read_text())
    assert state.readRecords(fx.root, "outcomes") == []  # local JSONL is not shared settlement


@pytest.mark.parametrize("action", ["merge", "close"])
def test_lost_response_recovery_no_resend_closed_is_not_absorbing(tmp_path, monkeypatch, action):
    fixture = world(tmp_path, monkeypatch, action)
    _, forge, clock, executor, _, cold = fixture
    operation = prepare(fixture)
    forge.lost = True
    assert executor.execute(operation["operationId"])["state"] == "unknown"
    recovered = cold().recover(operation["operationId"])
    assert recovered["state"] == ("already-merged" if action == "merge" else "quarantined")
    if action == "close":
        forge.fact["state"] = "open"
        clock.instant += 100000
        assert cold().recover(operation["operationId"])["state"] == "quarantined"
    assert len(forge.invocations) == len(forge.effects) == 1


def test_authenticated_close_response_can_retire_after_reopen(tmp_path, monkeypatch):
    fixture = world(tmp_path, monkeypatch, "close")
    _, forge, _, executor, _, _ = fixture
    operation = prepare(fixture)
    forge.reopen = True
    assert executor.execute(operation["operationId"])["state"] == "closed"
    stored = executor.coordinator.inspect()["operations"][operation["operationId"]]
    assert stored["evidence"]["observedState"] == "reopened"
    assert len(forge.invocations) == len(forge.effects) == 1


@pytest.mark.parametrize("change", ["kill", "source", "head", "base", "hold", "verification", "identity"])
def test_current_boundary_refuses_changes_without_http_invocation(tmp_path, monkeypatch, change):
    fixture = world(tmp_path, monkeypatch)
    fx, forge, _, executor, _, _ = fixture
    operation = prepare(fixture)
    if change == "kill":
        monkeypatch.setenv("GAIA_STEWARD_PR_KILL", "1")
    elif change == "source":
        forge.sources[gate.AUTHORITY_FILES[0]] += b"\n"
    elif change == "head":
        forge.snap = dataclasses.replace(forge.snap, row={**forge.snap.row, "headSha": "e" * 40})
    elif change == "base":
        forge.snap = dataclasses.replace(forge.snap, tips={"main": "e" * 40})
    elif change == "hold":
        forge.snap = dataclasses.replace(forge.snap, row={**forge.snap.row, "labels": ["content-engine", "founder-hold"]})
    elif change == "identity":
        forge.snap = dataclasses.replace(forge.snap, row={**forge.snap.row, "prId": "another"})
    else:
        state.appendRecord(fx.root, "verifications", {"repo": h.REPO, "number": 2270, "action": "merge", "headSha": forge.snap.row["headSha"],
                                                     "at": "2026-11-04T18:30:00Z", "verdict": "fail"})
    with pytest.raises((core.CoordinationError, gate.GateRefused)):
        executor.execute(operation["operationId"])
    assert forge.invocations == forge.effects == []


def test_receipt_post_failure_and_loss_of_local_receipts_cannot_invalidate_durable_proof(tmp_path, monkeypatch):
    fixture = world(tmp_path, monkeypatch)
    fx, forge, _, executor, _, _ = fixture
    operation = prepare(fixture)
    # All comments were absent. The independent dispatch/verdict is now in the
    # protected shared operation, not dependent on this checkout's JSONL files.
    for name in ("verifications", "dispatches"):
        (state.storeDir(fx.root) / f"{name}.jsonl").unlink()
    with pytest.raises(OSError):
        forge.request("POST", "/synthetic-receipt", {"body": "synthetic"})
    assert executor.execute(operation["operationId"])["state"] == "merged"
    assert len(forge.invocations) == len(forge.effects) == 1


def test_factory_missing_binding_fails_before_credentials_transport_or_store(tmp_path, monkeypatch):
    fx = h.makeRepo(tmp_path)
    monkeypatch.setattr(ex, "HttpsTransport", lambda *a: pytest.fail("must not construct transport"))
    with pytest.raises(core.CoordinationError, match="unconfigured"):
        ex.makeExecutor(fx.root)


class ClockHttp:
    def __init__(self):
        self.instant, self.mode = 10000, "valid"
    def request(self, method, path, body=None):
        nonce = parse_qs(urlsplit(path).query)["nonce"][0]
        headers = {"cache-control": "no-store", "age": "0"}
        data = {"nonce": nonce, "unixSeconds": self.instant, "uncertaintySeconds": 1}
        if self.mode == "cache": headers["age"] = "1"
        if self.mode == "nonce": data["nonce"] = "stale"
        if self.mode == "bad": data["unixSeconds"] = True
        if self.mode == "missing": data.pop("unixSeconds")
        if self.mode == "no-store": headers.clear()
        return ex.HttpReply(200, headers, data)


@pytest.mark.parametrize("mode", ["cache", "nonce", "bad", "missing", "no-store", "regression", "delay", "monotonic"])
def test_concrete_clock_missing_stale_skew_network_and_regression_fail_closed(mode):
    http = ClockHttp()
    instants = iter([1.0, 1.1, 2.0, 2.1])
    clock = ex.BoundedClock({"url": "https://clock.invalid/v1", "maxSkewSeconds": 1,
                             "precisionSeconds": 1, "maxRoundTripSeconds": 2}, http, lambda: next(instants))
    assert clock.sample() == core.TimeBounds(9998, 10003, "nonce-bound-https-clock-v1")
    if mode == "regression": http.instant -= 5
    elif mode == "delay": clock.monotonic = iter([2.0, 8.0]).__next__
    elif mode == "monotonic": clock.monotonic = iter([0.0, 0.1]).__next__
    else: http.mode = mode
    with pytest.raises(core.CoordinationError):
        clock.sample()
