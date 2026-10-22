"""Adversarial lane E, scenarios 10 to 13 at the runner: durable resume, bounded retries, routing, C non-mutation.

Driven through the real ``FullRunner`` phases on a local fixture, exactly as the D1 runner tests are.
The reconciliation seam is stubbed with a manifest so each scenario states its inputs directly.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from gaia_cli.steward.issuehygiene.outcomes import loadOutcomes
from gaia_cli.steward.issuehygiene.sensor import IssueHygieneSensor
from tests.steward.issuehygiene.test_d1_runner import (
    settle,
    CLOSE,
    closeActions,
    closureItems,
    closureRows,
    outcomeFor,
    runnerFor,
)
from tests.steward.issuehygiene.test_d1_sensor import makeCensus, makeItem, makeManifest, stubReconcile, writeCensus
from tests.steward.test_fullrun import makeRunner


def operationsOf(view, kind: str) -> list[dict]:
    return [op for op in (view.desk or {}).get("operations", []) if op["kind"] == kind]


def checkoutDigest(root: Path) -> str:
    """Hash every file in the checkout except runner state (.gaia) and git internals."""

    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_dir() or relative.startswith((".gaia/", ".git/")):
            continue
        digest.update(relative.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


# ------------------------------------------------------------------ scenario 12: durable, restart-safe resume


def test_a_restarted_runner_object_never_reemits_a_recorded_closure(tmp_path, monkeypatch) -> None:
    repo, store, runner = runnerFor(tmp_path)
    rows = closureRows(12)
    writeCensus(repo, makeCensus(rows))
    stubReconcile(monkeypatch, makeManifest(closureItems(rows)))
    view = runner.start("full")
    emitted = closeActions(view)
    assert len(emitted) == 10  # the cap for this run
    for action in emitted[:6]:
        settle(runner, view.runId, action, outcomeFor(action))

    # The first run still awaits four outcomes and holds the run lease. A fresh runner object is refused.
    fresh = makeRunner(repo, store, [IssueHygieneSensor()], agents=False)
    refused = fresh.start("full")
    assert refused.status == "observing-existing"
    assert closeActions(refused) == []

    for action in emitted[6:]:
        settle(runner, view.runId, action, outcomeFor(action))
    runner.resume(view.runId)
    assert len(loadOutcomes(repo)) == 10
    monkeypatch.setenv("GAIA_STEWARD_NOW", "2026-10-21T20:30:00Z")  # the hourly budget renews in the next UTC hour (B7 L2)
    second = fresh.start("full")
    assert sorted(action["params"]["issue"] for action in closeActions(second)) == [110, 111]  # never 100 to 109


def test_a_closure_still_pending_in_one_run_is_not_emitted_again_by_another_run(tmp_path, monkeypatch) -> None:
    repo, store, runner = runnerFor(tmp_path)
    rows = closureRows(3)
    writeCensus(repo, makeCensus(rows))
    stubReconcile(monkeypatch, makeManifest(closureItems(rows)))
    first = runner.start("full")
    pendingPairs = {(a["params"]["key"], a["params"]["issue"]) for a in closeActions(first)}
    assert len(pendingPairs) == 3

    fresh = makeRunner(repo, store, [IssueHygieneSensor()], agents=False)
    second = fresh.start("full")
    assert second.status == "observing-existing"  # the pending run holds the lease: nothing is emitted twice
    assert closeActions(second) == []


def test_a_retryable_failure_is_retried_a_bounded_number_of_times_then_needs_a_human(tmp_path, monkeypatch) -> None:
    repo, store, runner = runnerFor(tmp_path)
    rows = closureRows(1)
    writeCensus(repo, makeCensus(rows))
    stubReconcile(monkeypatch, makeManifest(closureItems(rows)))
    emittedPerRun = []
    for _attempt in range(4):
        view = runner.start("full")
        actions = closeActions(view)
        emittedPerRun.append(len(actions))
        for action in actions:
            settle(runner, view.runId, action, outcomeFor(action, "failed", failure="http-502"))
        if view.status == "awaiting-action":
            runner.resume(view.runId)  # let the run finish so the next attempt is not lease-refused
    assert emittedPerRun == [1, 1, 1, 0]  # three attempts, then the retry limit stops emission
    assert loadOutcomes(repo)["upstream-candidate:o/r:c0#100"]["attempts"] == 3


def test_a_terminal_outcome_recorded_twice_by_a_driver_retry_is_a_single_write(tmp_path, monkeypatch) -> None:
    repo, store, runner = runnerFor(tmp_path)
    rows = closureRows(1)
    writeCensus(repo, makeCensus(rows))
    stubReconcile(monkeypatch, makeManifest(closureItems(rows)))
    view = runner.start("full")
    (action,) = closeActions(view)
    settle(runner, view.runId, action, outcomeFor(action))
    before = (repo / ".gaia/steward/issue-hygiene/outcomes.json").read_bytes()
    settle(runner, view.runId, action, outcomeFor(action))
    assert (repo / ".gaia/steward/issue-hygiene/outcomes.json").read_bytes() == before


# ------------------------------------------------------------------ scenario 13: second run, no duplicate noise


def test_a_second_run_after_the_first_drained_its_closures_emits_nothing_and_its_debts_are_identical(tmp_path, monkeypatch) -> None:
    repo, store, runner = runnerFor(tmp_path)
    rows = closureRows(10)
    writeCensus(repo, makeCensus(rows))
    stubReconcile(monkeypatch, makeManifest(closureItems(rows)))
    first = runner.start("full")
    for action in closeActions(first):
        settle(runner, first.runId, action, outcomeFor(action))
    runner.resume(first.runId)

    second = runner.start("full")
    third = runner.start("full")
    assert closeActions(second) == [] and closeActions(third) == []
    assert [a for a in second.actions if a["type"] == "agent.build"] == []
    desk2 = sorted((op["kind"], op["detail"]) for op in (second.desk or {}).get("operations", []))
    desk3 = sorted((op["kind"], op["detail"]) for op in (third.desk or {}).get("operations", []))
    assert desk2 and desk2 == desk3  # non-empty, and the second and third runs post identical desk noise
    assert len(operationsOf(second, "issue_backlog")) == len(operationsOf(third, "issue_backlog")) == 1


# ------------------------------------------------------------------ scenario 10: class B routing


def test_class_b_items_route_to_the_suite_review_dispatch_and_never_to_a_forge_write(tmp_path, monkeypatch) -> None:
    repo, store, runner = runnerFor(tmp_path, agents=True)
    rows = closureRows(2, start=300)
    writeCensus(repo, makeCensus(rows))
    items = [
        makeItem(300, "upstream-candidate:o/r:c0", "B", state="actionable"),
        makeItem(301, "upstream-candidate:o/r:c1", "B", state="actionable"),
    ]
    batches = [{"suite": "o/r", "umbrella": 1835, "classB": ["upstream-candidate:o/r:c0", "upstream-candidate:o/r:c1"], "size": 2}]
    stubReconcile(monkeypatch, makeManifest(items, batches=batches))
    view = runner.start("full")
    assert closeActions(view) == []
    builds = [action for action in view.actions if action["type"] == "agent.build"]
    assert len(builds) == 1  # one batch per run, however many rows it holds
    assert "issue-suite-review" in json.dumps(builds[0])
    assert builds[0]["debtId"].startswith("debt:issue_suite_review:")


def test_class_b_without_agents_is_held_for_review_and_writes_nothing(tmp_path, monkeypatch) -> None:
    repo, store, runner = runnerFor(tmp_path, agents=False)
    rows = closureRows(1, start=300)
    writeCensus(repo, makeCensus(rows))
    items = [makeItem(300, "upstream-candidate:o/r:c0", "B", state="actionable")]
    stubReconcile(monkeypatch, makeManifest(items, batches=[{"suite": "o/r", "umbrella": 1835,
                                                              "classB": ["upstream-candidate:o/r:c0"], "size": 1}]))
    view = runner.start("full")
    assert closeActions(view) == []
    assert [a for a in view.actions if a["type"] == "agent.build"] == []


# ------------------------------------------------------------------ scenario 11: class C is never mutated


def test_thirty_class_c_items_under_one_question_make_one_decision_and_no_action(tmp_path, monkeypatch) -> None:
    repo, store, runner = runnerFor(tmp_path)
    rows = closureRows(30, start=500)
    writeCensus(repo, makeCensus(rows))
    items = closureItems(rows, start=500)
    for item in items:
        item.update(authority="C", ruleId=None, state="awaiting-founder")
    question = {"id": "Q-c0ffee01", "question": "Accept the o/r alias family of candidates?",
                "affected": [500 + index for index in range(30)], "options": ["accept", "reject", "defer"],
                "recommendation": None, "basis": "one handle pair"}
    stubReconcile(monkeypatch, makeManifest(items, founderQuestions=[question]))
    view = runner.start("full")
    assert closeActions(view) == []
    assert [a for a in view.actions if a["type"] == "agent.build"] == []
    decisions = [d for d in view.desk["decisions"] if "alias family" in d["decision"]]
    assert len(decisions) == 1
    assert len(decisions[0]["debtIds"]) == 1


def test_a_run_over_a_closure_debt_never_writes_into_the_checkout(tmp_path, monkeypatch) -> None:
    repo, store, runner = runnerFor(tmp_path)
    rows = closureRows(4)
    writeCensus(repo, makeCensus(rows))
    stubReconcile(monkeypatch, makeManifest(closureItems(rows)))
    before = checkoutDigest(repo)
    view = runner.start("full")
    assert len(closeActions(view)) == 4
    assert checkoutDigest(repo) == before  # emitting a forge action edits nothing in the repository
    assert view.actions and all(a["type"] == CLOSE or a["type"] != "forge.open_pr" for a in view.actions)
