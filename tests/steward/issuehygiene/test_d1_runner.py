"""D1: forge.close_issue emission, outcome recording and exactly-once closure (contract 3.4-3.6).

The runner is driven through the real full-run phases on a local bare remote; the
issue census and the reconciliation are supplied the same way the sensor tests do it.
"""

from __future__ import annotations

import json

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
from gaia_cli.steward.clock import parseInstant, setClock

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
            evidence=[{"type": "registry", "ref": f"registry/named/o/c{index}.md", "sha256": "a" * 64,
                       "detail": "exact candidate"}],
            snapshot={"state": "open", "title": row["title"], "updatedAt": row["updatedAt"],
                      "bodySha256": row["bodySha256"], "labels": sorted(row["labels"])},
            original={"title": row["title"], "labels": sorted(row["labels"]), "bodySha256": row["bodySha256"],
                      "candidate": {"suggestedId": f"c{index}"}},
        ))
    return items


def closeActions(view) -> list[dict]:
    return [action for action in view.actions if action["type"] == CLOSE]


def settle(runner, runId: str, action: dict, outcome: dict):
    """Record a driver outcome the way the executor leaves it: a closed outcome has a matching receipt (B7 D7).

    The real script writes this receipt before it prints the outcome. Recording a terminal closure without one
    is refused, and that refusal is tested on its own.
    """
    if outcome.get("outcome") in ("closed", "already-closed"):
        params = action["params"]
        receipt = runner.root / params["receiptPath"]
        receipt.parent.mkdir(parents=True, exist_ok=True)
        entry = {"schemaVersion": "steward-issue-closure-receipt-v1", "runId": runId, "key": params["key"],
                 "issue": params["issue"], "ruleId": params["ruleId"], "outcome": outcome["outcome"],
                 "commentUrl": outcome.get("commentUrl"), "commentId": outcome.get("commentId"),
                 "markerVerified": outcome.get("markerVerified", False), "closedAt": "2026-10-21T19:30:00Z"}
        with receipt.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, sort_keys=True) + "\n")
    return runner.record(runId, action["stepId"], outcome)


def outcomeFor(action: dict, result: str = "closed", **extra) -> dict:
    params = action["params"]
    body = {"outcome": result, "issue": params["issue"], "key": params["key"]}
    if result == "closed":
        # One GitHub-shaped comment URL on this issue and repo: exactly one proof (D3).
        body["commentUrl"] = f"https://github.com/gaia-research/gaia-skill-tree/issues/{params['issue']}#issuecomment-{1000 + params['issue']}"
    body.update(extra)
    return body


def runnerFor(tmp_path: Path, *extra_sensors, agents: bool = False):
    repo, _bare = makeFixture(tmp_path)
    # The shipped policy is dry-run (B5). These runner tests exercise the writable path explicitly.
    from .e_fakes import approveClosureFixture
    approveClosureFixture(repo)
    policyFile = repo / "founder/steward/POLICY.yaml"
    policyFile.write_text(policyFile.read_text(encoding="utf-8").replace("writesEnabled: false", "writesEnabled: true", 1),
                          encoding="utf-8")
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
    assert "comment" not in params and "original" not in params  # compact: the executor rebuilds them from the census (B7 D5)
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
        settle(runner, view.runId, action, outcomeFor(action))
    view = runner.resume(view.runId)
    assert closeActions(view) == []  # the cap for this run is spent; the two deferred items wait
    assert len(loadOutcomes(repo)) == 10

    # The policy cap is per UTC hour (B7 L2): the two deferred closures wait for the next hour.
    setClock(lambda: parseInstant("2026-10-21T20:30:00Z"))
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
    settle(runner, view.runId, action, outcomeFor(action))
    settle(runner, view.runId, action, outcomeFor(action))  # same outcome: no-op
    with pytest.raises(RecordRefused):
        settle(runner, view.runId, action, outcomeFor(action, "failed", failure="late change"))


@pytest.mark.parametrize("body", [
    {"outcome": "default"},
    {"outcome": "inherit"},
    {"outcome": "closed", "commentUrl": "https://example.invalid/c"},  # wrong issue or key below
    {"outcome": "closed"},  # no closing comment recorded
    {"outcome": "closed", "commentUrl": "ISSUE_URL", "commentId": 5},  # two proofs: exactly one is required (D3)
    {"outcome": "closed", "commentUrl": "ISSUE_URL", "markerVerified": True},  # two proofs (D3)
    {"outcome": "closed", "markerVerified": False},  # a false marker is not proof
    {"outcome": "closed", "commentId": True},  # a boolean is not a comment id
    {"outcome": "closed", "commentId": "4567"},  # a comment id is an integer
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
    if payload.get("commentUrl") == "ISSUE_URL":
        payload["commentUrl"] = f"https://github.com/gaia-research/gaia-skill-tree/issues/{action['params']['issue']}#issuecomment-7"
    with pytest.raises(RecordRefused):
        settle(runner, view.runId, action, payload)
    assert loadOutcomes(repo) == {}


@pytest.mark.parametrize("proof", [
    {"commentUrl": "ISSUE_URL"},
    {"commentId": 99},
    {"markerVerified": True},
])
def test_closed_outcome_is_accepted_with_any_one_proof(tmp_path, monkeypatch, proof) -> None:
    repo, store, runner = runnerFor(tmp_path)
    rows = closureRows(1)
    writeCensus(repo, makeCensus(rows))
    stubReconcile(monkeypatch, makeManifest(closureItems(rows)))
    view = runner.start("full")
    (action,) = closeActions(view)
    proof = {key: (f"https://github.com/gaia-research/gaia-skill-tree/issues/{action['params']['issue']}#issuecomment-99"
                   if value == "ISSUE_URL" else value) for key, value in proof.items()}
    payload = {"outcome": "closed", "issue": action["params"]["issue"], "key": action["params"]["key"], **proof}
    settle(runner, view.runId, action, payload)
    entry = loadOutcomes(repo)[f"{action['params']['key']}#{action['params']['issue']}"]
    assert entry["outcome"] == "closed"
    assert entry["commentId"] == proof.get("commentId")
    assert entry["markerVerified"] is (proof.get("markerVerified") is True)


def test_failed_and_stale_outcomes_are_retryable_and_bounded(tmp_path) -> None:
    root = tmp_path
    for attempt in range(3):
        assert writeOutcome(root, "key:x", 1, {"outcome": "failed", "failure": "403"}) == "recorded"
    assert loadOutcomes(root)["key:x#1"]["attempts"] == 3
    assert writeOutcome(root, "key:x", 1, {"outcome": "closed", "commentUrl": "u"}) == "recorded"
    assert writeOutcome(root, "key:x", 1, {"outcome": "failed", "failure": "late"}) == "repeat"
    assert writeOutcome(root, "key:x", 2, {"outcome": "closed", "commentUrl": "u"}) == "recorded"  # pair, not key


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


def operationsOf(view, kind: str) -> list[dict]:
    return [op for op in view.desk["operations"] if op["kind"] == kind]


def test_founder_question_reaches_the_desk_as_an_exact_decision_with_affected_issues(tmp_path, monkeypatch) -> None:
    repo, store, runner = runnerFor(tmp_path)
    rows = closureRows(2, start=200)
    writeCensus(repo, makeCensus(rows))
    items = closureItems(rows, start=200)
    for item in items:
        item.update(authority="C", ruleId=None, state="awaiting-founder")
    question = {"id": "Q-cafe0001", "question": "Accept the o/r family of candidates?", "affected": [200, 201],
                "options": ["accept", "reject", "defer"], "recommendation": None, "basis": "two candidates"}
    stubReconcile(monkeypatch, makeManifest(items, founderQuestions=[question]))
    view = runner.start("full")
    matching = [d for d in view.desk["decisions"] if "Accept the o/r family" in d["decision"]]
    assert len(matching) == 1
    assert "#200, #201" in matching[0]["decision"]
    assert len(matching[0]["debtIds"]) == 1


def test_backlog_line_reports_closures_and_the_change_since_the_previous_run(tmp_path, monkeypatch) -> None:
    repo, store, runner = runnerFor(tmp_path)
    rows = closureRows(2)
    writeCensus(repo, makeCensus(rows))
    stubReconcile(monkeypatch, makeManifest(closureItems(rows)))
    view = runner.start("full")
    for action in closeActions(view):
        settle(runner, view.runId, action, outcomeFor(action))
    view = runner.resume(view.runId)
    lines = operationsOf(view, "issue_backlog")
    assert len(lines) == 1
    assert "closed this run 2 of 2 total" in lines[0]["detail"]
    assert "no previous run recorded" in lines[0]["detail"]
    later = runner.start("full")
    detail = operationsOf(later, "issue_backlog")[0]["detail"]
    assert "net change +0 since the previous run" in detail
    assert "closed this run 0 of 2 total" in detail


def test_class_b_suite_review_dispatches_at_most_one_build_per_run(tmp_path, monkeypatch) -> None:
    repo, store, runner = runnerFor(tmp_path, agents=True)
    rows = [makeRow(300, "[intake] one"), makeRow(301, "[intake] two")]
    writeCensus(repo, makeCensus(rows))
    items = [
        makeItem(300, "upstream-candidate:o/r:one", "B", state="actionable"),
        makeItem(301, "upstream-candidate:x/y:two", "B", state="actionable"),
    ]
    batches = [
        {"suite": "o/r", "umbrella": 1835, "classB": ["upstream-candidate:o/r:one"], "size": 1},
        {"suite": "x/y", "umbrella": 2002, "classB": ["upstream-candidate:x/y:two"], "size": 1},
    ]
    stubReconcile(monkeypatch, makeManifest(items, batches=batches))
    view = runner.start("full")
    builds = [action for action in view.actions if action["type"] == "agent.build"]
    assert len(builds) == 1
    assert builds[0]["debtId"].startswith("debt:issue_suite_review:")
    assert closeActions(view) == []


def test_digest_and_desk_show_the_exact_question_with_its_affected_issues() -> None:
    from gaia_cli.steward.digest import ISSUE_FOUNDER_RULE, issueQuestion
    from gaia_cli.steward.models import FounderDecision

    decision = FounderDecision.create(
        rule=ISSUE_FOUNDER_RULE, decision_target="issue-question/q-1", objective="generic objective",
        debt_ids=("debt:issue_founder_decision:q-1:abc",),
        evidence=({"observedState": {"question": "Accept the family?", "affected": [5, 6]}},),
    )
    assert issueQuestion(decision) == "Accept the family? Affected issues: #5, #6."
    other = FounderDecision.create(
        rule="generic-mapping-decision", decision_target="generic-mapping/x", objective="map it",
        debt_ids=("debt:generic_mapping:x:abc",), evidence=({"observedState": {"question": "no"}},),
    )
    assert issueQuestion(other) is None
