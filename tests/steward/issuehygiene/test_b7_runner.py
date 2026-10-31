"""Lane B7 round-2 runner rules: the kill switch cancels pending closures (D3), a terminal closure needs a receipt
(D7), a malformed issueHygiene block disables only its own surface (D8), and the ready-but-disabled count is
surfaced (D10). The runner fixtures are the lane-D1 runner fixtures.
"""

from __future__ import annotations

import pytest

from gaia_cli.steward.fullrun import RecordRefused
from gaia_cli.steward.policy import PolicyError, StewardPolicy
from tests.steward.issuehygiene.test_d1_runner import (
    CLOSE,
    closeActions,
    closureItems,
    closureRows,
    makeCensus,
    makeManifest,
    operationsOf,
    outcomeFor,
    runnerFor,
    settle,
    stubReconcile,
    writeCensus,
)


def policyPath(repo):
    return repo / "founder" / "steward" / "POLICY.yaml"


def setPolicy(repo, text: str, new: str) -> None:
    target = policyPath(repo)
    target.write_text(target.read_text(encoding="utf-8").replace(text, new, 1), encoding="utf-8")


def test_switching_writes_off_after_emission_cancels_the_pending_closures_and_settles(tmp_path, monkeypatch) -> None:
    repo, store, runner = runnerFor(tmp_path)
    rows = closureRows(2)
    writeCensus(repo, makeCensus(rows))
    stubReconcile(monkeypatch, makeManifest(closureItems(rows)))
    view = runner.start("full")
    assert len(closeActions(view)) == 2

    setPolicy(repo, "writesEnabled: true", "writesEnabled: false")
    view = runner.resume(view.runId)

    assert view.status == "completed"
    actions = [a for a in store.load()[0]["runs"][view.runId]["actions"] if a["type"] == CLOSE]
    assert actions and all(a["status"] == "cancelled" for a in actions)
    assert all(a["outcome"]["reason"] == "writes-disabled" for a in actions)
    assert not closeActions(view)
    again = runner.start("full")  # the lease is released: a new run is not held behind the cancelled one
    assert again.status != "observing-existing"
    assert closeActions(again) == []  # writes are off, so nothing is re-emitted


def test_a_disabled_rule_cancels_only_its_own_pending_closures(tmp_path, monkeypatch) -> None:
    repo, store, runner = runnerFor(tmp_path)
    rows = closureRows(2)
    writeCensus(repo, makeCensus(rows))
    stubReconcile(monkeypatch, makeManifest(closureItems(rows)))
    view = runner.start("full")
    assert len(closeActions(view)) == 2

    setPolicy(repo, "- A1-child-curated", "- A4-duplicate-child")
    runner.resume(view.runId)

    actions = [a for a in store.load()[0]["runs"][view.runId]["actions"] if a["type"] == CLOSE]
    assert all(a["status"] == "cancelled" for a in actions)


def test_a_closed_outcome_without_a_receipt_is_refused_and_the_action_stays_pending(tmp_path, monkeypatch) -> None:
    repo, store, runner = runnerFor(tmp_path)
    rows = closureRows(1)
    writeCensus(repo, makeCensus(rows))
    stubReconcile(monkeypatch, makeManifest(closureItems(rows)))
    view = runner.start("full")
    action = closeActions(view)[0]

    with pytest.raises(RecordRefused, match="no receipt records"):
        runner.record(view.runId, action["stepId"], outcomeFor(action))
    pending = [a for a in store.load()[0]["runs"][view.runId]["actions"] if a["stepId"] == action["stepId"]]
    assert pending and pending[0]["status"] == "pending"


def test_a_receipt_with_a_different_proof_does_not_verify_the_outcome(tmp_path, monkeypatch) -> None:
    repo, store, runner = runnerFor(tmp_path)
    rows = closureRows(1)
    writeCensus(repo, makeCensus(rows))
    stubReconcile(monkeypatch, makeManifest(closureItems(rows)))
    view = runner.start("full")
    action = closeActions(view)[0]
    receipt = repo / action["params"]["receiptPath"]
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text('{"key": "%s", "issue": %d, "outcome": "closed", "commentUrl": '
                       '"https://github.com/gaia-research/gaia-skill-tree/issues/%d#issuecomment-1"}\n'
                       % (action["params"]["key"], action["params"]["issue"], action["params"]["issue"]), encoding="utf-8")
    with pytest.raises(RecordRefused, match="no receipt records"):
        runner.record(view.runId, action["stepId"], outcomeFor(action))  # the outcome names comment 1000 + issue


def test_a_malformed_issue_hygiene_block_disables_only_the_issue_hygiene_surface(tmp_path, monkeypatch) -> None:
    repo, store, runner = runnerFor(tmp_path)
    rows = closureRows(2)
    writeCensus(repo, makeCensus(rows))  # a census is present, so the sensor is evaluated and must refuse
    setPolicy(repo, "  maxClosuresPerRun: 10", "  maxClosuresPerRun: many")
    policy = StewardPolicy.load(repo)
    assert policy.issue_hygiene_error and "malformed" in policy.issue_hygiene_error
    assert policy.issue_hygiene.writesEnabled is False  # the disabled default, never a partly-parsed block

    view = runner.start("full")

    assert view.status != "failed"
    assert "issue-hygiene" in (view.coverageUnknown or [])
    assert not closeActions(view)


def test_the_policy_still_loads_for_every_other_surface_when_issue_hygiene_is_malformed(tmp_path) -> None:
    repo, _store, _runner = runnerFor(tmp_path)
    setPolicy(repo, "  maxClosuresPerRun: 10", "  maxClosuresPerRun: many")
    try:
        policy = StewardPolicy.load(repo)
    except PolicyError:  # pragma: no cover - the whole policy failing is the defect this test guards against
        pytest.fail("a malformed issueHygiene block must not make the whole steward policy unreadable")
    assert policy.max_observations_per_run >= 1  # another surface of the same policy still parses


def test_the_ready_but_disabled_count_is_on_the_desk_backlog_line(tmp_path, monkeypatch) -> None:
    repo, store, runner = runnerFor(tmp_path)
    rows = closureRows(2)
    writeCensus(repo, makeCensus(rows))
    stubReconcile(monkeypatch, makeManifest(closureItems(rows)))
    setPolicy(repo, "writesEnabled: true", "writesEnabled: false")

    view = runner.start("full")

    detail = operationsOf(view, "issue_backlog")[0]["detail"]
    assert "ready (writes disabled): 2 proven closures" in detail
    assert not closeActions(view)


def test_steward_full_status_prints_the_ready_but_disabled_count(tmp_path, monkeypatch, capsys) -> None:
    from types import SimpleNamespace

    from gaia_cli.commands.steward import StewardCommand

    view = SimpleNamespace(
        ledger={"transport": "local-file", "shared": False}, holder=None, holderPhase=None, holderExpiresAt=None,
        lastScheduledRunAt=None, workCounts={}, lane=None,
        recentRuns=[{"runId": "run-1", "mode": "full", "status": "completed", "startedAt": "2026-10-21T19:30:00Z",
                     "readyWritesDisabled": 3}],
        desk=None, deskRunId=None,
    )
    StewardCommand._printFullStatus(view)
    out = capsys.readouterr().out
    assert "Issue closures       ready (writes disabled): 3 proven closures" in out
