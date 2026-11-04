"""Lane B continuation: protocol, artifact and finite-capacity regression proofs.

All shared operations here target disposable bare Git remotes, never production.
"""
from __future__ import annotations

import copy
import json

import pytest

from gaia_cli.steward import archive as a
from gaia_cli.steward import ledger as l
from tests.steward.test_archive import hosts, seed, run_record, refs, raw_source, START, END


def legacy_read(data):
    """Frozen legacy read boundary: 1 MiB then exact steward-ledger-v1.

    This is the old refusal contract, not an emulation of legacy compaction.
    A refusal happens before its lossy >25-terminal-run compactor can execute.
    """
    if len(data) > 1024 * 1024:
        raise l.LedgerUnavailable("legacy byte bound")
    document = json.loads(data)
    if document.get("schemaVersion") != "steward-ledger-v1":
        raise l.LedgerUnavailable("legacy schemaVersion refusal")
    return document


def test_upgrade_refuses_old_reader_even_below_one_mib_and_rollback_stays_upgraded(hosts):
    _, one, two = hosts
    before, version = seed(one)
    assert legacy_read(raw_source(one, version)) == before
    a.migrate(one)
    after, migrated = two.load()
    raw = raw_source(two, migrated)
    assert len(raw) < 1024 * 1024
    assert after["schemaVersion"] == l.ARCHIVE_LEDGER_SCHEMA
    with pytest.raises(l.LedgerUnavailable, match="schemaVersion"):
        legacy_read(raw)
    # New ordinary operations continue preserving pointers and hot metadata.
    l.update(two, lambda d: d["operations"].update({"new-work": {"status": "pending"}}))
    a.rollback(one, "run-a")
    restored, restored_version = two.load()
    assert restored["runs"] == before["runs"]
    assert restored["schemaVersion"] == l.ARCHIVE_LEDGER_SCHEMA
    assert restored["operations"]["new-work"] == {"status": "pending"}
    with pytest.raises(l.LedgerUnavailable, match="schemaVersion"):
        legacy_read(raw_source(two, restored_version))


def test_legacy_limit_refuses_large_v1_without_touching_shared_state(hosts, monkeypatch):
    _, one, two = hosts
    original, version = seed(one, {"run-a": run_record(phases={"observe": {"payload": "x" * 1100000}})})
    with pytest.raises(l.LedgerUnavailable, match="legacy byte bound"):
        legacy_read(raw_source(one, version))
    monkeypatch.setenv("GAIA_STEWARD_LEDGER_MAX_BYTES", str(1024 * 1024))
    with pytest.raises(l.LedgerUnavailable, match="bound"):
        two.load()
    monkeypatch.delenv("GAIA_STEWARD_LEDGER_MAX_BYTES")
    assert two.load() == (original, version)
    assert a.migrate(one)["archived"] == ["run-a"]
    hot, version = two.load()
    assert len(raw_source(two, version)) < 1024 * 1024
    assert a.show(two, "run-a")["run"] == original["runs"]["run-a"]


def test_schema_downgrade_with_archive_metadata_is_refused(hosts):
    _, one, _ = hosts
    seed(one)
    a.migrate(one)
    before = one.load()
    downgraded = copy.deepcopy(before[0])
    downgraded["schemaVersion"] = l.LEDGER_SCHEMA
    with pytest.raises(l.LedgerUnavailable, match="archive-aware"):
        one.compare_and_swap(before[1], downgraded, "must refuse")
    assert one.load() == before


@pytest.mark.parametrize("phase", [
    {"proofPath": ".gaia/steward/proof.json"},
    {"receipt": {"file": "receipts/local.json"}},
    {"artifact": {"sha256": "a" * 64}},  # a hash is not the referenced bytes
    {"message": "See .gaia/steward/proof.json"},
    {"message": "https://example.invalid/receipt"},
    {"message": "file:///tmp/proof"},
    {"message": "../proof"},
    {"message": "C:\\proof\\result"},
    {"status": "active"}, {"status": "queued"}, {"status": "blocked"},
    {"state": "escalated"}, {"state": "decision-pending"}, {"state": {"unknown": 1}},
    {"decisions": [{"decisionId": "c", "status": "pending"}]},
    {"classC": ["c"]}, {"debtStatus": {"d": "open"}},
])
def test_protected_phase_payloads_remain_entirely_hot(hosts, phase):
    remote, one, _ = hosts
    record = run_record()
    record["phases"]["protected"] = phase
    before = seed(one, {"run-a": record})
    branches = refs(remote)
    plan = a.plan(one)
    assert plan["eligible"] == []
    assert plan["phaseHolds"]["run-a"]
    assert a.migrate(one)["archived"] == []
    assert one.load() == before
    assert refs(remote) == branches


def test_hot_artifact_references_are_preserved_without_reading_or_claiming_portability(hosts):
    _, one, two = hosts
    record = run_record(proofArtifacts=[{"proofPath": "/does/not/exist/proof.json", "sha256": "b" * 64}],
                        receipts=[{"path": ".gaia/steward/local-receipt.json"}])
    before, _ = seed(one, {"run-a": record})
    assert a.migrate(one)["archived"] == ["run-a"]
    hot, _ = two.load()
    assert hot["runs"]["run-a"]["proofArtifacts"] == record["proofArtifacts"]
    assert hot["runs"]["run-a"]["receipts"] == record["receipts"]
    shown = a.show(two, "run-a")
    assert shown["run"] == before["runs"]["run-a"]
    assert "not bundled" in shown["retrievalGuarantee"]


def test_rollback_forward_cas_retries_and_preserves_concurrent_work(hosts, monkeypatch):
    _, one, two = hosts
    before, _ = seed(one)
    a.migrate(one)
    actual = one.compare_and_swap
    raced = False
    def racing(expected, document, message):
        nonlocal raced
        if not raced:
            raced = True
            l.update(two, lambda d: d["work"].update({"later": {
                "debtId": "later", "state": "queued", "history": []}}))
        return actual(expected, document, message)
    monkeypatch.setattr(one, "compare_and_swap", racing)
    assert a.rollback(one, "run-a")["restored"] == ["run-a"]
    restored, _ = two.load()
    assert restored["runs"] == before["runs"]
    assert restored["work"]["later"]["state"] == "queued"
    assert [r["event"] for r in a.history(two, pages=2)["entries"]] == ["rollback", "archive"]


def test_capacity_measures_parent_delta_contributors_and_read_only_stop_model(hosts, monkeypatch):
    remote, one, _ = hosts
    first, version = seed(one)
    l.update(one, lambda d: d["operations"].update({"growth-baseline": True}),
             clock=lambda: l.parseTime(START))
    initial, initial_version = one.load()
    def grow(d):
        d["updatedAt"] = END
        d["operations"]["growth"] = {"payload": "g" * 10000}
    l.update(one, grow, clock=lambda: l.parseTime(END))
    current, current_version = one.load()
    branches = refs(remote)
    report = a.plan(one)["capacity"]
    actual = len(raw_source(one, current_version))
    delta = actual - len(raw_source(one, initial_version))
    assert report["bytes"] == actual
    assert report["growth"]["previousVersion"] == initial_version
    assert report["growth"]["deltaBytes"] == delta
    assert report["growth"]["bytesPerGeneration"] == delta
    assert report["growth"]["bytesPerSecond"] == delta / 86400
    assert report["largestSections"][0]["section"] == "runs"
    assert report["largestRuns"][0]["runId"] == "run-a"
    assert report["headroomBytes"] == l.ledgerByteLimit() - actual
    for percent, expected in ((.72, "plan-archive"), (.92, "stop-new-runs")):
        # Use ample synthetic metadata so the explicit reserve does not trigger
        # before the percent threshold under test.
        large = copy.deepcopy(current)
        large["operations"]["baseline"] = "z" * 2000000
        report_size = len(l.serialize(large))
        monkeypatch.setenv("GAIA_STEWARD_LEDGER_MAX_BYTES", str(int(report_size / percent)))
        report = a.capacity(one, large, None)
        assert report["alert"] == expected
        assert report["operatorStopNewRuns"] == (expected == "stop-new-runs")
    assert refs(remote) == branches


def test_metadata_still_grows_after_archival_and_hard_capacity_is_not_hidden(hosts, monkeypatch):
    _, one, _ = hosts
    seed(one)
    a.migrate(one)
    before = a.plan(one)["capacity"]
    # New run IDs, steps and tombstones are NOT expired, even above 25 runs.
    def add_metadata(d):
        for n in range(26):
            d["runs"][f"historic-{n}"] = run_record(f"historic-{n}", phases={},
                                                  actions=[{"status": "done", "idempotencyKey": f"never-repeat-{n}", "outcome": "h" * 5000}])
    l.update(one, add_metadata)
    hot, version = one.load()
    after = a.plan(one)["capacity"]
    assert after["bytes"] > before["bytes"]
    assert len(after["largestRuns"]) == 10
    assert hot["runs"]["historic-0"]["actions"][0]["idempotencyKey"] == "never-repeat-0"
    assert after["growth"]["deltaBytes"] > 100000
    monkeypatch.setenv("GAIA_STEWARD_LEDGER_MAX_BYTES", str(after["bytes"] + 1024))
    assert a.plan(one)["capacity"]["operatorStopNewRuns"] is True
    with pytest.raises(l.LedgerUnavailable, match="bound"):
        l.update(one, lambda d: d["operations"].update({"too-large": "x" * 5000}))
    assert one.load() == (hot, version)
