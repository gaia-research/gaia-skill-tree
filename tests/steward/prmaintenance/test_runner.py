"""Runner integration: forge.merge_pr / forge.close_pr are emitted sequentially, only with verification, and only settle on the store."""

from __future__ import annotations

import json
import shutil

import pytest

from gaia_cli.steward.fullrun import MERGEACTION, RecordRefused
from gaia_cli.steward.models import Observation, Subject
from gaia_cli.steward.prmaintenance import coordination as core, state
from .coordination_helpers import FakeServices, seed, subject, proof
from gaia_cli.steward.prmaintenance.sensor import PrMaintenanceSensor  # noqa: F401

from tests.steward.prmaintenance import helpers as h
from tests.steward.test_fullrun import REPO_ROOT, commitAll, fileStore, git, makeFixture, makeRunner

HEAD, BASE = "a" * 40, "b" * 40


class PrStub:
    """A sensor that reports routine pull requests with the fields the runner reads from the real sensor."""

    id = "pr-maintenance"
    resolution_scope = "exhaustive"
    routine_ids = (19,)
    debt_kinds = ("routine_pr_merge_ready", "routine_pr_closure_ready")

    def __init__(self, rows):
        self.rows = rows

    def scan(self, repo_root, observed_at):
        return [Observation(kind=kind, subject=Subject("pull-request", f"{h.REPO}#{n}"), observed_at=observed_at, source=self.id,
                            status="drift", current_state={"count": 0},
                            observed_state={"repo": h.REPO, "number": n, "headSha": head, "baseSha": BASE, "baseRef": "main",
                                            "producerId": "weekly-content-engine", "label": label, "evaluationSha256": "e" * 64,
                                            **({"closureReason": "label-already-published", "replacement": 2400} if kind == "routine_pr_closure_ready" else {})})
                for kind, n, head, label in self.rows]


def fixture(tmp_path, *, authority=True):
    repo, _bare = makeFixture(tmp_path)
    for relative in ("founder/steward/pr-producers.json", "founder/steward/decisions/steward-pr-maintenance-authority.json"):
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if authority or "decisions" not in relative:
            shutil.copyfile(REPO_ROOT / relative, target)
    commitAll(repo, "steward pr route")
    git(repo, "push", "-q", "origin", "main")
    return repo


def verify(repo, number, head=HEAD):
    state.appendRecord(repo, "verifications", {"repo": h.REPO, "number": number, "action": "merge", "headSha": head, "baseSha": BASE,
                                               "verdict": "pass", "at": "2026-11-04T18:00:00Z"})


def pending(view):
    return [a for a in view.actions if a["type"] == MERGEACTION and a["status"] == "pending"]


def test_a_merge_ready_debt_without_verification_emits_nothing_and_is_listed_as_waiting(tmp_path):
    repo = fixture(tmp_path)
    view = makeRunner(repo, fileStore(tmp_path), [PrStub([("routine_pr_merge_ready", 2270, HEAD, "2026-45")])]).start("full")
    assert pending(view) == []
    run = json.loads((tmp_path / "ledger" / "ledger.json").read_text())["runs"][view.runId]
    assert run["prMaintenance"]["awaitingVerification"][0]["number"] == 2270


def test_with_verification_one_merge_is_emitted_and_integration_stays_sequential(tmp_path):
    repo = fixture(tmp_path)
    verify(repo, 2157)
    verify(repo, 2270)
    sensor = PrStub([("routine_pr_merge_ready", 2270, HEAD, "2026-45"), ("routine_pr_merge_ready", 2157, HEAD, "2026-44")])
    runner = makeRunner(repo, fileStore(tmp_path), [sensor])
    view = runner.start("full")
    action = pending(view)
    assert len(action) == 1 and action[0]["params"]["number"] == 2157  # chronological: 2026-44 before 2026-45
    assert action[0]["params"]["headSha"] == HEAD and action[0]["params"]["producerId"] == "weekly-content-engine"
    again = runner.resume(view.runId)
    assert len(pending(again)) == 1  # never a second action while the first awaits its driver


def test_a_driver_cannot_claim_a_merge_the_store_does_not_hold(tmp_path):
    repo = fixture(tmp_path)
    verify(repo, 2270)
    runner = makeRunner(repo, fileStore(tmp_path), [PrStub([("routine_pr_merge_ready", 2270, HEAD, "2026-45")])])
    view = runner.start("full")
    step = pending(view)[0]["stepId"]
    claim = {"state": "merged", "repo": h.REPO, "number": 2270, "mergeCommitSha": "9" * 40}
    with pytest.raises(RecordRefused, match="no recorded shared"):
        runner.record(view.runId, step, claim)
    state.appendRecord(repo, "outcomes", {"at": "2026-11-04T18:31:00Z", "runId": view.runId, "repo": h.REPO, "number": 2270, "action": "merge",
                                          "headSha": HEAD, "state": "merged", "mergeCommitSha": "9" * 40})
    for reportedState in ("merged", "closed", "already-merged", "already-closed"):
        with pytest.raises(RecordRefused, match="no recorded shared"):
            runner.record(view.runId, step, {**claim, "state": reportedState})
    # Local JSONL forgery cannot become shared terminal evidence, even for already-*.
    with pytest.raises(RecordRefused):
        runner.record(view.runId, step, {**claim, "mergeCommitSha": "8" * 40})


def test_a_local_terminal_claim_cannot_suppress_a_fresh_local_proposal(tmp_path):
    repo = fixture(tmp_path)
    verify(repo, 2270)
    state.appendRecord(repo, "outcomes", {"at": "2026-11-04T18:00:00Z", "runId": "r0", "repo": h.REPO, "number": 2270, "action": "merge",
                                          "headSha": HEAD, "state": "merged", "mergeCommitSha": "9" * 40})
    view = makeRunner(repo, fileStore(tmp_path), [PrStub([("routine_pr_merge_ready", 2270, HEAD, "2026-45")])]).start("full")
    assert len(pending(view)) == 1  # a proposal, not admission/send permission


def test_revoked_authority_or_kill_switch_emits_nothing(tmp_path):
    repo = fixture(tmp_path / "a", authority=False)
    verify(repo, 2270)
    view = makeRunner(repo, fileStore(tmp_path / "a"), [PrStub([("routine_pr_merge_ready", 2270, HEAD, "2026-45")])]).start("full")
    assert pending(view) == []
    repo = fixture(tmp_path / "b")
    verify(repo, 2270)
    (state.storeDir(repo) / state.KILL_FILE).write_text("x")
    view = makeRunner(repo, fileStore(tmp_path / "b"), [PrStub([("routine_pr_merge_ready", 2270, HEAD, "2026-45")])]).start("full")
    assert pending(view) == []


def test_routine_filter_accepts_nineteen_and_refuses_twenty(tmp_path):
    repo = fixture(tmp_path)
    runner = makeRunner(repo, fileStore(tmp_path), [PrStub([])])
    assert runner.start("triage", routine=19).status in {"completed", "awaiting-action", "blocked"}
    with pytest.raises(Exception, match="between 1 and 19"):
        runner.start("triage", routine=20)


def test_no_agents_means_no_pr_merge_or_closure_action_either(tmp_path):
    repo = fixture(tmp_path)
    verify(repo, 2270)
    sensor = PrStub([("routine_pr_merge_ready", 2270, HEAD, "2026-45")])
    view = makeRunner(repo, fileStore(tmp_path), [sensor], agents=False).start("full")
    assert pending(view) == []


def test_a_stuck_pr_action_cannot_starve_the_lane_the_lease_ttl_supersedes_it(tmp_path):
    from tests.steward.test_fullrun import Clock

    repo = fixture(tmp_path)
    verify(repo, 2270)
    clock = Clock()
    runner = makeRunner(repo, fileStore(tmp_path), [PrStub([("routine_pr_merge_ready", 2270, HEAD, "2026-45")])], clock=clock)
    view = runner.start("full")
    assert len(pending(view)) == 1
    assert runner.start("full").status in {"observing-existing", "awaiting-action"}  # while the lease holds, a second run waits
    clock.advance(hours=2)
    nxt = runner.start("full")
    doc = json.loads((tmp_path / "ledger" / "ledger.json").read_text())
    old = [a for a in doc["runs"][view.runId]["actions"] if a["type"] == MERGEACTION]
    assert old and old[0]["status"] == "superseded"  # the stale action is retired; it can never be recorded against newer work
    assert len(pending(nxt)) == 1 and nxt.runId != view.runId  # and the next run offers it afresh, once


def coordinated(tmp_path, monkeypatch, *, lost=False, action="merge", runId="stable-run", changes=None, repository=h.REPO,
                response=None):
    from gaia_cli.steward import ledger
    namespace = core.Namespace("forge.invalid", "42", repository, "a" * 32)
    root = tmp_path / "critical"
    root.mkdir()
    _, binding, first, _ = seed(root, monkeypatch, namespace)
    services = FakeServices()
    candidate = subject(2270, action)
    candidate.update(headSha=HEAD, baseSha=BASE, producerId="weekly-content-engine")
    if action == "close":
        candidate.update(reason="label-already-published", replacement={"repositoryId": "42", "prId": "replacement", "number": 2400, "headSha": "c" * 40})
    if changes:
        candidate.update(changes)
    expected = proof(candidate)
    def authorize(ns, sub, bindingProof):
        if ns != namespace or sub != candidate or bindingProof != expected:
            raise core.CoordinationError("exact test binding mismatch")
    services.authorize = authorize
    original = services.completion
    def completed(operation, invocationId, response):
        result = original(operation, invocationId, response)
        result["detail"] = json.dumps({"mergeCommitSha": "9" * 40, "parentsVerified": True})
        return result
    services.completion = completed
    services.response = response or ("lost" if lost else "effect")
    coord = core.PrWriteCoordinator(ledger.GitRefLedgerStore(first, ref=core.REF), binding, services)
    token = coord.reserve(candidate, expected, runId, "owner", "reserve").token
    coord.recordIntent(token, core.exactRequest(namespace, candidate), "intent")
    coord.invoke(token, "claim")
    operation = coord.inspect()["operations"][token.operationId]
    return coord, operation, services


@pytest.mark.parametrize("reportedState", ["merged", "already-merged", "closed", "already-closed"])
def test_all_success_shaped_reports_bind_shared_subject_and_exact_evidence(tmp_path, monkeypatch, reportedState):
    repo = fixture(tmp_path)
    verify(repo, 2270)
    runner = makeRunner(repo, fileStore(tmp_path), [PrStub([("routine_pr_merge_ready", 2270, HEAD, "2026-45")])])
    view = runner.start("full")
    step = pending(view)[0]["stepId"]
    coord, operation, services = coordinated(tmp_path, monkeypatch)
    runner.config.prCoordinatorFactory = lambda: coord
    claim = {"state": reportedState, "repo": h.REPO, "number": 2270, "operationId": operation["operationId"],
             "evidenceSha256": core.digest(operation["evidence"]), "mergeCommitSha": "9" * 40}
    with pytest.raises(RecordRefused, match="no recorded shared"):
        runner.record(view.runId, step, {**claim, "evidenceSha256": "0" * 64})
    if reportedState in ("closed", "already-closed"):
        with pytest.raises(RecordRefused, match="no recorded shared"):
            runner.record(view.runId, step, claim)
        unchanged = runner._load()["runs"][view.runId]["actions"]
        stored = next(item for item in unchanged if item["stepId"] == step)
        assert stored["status"] == "pending" and "outcome" not in stored
    else:
        recorded = runner.record(view.runId, step, claim)
        assert pending(recorded) == []
        assert runner.record(view.runId, step, claim).runId == view.runId
        with pytest.raises(RecordRefused):
            runner.record(view.runId, step, {**claim, "mergeCommitSha": "8" * 40})
    assert len(services.invocations) == len(services.effects) == 1


@pytest.mark.parametrize("reportedState", ["closed", "already-closed"])
def test_completed_closure_reports_also_require_matching_shared_proof(tmp_path, monkeypatch, reportedState):
    from gaia_cli.steward.fullrun import CLOSEPRACTION
    repo = fixture(tmp_path)
    state.appendRecord(repo, "verifications", {"repo": h.REPO, "number": 2270, "action": "close", "headSha": HEAD, "baseSha": BASE, "verdict": "pass"})
    runner = makeRunner(repo, fileStore(tmp_path), [PrStub([("routine_pr_closure_ready", 2270, HEAD, "2026-45")])])
    view = runner.start("full")
    step = next(a["stepId"] for a in view.actions if a["type"] == CLOSEPRACTION)
    coord, operation, services = coordinated(tmp_path, monkeypatch, action="close")
    runner.config.prCoordinatorFactory = lambda: coord
    outcome = {"state": reportedState, "repo": h.REPO, "number": 2270, "operationId": operation["operationId"], "evidenceSha256": core.digest(operation["evidence"])}
    with pytest.raises(RecordRefused, match="no recorded shared"):
        runner.record(view.runId, step, {**outcome, "evidenceSha256": "0" * 64})
    recorded = runner.record(view.runId, step, outcome)
    assert not [a for a in recorded.actions if a["type"] == CLOSEPRACTION and a["status"] == "pending"]
    assert len(services.invocations) == len(services.effects) == 1


def test_unknown_shared_sender_stays_pending_and_local_supersession_does_not_refund(tmp_path, monkeypatch):
    from tests.steward.test_fullrun import Clock
    repo = fixture(tmp_path)
    verify(repo, 2270)
    clock = Clock()
    runner = makeRunner(repo, fileStore(tmp_path), [PrStub([("routine_pr_merge_ready", 2270, HEAD, "2026-45")])], clock=clock)
    view = runner.start("full")
    action = pending(view)[0]
    coord, operation, services = coordinated(tmp_path, monkeypatch, lost=True)
    runner.config.prCoordinatorFactory = lambda: coord
    outcome = {"state": "unknown", "repo": h.REPO, "number": 2270, "operationId": operation["operationId"]}
    recorded = runner.record(view.runId, action["stepId"], outcome)
    assert pending(recorded)[0]["params"]["operationId"] == operation["operationId"]
    clock.advance(hours=2)
    runner.start("full")
    assert coord.inspect()["activeOperationId"] == operation["operationId"]
    assert core.usage(coord.inspect(), core.TimeBounds(999999, 999999, "authority"), "stable-run", "merge") == (1, 1)
    assert len(services.invocations) == len(services.effects) == 1


@pytest.mark.parametrize("reportedState", ["failed", "refused", "aborted"])
def test_attached_unknown_failure_reports_bind_and_preserve_shared_sender(tmp_path, monkeypatch, reportedState):
    repo = fixture(tmp_path)
    verify(repo, 2270)
    runner = makeRunner(repo, fileStore(tmp_path), [PrStub([("routine_pr_merge_ready", 2270, HEAD, "2026-45")])])
    view = runner.start("full")
    step = pending(view)[0]["stepId"]
    coord, operation, services = coordinated(tmp_path, monkeypatch, lost=True)
    runner.config.prCoordinatorFactory = lambda: coord
    opid = operation["operationId"]
    runner.record(view.runId, step, {"state": "unknown", "repo": h.REPO, "number": 2270, "operationId": opid})
    failure = {"state": reportedState, "repo": h.REPO, "number": 2270, "reason": "fixture"}
    for report in ({**failure, "operationId": opid}, failure):
        assert pending(runner.record(view.runId, step, report))[0]["params"]["operationId"] == opid
    with pytest.raises(RecordRefused, match="conflicts"):
        runner.record(view.runId, step, {**failure, "operationId": "0" * 64})
    doc = runner._load()["runs"][view.runId]
    assert next(a for a in doc["actions"] if a["stepId"] == step)["status"] == "pending"
    assert next(s for s in doc["steps"] if s["stepId"] == step)["status"] == "pending"
    shared = coord.inspect()
    assert shared["operations"][opid]["state"] == "unknown" and shared["activeOperationId"] == opid
    assert core.usage(shared, core.TimeBounds(999999, 999999, "authority"), "stable-run", "merge") == (1, 1)
    assert len(services.invocations) == len(services.effects) == 1


def test_attached_operation_reconciles_independently_observed_terminal(tmp_path, monkeypatch):
    from .coordination_helpers import evidence
    repo = fixture(tmp_path)
    verify(repo, 2270)
    runner = makeRunner(repo, fileStore(tmp_path), [PrStub([("routine_pr_merge_ready", 2270, HEAD, "2026-45")])])
    view = runner.start("full")
    step = pending(view)[0]["stepId"]
    coord, operation, services = coordinated(tmp_path, monkeypatch, lost=True)
    runner.config.prCoordinatorFactory = lambda: coord
    opid = operation["operationId"]
    runner.record(view.runId, step, {"state": "unknown", "repo": h.REPO, "number": 2270, "operationId": opid})
    def observed(item):
        result = evidence(item, "observed-terminal", "merged")
        result["detail"] = json.dumps({"mergeCommitSha": "9" * 40, "parentsVerified": True})
        return result
    services.observation = observed
    assert coord.recover(opid).state == "observed-terminal"
    shared = coord.inspect()
    claim = {"state": "already-merged", "repo": h.REPO, "number": 2270,
             "evidenceSha256": core.digest(shared["operations"][opid]["evidence"])}
    assert not pending(runner.record(view.runId, step, claim))
    assert shared["activeOperationId"] is None
    assert core.usage(shared, services.now, "stable-run", "merge") == (1, 1)
    assert len(services.invocations) == len(services.effects) == 1


def test_cas_retry_refuses_concurrent_attachment_without_replaying_shared_inspection(tmp_path, monkeypatch):
    repo = fixture(tmp_path)
    verify(repo, 2270)
    runner = makeRunner(repo, fileStore(tmp_path), [PrStub([("routine_pr_merge_ready", 2270, HEAD, "2026-45")])])
    view = runner.start("full")
    step = pending(view)[0]["stepId"]
    coord, operation, services = coordinated(tmp_path, monkeypatch, lost=True)
    runner.config.prCoordinatorFactory = lambda: coord
    opid = operation["operationId"]
    store = runner.config.store
    original = store.compare_and_swap
    calls = []
    def concurrent(version, document, message):
        if not calls:
            calls.append("raced")
            runner.record(view.runId, step, {"state": "unknown", "repo": h.REPO, "number": 2270, "operationId": opid})
        return original(version, document, message)
    monkeypatch.setattr(store, "compare_and_swap", concurrent)
    with pytest.raises(RecordRefused, match="action changed"):
        runner.record(view.runId, step, {"state": "failed", "repo": h.REPO, "number": 2270, "reason": "fixture"})
    doc = runner._load()["runs"][view.runId]
    action = next(a for a in doc["actions"] if a["stepId"] == step)
    assert action["status"] == "pending" and action["params"]["operationId"] == opid
    assert next(s for s in doc["steps"] if s["stepId"] == step)["status"] == "pending"
    shared = coord.inspect()
    assert shared["operations"][opid]["state"] == "unknown" and shared["activeOperationId"] == opid
    assert core.usage(shared, core.TimeBounds(999999, 999999, "authority"), "stable-run", "merge") == (1, 1)
    assert len(services.invocations) == len(services.effects) == 1


def test_failure_report_while_shared_sender_is_possibly_sent(tmp_path, monkeypatch):
    from gaia_cli.steward import ledger
    repo = fixture(tmp_path)
    verify(repo, 2270)
    runner = makeRunner(repo, fileStore(tmp_path), [PrStub([("routine_pr_merge_ready", 2270, HEAD, "2026-45")])])
    view = runner.start("full")
    step = pending(view)[0]["stepId"]
    namespace = core.Namespace("forge.invalid", "42", h.REPO, "a" * 32)
    root = tmp_path / "critical"
    root.mkdir()
    _, binding, first, _ = seed(root, monkeypatch, namespace)
    services = FakeServices()
    candidate = subject(2270, "merge")
    candidate.update(headSha=HEAD, baseSha=BASE, producerId="weekly-content-engine")
    expected = proof(candidate)
    def authorize(ns, sub, bindingProof):
        if (ns, sub, bindingProof) != (namespace, candidate, expected):
            raise core.CoordinationError("exact test binding mismatch")
    services.authorize = authorize
    services.response = "lost"
    coord = core.PrWriteCoordinator(ledger.GitRefLedgerStore(first, ref=core.REF), binding, services)
    runner.config.prCoordinatorFactory = lambda: coord
    token = coord.reserve(candidate, expected, "stable-run", "owner", "reserve").token
    coord.recordIntent(token, core.exactRequest(namespace, candidate), "intent")
    original = services.invoke
    def duringInvoke(request, invocationId):
        opid = token.operationId
        shared = coord.inspect()
        assert shared["operations"][opid]["state"] == "possibly-sent" and shared["activeOperationId"] == opid
        runner.record(view.runId, step, {"state": "possibly-sent", "repo": h.REPO, "number": 2270, "operationId": opid})
        result = runner.record(view.runId, step, {"state": "aborted", "repo": h.REPO, "number": 2270, "reason": "fixture"})
        assert pending(result)[0]["params"]["operationId"] == opid
        assert core.usage(shared, core.TimeBounds(999999, 999999, "authority"), "stable-run", "merge") == (1, 1)
        return original(request, invocationId)
    services.invoke = duringInvoke
    coord.invoke(token, "claim")
    shared = coord.inspect()
    assert shared["operations"][token.operationId]["state"] == "unknown" and shared["activeOperationId"] == token.operationId
    assert len(services.invocations) == len(services.effects) == 1


def test_inspected_attachment_changed_on_cas_is_refused(tmp_path, monkeypatch):
    repo = fixture(tmp_path)
    verify(repo, 2270)
    runner = makeRunner(repo, fileStore(tmp_path), [PrStub([("routine_pr_merge_ready", 2270, HEAD, "2026-45")])])
    view = runner.start("full")
    step = pending(view)[0]["stepId"]
    coord, operation, services = coordinated(tmp_path, monkeypatch, lost=True)
    runner.config.prCoordinatorFactory = lambda: coord
    opid = operation["operationId"]
    runner.record(view.runId, step, {"state": "unknown", "repo": h.REPO, "number": 2270, "operationId": opid})
    assert coord.recover(opid).state == "quarantined"
    store = runner.config.store
    original = store.compare_and_swap
    calls = []
    def concurrent(version, document, message):
        if not calls:
            calls.append(True)
            def change(doc, run):
                next(a for a in run["actions"] if a["stepId"] == step)["params"]["operationId"] = "0" * 64
            runner._mutateRun(view.runId, change, holdsLease=False)
        return original(version, document, message)
    monkeypatch.setattr(store, "compare_and_swap", concurrent)
    with pytest.raises(RecordRefused, match="action changed"):
        runner.record(view.runId, step, {"state": "refused", "repo": h.REPO, "number": 2270, "reason": "fixture"})
    action = next(a for a in runner._load()["runs"][view.runId]["actions"] if a["stepId"] == step)
    assert action["status"] == "pending" and action["params"]["operationId"] == "0" * 64
    shared = coord.inspect()
    assert shared["operations"][opid]["state"] == "quarantined" and shared["activeOperationId"] == opid
    assert core.usage(shared, core.TimeBounds(999999, 999999, "authority"), "stable-run", "merge") == (1, 1)
    assert len(services.invocations) == len(services.effects) == 1


def test_no_id_failure_does_not_finish_matching_outstanding_sender(tmp_path, monkeypatch):
    repo = fixture(tmp_path)
    verify(repo, 2270)
    runner = makeRunner(repo, fileStore(tmp_path), [PrStub([("routine_pr_merge_ready", 2270, HEAD, "2026-45")])])
    view = runner.start("full")
    step = pending(view)[0]["stepId"]
    coord, operation, services = coordinated(tmp_path, monkeypatch, lost=True, runId=view.runId)
    runner.config.prCoordinatorFactory = lambda: coord
    shared = coord.inspect()
    assert shared["operations"][operation["operationId"]]["runId"] == view.runId
    assert shared["operations"][operation["operationId"]]["state"] == "unknown"
    assert shared["activeOperationId"] == operation["operationId"]
    assert core.usage(shared, core.TimeBounds(999999, 999999, "authority"), view.runId, "merge") == (1, 1)
    assert len(services.invocations) == len(services.effects) == 1
    from scripts.steward_drive import Driver
    driverReport = Driver.handlePrWrite(None, pending(view)[0]).outcome
    reports = [{"state": stateName, "repo": h.REPO, "number": 2270, "reason": "fixture"}
               for stateName in ("failed", "refused", "aborted")] + [driverReport]
    assert driverReport["state"] == "aborted" and "operationId" not in driverReport
    for report in reports:
        with pytest.raises(RecordRefused, match="shared operation"):
            runner.record(view.runId, step, report)
    with pytest.raises(RecordRefused, match="no recorded shared"):
        runner.record(view.runId, step, {**reports[0], "operationId": ""})
    run = runner._load()["runs"][view.runId]
    assert next(a for a in run["actions"] if a["stepId"] == step)["status"] == "pending"
    assert next(s for s in run["steps"] if s["stepId"] == step)["status"] == "awaiting"
    shared = coord.inspect()
    assert shared["operations"][operation["operationId"]]["state"] == "unknown"
    assert shared["activeOperationId"] == operation["operationId"]
    assert core.usage(shared, core.TimeBounds(999999, 999999, "authority"), view.runId, "merge") == (1, 1)
    assert len(services.invocations) == len(services.effects) == 1


def test_never_attached_local_failure_remains_terminal(tmp_path, monkeypatch):
    from gaia_cli.steward import ledger
    repo = fixture(tmp_path)
    verify(repo, 2270)
    runner = makeRunner(repo, fileStore(tmp_path), [PrStub([("routine_pr_merge_ready", 2270, HEAD, "2026-45")])])
    view = runner.start("full")
    step = pending(view)[0]["stepId"]
    root = tmp_path / "critical"
    root.mkdir()
    namespace = core.Namespace("forge.invalid", "42", h.REPO, "a" * 32)
    _, binding, first, _ = seed(root, monkeypatch, namespace)
    coord = core.PrWriteCoordinator(ledger.GitRefLedgerStore(first, ref=core.REF), binding, FakeServices())
    runner.config.prCoordinatorFactory = lambda: coord
    assert coord.inspect()["operations"] == {}
    assert not pending(runner.record(view.runId, step, {"state": "failed", "repo": h.REPO, "number": 2270, "reason": "not sent"}))


@pytest.mark.parametrize("field,value", [("run", "other-run"), ("number", 2271), ("headSha", "c" * 40),
                                         ("baseRef", "other"), ("baseSha", "c" * 40),
                                         ("producerId", "other-producer"), ("action", "close")])
def test_no_id_failure_ignores_foreign_shared_subject(tmp_path, monkeypatch, field, value):
    repo = fixture(tmp_path)
    verify(repo, 2270)
    runner = makeRunner(repo, fileStore(tmp_path), [PrStub([("routine_pr_merge_ready", 2270, HEAD, "2026-45")])])
    view = runner.start("full")
    step = pending(view)[0]["stepId"]
    coord, operation, services = coordinated(tmp_path, monkeypatch, lost=True,
        action=value if field == "action" else "merge", runId=value if field == "run" else view.runId,
        changes={} if field in ("run", "action") else {field: value})
    runner.config.prCoordinatorFactory = lambda: coord
    assert not pending(runner.record(view.runId, step, {"state": "failed", "repo": h.REPO, "number": 2270, "reason": "not sent"}))
    shared = coord.inspect()
    assert shared["operations"][operation["operationId"]]["state"] == "unknown"
    assert shared["activeOperationId"] == operation["operationId"]
    assert len(services.invocations) == len(services.effects) == 1


@pytest.mark.parametrize("variant", ["matching", "reason", "replacement"])
def test_no_id_close_subject_includes_reason_and_replacement(tmp_path, monkeypatch, variant):
    from gaia_cli.steward.fullrun import CLOSEPRACTION
    repo = fixture(tmp_path)
    state.appendRecord(repo, "verifications", {"repo": h.REPO, "number": 2270, "action": "close",
        "headSha": HEAD, "baseSha": BASE, "verdict": "pass"})
    runner = makeRunner(repo, fileStore(tmp_path), [PrStub([("routine_pr_closure_ready", 2270, HEAD, "2026-45")])])
    view = runner.start("full")
    step = next(a["stepId"] for a in view.actions if a["type"] == CLOSEPRACTION)
    changes = ({"reason": "other reason"} if variant == "reason" else
               {"replacement": {"repositoryId": "42", "prId": "other", "number": 2401, "headSha": "c" * 40}}
               if variant == "replacement" else {})
    coord, operation, services = coordinated(tmp_path, monkeypatch, action="close", lost=True,
                                               runId=view.runId, changes=changes)
    runner.config.prCoordinatorFactory = lambda: coord
    report = {"state": "aborted", "repo": h.REPO, "number": 2270, "reason": "fixture"}
    if variant == "matching":
        with pytest.raises(RecordRefused, match="shared operation"):
            runner.record(view.runId, step, report)
    else:
        runner.record(view.runId, step, report)
    stored = next(a for a in runner._load()["runs"][view.runId]["actions"] if a["stepId"] == step)
    assert stored["status"] == ("pending" if variant == "matching" else "done")
    shared = coord.inspect()
    assert shared["activeOperationId"] == operation["operationId"]
    assert shared["operations"][operation["operationId"]]["state"] == "unknown"
    assert len(services.invocations) == len(services.effects) == 1


def test_foreign_repository_binding_cannot_prove_absence(tmp_path, monkeypatch):
    repo = fixture(tmp_path)
    verify(repo, 2270)
    runner = makeRunner(repo, fileStore(tmp_path), [PrStub([("routine_pr_merge_ready", 2270, HEAD, "2026-45")])])
    view = runner.start("full")
    step = pending(view)[0]["stepId"]
    coord, operation, services = coordinated(tmp_path, monkeypatch, lost=True, runId=view.runId,
                                               repository="other/project")
    runner.config.prCoordinatorFactory = lambda: coord
    with pytest.raises(RecordRefused, match="shared operation"):
        runner.record(view.runId, step, {"state": "failed", "repo": h.REPO, "number": 2270, "reason": "fixture"})
    assert coord.inspect()["activeOperationId"] == operation["operationId"]
    assert len(services.invocations) == len(services.effects) == 1


def test_unavailable_physical_pr_identity_cannot_prove_foreign_subject(tmp_path, monkeypatch):
    repo = fixture(tmp_path)
    verify(repo, 2270)
    runner = makeRunner(repo, fileStore(tmp_path), [PrStub([("routine_pr_merge_ready", 2270, HEAD, "2026-45")])])
    view = runner.start("full")
    step = pending(view)[0]["stepId"]
    coord, operation, services = coordinated(tmp_path, monkeypatch, lost=True, runId=view.runId,
                                               changes={"prId": "different-physical-id"})
    runner.config.prCoordinatorFactory = lambda: coord
    with pytest.raises(RecordRefused, match="shared operation"):
        runner.record(view.runId, step, {"state": "failed", "repo": h.REPO, "number": 2270, "reason": "fixture"})
    assert coord.inspect()["activeOperationId"] == operation["operationId"]
    assert len(services.invocations) == len(services.effects) == 1


def test_missing_binding_and_shared_read_failure_do_not_imply_absence(tmp_path, monkeypatch):
    from gaia_cli.steward import ledger
    repo = fixture(tmp_path)
    verify(repo, 2270)
    runner = makeRunner(repo, fileStore(tmp_path), [PrStub([("routine_pr_merge_ready", 2270, HEAD, "2026-45")])])
    view = runner.start("full")
    step = pending(view)[0]["stepId"]
    report = {"state": "aborted", "repo": h.REPO, "number": 2270, "reason": "fixture"}
    with pytest.raises(RecordRefused, match="shared operation"):
        runner.record(view.runId, step, report)
    coord, operation, services = coordinated(tmp_path, monkeypatch, lost=True, runId=view.runId)
    runner.config.prCoordinatorFactory = lambda: coord
    with monkeypatch.context() as patch:
        def unavailable():
            raise ledger.LedgerUnavailable("synthetic read failure")
        patch.setattr(coord, "inspect", unavailable)
        with pytest.raises(RecordRefused, match="shared operation"):
            runner.record(view.runId, step, report)
    assert next(a for a in runner._load()["runs"][view.runId]["actions"] if a["stepId"] == step)["status"] == "pending"
    assert coord.inspect()["activeOperationId"] == operation["operationId"]
    assert len(services.invocations) == len(services.effects) == 1


def attach(tmp_path, monkeypatch, terminal, **kw):
    """A runner holding one pending merge action plus a shared operation in the requested terminal state."""
    from .coordination_helpers import evidence
    repo = fixture(tmp_path)
    verify(repo, 2270)
    runner = makeRunner(repo, fileStore(tmp_path), [PrStub([("routine_pr_merge_ready", 2270, HEAD, "2026-45")])])
    view = runner.start("full")
    step = pending(view)[0]["stepId"]
    coord, operation, services = coordinated(tmp_path, monkeypatch, runId=view.runId, lost=terminal == "observed-terminal", **kw)
    if terminal == "observed-terminal":
        def observed(item):
            result = evidence(item, "observed-terminal", "merged")
            result["detail"] = json.dumps({"mergeCommitSha": "9" * 40, "parentsVerified": True})
            return result
        services.observation = observed
        assert coord.recover(operation["operationId"]).state == "observed-terminal"
    runner.config.prCoordinatorFactory = lambda: coord
    return runner, view, step, coord, operation["operationId"], services


@pytest.mark.parametrize("terminal", ["completed-effect", "observed-terminal"])
@pytest.mark.parametrize("reportedState", ["failed", "refused", "aborted"])
def test_no_id_failure_report_cannot_contradict_a_matching_committed_effect(tmp_path, monkeypatch, terminal, reportedState):
    """The effect completed before this action was ever attached to an operation id (completion before attachment)."""
    runner, view, step, coord, opid, services = attach(tmp_path, monkeypatch, terminal)
    assert coord.inspect()["operations"][opid]["state"] == terminal
    assert "operationId" not in next(a for a in runner._load()["runs"][view.runId]["actions"] if a["stepId"] == step)["params"]
    with pytest.raises(RecordRefused, match="already effective"):
        runner.record(view.runId, step, {"state": reportedState, "repo": h.REPO, "number": 2270, "reason": "fixture"})
    stored = next(a for a in runner._load()["runs"][view.runId]["actions"] if a["stepId"] == step)
    assert stored["status"] == "pending" and "outcome" not in stored
    assert coord.inspect()["operations"][opid]["state"] == terminal  # shared truth unchanged
    assert len(services.invocations) == len(services.effects) == 1


@pytest.mark.parametrize("terminal", ["completed-effect", "observed-terminal"])
def test_the_matching_effect_is_still_recordable_with_its_operation_and_evidence(tmp_path, monkeypatch, terminal):
    runner, view, step, coord, opid, _ = attach(tmp_path, monkeypatch, terminal)
    shared = coord.inspect()["operations"][opid]
    reported = {"state": "merged" if terminal == "completed-effect" else "already-merged", "repo": h.REPO, "number": 2270,
                "operationId": opid, "evidenceSha256": core.digest(shared["evidence"]), "mergeCommitSha": "9" * 40}
    assert not pending(runner.record(view.runId, step, reported))


def test_a_matching_effect_from_another_run_also_blocks_an_uncorrelated_failure(tmp_path, monkeypatch):
    repo = fixture(tmp_path)
    verify(repo, 2270)
    runner = makeRunner(repo, fileStore(tmp_path), [PrStub([("routine_pr_merge_ready", 2270, HEAD, "2026-45")])])
    view = runner.start("full")
    step = pending(view)[0]["stepId"]
    # The same immutable subject effected under a different run id still contradicts a failure report for it.
    coord, operation, services = coordinated(tmp_path, monkeypatch, runId="another-run")
    assert operation["state"] == "completed-effect" and operation["runId"] != view.runId
    runner.config.prCoordinatorFactory = lambda: coord
    with pytest.raises(RecordRefused, match="already effective"):
        runner.record(view.runId, step, {"state": "failed", "repo": h.REPO, "number": 2270, "reason": "fixture"})
    assert next(a for a in runner._load()["runs"][view.runId]["actions"] if a["stepId"] == step)["status"] == "pending"


@pytest.mark.parametrize("scenario", ["unrelated-subject", "definite-no-effect"])
def test_genuine_no_operation_failures_are_still_accepted(tmp_path, monkeypatch, scenario):
    repo = fixture(tmp_path)
    verify(repo, 2270)
    runner = makeRunner(repo, fileStore(tmp_path), [PrStub([("routine_pr_merge_ready", 2270, HEAD, "2026-45")])])
    view = runner.start("full")
    step = pending(view)[0]["stepId"]
    if scenario == "unrelated-subject":
        coord, operation, services = coordinated(tmp_path, monkeypatch, runId=view.runId, changes={"number": 2271})
    else:
        coord, operation, services = coordinated(tmp_path, monkeypatch, runId=view.runId, response="reject")
        assert operation["state"] == "completed-no-effect"
    runner.config.prCoordinatorFactory = lambda: coord
    assert not pending(runner.record(view.runId, step, {"state": "failed", "repo": h.REPO, "number": 2270, "reason": "fixture"}))
    assert bool(services.effects) == (scenario == "unrelated-subject")  # only the unrelated PR was ever effected
