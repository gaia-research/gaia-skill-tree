"""The merge/closure gate: every refusal is proven, and the absence of an unauthorized write is the point of the suite."""

from __future__ import annotations

import dataclasses
import json
from datetime import timedelta

import pytest

from gaia_cli.steward.policy import StewardPolicy
from gaia_cli.steward.prmaintenance import coordination as core, gate, receipts, state
from .test_executor import world as sharedWorld, prepare as sharedPrepare
from gaia_cli.steward.prmaintenance.evaluate import KIND_MERGE
from gaia_cli.steward.prmaintenance.sensor import PrMaintenanceSensor  # noqa: F401  (the sensor this gate is the executor of)

from tests.steward.prmaintenance import helpers as h

RUN = "run-1"


@pytest.fixture(autouse=True)
def knowingLocalAuthority(monkeypatch):
    """These tests run under a committed local head, which the operator must say out loud (the default is fail closed)."""

    monkeypatch.delenv(gate.AUTHORITY_REF, raising=False)
    monkeypatch.setenv(gate.AUTHORITY_LOCAL, "1")


def comment(body, assoc="MEMBER", cid=1):
    return {"id": cid, "user": "mbtiongson1", "body": body, "authorAssociation": assoc}


def trail(number, head, run=RUN):
    pick = receipts.pickup(number=number, head=head, runId=run, producer="weekly-content-engine", authority="B", baseRef="main",
                           baseSha="a" * 40, action="merge")
    ver = receipts.verification(number=number, head=head, runId=run, verifier="verifier-a", evidence=["proof"],
                                gates={"provenance": "PASS", "scope": "PASS", "ci": "PASS", "policy": "PASS", "reviews": "PASS"},
                                reconciliation="NOT REQUIRED")
    return [comment(pick, cid=1), comment(ver, cid=2)]


def dispatched(fx, verifier, builders, run=RUN, subject=None):
    """The recorded verifier dispatch a verification must stand on (independence is derived from it, never self-declared)."""

    state.appendRecord(fx.root, "dispatches", {"kind": "dispatch", "status": "started", "at": "2026-11-04T18:00:00Z", "runId": run,
                                               "dispatchId": f"d-{verifier['agentId']}-{len(state.readRecords(fx.root, 'dispatches'))}",
                                               "role": "verifier", "agentId": verifier["agentId"], "effort": verifier["effort"],
                                               "builders": list(builders), "envelope": {"subjects": [subject] if subject else []}})


def verification(fx, head, number=2270, action="merge", dispatch=True, **over):
    record = {"repo": h.REPO, "number": number, "action": action, "headSha": head, "baseSha": fx.base, "verdict": "pass",
              "verifier": {"agentId": "verifier-a", "effort": "high", "profileId": "p"}, "builders": ["builder-x"],
              "proofs": [{"name": "provenance", "state": "pass", "detail": "ok"}], "runId": RUN}
    record.update(over)
    if dispatch:
        dispatched(fx, record["verifier"], record["builders"], record["runId"],
                   {"repo": record["repo"], "number": record["number"], "headSha": record["headSha"]})
    return gate.recordVerification(fx.root, record, h.utc())


def snapshot(fx, head, label="2026-44", *, comments=None, number=2270, **over):
    row = h.row(fx, head, label, number=number, comments=trail(number, head) if comments is None else comments)
    row.update(over)
    return gate.Snapshot(row=row, tips={"main": fx.base}, protection={"complete": True, "requiredChecks": h.REQUIRED}, siblings=[], closed=[])


def request(head, number=2270, **over):
    value = {"action": "merge", "repo": h.REPO, "number": number, "expectedHeadSha": head, "baseRef": "main", "producerId": "weekly-content-engine"}
    value.update(over)
    return value


@pytest.fixture()
def fx(tmp_path):
    return h.makeRepo(tmp_path)


def ready(fx, label="2026-44"):
    head = fx.head(label)
    verification(fx, head)
    return head


def refused(fx, snap, req, code, now=None, run=RUN, **kw):
    with pytest.raises(gate.GateRefused) as caught:
        gate.gateMerge(fx.root, req, snap, now or h.utc(), run, **kw)
    assert caught.value.code == code, caught.value
    assert not isinstance(caught.value, gate.AlreadyDone) or code.startswith("already")


def outcomes(fx):
    return state.readRecords(fx.root, "outcomes")


def test_happy_path_authorizes_exactly_one_call_and_settles_from_observed_state(tmp_path, monkeypatch):
    fixture = sharedWorld(tmp_path, monkeypatch)
    fx, forge, _, executor, req, _ = fixture
    auth = sharedPrepare(fixture)
    assert auth["headSha"] == req["expectedHeadSha"] and auth["method"] == "merge" and auth["state"] == "intent"
    assert outcomes(fx) == [] and forge.invocations == []
    done = executor.execute(auth["operationId"])
    assert done["state"] == "merged" and done["evidenceSha256"]
    assert gate.finalize(fx.root, auth, forge.snap, h.utc())["state"] == "merged"
    assert executor.execute(auth["operationId"])["state"] == "merged"
    assert len(forge.invocations) == len(forge.effects) == 1


def test_no_independent_verification_means_no_merge(fx):
    head = fx.head("2026-44")
    refused(fx, snapshot(fx, head), request(head), "no-verification")
    assert outcomes(fx) == []


def test_interrupted_verification_a_failed_or_missing_verdict_never_authorizes(fx):
    head = fx.head("2026-44")
    verification(fx, head, verdict="fail", proofs=[{"name": "x", "state": "fail", "detail": "no"}])
    refused(fx, snapshot(fx, head), request(head), "verification-failed")


def test_verifier_must_not_be_a_builder_and_effort_must_be_explicit(fx):
    head = fx.head("2026-44")
    with pytest.raises(gate.GateRefused) as caught:
        verification(fx, head, builders=["verifier-a"])
    assert caught.value.code == "verification-not-independent"
    for bad in ("default", "inherit", ""):
        with pytest.raises(gate.GateRefused):
            verification(fx, head, verifier={"agentId": "v", "effort": bad, "profileId": "p"})
    with pytest.raises(gate.GateRefused):
        verification(fx, head, proofs=[{"name": "a", "state": "unknown", "detail": ""}])


def test_changed_head_after_verification_invalidates_it_and_the_action(fx):
    head = ready(fx)
    h.run(fx.root, "commit", "-q", "--allow-empty", "-m", "the bot pushed again")
    newHead = h.run(fx.root, "rev-parse", "HEAD")
    assert newHead != head
    refused(fx, snapshot(fx, newHead), request(head), "head-moved")  # the action names the old head
    refused(fx, snapshot(fx, newHead), request(newHead), "no-verification")  # the new head was never verified
    assert outcomes(fx) == []


def test_verification_expires_and_a_moved_destination_requires_reverification(fx):
    head = ready(fx)
    refused(fx, snapshot(fx, head), request(head), "verification-stale", now=h.utc() + timedelta(hours=7))
    moved = snapshot(fx, head)
    moved = dataclasses.replace(moved, tips={"main": "f" * 40})
    refused(fx, moved, request(head), "not-eligible")


def test_policy_or_registry_revision_change_invalidates_verification(fx):
    head = ready(fx)
    (fx.root / "founder/steward/pr-producers.json").write_text((fx.root / "founder/steward/pr-producers.json").read_text() + "\n")
    refused(fx, snapshot(fx, head), request(head), "authority-drift")  # uncommitted authority is never trusted
    h.run(fx.root, "add", "-A")
    h.run(fx.root, "commit", "-q", "-m", "registry reformatted")
    refused(fx, snapshot(fx, head), request(head), "policy-revision-moved")  # committed, but the verification vouched for other bytes


def test_concurrent_merge_attempt_is_refused_while_a_live_reservation_exists(tmp_path, monkeypatch):
    fixture = sharedWorld(tmp_path, monkeypatch)
    fx, forge, _, executor, req, _ = fixture
    sharedPrepare(fixture)
    with pytest.raises(core.Refused):
        gate.gateMerge(fx.root, req, forge.snap, h.utc(), "run-2")
    assert forge.invocations == [] and len(executor.coordinator.inspect()["operations"]) == 1


def test_crash_before_the_merge_is_recovered_from_github_state_not_repeated_blindly(tmp_path, monkeypatch):
    fixture = sharedWorld(tmp_path, monkeypatch)
    fx, forge, clock, executor, req, _ = fixture
    auth = sharedPrepare(fixture)
    clock.instant += 1800
    with pytest.raises(core.Refused):
        executor.execute(auth["operationId"])
    with pytest.raises(core.Refused):
        gate.gateMerge(fx.root, req, forge.snap, h.utc() + timedelta(minutes=30), "run-2")
    assert gate.finalize(fx.root, auth, forge.snap, h.utc())["state"] == "intent"
    assert forge.invocations == forge.effects == []


def test_crash_after_merge_before_receipt_resumes_by_posting_the_receipt_once(tmp_path, monkeypatch):
    fixture = sharedWorld(tmp_path, monkeypatch)
    fx, forge, _, executor, req, cold = fixture
    auth = sharedPrepare(fixture)
    forge.lost = True
    assert executor.execute(auth["operationId"])["state"] == "unknown"
    assert cold().recover(auth["operationId"])["state"] == "already-merged"
    head = req["expectedHeadSha"]
    assert state.receiptPosted(fx.root, h.REPO, 2270, "merged", head[:12]) is None
    body = receipts.merged(number=2270, head=head, runId=RUN, url="u", destination="main", mergeCommit="d" * 40, method="merge", postMerge="pending")
    assert receipts.findReceipt([comment(body)], "merged", 2270, head[:12]) is not None
    assert executor.execute(auth["operationId"])["state"] == "already-merged"
    assert len(forge.invocations) == len(forge.effects) == 1


def test_comment_write_failure_leaves_no_false_record_and_the_marker_is_the_idempotency_key(fx):
    head = ready(fx)
    assert state.receiptPosted(fx.root, h.REPO, 2270, "pickup", head[:12]) is None
    state.recordReceipt(fx.root, {"at": state.stamp(), "repo": h.REPO, "number": 2270, "kind": "pickup", "head12": head[:12], "runId": RUN, "commentId": 1})
    assert state.receiptPosted(fx.root, h.REPO, 2270, "pickup", head[:12])["commentId"] == 1
    forged = [comment(receipts.pickup(number=2270, head=head, runId=RUN, producer="p", authority="B", baseRef="main", baseSha="a" * 40, action="merge"), assoc="NONE")]
    assert receipts.findReceipt(forged, "pickup", 2270, head[:12]) is None  # a stranger cannot suppress a receipt


def test_existing_merged_or_closed_state_is_reported_never_acted_on(fx):
    head = ready(fx)
    merged = snapshot(fx, head, merged=True, state="closed")
    merged = dataclasses.replace(merged, merged=True, mergeCommitSha="9" * 40)
    with pytest.raises(gate.AlreadyDone) as caught:
        gate.gateMerge(fx.root, request(head), merged, h.utc(), RUN)
    assert caught.value.code == "already-merged" and caught.value.detail["mergeCommitSha"] == "9" * 40
    refused(fx, snapshot(fx, head, state="closed"), request(head), "closed-unmerged")
    assert outcomes(fx) == []


def test_kill_switch_revokes_every_route(fx, monkeypatch):
    head = ready(fx)
    assert state.killSwitchActive(fx.root) is None
    (state.storeDir(fx.root) / state.KILL_FILE).write_text("x")
    refused(fx, snapshot(fx, head), request(head), "kill-switch")
    (state.storeDir(fx.root) / state.KILL_FILE).unlink()
    monkeypatch.setenv("GAIA_STEWARD_PR_KILL", "1")
    refused(fx, snapshot(fx, head), request(head), "kill-switch")
    monkeypatch.delenv("GAIA_STEWARD_PR_KILL")
    policy = StewardPolicy.load(fx.root)
    killed = dataclasses.replace(policy, pr_maintenance=dataclasses.replace(policy.pr_maintenance, killSwitch=True))
    refused(fx, snapshot(fx, head), request(head), "kill-switch", policy=killed)
    assert outcomes(fx) == []


def test_revoked_or_unratified_authority_blocks_even_with_writes_enabled_in_policy(fx):
    head = ready(fx)
    record = fx.root / "founder/steward/decisions/steward-pr-maintenance-authority.json"
    data = json.loads(record.read_text())
    data["resolution"] = "rejected"
    record.write_text(json.dumps(data))
    refused(fx, snapshot(fx, head), request(head), "authority-drift")
    h.run(fx.root, "add", "-A")
    h.run(fx.root, "commit", "-q", "-m", "authority rejected")
    refused(fx, snapshot(fx, head), request(head), "authority-unratified")
    assert StewardPolicy.load(fx.root).pr_maintenance.writesEnabled is False  # a switch edit alone grants nothing
    record.unlink()
    h.run(fx.root, "add", "-A")
    h.run(fx.root, "commit", "-q", "-m", "authority removed")
    refused(fx, snapshot(fx, head), request(head), "authority-unratified")


def test_disabled_action_malformed_policy_and_unknown_repositories_are_refused(fx):
    head = ready(fx)
    policy = StewardPolicy.load(fx.root)
    noMerge = dataclasses.replace(policy, pr_maintenance=dataclasses.replace(policy.pr_maintenance, enabledActions=("comment",)))
    refused(fx, snapshot(fx, head), request(head), "action-disabled", policy=noMerge)
    bad = dataclasses.replace(policy, pr_maintenance_error="prMaintenance is malformed: x")
    refused(fx, snapshot(fx, head), request(head), "policy-malformed", policy=bad)
    refused(fx, snapshot(fx, head), request(head, repo="gaia-research/gaia-skill-heaven"), "repo-deferred")
    refused(fx, snapshot(fx, head), request(head, repo="gaia-research/elsewhere"), "repo-not-enabled")


def test_destination_and_method_outside_policy_are_refused(fx):
    head = ready(fx)
    refused(fx, snapshot(fx, head), request(head, method="squash"), "merge-method-not-allowed")
    refused(fx, snapshot(fx, head), request(head, baseRef="release"), "destination-not-allowed")
    other = snapshot(fx, head, baseRef="release")
    refused(fx, other, request(head, baseRef="release"), "destination-not-allowed")


def test_branch_protection_is_never_bypassed(fx):
    head = ready(fx)
    refused(fx, snapshot(fx, head, mergeableState="blocked"), request(head), "branch-protection")
    unreadable = dataclasses.replace(snapshot(fx, head), protection={"complete": False, "requiredChecks": []})
    refused(fx, unreadable, request(head), "branch-protection")
    failing = h.passing()
    failing[0] = {**failing[0], "conclusion": "failure"}
    refused(fx, snapshot(fx, head, checkRuns=failing), request(head), "not-eligible")


def test_ineligible_pull_requests_are_refused_with_their_disposition(fx):
    head = ready(fx)
    refused(fx, snapshot(fx, head, draft=True), request(head), "not-eligible")
    refused(fx, snapshot(fx, head, labels=["content-engine", "needs-review"]), request(head), "not-eligible")
    refused(fx, snapshot(fx, head, author={"login": "github-actions", "id": 1, "type": "User"}), request(head), "not-eligible")
    refused(fx, snapshot(fx, head), request(head, producerId="scheduled-docs-routine"), "producer-mismatch")


def test_github_trail_is_best_effort_not_independent_verification(tmp_path, monkeypatch):
    fixture = sharedWorld(tmp_path, monkeypatch)
    fx, forge, _, executor, req, _ = fixture
    for comments in ([], [comment(c["body"], assoc="NONE") for c in trail(2270, req["expectedHeadSha"])], trail(2270, "b" * 40)):
        forge.snap = dataclasses.replace(forge.snap, row={**forge.snap.row, "comments": comments})
        assert sharedPrepare(fixture)["state"] == "intent"
    assert len(executor.coordinator.inspect()["operations"]) == 1 and forge.invocations == []
    (state.storeDir(fx.root) / "verifications.jsonl").unlink()
    with pytest.raises(gate.GateRefused, match="no-verification"):
        sharedPrepare(fixture)


def test_exhausted_per_run_and_hourly_budgets_defer_rather_than_loop(tmp_path, monkeypatch):
    fixture = sharedWorld(tmp_path, monkeypatch)
    fx, forge, _, executor, req, _ = fixture
    executor.services.limits = lambda: core.Limits(mergesPerRun=1, writesPerHour=1)
    auth = sharedPrepare(fixture)
    executor.execute(auth["operationId"])
    second = fx.head("2026-45")
    verification(fx, second, number=2271, runId="stable-run")
    nextSnap = snapshot(fx, second, "2026-45", number=2271, prId="2271", repositoryId="42")
    forge.snap = nextSnap
    for run in ("stable-run", "different-run"):
        with pytest.raises(core.Refused, match="ceiling"):
            gate.gateMerge(fx.root, request(second, number=2271), nextSnap, h.utc(), run)
    assert len(forge.invocations) == 1 and len(executor.coordinator.inspect()["operations"]) == 1


def test_abort_releases_only_unsent_capacity_and_retains_replay_tombstone(tmp_path, monkeypatch):
    fixture = sharedWorld(tmp_path, monkeypatch)
    fx, forge, _, executor, req, _ = fixture
    auth = sharedPrepare(fixture)
    assert gate.abort(fx.root, auth, "forge call not made", h.utc())["state"] == "aborted"
    durable = executor.coordinator.inspect()
    assert durable["activeOperationId"] is None
    assert durable["operations"][auth["operationId"]]["state"] == "canceled-unsent"
    with pytest.raises(core.Refused):
        gate.gateMerge(fx.root, req, forge.snap, h.utc(), "run-2")
    assert forge.invocations == [] and state.terminalFor(fx.root, h.REPO, 2270, "merge") is None


def test_finalize_trusts_independent_observation_not_supplied_snapshot(tmp_path, monkeypatch):
    fixture = sharedWorld(tmp_path, monkeypatch)
    fx, forge, _, executor, _, _ = fixture
    auth = sharedPrepare(fixture)
    forge.lost = True
    executor.execute(auth["operationId"])
    forge.fact["head"] = {"sha": "c" * 40}
    fabricated = dataclasses.replace(forge.snap, merged=True, mergeCommitSha="9" * 40)
    assert gate.finalize(fx.root, auth, fabricated, h.utc(), parents=[forge.snap.row["headSha"]])["state"] == "quarantined"
    assert executor.coordinator.inspect()["activeOperationId"] == auth["operationId"]
    assert len(forge.invocations) == 1


# --- closure ------------------------------------------------------------------------------------------------------

def closureWorld(tmp_path, *, replacement=True, justification=True, number=2270):
    fx = h.makeRepo(tmp_path, labels=("2026-42", "2026-43", "2026-44"))
    head = fx.head("2026-44")
    closedRows = [{"number": 2400, "state": "closed", "mergedAt": "2026-11-04T17:59:00Z", "mergeCommitSha": "d" * 40, "headRef": "steward/b/x",
                   "title": "replacement", "closedAt": "2026-11-04T18:00:00Z",
                   "body": f"<!-- gaia-steward:replaces repo={h.REPO} pr={number} -->"}] if replacement else []
    verification(fx, head, action="close", number=number)
    note = receipts.closed(number=number, head=head, runId=RUN, url="u", reason="label-already-published", replacement="#2400", verifier="verifier-a")
    snap = snapshot(fx, head, "2026-44", number=number, comments=[comment(note)] if justification else [])
    snap = dataclasses.replace(snap, closed=closedRows)
    req = {"action": "close", "repo": h.REPO, "number": number, "expectedHeadSha": head, "baseRef": "main", "producerId": "weekly-content-engine",
           "reason": "label-already-published", "replacement": 2400}
    return fx, head, snap, req


def refusedClose(fx, snap, req, code):
    with pytest.raises(gate.GateRefused) as caught:
        gate.gateClose(fx.root, req, snap, h.utc(), RUN)
    assert caught.value.code == code, caught.value


def test_closure_happy_path_stores_justification_before_sole_coordinated_close(tmp_path, monkeypatch):
    fixture = sharedWorld(tmp_path, monkeypatch, "close")
    fx, forge, _, executor, _, _ = fixture
    auth = sharedPrepare(fixture)
    stored = executor.coordinator.inspect()["operations"][auth["operationId"]]
    assert stored["proof"]["justification"] and stored["state"] == "intent" and forge.invocations == []
    assert executor.execute(auth["operationId"])["state"] == "closed"
    assert gate.finalize(fx.root, auth, forge.snap, h.utc())["state"] == "closed"
    assert executor.execute(auth["operationId"])["state"] == "closed"
    assert len(forge.invocations) == len(forge.effects) == 1


def test_closure_without_adequate_evidence_is_refused(tmp_path):
    fx, head, snap, req = closureWorld(tmp_path, replacement=False)
    refusedClose(fx, snap, req, "closure-not-proven")  # label published but no merged, marker-linked replacement
    fx, head, snap, req = closureWorld(tmp_path / "b", justification=False)
    assert gate.validateClose(fx.root, req, snap, h.utc())["verdict"] == "pass"  # publication is best effort; proof is still mandatory
    fx, head, snap, req = closureWorld(tmp_path / "c")
    refusedClose(fx, snap, {**req, "reason": "duplicate-of-open-sibling"}, "closure-reason-not-eligible")
    refusedClose(fx, snap, {**req, "replacement": 9999}, "replacement-missing")


def test_a_pull_request_that_is_merely_old_or_conflicted_is_never_closable(fx):
    head = fx.head("2026-44")
    snap = snapshot(fx, head, mergeable=False, mergeableState="dirty")
    verification(fx, head, action="close")
    req = {"action": "close", "repo": h.REPO, "number": 2270, "expectedHeadSha": head, "baseRef": "main", "producerId": "weekly-content-engine",
           "reason": "label-already-published", "replacement": 1}
    refusedClose(fx, snap, req, "closure-not-proven")
    assert KIND_MERGE and outcomes(fx) == []


# --- verifier findings: independence is derived, authority is committed, settlement needs a live reservation -------------

def test_a_verification_without_a_recorded_verifier_dispatch_or_with_empty_builders_is_refused(fx):
    head = fx.head("2026-44")
    with pytest.raises(gate.GateRefused) as caught:
        verification(fx, head, dispatch=False)
    assert caught.value.code == "verification-not-dispatched"
    with pytest.raises(gate.GateRefused) as empty:
        verification(fx, head, builders=[])
    assert empty.value.code == "verification-malformed" and "builders" in empty.value.message
    dispatched(fx, {"agentId": "verifier-a", "effort": "low"}, ["builder-x"], subject={"repo": h.REPO, "number": 2270, "headSha": head})
    with pytest.raises(gate.GateRefused) as mismatch:
        gate.recordVerification(fx.root, {"repo": h.REPO, "number": 2270, "action": "merge", "headSha": head, "baseSha": fx.base, "verdict": "pass",
                                          "verifier": {"agentId": "verifier-a", "effort": "xhigh", "profileId": "p"}, "builders": ["builder-x"],
                                          "proofs": [{"name": "a", "state": "pass", "detail": ""}], "runId": RUN}, h.utc())
    assert mismatch.value.code == "verification-malformed" and "effort" in mismatch.value.message


def test_the_builders_recorded_on_the_dispatch_count_even_if_the_caller_omits_them(fx):
    head = fx.head("2026-44")
    dispatched(fx, {"agentId": "verifier-a", "effort": "high"}, ["verifier-a"],
               subject={"repo": h.REPO, "number": 2270, "headSha": head})  # the dispatch itself says this agent built it
    with pytest.raises(gate.GateRefused) as caught:
        gate.recordVerification(fx.root, {"repo": h.REPO, "number": 2270, "action": "merge", "headSha": head, "baseSha": fx.base, "verdict": "pass",
                                          "verifier": {"agentId": "verifier-a", "effort": "high", "profileId": "p"}, "builders": ["builder-x"],
                                          "proofs": [{"name": "a", "state": "pass", "detail": ""}], "runId": RUN}, h.utc())
    assert caught.value.code == "verification-not-independent"


def test_the_policy_digest_is_computed_by_the_gate_never_taken_from_the_caller(fx):
    head = fx.head("2026-44")
    stored = verification(fx, head, policySha256="0" * 64)
    assert stored["policySha256"] == gate.policyDigest(fx.root) != "0" * 64
    assert gate.validateWrite(fx.root, request(head), snapshot(fx, head), h.utc(), "merge")["policySha256"] == stored["policySha256"]


def test_a_verification_written_around_the_recorder_is_still_refused_at_the_gate(fx):
    head = fx.head("2026-44")
    state.appendRecord(fx.root, "verifications", {"repo": h.REPO, "number": 2270, "action": "merge", "headSha": head, "baseSha": fx.base,
                                                  "verdict": "pass", "at": "2026-11-04T18:20:00Z", "policySha256": gate.policyDigest(fx.root),
                                                  "verifier": {"agentId": "same", "effort": "high", "profileId": "p"}, "builders": ["same"]})
    refused(fx, snapshot(fx, head), request(head), "verification-not-independent")


def test_a_verification_for_a_different_destination_tip_is_stale(fx):
    head = fx.head("2026-44")
    verification(fx, head, baseSha="f" * 40)
    refused(fx, snapshot(fx, head), request(head), "verification-stale")


def test_authority_source_must_be_named_and_the_default_fails_closed(fx, monkeypatch):
    head = ready(fx)
    monkeypatch.delenv(gate.AUTHORITY_LOCAL)
    refused(fx, snapshot(fx, head), request(head), "authority-source-unset")
    monkeypatch.setenv(gate.AUTHORITY_LOCAL, "yes")  # only the explicit value 1 counts
    refused(fx, snapshot(fx, head), request(head), "authority-source-unset")
    monkeypatch.setenv(gate.AUTHORITY_LOCAL, "1")
    assert gate.validateWrite(fx.root, request(head), snapshot(fx, head), h.utc(), "merge")["verdict"] == "pass"
    with pytest.raises(core.CoordinationError, match="unconfigured"):
        gate.gateMerge(fx.root, request(head), snapshot(fx, head), h.utc(), RUN)  # local authority is not a shared send route


def test_local_authority_or_receipt_json_cannot_replace_configured_shared_coordination(fx, monkeypatch):
    head = ready(fx)
    for ref in (None, "origin/dest"):
        if ref:
            h.run(fx.root, "update-ref", "refs/remotes/origin/dest", fx.base)
            monkeypatch.setenv(gate.AUTHORITY_REF, ref)
        with pytest.raises(core.CoordinationError, match="unconfigured"):
            gate.gateMerge(fx.root, request(head), snapshot(fx, head), h.utc(), RUN)
    with pytest.raises(gate.GateRefused, match="legacy-route-disabled"):
        gate.checkAuthorization(fx.root, {"digest": "forged-local-json"})
    assert outcomes(fx) == []


def test_authority_must_equal_the_destination_tip_when_one_is_named(fx, monkeypatch):
    head = ready(fx)
    h.run(fx.root, "update-ref", "refs/remotes/origin/dest", fx.base)
    monkeypatch.setenv(gate.AUTHORITY_REF, "origin/dest")
    assert gate.validateWrite(fx.root, request(head), snapshot(fx, head), h.utc(), "merge")["verdict"] == "pass"
    (fx.root / "founder/steward/pr-producers.json").write_text((fx.root / "founder/steward/pr-producers.json").read_text() + " ")
    h.run(fx.root, "add", "-A")
    h.run(fx.root, "commit", "-q", "-m", "widened registry on a branch")
    refused(fx, snapshot(fx, head), request(head), "authority-drift", run="run-2")  # committed here, but not what the destination holds


def test_finalize_and_abort_refuse_legacy_forgery_and_cannot_resurrect_canceled_operation(tmp_path, monkeypatch):
    fixture = sharedWorld(tmp_path, monkeypatch)
    fx, forge, _, executor, _, _ = fixture
    auth = sharedPrepare(fixture)
    with pytest.raises(gate.GateRefused, match="legacy-route-disabled"):
        gate.finalize(fx.root, {"digest": "caller-claimed-success"}, forge.snap, h.utc())
    with pytest.raises(core.Refused, match="unknown operation"):
        gate.finalize(fx.root, {"operationId": "0" * 64}, forge.snap, h.utc())
    gate.abort(fx.root, auth, "not made", h.utc())
    assert gate.finalize(fx.root, {**auth, "state": "merged", "runId": "forged"}, forge.snap, h.utc())["state"] == "aborted"
    with pytest.raises(core.Refused):
        executor.coordinator.invoke(core.tokenFor(executor.coordinator.inspect()["operations"][auth["operationId"]]), "fresh-send")
    assert forge.invocations == [] and state.terminalFor(fx.root, h.REPO, 2270, "merge") is None


def test_late_preparation_cannot_send_or_manufacture_terminal_observation(tmp_path, monkeypatch):
    fixture = sharedWorld(tmp_path, monkeypatch)
    fx, forge, clock, executor, _, _ = fixture
    auth = sharedPrepare(fixture)
    clock.instant += 3600
    with pytest.raises(core.Refused, match="live preparation"):
        executor.execute(auth["operationId"])
    assert gate.finalize(fx.root, auth, dataclasses.replace(forge.snap, merged=True), h.utc())["state"] == "intent"
    assert forge.invocations == []


def test_closure_of_a_held_or_draft_original_is_refused_even_when_superseded(tmp_path):
    for over in ({"labels": ["content-engine", "founder-hold"]}, {"draft": True}, {"reviewThreadsUnresolved": 1}, {"reviewThreadsUnresolved": None}):
        fx, head, snap, req = closureWorld(tmp_path / f"c{abs(hash(str(over)))}")
        held = dataclasses.replace(snap, row={**snap.row, **over})
        with pytest.raises(gate.GateRefused) as caught:
            gate.gateClose(fx.root, req, held, h.utc(), RUN)
        assert caught.value.code in ("closure-not-proven", "closure-held"), caught.value
        assert outcomes(fx) == []


def test_new_run_or_negative_get_never_supersedes_claimed_sender(tmp_path, monkeypatch):
    fixture = sharedWorld(tmp_path, monkeypatch, "close")
    fx, forge, clock, executor, req, _ = fixture
    auth = sharedPrepare(fixture)
    forge.lost = True
    executor.execute(auth["operationId"])
    clock.instant += 1800
    with pytest.raises(core.Refused):
        gate.gateClose(fx.root, req, forge.snap, h.utc() + timedelta(minutes=30), "run-2")
    assert gate.finalize(fx.root, auth, forge.snap, h.utc())["state"] == "quarantined"
    with pytest.raises(core.Refused):
        gate.abort(fx.root, auth, "claimed sender is not canceled by local supersession", h.utc())
    assert len(forge.invocations) == len(forge.effects) == 1


def test_a_verifier_dispatch_that_does_not_name_this_head_cannot_back_a_verification(fx):
    head = fx.head("2026-44")
    other = fx.head("2026-45", name="docs/content-engine-2026-45")
    dispatched(fx, {"agentId": "verifier-a", "effort": "high"}, ["builder-x"], subject={"repo": h.REPO, "number": 2271, "headSha": other})
    with pytest.raises(gate.GateRefused) as caught:
        gate.recordVerification(fx.root, {"repo": h.REPO, "number": 2270, "action": "merge", "headSha": head, "baseSha": fx.base, "verdict": "pass",
                                          "verifier": {"agentId": "verifier-a", "effort": "high", "profileId": "p"}, "builders": ["builder-x"],
                                          "proofs": [{"name": "a", "state": "pass", "detail": ""}], "runId": RUN}, h.utc())
    assert caught.value.code == "verification-not-dispatched" and "envelope subjects" in caught.value.message


def test_the_builder_of_a_replacement_comes_from_the_reconcile_record_not_the_caller(fx):
    head = fx.head("2026-44")
    state.appendRecord(fx.root, "outcomes", {"at": "2026-11-04T18:00:00Z", "runId": "r0", "repo": h.REPO, "number": 2157, "action": "reconcile",
                                             "state": "built", "headSha": head, "originalHead": "a" * 40, "branch": "steward/b/x",
                                             "builders": ["reconciler:content-engine-cachebust", "verifier-a"]})
    with pytest.raises(gate.GateRefused) as caught:
        verification(fx, head)  # the caller lists only builder-x, but the store says verifier-a did the building
    assert caught.value.code == "verification-not-independent"


def test_closure_gate_rechecks_every_hold_class_gate_itself(tmp_path, monkeypatch):
    fx, head, snap, req = closureWorld(tmp_path)
    real = gate.evaluate

    def flipped(*args, **kwargs):
        found = real(*args, **kwargs)
        gates = tuple(dataclasses.replace(g, state="fail") if g.name == "holds" else g for g in found.gates)
        return dataclasses.replace(found, gates=gates)

    monkeypatch.setattr(gate, "evaluate", flipped)
    with pytest.raises(gate.GateRefused) as caught:
        gate.gateClose(fx.root, req, snap, h.utc(), RUN)
    assert caught.value.code == "closure-held"
    assert outcomes(fx) == []


def test_the_authority_ref_must_be_a_remote_tracking_ref_never_head_or_a_local_branch(fx, monkeypatch):
    head = ready(fx)
    for bad in ("HEAD", "main", fx.base):
        monkeypatch.setenv(gate.AUTHORITY_REF, bad)
        refused(fx, snapshot(fx, head), request(head), "authority-ref-invalid")
    assert outcomes(fx) == []
