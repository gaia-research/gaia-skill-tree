"""Real coordinator + concrete production services, fixture-only forge/clock."""
from __future__ import annotations

import base64
import copy
import dataclasses
import json
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
        self.fact = {"id": snap.row["number"], "state": "open", "merged": False, "head": {"sha": snap.row["headSha"]}, "base": {"ref": snap.row["baseRef"], "repo": {"id": 42}}}
        self.parentShas = None
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
            value = {"parents": [{"sha": sha} for sha in (self.parentShas or [self.fx.base, self.snap.row["headSha"]])]}
        elif route == prefix + "/commits/" + "d" * 40 + "/check-runs":
            value = {"check_runs": []}
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
        service = ex.ProductionServices(root, configured, forge, clock, lambda n: forge.snap,
                                        lambda: h.run(root, "rev-parse", "refs/heads/main"))
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


def test_cli_close_502_reports_correlated_uncertainty(tmp_path, monkeypatch, capsys):
    from gaia_cli.steward.prmaintenance import cli
    fixture = world(tmp_path, monkeypatch, "close")
    fx, forge, clock, executor, _, cold = fixture
    operation = prepare(fixture)
    original = forge.request
    def response502(method, path, body=None):
        response = original(method, path, body)
        return ex.HttpReply(502, {}, {}) if method == "PATCH" else response
    forge.request = response502
    monkeypatch.setattr(ex, "makeExecutor", lambda root: executor)
    assert cli.main(["--root", str(fx.root), "--json", "execute", "--operation-id", operation["operationId"]]) == 2
    output = json.loads(capsys.readouterr().out)
    shared = executor.coordinator.inspect()
    assert shared["operations"][operation["operationId"]]["state"] == "possibly-sent"
    assert shared["activeOperationId"] == operation["operationId"]
    assert core.usage(shared, clock.sample(), "stable-run", "close") == (1, 1)
    assert forge.fact["state"] == "closed"
    assert len(forge.invocations) == len(forge.effects) == 1
    assert output.get("operationId") == operation["operationId"]
    assert output.get("state") in {"possibly-sent", "unknown", "quarantined"}
    assert output.get("uncertaintyCause") == "transport"  # the 502 could not authenticate an effect
    assert "refused" not in output
    shared = executor.coordinator.inspect()
    assert shared["operations"][operation["operationId"]]["state"] in core.PENDING
    assert shared["activeOperationId"] == operation["operationId"]
    assert core.usage(shared, clock.sample(), "stable-run", "close") == (1, 1)
    assert forge.fact["state"] == "closed"
    assert len(forge.invocations) == len(forge.effects) == 1
    assert cold().recover(operation["operationId"])["state"] == "quarantined"
    clock.instant += 10 * 86400
    assert cold().recover(operation["operationId"])["state"] == "quarantined"
    assert len(forge.invocations) == len(forge.effects) == 1


@pytest.mark.parametrize("failure", ["completion", "settlement", "unknown-transition"])
def test_post_effect_errors_remain_correlated_even_when_shared_write_fails(tmp_path, monkeypatch, failure):
    fixture = world(tmp_path, monkeypatch, "close")
    _, forge, clock, executor, _, cold = fixture
    operation = prepare(fixture)
    if failure == "completion":
        def fail(*args):
            raise core.CoordinationError("synthetic completion authentication failure")
        monkeypatch.setattr(executor.services, "completion", fail)
    else:
        original = executor.coordinator._transition
        if failure == "unknown-transition":
            forge.lost = True
        def transition(kind, *args):
            if kind == ("unknown" if failure == "unknown-transition" else "complete"):
                raise ledger.LedgerUnavailable("synthetic settlement failure")
            return original(kind, *args)
        monkeypatch.setattr(executor.coordinator, "_transition", transition)
    result = executor.execute(operation["operationId"])
    assert result["operationId"] == operation["operationId"] and result["state"] == "possibly-sent"
    assert result["coordinationState"] == "unavailable"
    assert result["uncertaintyCause"] == {"completion": "completion-failed", "settlement": "persistence",
                                          "unknown-transition": "persistence"}[failure]
    shared = executor.coordinator.inspect()
    assert shared["operations"][operation["operationId"]]["state"] == "possibly-sent"
    assert shared["activeOperationId"] == operation["operationId"]
    assert core.usage(shared, clock.sample(), "stable-run", "close") == (1, 1)
    assert len(forge.invocations) == len(forge.effects) == 1
    assert cold().execute(operation["operationId"])["state"] == "possibly-sent"
    assert len(forge.invocations) == len(forge.effects) == 1


def test_cli_presend_refusal_remains_distinct(tmp_path, monkeypatch, capsys):
    from gaia_cli.steward.prmaintenance import cli
    fixture = world(tmp_path, monkeypatch, "close")
    fx, forge, _, executor, _, _ = fixture
    operation = prepare(fixture)
    monkeypatch.setattr(ex, "makeExecutor", lambda root: executor)
    monkeypatch.setenv("GAIA_STEWARD_PR_KILL", "1")
    assert cli.main(["--root", str(fx.root), "--json", "execute", "--operation-id", operation["operationId"]]) == 2
    result = json.loads(capsys.readouterr().out)
    assert result["refused"] == "kill-switch" and "state" not in result
    assert forge.invocations == forge.effects == []
    assert executor.coordinator.inspect()["operations"][operation["operationId"]]["state"] == "intent"


def test_cli_capacity_settlement_refusal_stays_sanitized_uncertainty(tmp_path, monkeypatch, capsys):
    from gaia_cli.steward.prmaintenance import cli
    fixture = world(tmp_path, monkeypatch, "close")
    fx, forge, clock, executor, _, cold = fixture
    operation = prepare(fixture)
    original = executor.coordinator._transition
    def capacity(kind, *args):
        if kind == "complete":
            raise core.CapacityRefused("critical record capacity exhausted; settlement headroom retained")
        return original(kind, *args)
    monkeypatch.setattr(executor.coordinator, "_transition", capacity)
    monkeypatch.setattr(ex, "makeExecutor", lambda root: executor)
    assert cli.main(["--root", str(fx.root), "--json", "execute", "--operation-id", operation["operationId"]]) == 2
    output = json.loads(capsys.readouterr().out)
    assert output["operationId"] == operation["operationId"] and output["state"] == "possibly-sent"
    assert output["coordinationState"] == "unavailable" and output["uncertaintyCause"] == "capacity"
    assert output["evidenceSha256"] is None and "refused" not in output
    assert "critical record" not in json.dumps(output)  # raw cause text is never published
    shared = executor.coordinator.inspect()
    assert shared["operations"][operation["operationId"]]["state"] == "possibly-sent"
    assert shared["activeOperationId"] == operation["operationId"]
    assert core.usage(shared, clock.sample(), "stable-run", "close") == (1, 1)
    assert forge.fact["state"] == "closed"
    assert len(forge.invocations) == len(forge.effects) == 1
    assert cold().execute(operation["operationId"])["state"] == "possibly-sent"  # no replay
    assert len(forge.invocations) == len(forge.effects) == 1


def test_completion_evidence_mismatch_is_sanitized_uncertainty(tmp_path, monkeypatch):
    fixture = world(tmp_path, monkeypatch, "close")
    _, forge, clock, executor, _, cold = fixture
    operation = prepare(fixture)
    original = executor.services.completion
    def invalidEvidence(operationArg, invocationId, response):
        result = original(operationArg, invocationId, response)
        result["attemptId"] = "0" * 64
        return result
    monkeypatch.setattr(executor.services, "completion", invalidEvidence)
    result = executor.execute(operation["operationId"])
    assert result["operationId"] == operation["operationId"] and result["state"] == "possibly-sent"
    assert result["coordinationState"] == "unavailable" and result["uncertaintyCause"] == "completion-failed"
    assert "0" * 64 not in json.dumps(result)  # the rejected evidence is not echoed
    shared = executor.coordinator.inspect()
    assert shared["operations"][operation["operationId"]]["state"] == "possibly-sent"
    assert shared["activeOperationId"] == operation["operationId"]
    assert core.usage(shared, clock.sample(), "stable-run", "close") == (1, 1)
    assert len(forge.invocations) == len(forge.effects) == 1
    assert cold().execute(operation["operationId"])["state"] == "possibly-sent"  # no replay
    assert len(forge.invocations) == len(forge.effects) == 1


def test_untrusted_completion_binding_is_sanitized_uncertainty(tmp_path, monkeypatch):
    fixture = world(tmp_path, monkeypatch, "close")
    _, forge, clock, executor, _, cold = fixture
    operation = prepare(fixture)
    def untrusted(*args):
        raise core.CompletionInvalid("not an authentic completion of this sole invocation")
    monkeypatch.setattr(executor.services, "completion", untrusted)
    result = executor.execute(operation["operationId"])
    assert result["operationId"] == operation["operationId"] and result["state"] == "possibly-sent"
    assert result["coordinationState"] == "unavailable" and result["uncertaintyCause"] == "completion-failed"
    shared = executor.coordinator.inspect()
    assert shared["operations"][operation["operationId"]]["state"] == "possibly-sent"
    assert shared["activeOperationId"] == operation["operationId"]
    assert core.usage(shared, clock.sample(), "stable-run", "close") == (1, 1)
    assert forge.fact["state"] == "closed"
    assert len(forge.invocations) == len(forge.effects) == 1
    assert cold().execute(operation["operationId"])["state"] == "possibly-sent"  # no replay
    assert len(forge.invocations) == len(forge.effects) == 1


def test_post_settlement_inspect_failure_is_correlated_uncertainty(tmp_path, monkeypatch):
    fixture = world(tmp_path, monkeypatch, "close")
    _, forge, clock, executor, _, cold = fixture
    operation = prepare(fixture)
    originalInvoke, originalInspect = executor.coordinator.invoke, executor.coordinator.inspect
    sent = {"done": False}
    def invoke(*args, **kwargs):
        try:
            return originalInvoke(*args, **kwargs)
        finally:
            sent["done"] = True
    def inspect():
        if sent["done"]:
            raise ledger.LedgerUnavailable("synthetic post-settlement report unavailable")
        return originalInspect()
    monkeypatch.setattr(executor.coordinator, "invoke", invoke)
    monkeypatch.setattr(executor.coordinator, "inspect", inspect)
    result = executor.execute(operation["operationId"])
    assert result["operationId"] == operation["operationId"] and result["state"] == "possibly-sent"
    assert result["coordinationState"] == "unavailable" and result["uncertaintyCause"] == "inspection"
    assert "synthetic post-settlement" not in json.dumps(result)  # raw cause text is never published
    shared = originalInspect()  # actual shared truth, observed outside the failure
    assert shared["operations"][operation["operationId"]]["state"] == "completed-effect"
    assert shared["activeOperationId"] is None
    assert core.usage(shared, clock.sample(), "stable-run", "close") == (1, 1)
    assert forge.fact["state"] == "closed"
    assert len(forge.invocations) == len(forge.effects) == 1
    assert cold().execute(operation["operationId"])["state"] == "closed"  # terminal report, no replay
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
        if self.mode == "fake-no-store": headers["cache-control"] = "x-no-store=false"
        if self.mode == "date-only": data = {}; headers["date"] = "Wed, 04 Nov 2026 18:30:00 GMT"
        return ex.HttpReply(200, headers, data)


@pytest.mark.parametrize("mode", ["cache", "nonce", "bad", "missing", "no-store", "fake-no-store", "regression", "future", "delay", "monotonic", "stalled", "date-only"])
def test_concrete_clock_missing_stale_skew_network_and_regression_fail_closed(mode):
    http = ClockHttp()
    instants = iter([1.0, 1.1, 2.0, 2.1])
    clock = ex.BoundedClock({"url": "https://clock.invalid/v1", "maxSkewSeconds": 1,
                             "precisionSeconds": 1, "maxRoundTripSeconds": 2}, http, lambda: next(instants))
    assert clock.sample() == core.TimeBounds(9998, 10003, "nonce-bound-https-clock-v1")
    if mode == "regression": http.instant -= 5
    elif mode == "future": http.instant += 10000
    elif mode == "delay": clock.monotonic = iter([2.0, 8.0]).__next__
    elif mode == "monotonic": clock.monotonic = iter([0.0, 0.1]).__next__
    elif mode == "stalled": clock.monotonic = iter([100.0, 100.1]).__next__
    else: http.mode = mode
    with pytest.raises(core.CoordinationError):
        clock.sample()


def test_post_claim_last_boundary_failure_is_proven_unsent_without_http_or_refund(tmp_path, monkeypatch):
    # Deliberate contract change (lead decision 1, review of #2317): a live re-check refusal after the claim and before
    # any socket write is a PROVEN no-send. It no longer pins the global slot forever, but it is never a refund: the
    # attempt and its charge stay counted, the operation stays spent, and nothing was ever sent.
    fixture = world(tmp_path, monkeypatch)
    _, forge, clock, executor, _, _ = fixture
    operation = prepare(fixture)
    consume = executor.coordinator._consume
    def changed(grant, op):
        consume(grant, op)
        forge.sources[gate.AUTHORITY_FILES[0]] += b"\n"
    monkeypatch.setattr(executor.coordinator, "_consume", changed)
    first = executor.execute(operation["operationId"])
    assert (first["state"], first["coordinationState"]) == ("failed", "canceled-after-claim")
    shared = executor.coordinator.inspect()
    assert shared["activeOperationId"] is None
    assert core.usage(shared, clock.sample(), "stable-run", "merge") == (1, 1)
    again = executor.execute(operation["operationId"])  # a terminal record is inspection, never a send grant
    assert (again["state"], again["coordinationState"]) == ("failed", "canceled-after-claim")
    assert forge.invocations == forge.effects == []


def test_stale_api_authority_cannot_override_current_canonical_git_tip(tmp_path, monkeypatch):
    fixture = world(tmp_path, monkeypatch)
    fx, forge, _, executor, _, _ = fixture
    operation = prepare(fixture)
    current = fx.commit("fixture canonical tip advanced without source-text edits")
    h.run(fx.root, "update-ref", "refs/heads/main", current)
    with pytest.raises(core.CoordinationError, match="current canonical Git"):
        executor.execute(operation["operationId"])
    assert forge.invocations == forge.effects == []


def test_explicit_cli_carries_operation_identity_and_shared_terminal_proof(tmp_path, monkeypatch, capsys):
    from gaia_cli.steward.prmaintenance import cli
    fixture = world(tmp_path, monkeypatch)
    fx, forge, _, executor, request, _ = fixture
    monkeypatch.setattr(cli, "snapshotFor", lambda *a: forge.snap)
    monkeypatch.setattr(ex, "makeExecutor", lambda root: executor)
    base = ["--root", str(fx.root), "--json"]
    assert cli.main(base + ["gate-merge", "--repo", h.REPO, "--number", "2270", "--head", request["expectedHeadSha"],
                            "--producer", "weekly-content-engine", "--run-id", "stable-run"]) == 0
    prepared = json.loads(capsys.readouterr().out)
    assert prepared["state"] == "intent" and forge.invocations == []
    assert cli.main(base + ["execute", "--operation-id", prepared["operationId"]]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["repo"] == h.REPO and result["state"] == "merged" and result["evidenceSha256"]
    assert result["mergeCommitSha"] == "d" * 40
    assert cli.main(base + ["recover", "--operation-id", prepared["operationId"]]) == 0
    assert json.loads(capsys.readouterr().out)["evidenceSha256"] == result["evidenceSha256"]
    assert len(forge.invocations) == len(forge.effects) == 1


def test_https_mutation_transport_never_retries_or_follows_redirects(monkeypatch):
    calls = []
    class Response:
        status = 302
        def read(self, maximum): return b"{}"
        def getheaders(self): return [("Location", "https://elsewhere.invalid/")]
    class Connection:
        def connect(self): calls.append(("connect",))  # the transport now connects explicitly, before any request byte
        def request(self, method, path, body, headers): calls.append((method, path))
        def getresponse(self): return Response()
        def close(self): pass
    monkeypatch.setattr(ex.http.client, "HTTPSConnection", lambda *a, **kw: Connection())
    transport = ex.HttpsTransport("https://forge.invalid", "synthetic-test-only")
    response = transport.request("PATCH", "/exact-route", {"state": "closed"})
    assert response.status == 302 and calls == [("connect",), ("PATCH", "/exact-route")]
    assert "synthetic-test-only" not in repr(response)


def test_definite_rejection_releases_sender_but_keeps_counted_attempt(tmp_path, monkeypatch):
    fixture = world(tmp_path, monkeypatch)
    _, forge, clock, executor, _, _ = fixture
    operation = prepare(fixture)
    forge.reject = True
    result = executor.execute(operation["operationId"])
    assert result["state"] == "failed" and result["reason"]
    durable = executor.coordinator.inspect()
    assert durable["activeOperationId"] is None
    assert core.usage(durable, clock.sample(), "stable-run", "merge") == (1, 1)
    assert len(forge.invocations) == 1 and forge.effects == []


def test_caller_response_or_replayed_capture_cannot_settle(tmp_path, monkeypatch):
    fixture = world(tmp_path, monkeypatch)
    _, forge, _, executor, _, _ = fixture
    operation = prepare(fixture)
    durable = executor.coordinator.inspect()["operations"][operation["operationId"]]
    forged = ex.HttpReply(200, {}, {"merged": True, "sha": "d" * 40})
    with pytest.raises(core.CoordinationError, match="authentic completion"):
        executor.services.completion(durable, "0" * 64, forged)
    assert executor.coordinator.inspect()["operations"][operation["operationId"]]["state"] == "intent"
    executor.execute(operation["operationId"])
    durable = executor.coordinator.inspect()["operations"][operation["operationId"]]
    with pytest.raises(core.CoordinationError, match="authentic completion"):
        executor.services.completion(durable, durable["invocationId"], forged)
    assert len(forge.invocations) == len(forge.effects) == 1


def test_required_comment_read_failure_and_stale_clock_cannot_send(tmp_path, monkeypatch):
    from gaia_cli.steward.prmaintenance import collect
    fixture = world(tmp_path, monkeypatch)
    _, forge, _, executor, _, _ = fixture
    operation = prepare(fixture)
    def unavailable(number):
        raise collect.CollectError("required hold-comment read failed")
    executor.services.snapshot = unavailable
    with pytest.raises(collect.CollectError):
        executor.execute(operation["operationId"])
    assert forge.invocations == forge.effects == []
    executor.services.snapshot = lambda number: forge.snap
    def badClock(): raise core.CoordinationError("trusted clock unavailable")
    executor.services.time.sample = badClock
    with pytest.raises(core.CoordinationError, match="clock unavailable"):
        executor.execute(operation["operationId"])
    assert executor.coordinator.inspect()["operations"][operation["operationId"]]["state"] == "intent"
    assert forge.invocations == forge.effects == []


def test_strict_optional_binding_rejects_namespace_clock_and_protection_spoofs(tmp_path, monkeypatch):
    from gaia_cli.steward.prmaintenance.policy import coordinationBinding, PrPolicyError
    fixture = world(tmp_path, monkeypatch)
    configured = asdict(fixture[3].services.binding)
    assert coordinationBinding(configured) == fixture[3].services.binding
    changes = {"remote": "other", "ref": "refs/heads/main", "protocol": "unknown", "epoch": "bad",
               "genesis": "short", "historyPin": "short", "protectionsVerified": False,
               "bypassingWritersDrained": False, "authorityBranch": "main\nother"}
    for key, value in changes.items():
        with pytest.raises(PrPolicyError):
            coordinationBinding({**configured, key: value})
    with pytest.raises(PrPolicyError):
        coordinationBinding({**configured, "authorityBranch": "dev/self-nominated"})
    for clock in ({}, {**configured["clock"], "precisionSeconds": 0},
                  {**configured["clock"], "url": "https://user:secret@clock.invalid/v1"},
                  {**configured["clock"], "url": "https://clock.invalid:invalid/v1"},
                  {**configured["clock"], "url": {}}):
        with pytest.raises(PrPolicyError):
            coordinationBinding({**configured, "clock": clock})


def test_unverified_config_cannot_send_github_credentials_to_another_host(tmp_path, monkeypatch):
    fixture = world(tmp_path, monkeypatch)
    fx = fixture[0]
    path = fx.root / "founder/steward/POLICY.yaml"
    document = yaml.safe_load(path.read_text())
    configured = document["prMaintenance"]["writeCoordination"]
    configured.update(forgeHost="elsewhere.invalid", canonicalUrl=f"https://elsewhere.invalid/{h.REPO}.git")
    path.write_text(yaml.safe_dump(document, sort_keys=False))
    monkeypatch.setattr(ex.subprocess, "run", lambda *a, **kw: pytest.fail("must refuse before auth/Git subprocess"))
    monkeypatch.setattr(ex, "HttpsTransport", lambda *a, **kw: pytest.fail("must not select a credential origin"))
    with pytest.raises(core.CoordinationError, match="credential origin"):
        ex.makeExecutor(fx.root)


def test_revocation_stops_sends_but_not_truthful_outcome_recovery(tmp_path, monkeypatch):
    fixture = world(tmp_path, monkeypatch)
    fx, forge, _, executor, _, cold = fixture
    operation = prepare(fixture)
    forge.lost = True
    assert executor.execute(operation["operationId"])["state"] == "unknown"
    (state.storeDir(fx.root) / state.KILL_FILE).write_text("fixture local stop")
    assert cold().recover(operation["operationId"])["state"] == "already-merged"
    assert executor.execute(operation["operationId"])["state"] == "already-merged"
    assert len(forge.invocations) == len(forge.effects) == 1


def test_persisted_claim_cannot_directly_reenter_production_adapter(tmp_path, monkeypatch):
    fixture = world(tmp_path, monkeypatch, "close")
    _, forge, _, executor, _, _ = fixture
    prepared = prepare(fixture)
    forge.lost = forge.reopen = True
    assert executor.execute(prepared["operationId"])["state"] == "unknown"
    operation = executor.coordinator.inspect()["operations"][prepared["operationId"]]
    failure = None
    try:
        executor.services.invoke(operation["request"], operation["invocationId"])
    except Exception as exc:
        failure = exc
    print(f"direct-adapter-reentry invocations={len(forge.invocations)} effects={len(forge.effects)} refusal={type(failure).__name__}")
    assert isinstance(failure, core.Refused)
    assert len(forge.invocations) == len(forge.effects) == 1


def test_concrete_adapter_entry_rejects_copy_other_thread_and_reentry(tmp_path, monkeypatch):
    import threading
    fixture = world(tmp_path, monkeypatch)
    _, forge, _, executor, _, _ = fixture
    prepared = prepare(fixture)
    original = executor.coordinator._consumeAdapter
    checked = []
    def check(service, request, invocationId):
        with pytest.raises(core.Refused):
            original(copy.copy(service), request, invocationId)
        failures = []
        def attempt():
            try: original(service, request, invocationId)
            except core.Refused: failures.append(True)
        thread = threading.Thread(target=attempt, daemon=True)
        thread.start(); thread.join(5)
        assert not thread.is_alive() and failures == [True]
        entered = original(service, request, invocationId)
        with pytest.raises(core.Refused):
            original(service, request, invocationId)
        checked.append(True)
        return entered  # the committed claim, which the production adapter uses instead of re-reading the ledger
    monkeypatch.setattr(executor.coordinator, "_consumeAdapter", check)
    assert executor.execute(prepared["operationId"])["state"] == "merged"
    assert checked == [True]
    assert executor.coordinator.adapterEntries == {}
    assert len(forge.invocations) == len(forge.effects) == 1


@pytest.mark.parametrize("mismatch", ["head", "base", "parents"])
def test_post_effect_mismatch_cannot_invent_matching_merge_settlement(tmp_path, monkeypatch, mismatch):
    fixture = world(tmp_path, monkeypatch)
    _, forge, clock, executor, _, _ = fixture
    operation = prepare(fixture)
    def race():
        if mismatch == "head": forge.fact["head"]["sha"] = "e" * 40
        elif mismatch == "base": forge.fact["base"]["ref"] = "other"
        else: forge.parentShas = [forge.fx.base, "e" * 40]
    forge.before = race
    # Deliberate contract change: a post-entry settlement failure is reported as
    # operation-correlated uncertainty. It is never a pre-send refusal and never
    # a synthesized matching merge settlement.
    result = executor.execute(operation["operationId"])
    shared = executor.coordinator.inspect()
    stored = shared["operations"][operation["operationId"]]
    assert result["operationId"] == operation["operationId"]
    assert result["state"] == "possibly-sent" and result["coordinationState"] == "unavailable"
    assert result["uncertaintyCause"] == "completion-failed"  # completion could not authenticate the merge fact
    assert stored["state"] == "possibly-sent" and stored["evidence"] is None
    assert result["evidenceSha256"] is None
    assert "mergeCommitSha" not in result and "observedState" not in result
    assert shared["activeOperationId"] == operation["operationId"]
    assert core.usage(shared, clock.sample(), "stable-run", "merge") == (1, 1)
    assert executor.recover(operation["operationId"])["state"] == "quarantined"
    assert executor.execute(operation["operationId"])["state"] == "quarantined"
    assert core.usage(executor.coordinator.inspect(), clock.sample(), "stable-run", "merge") == (1, 1)
    assert len(forge.invocations) == len(forge.effects) == 1


def test_close_reports_nonatomic_destination_race_without_refund_or_retry(tmp_path, monkeypatch):
    fixture = world(tmp_path, monkeypatch, "close")
    _, forge, _, executor, _, _ = fixture
    operation = prepare(fixture)
    forge.before = lambda: forge.fact["base"].update(ref="other")
    result = executor.execute(operation["operationId"])
    assert result["state"] == "closed" and result["conditionalHead"] is False
    assert result["responseBaseChanged"] is result["observedBaseChanged"] is True
    assert executor.coordinator.inspect()["activeOperationId"] is None
    assert len(forge.invocations) == len(forge.effects) == 1


def test_post_merge_diagnostic_read_failure_is_unknown_not_fake_health_or_undo(tmp_path, monkeypatch):
    from gaia_cli.steward.prmaintenance import collect
    fixture = world(tmp_path, monkeypatch)
    _, forge, _, executor, _, _ = fixture
    operation = prepare(fixture)
    request = forge.request
    def unavailable(method, path, body=None):
        if urlsplit(path).path.endswith("/check-runs"):
            raise collect.CollectError("synthetic post-merge diagnostic unavailable")
        return request(method, path, body)
    monkeypatch.setattr(forge, "request", unavailable)
    result = executor.execute(operation["operationId"])
    assert result["state"] == "merged" and result["postMergeChecks"] == {"observed": False}
    assert len(forge.invocations) == len(forge.effects) == 1


def test_git_replace_ref_cannot_turn_tampered_report_into_accepted_send(tmp_path, monkeypatch):
    fixture = world(tmp_path, monkeypatch)
    fx, forge, clock, executor, request, cold = fixture
    good = request["expectedHeadSha"]
    bad = fx.head("2026-44", tamper=True, name="adversarial-report")
    badrow = h.row(fx, bad, "2026-44", prId="2270", repositoryId="42")
    forge.snap = dataclasses.replace(forge.snap, row=badrow)
    forge.fact["head"]["sha"] = bad
    request["expectedHeadSha"] = bad

    # Before replacement: bad head fails write validation
    with pytest.raises(gate.GateRefused, match="rendered surface is not proven"):
        gate.validateWrite(fx.root, request, forge.snap, h.utc(), "merge")

    # Record fake verification for the bad head and add replacement ref bad -> good
    state.appendRecord(fx.root, "dispatches", {"kind": "dispatch", "status": "started", "role": "verifier", "runId": "stable-run",
        "dispatchId": "new-dispatch", "agentId": "verifier", "effort": "xhigh", "builders": ["builder"],
        "envelope": {"subjects": [{"repo": h.REPO, "number": 2270, "headSha": bad}]}})
    gate.recordVerification(fx.root, {"runId": "stable-run", "repo": h.REPO, "number": 2270, "action": "merge",
        "headSha": bad, "baseSha": fx.base, "verdict": "pass", "verifier": {"agentId": "verifier", "profileId": "fixture", "effort": "xhigh"},
        "builders": ["builder"], "proofs": [{"name": "actual fixture validation", "state": "pass"}]}, h.utc())
    h.run(fx.root, "replace", bad, good)

    # After replacement: bad head is STILL refused because proofs.git ignores replace refs
    with pytest.raises(gate.GateRefused, match="rendered surface is not proven"):
        gate.validateWrite(fx.root, request, forge.snap, h.utc(), "merge")
    with pytest.raises(gate.GateRefused, match="rendered surface is not proven"):
        prepare(fixture)

    assert len(forge.invocations) == len(forge.effects) == 0


def test_clean_head_succeeds_even_when_replacement_refs_exist(tmp_path, monkeypatch):
    fixture = world(tmp_path, monkeypatch)
    fx, forge, clock, executor, request, cold = fixture
    good = request["expectedHeadSha"]
    bad = fx.head("2026-44", tamper=True, name="adversarial-dummy")
    h.run(fx.root, "replace", bad, good)

    operation = prepare(fixture)
    result = executor.execute(operation["operationId"])
    assert result["state"] == "merged"
    assert len(forge.invocations) == len(forge.effects) == 1


@pytest.mark.parametrize("override_var", [
    "GIT_REPLACE_REF_BASE", "GIT_GRAFT_FILE", "GIT_COMMON_DIR",
    "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
])
def test_inherited_git_overrides_refuse_at_service_boundary(tmp_path, monkeypatch, override_var):
    fixture = world(tmp_path, monkeypatch)
    fx, forge, clock, _, request, _ = fixture
    monkeypatch.setenv(override_var, "/nonexistent/override")
    with pytest.raises(core.CoordinationError, match="inherited Git object/worktree overrides"):
        ex.ProductionServices(fx.root, request, forge, clock)


def test_env_selected_replacement_namespace_cannot_bypass_object_reads(tmp_path, monkeypatch):
    fixture = world(tmp_path, monkeypatch)
    fx, forge, clock, executor, request, cold = fixture
    good = request["expectedHeadSha"]
    bad = fx.head("2026-44", tamper=True, name="adversarial-report-custom-ns")
    badrow = h.row(fx, bad, "2026-44", prId="2270", repositoryId="42")
    forge.snap = dataclasses.replace(forge.snap, row=badrow)
    forge.fact["head"]["sha"] = bad
    request["expectedHeadSha"] = bad

    # Set up custom replacement ref under refs/custom/
    h.run(fx.root, "update-ref", f"refs/custom/{bad}", good)
    monkeypatch.setenv("GIT_REPLACE_REF_BASE", "refs/custom/")

    # Service refuses to initialize with inherited override
    with pytest.raises(core.CoordinationError, match="inherited Git object/worktree overrides"):
        ex.ProductionServices(fx.root, request, forge, clock)

    # proofs.git sanitizes GIT_REPLACE_REF_BASE and uses --no-replace-objects, refusing bad head
    with pytest.raises(gate.GateRefused, match="rendered surface is not proven"):
        gate.validateWrite(fx.root, request, forge.snap, h.utc(), "merge")
    assert len(forge.invocations) == len(forge.effects) == 0


def test_coordination_store_and_history_immune_to_replacement_refs(tmp_path, monkeypatch):
    from gaia_cli.steward.ledger import GitRefLedgerStore, empty_ledger, serialize
    root = tmp_path / "ledger_replace"
    root.mkdir()
    h.run(root, "init")
    h.run(root, "config", "user.name", "Test")
    h.run(root, "config", "user.email", "test@test.com")
    bare = tmp_path / "ledger_bare.git"
    h.run(tmp_path, "init", "--bare", str(bare))
    h.run(root, "remote", "add", "origin", str(bare))

    store = GitRefLedgerStore(root, ref=core.REF)
    doc1 = empty_ledger()
    doc1["runs"] = {"r1": {"runId": "r1", "status": "authentic"}}
    c1 = store.compare_and_swap(None, doc1, "genesis")
    assert store.load()[0]["runs"]["r1"]["status"] == "authentic"

    # Create a tampered commit replacing c1 in refs/replace
    doc_bad = empty_ledger()
    doc_bad["runs"] = {"r1": {"runId": "r1", "status": "tampered"}}
    doc_bad["generation"] = 1
    blob = store.plumb(["hash-object", "-w", "--stdin"], stdin=serialize(doc_bad))
    tree = store.plumb(["mktree"], stdin=f"100644 blob {blob}\tledger.json\n".encode())
    c_bad = store.plumb(["commit-tree", tree, "-m", "bad"], identity=True)
    h.run(root, "replace", c1, c_bad)

    # store.load() uses --no-replace-objects and safeGitEnv; loads authentic commit
    loaded, loaded_sha = store.load()
    assert loaded["runs"]["r1"]["status"] == "authentic"
    assert loaded_sha == c1


def test_canonical_source_authority_immune_to_replacement_refs(tmp_path, monkeypatch):
    import subprocess, os
    fixture = world(tmp_path, monkeypatch)
    fx, forge, clock, executor, request, cold = fixture
    service = executor.coordinator.services

    # Create a replaced commit for fx.base in refs/replace with a modified POLICY.yaml
    tampered_policy = (fx.root / "founder/steward/POLICY.yaml").read_text() + "\n# tampered\n"
    blob = subprocess.run(["git", "-C", str(fx.root), "hash-object", "-w", "--stdin"],
                          input=tampered_policy, text=True, capture_output=True, check=True).stdout.strip()
    idx = str(tmp_path / "temp_idx")
    temp_env = dict(os.environ, GIT_INDEX_FILE=idx)
    subprocess.run(["git", "-C", str(fx.root), "read-tree", fx.base], env=temp_env, check=True)
    subprocess.run(["git", "-C", str(fx.root), "update-index", "--add", "--cacheinfo", "100644", blob, "founder/steward/POLICY.yaml"], env=temp_env, check=True)
    tree = subprocess.run(["git", "-C", str(fx.root), "write-tree"], env=temp_env, capture_output=True, text=True, check=True).stdout.strip()
    c_bad = subprocess.run(["git", "-C", str(fx.root), "commit-tree", tree, "-p", fx.base, "-m", "bad base"],
                           capture_output=True, text=True, check=True,
                           env={"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@e.com", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@e.com"}).stdout.strip()
    h.run(fx.root, "replace", fx.base, c_bad)

    # sourceTexts verifies committed blobs at fx.base; because proofs.blob uses --no-replace-objects,
    # it reads the authentic blob matching the local file, not the tampered replacement
    texts, policy, commit = service.sourceTexts()
    assert core.digest(texts["policy"]) == core.digest((fx.root / "founder/steward/POLICY.yaml").read_text())
