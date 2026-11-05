"""Current settlement, not missing work: synthetic data/disposable remotes only."""
from pathlib import Path

import pytest

from gaia_cli.steward import archive as a
from gaia_cli.steward.controller import ScanResult
from gaia_cli.steward.fullrun import FullRunConfig, FullRunner
from gaia_cli.steward.ledger import FileLedgerStore, LedgerUnavailable, empty_ledger, update, validate_ledger
from gaia_cli.steward.models import AuthorityClass, Debt, Observation, Priority, Receipt, Subject
from tests.steward.test_archive import hosts, seed, run_record, refs, observation_phases, START, END


def open_summary(sensorCount=400):
    """Real canonical producer: undispatched C is NOT in the tracked work IDs."""
    observation = Observation(kind="synthetic", subject=Subject("synthetic", "pending-c"),
                              observed_at=START, source="synthetic", status="drift",
                              current_state={}, observed_state={})
    debt = Debt(id=observation.debt_id, kind=observation.kind, subject=observation.subject,
                source=observation.source, current_state={}, observed_state={}, confidence=1.0,
                priority=Priority(1, 1, 1, 1, 1, 1), authority=AuthorityClass.C, status="open",
                first_observed_at=START, last_observed_at=START, observation_count=1)
    observations = (observation,) + tuple(Observation(
        kind="synthetic", subject=Subject("synthetic", str(number)), observed_at=START,
        source=f"sensor-{number:06d}", status="healthy", current_state={}, observed_state={}
    ) for number in range(sensorCount))
    receipt = Receipt(run_id="scan-original", started_at=START, finished_at=END,
                      observations_collected=len(observations), coverage_unknown=(),
                      debt_created=(debt.id,), debt_updated=(), debt_resolved=(),
                      open_debt=(debt.id,), authority_counts={"A": 0, "B": 0, "C": 1},
                      result_status="no_change")
    scan = ScanResult(observations=observations, debts=(debt,), receipt=receipt,
                      debt_state_path=Path("unused-debts"), receipt_path=Path("unused-receipt"),
                      fresh_open_debt_ids=frozenset({debt.id}))
    runner = FullRunner(FullRunConfig(repo_root=Path("."), store=FileLedgerStore(Path("unused-ledger"))))
    return runner._observationSummary(scan, ()), debt.id


def settled(debt, authority="C", **fields):
    return {"debtId": debt, "authority": authority, "state": "resolved", "runId": "other",
            "history": [{"from": "escalated", "to": "resolved", "at": END,
                         "reason": "synthetic authoritative re-observation"}], **fields}


def historical_record(summary):
    return run_record(mode="observe", desk={}, phases={"observe": summary})


def test_real_producer_missing_c_work_is_not_settlement():
    summary, debt = open_summary()
    assert summary["debtStatus"] == {}
    assert summary["openDebt"] == summary["authorityCounts"]["C"] == 1
    assert summary["openDebtIds"] == summary["freshOpenDebt"] == [debt]
    run = historical_record(summary)
    document = empty_ledger()
    document["runs"]["run-a"] = run
    assert validate_ledger(document) is document
    assert a.phase_hold(run["phases"]) is None
    assert not a.eligible(document, run)


def test_missing_c_reference_actual_migration_keeps_document_and_version(hosts, monkeypatch):
    remote, one, two = hosts
    summary, debt = open_summary()
    before = seed(one, {"run-a": historical_record(summary)})
    branches = refs(remote)

    def noCas(*args, **kwargs):
        pytest.fail("missing settlement must hold before canonical CAS")

    monkeypatch.setattr(one, "compare_and_swap", noCas)
    assert a.plan(one)["eligible"] == []
    assert a.migrate(one)["archived"] == []
    assert two.load() == before
    assert refs(remote) == branches
    assert a.show(two, "run-a")["run"] == before[0]["runs"]["run-a"]
    assert debt not in before[0]["work"]


@pytest.mark.parametrize("state", ["resolved", "escalated", "blocked", "queued", "verified", "landed", "no_change"])
def test_current_authoritative_settlement_not_historical_b_status(state):
    summary, debt = open_summary(1)
    summary["debtStatus"] = {"settled-b": "resolved"}
    summary["resolved"] = ["settled-b"]
    run = historical_record(summary)
    document = empty_ledger()
    document["work"]["settled-b"] = settled("settled-b", "B")
    assert not a.eligible(document, run)  # deleting C work cannot improve eligibility
    document["work"][debt] = settled(debt, state=state)
    assert a.eligible(document, run) is (state == "resolved")


@pytest.mark.parametrize("fields", [{"authority": None}, {"authority": ""}, {"authority": "D"},
                                     {"authority": {"class": "C"}}, {"debtId": "wrong"},
                                     {"state": "completed"}, {"history": "resolved"}])
def test_malformed_current_work_cannot_authorize(fields):
    summary, debt = open_summary(1)
    document = empty_ledger()
    document["work"][debt] = settled(debt, **fields)
    assert not a.eligible(document, historical_record(summary))


def test_missing_authority_and_deleted_work_cannot_authorize():
    summary, debt = open_summary(1)
    document = empty_ledger()
    document["work"][debt] = settled(debt)
    assert a.eligible(document, historical_record(summary))
    del document["work"][debt]["authority"]
    assert not a.eligible(document, historical_record(summary))
    del document["work"][debt]
    assert not a.eligible(document, historical_record(summary))


@pytest.mark.parametrize("summary", [
    {"openDebt": 1}, {"authorityCounts": {"C": 1}},
    {"openDebt": 2, "openDebtIds": ["c"]},
    {"openDebt": 1, "openDebtIds": ["c", "c"]},
    {"openDebtIds": ["c"], "freshOpenDebt": ["another"]},
    {"openDebtIds": [], "authorityCounts": {"A": 0, "B": 0, "C": 1}},
    {"openDebtIds": ["c"], "authorityCounts": {"A": 0, "B": 0, "C": 0}},
    {"debtStatus": {"c": "resolved"}}, {"resolved": ["c"]},
])
def test_unidentified_or_historically_resolved_debts_are_not_current_settlement(summary):
    document = empty_ledger()
    assert not a.eligible(document, historical_record(summary))


@pytest.mark.parametrize("phase,field", [
    ("observe", "openDebtIds"), ("observe", "freshOpenDebt"), ("observe", "resolved"),
    ("reobserve", "resolvedWork"), ("triage", "classA"), ("triage", "classB"),
    ("triage", "reportOnly"), ("triage", "issueClosure"), ("triage", "held"),
    ("triage", "skippedActive"), ("triage", "carried"), ("triage", "filtered"),
    ("verify", "expired"),
])
def test_all_supported_phase_debt_roles_need_current_work(phase, field):
    document = empty_ledger()
    run = run_record(desk={}, phases={phase: {field: ["c"]}})
    assert a.phase_hold(run["phases"]) is None
    assert not a.eligible(document, run)
    authority = "A" if field in ("classA", "issueClosure") else "B" if field in ("classB", "reportOnly") else "C"
    document["work"]["c"] = settled("c", authority)
    assert a.eligible(document, run)


@pytest.mark.parametrize("role", ["actions", "steps", "decisions", "desk", "proofArtifacts", "receipts", "branches", "pullRequests", "agentAssignments", "ciResults"])
def test_record_debt_references_need_current_work_without_confusing_other_ids(role):
    document = empty_ledger()
    run = run_record(desk={}, phases=observation_phases(1))
    record = {"debtId": "c", "status": "done"}
    if role == "decisions":
        record["status"] = "resolved"
    run[role] = {"decisions": [{"decisionId": "not-a-debt", "debtIds": ["c"]}]} if role == "desk" else [record]
    assert not a.eligible(document, run)
    document["work"]["c"] = settled("c")
    assert a.eligible(document, run)
    assert "scan-original" not in document["work"]  # receipt/sensor identities need no fake work


@pytest.mark.parametrize("kind", ["exhausted_attempts", "failed_dispatch", "coverage_unknown", "not_evaluated", "stale_schedule", "ledger_local_only"])
def test_desk_operation_subjects_have_typed_debt_or_nondebt_roles(kind):
    document = empty_ledger()
    run = run_record(phases=observation_phases(1), desk={"operations": [
        {"kind": kind, "subject": "synthetic-subject", "detail": "synthetic original"},
    ]})
    debtRole = kind in ("exhausted_attempts", "failed_dispatch")
    assert a.eligible(document, run) is not debtRole
    if debtRole:
        document["work"]["synthetic-subject"] = settled("synthetic-subject", "B")
        assert a.eligible(document, run)


@pytest.mark.parametrize("phase", [
    {"triage": {"counts": {"C": 1}}},
    {"triage": {"counts": {"B": 1}, "classB": []}},
    {"triage": {"carried": 1}}, {"triage": {"filtered": 1}},
])
def test_unidentified_triage_counts_hold(phase):
    assert not a.eligible(empty_ledger(), run_record(desk={}, phases=phase))


def test_selected_debt_option_needs_current_settlement_but_other_ids_do_not():
    document = empty_ledger()
    run = run_record(desk={}, phases=observation_phases(1), options={"debt": None, "routine": 18})
    assert a.eligible(document, run)
    run["options"]["debt"] = "selected"
    assert not a.eligible(document, run)
    document["work"]["selected"] = settled("selected", "B")
    assert a.eligible(document, run)


@pytest.mark.parametrize("summary", [
    {"openDebtIds": [], "debtStatus": {"c": "open"}},
    {"openDebtIds": ["c"], "debtStatus": {"c": "resolved"}},
    {"openDebtIds": ["c"], "resolved": ["c"]},
    {"openDebtIds": ["c"], "authorityCounts": {"A": 0, "B": 1, "C": 0}},
])
def test_inconsistent_observations_hold_even_with_resolved_work(summary):
    document = empty_ledger()
    document["work"]["c"] = settled("c")
    assert not a.eligible(document, historical_record(summary))


def test_open_reference_cas_retry_holds_newest_valid_document(hosts):
    _, one, two = hosts
    original, _ = seed(one, {"run-a": run_record(desk={}, phases=observation_phases(400))})
    summary, debt = open_summary()
    newest = None
    attempts = 0

    def race(stage):
        nonlocal newest, attempts
        if stage == "before-cas":
            attempts += 1
            assert attempts == 1
            update(two, lambda doc: doc["runs"]["run-a"]["phases"].update(observe=summary))
            newest = two.load()
            assert validate_ledger(newest[0]) is newest[0]

    assert a.migrate(one, checkpoint=race)["archived"] == []
    assert attempts == 1
    assert one.load() == two.load() == newest
    hot = newest[0]
    assert hot["runs"]["run-a"]["phases"] == {"observe": summary}
    assert a.POINTER not in hot["runs"]["run-a"]
    assert debt not in hot["work"]
    for key in ("work", "leases", "lane", "operations"):
        assert hot[key] == original[key]
    for key in ("proofArtifacts", "receipts", "actions", "steps"):
        assert hot["runs"]["run-a"][key] == original["runs"]["run-a"][key]
    assert a.history(two)["entries"] == []


def test_complete_current_observe_producer_is_independently_held(tmp_path):
    from tests.steward.test_fullrun import makeFixture, makeRunner, StubSensor

    repo, _ = makeFixture(tmp_path)
    store = FileLedgerStore(repo / ".gaia/synthetic-ledger.json")
    runner = makeRunner(repo, store, [StubSensor("synthetic", "generic_mapping", ["pending-c"])])
    view = runner.start(mode="observe")
    document, _ = store.load()
    run = document["runs"][view.runId]
    assert run["status"] == "completed"
    assert run["phases"]["observe"]["authorityCounts"]["C"] == 1
    assert run["phases"]["observe"]["debtStatus"] == {}
    assert document["work"] == {}
    assert run["phases"]["reconcile"]["integrationBranch"]
    assert a.phase_hold(run["phases"]) is not None
    assert not a.eligible(document, run)


def test_original_reference_only_desk_and_resolved_fixture_stay_hot(hosts):
    from tests.steward.test_archive_contracts import canonical_phases

    remote, one, two = hosts
    seed(one)
    update(one, lambda doc: doc["work"].pop("debt-c"))
    before = one.load()
    branches = refs(remote)
    assert a.plan(one)["eligible"] == []
    assert a.migrate(one)["archived"] == []
    assert two.load() == before
    assert refs(remote) == branches
    update(one, lambda doc: doc["runs"]["run-a"].update(desk={}, phases=canonical_phases()))
    before = one.load()
    branches = refs(remote)
    assert "settled" not in before[0]["work"]
    assert a.migrate(one)["archived"] == []
    assert two.load() == before
    assert refs(remote) == branches


@pytest.mark.parametrize("change", ["delete", "escalate", "authority"])
def test_transition_refuses_projection_with_removed_current_settlement(hosts, monkeypatch, change):
    remote, one, two = hosts
    summary, debt = open_summary()
    seed(one, {"run-a": historical_record(summary)})
    update(one, lambda doc: doc["work"].update({debt: settled(debt)}))
    before = one.load()
    cas = one.compare_and_swap

    def invalidProjection(expected, candidate, message):
        if change == "delete":
            del candidate["work"][debt]
        elif change == "escalate":
            candidate["work"][debt]["state"] = "escalated"
        else:
            candidate["work"][debt].pop("authority")
        assert validate_ledger(candidate) is candidate
        return cas(expected, candidate, message)

    monkeypatch.setattr(one, "compare_and_swap", invalidProjection)
    with pytest.raises(LedgerUnavailable, match="not an eligible lossless transfer"):
        a.migrate(one)
    assert two.load() == before
    assert a.history(two)["entries"] == []


def test_explicit_current_settlement_roundtrip_keeps_hot_records(hosts):
    _, one, two = hosts
    summary, debt = open_summary()
    seed(one, {"run-a": historical_record(summary)})
    update(one, lambda doc: doc["work"].update({debt: settled(debt)}))
    before, _ = one.load()
    assert a.migrate(one)["archived"] == ["run-a"]
    after, _ = two.load()
    assert a.show(two, "run-a")["run"] == before["runs"]["run-a"]
    for key in ("work", "leases", "lane"):
        assert after[key] == before[key]
    for key, value in before["runs"]["run-a"].items():
        if key != "phases":
            assert after["runs"]["run-a"][key] == value
    assert debt in after["runs"]["run-a"][a.POINTER]["references"]["debtIds"]
