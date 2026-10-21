"""D1: forge.close_issue emission, outcome recording and exactly-once closure (contract 3.4-3.6).

The runner is driven through the real full-run phases on a local bare remote; the
issue census and the reconciliation are supplied the same way the sensor tests do it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from gaia_cli.steward.fullrun import RecordRefused
from gaia_cli.steward.issuehygiene.outcomes import OutcomeStoreError, loadOutcomes, writeOutcome
from gaia_cli.steward.issuehygiene.sensor import IssueHygieneSensor
from gaia_cli.steward.primitives import SensorUnavailable
from tests.steward.issuehygiene.test_d1_sensor import (
    makeCensus,
    makeItem,
    makeManifest,
    makeRow,
    stubReconcile,
    writeCensus,
)
from tests.steward.test_fullrun import StubSensor, fileStore, makeFixture, makeRunner

CLOSE = "forge.close_issue"


def closureRows(count: int, start: int = 100) -> list[dict]:
    return [
        makeRow(start + index, f"[intake] candidate {index}",
                body=f'<!-- gaia-upstream-payload {{"id": "o/r:c{index}"}} -->\ncandidate {index}')
        for index in range(count)
    ]


def closureItems(rows: list[dict], start: int = 100) -> list[dict]:
    items = []
    for index, row in enumerate(rows):
        items.append(makeItem(
            row["number"], f"upstream-candidate:o/r:c{index}", "A", ruleId="A1-child-curated",
            evidence=[{"type": "registry", "ref": f"registry/named/o/c{index}.md", "sha256": "a" * 64}],
            snapshot={"updatedAt": row["updatedAt"], "bodySha256": row["bodySha256"],
                      "labels": sorted(row["labels"])},
        ))
    return items


def closeActions(view) -> list[dict]:
    return [action for action in view.actions if action["type"] == CLOSE]


def outcomeFor(action: dict, result: str = "closed", **extra) -> dict:
    params = action["params"]
    body = {"outcome": result, "issue": params["issue"], "key": params["key"]}
    if result == "closed":
        body["commentUrl"] = f"https://example.invalid/issues/{params['issue']}#closure"
    body.update(extra)
    return body


def runnerFor(tmp_path: Path, *extra_sensors, agents: bool = False):
    repo, _bare = makeFixture(tmp_path)
    store = fileStore(tmp_path)
    sensors = [IssueHygieneSensor(), *extra_sensors]
    return repo, store, makeRunner(repo, store, sensors, agents=agents)


def test_class_a_emits_at_most_ten_closures_then_waits_for_driver_outcomes(tmp_path, monkeypatch) -> None:
    repo, store, runner = runnerFor(tmp_path)
    rows = closureRows(12)
    writeCensus(repo, makeCensus(rows))
    stubReconcile(monkeypatch, makeManifest(closureItems(rows)))
    view = runner.start("full")
    actions = closeActions(view)
    assert len(actions) == 10
    assert view.status == "awaiting-action"
    params = actions[0]["params"]
    assert params["ruleId"] == "A1-child-curated"
    assert params["expectedSnapshot"]["bodySha256"] == rows[0]["bodySha256"]
    assert params["receiptPath"].endswith(f"{view.runId}.jsonl")
    assert "<!-- gaia-steward-closure:" in params["comment"]
    assert "gaia-upstream-payload" in params["comment"]  # the original payload travels with the closure
    assert all(action["type"] != "agent.build" for action in view.actions)


def test_resume_neither_repeats_nor_loses_pending_closures(tmp_path, monkeypatch) -> None:
    repo, store, runner = runnerFor(tmp_path)
    rows = closureRows(3)
    writeCensus(repo, makeCensus(rows))
    stubReconcile(monkeypatch, makeManifest(closureItems(rows)))
    view = runner.start("full")
    first = [a["stepId"] for a in closeActions(view)]
    assert len(first) == 3
    again = runner.resume(view.runId)
    assert [a["stepId"] for a in closeActions(again)] == first
    recorded = store.load()[0]["runs"][view.runId]["actions"]
    assert sorted(a["stepId"] for a in recorded if a["type"] == CLOSE) == sorted(first)


def test_closed_outcomes_are_durable_and_a_later_run_never_reemits_them(tmp_path, monkeypatch) -> None:
    repo, store, runner = runnerFor(tmp_path)
    rows = closureRows(12)
    writeCensus(repo, makeCensus(rows))
    stubReconcile(monkeypatch, makeManifest(closureItems(rows)))
    view = runner.start("full")
    for action in closeActions(view):
        runner.record(view.runId, action["stepId"], outcomeFor(action))
    view = runner.resume(view.runId)
    assert closeActions(view) == []  # the cap for this run is spent; the two deferred items wait
    assert len(loadOutcomes(repo)) == 10

    second = runner.start("full")  # the census still lists all twelve as open
    emitted = [a["params"]["issue"] for a in closeActions(second)]
    assert sorted(emitted) == [110, 111]


def test_repeat_record_is_a_noop_and_a_different_outcome_is_refused(tmp_path, monkeypatch) -> None:
    repo, store, runner = runnerFor(tmp_path)
    rows = closureRows(1)
    writeCensus(repo, makeCensus(rows))
    stubReconcile(monkeypatch, makeManifest(closureItems(rows)))
    view = runner.start("full")
    (action,) = closeActions(view)
    runner.record(view.runId, action["stepId"], outcomeFor(action))
    runner.record(view.runId, action["stepId"], outcomeFor(action))  # same outcome: no-op
    with pytest.raises(RecordRefused):
        runner.record(view.runId, action["stepId"], outcomeFor(action, "failed", failure="late change"))


@pytest.mark.parametrize("body", [
    {"outcome": "default"},
    {"outcome": "inherit"},
    {"outcome": "closed", "commentUrl": "https://example.invalid/c"},  # wrong issue or key below
    {"outcome": "closed"},  # no closing comment recorded
    {"outcome": "failed"},  # no failure reason
])
def test_invalid_outcomes_are_refused(tmp_path, monkeypatch, body) -> None:
    repo, store, runner = runnerFor(tmp_path)
    rows = closureRows(1)
    writeCensus(repo, makeCensus(rows))
    stubReconcile(monkeypatch, makeManifest(closureItems(rows)))
    view = runner.start("full")
    (action,) = closeActions(view)
    payload = dict(body)
    payload.setdefault("issue", action["params"]["issue"])
    payload.setdefault("key", action["params"]["key"])
    if body.get("outcome") == "closed" and "commentUrl" in body:
        payload["issue"] = action["params"]["issue"] + 1
    with pytest.raises(RecordRefused):
        runner.record(view.runId, action["stepId"], payload)
    assert loadOutcomes(repo) == {}


def test_failed_and_stale_outcomes_are_retryable_and_bounded(tmp_path) -> None:
    root = tmp_path
    for attempt in range(3):
        assert writeOutcome(root, "key:x", {"outcome": "failed", "issue": 1, "failure": "403"}) == "recorded"
    assert loadOutcomes(root)["key:x"]["attempts"] == 3
    assert writeOutcome(root, "key:x", {"outcome": "closed", "issue": 1, "commentUrl": "u"}) == "recorded"
    assert writeOutcome(root, "key:x", {"outcome": "failed", "issue": 1, "failure": "late"}) == "repeat"


def test_a_malformed_outcome_store_is_an_error_never_an_empty_store(tmp_path) -> None:
    target = tmp_path / ".gaia/steward/issue-hygiene"
    target.mkdir(parents=True)
    (target / "outcomes.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(OutcomeStoreError):
        loadOutcomes(tmp_path)


def test_policy_writes_disabled_emits_nothing_and_leaves_the_debt_report_only(tmp_path, monkeypatch) -> None:
    repo, store, runner = runnerFor(tmp_path)
    policy = repo / "founder/steward/POLICY.yaml"
    policy.write_text(policy.read_text(encoding="utf-8").replace("writesEnabled: true", "writesEnabled: false", 1),
                      encoding="utf-8")
    rows = closureRows(2)
    writeCensus(repo, makeCensus(rows))
    stubReconcile(monkeypatch, makeManifest(closureItems(rows)))
    view = runner.start("full")
    assert closeActions(view) == []
    assert view.status == "completed"


def test_another_sensors_unknown_coverage_blocks_closure(tmp_path, monkeypatch) -> None:
    broken = StubSensor("flaky-surface", "registry_integrity_failed",
                        raises=SensorUnavailable("surface cannot be read completely"))
    repo, store, runner = runnerFor(tmp_path, broken)
    rows = closureRows(2)
    writeCensus(repo, makeCensus(rows))
    stubReconcile(monkeypatch, makeManifest(closureItems(rows)))
    view = runner.start("full")
    assert view.status == "blocked"
    assert closeActions(view) == []


def test_a_snapshot_that_moved_since_reconciliation_is_not_closed(tmp_path, monkeypatch) -> None:
    repo, store, runner = runnerFor(tmp_path)
    rows = closureRows(1)
    writeCensus(repo, makeCensus(rows))
    items = closureItems(rows)
    items[0]["snapshot"]["updatedAt"] = "2020-01-01T00:00:00Z"
    stubReconcile(monkeypatch, makeManifest(items))
    view = runner.start("full")
    assert closeActions(view) == []


def test_founder_debt_emits_no_action(tmp_path, monkeypatch) -> None:
    repo, store, runner = runnerFor(tmp_path)
    rows = closureRows(1, start=200)
    writeCensus(repo, makeCensus(rows))
    item = closureItems(rows, start=200)[0]
    item.update(authority="C", ruleId=None, state="awaiting-founder")
    question = {"id": "Q-cafe0001", "question": "Accept this family?", "affected": [200],
                "options": ["accept", "reject", "defer"], "recommendation": None, "basis": "one candidate"}
    stubReconcile(monkeypatch, makeManifest([item], founderQuestions=[question]))
    view = runner.start("full")
    assert [a["type"] for a in view.actions if a["type"] == CLOSE] == []
    assert view.status == "completed"


def test_forge_closure_needs_no_local_repair_executor(tmp_path, monkeypatch) -> None:
    from gaia_cli.steward.policy import StewardPolicy

    policy = StewardPolicy.load(Path(__file__).resolve().parents[3])
    assert policy.executor_for("issue_closure_ready") is None  # closure never routes through repairs.executors
