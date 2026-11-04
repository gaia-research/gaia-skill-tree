"""Runner integration: forge.merge_pr / forge.close_pr are emitted sequentially, only with verification, and only settle on the store."""

from __future__ import annotations

import json
import shutil

import pytest

from gaia_cli.steward.fullrun import MERGEACTION, RecordRefused
from gaia_cli.steward.models import Observation, Subject
from gaia_cli.steward.prmaintenance import state
from gaia_cli.steward.prmaintenance.sensor import PrMaintenanceSensor  # noqa: F401

from tests.steward.prmaintenance import helpers as h
from tests.steward.test_fullrun import REPO_ROOT, commitAll, fileStore, git, makeFixture, makeRunner

HEAD, BASE = "a" * 40, "b" * 40


class PrStub:
    """A sensor that reports routine pull requests with the fields the runner reads from the real sensor."""

    id = "pr-maintenance"
    resolution_scope = "exhaustive"
    routine_ids = (19,)
    debt_kinds = ("routine_pr_merge_ready",)

    def __init__(self, rows):
        self.rows = rows

    def scan(self, repo_root, observed_at):
        return [Observation(kind=kind, subject=Subject("pull-request", f"{h.REPO}#{n}"), observed_at=observed_at, source=self.id,
                            status="drift", current_state={"count": 0},
                            observed_state={"repo": h.REPO, "number": n, "headSha": head, "baseSha": BASE, "baseRef": "main",
                                            "producerId": "weekly-content-engine", "label": label, "evaluationSha256": "e" * 64})
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
    with pytest.raises(RecordRefused, match="no recorded merged outcome"):
        runner.record(view.runId, step, claim)
    state.appendRecord(repo, "outcomes", {"at": "2026-11-04T18:31:00Z", "runId": view.runId, "repo": h.REPO, "number": 2270, "action": "merge",
                                          "headSha": HEAD, "state": "merged", "mergeCommitSha": "9" * 40})
    with pytest.raises(RecordRefused, match="no recorded merged outcome"):
        runner.record(view.runId, step, {**claim, "mergeCommitSha": "8" * 40})
    runner.record(view.runId, step, claim)
    with pytest.raises(RecordRefused):
        runner.record(view.runId, step, {**claim, "mergeCommitSha": "8" * 40})  # a different outcome never replaces a recorded one


def test_a_recorded_terminal_outcome_is_never_emitted_again(tmp_path):
    repo = fixture(tmp_path)
    verify(repo, 2270)
    state.appendRecord(repo, "outcomes", {"at": "2026-11-04T18:00:00Z", "runId": "r0", "repo": h.REPO, "number": 2270, "action": "merge",
                                          "headSha": HEAD, "state": "merged", "mergeCommitSha": "9" * 40})
    view = makeRunner(repo, fileStore(tmp_path), [PrStub([("routine_pr_merge_ready", 2270, HEAD, "2026-45")])]).start("full")
    assert pending(view) == []


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
