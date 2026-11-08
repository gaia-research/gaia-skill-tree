"""Integrity and operational boundary proofs; disposable shared Git only."""
from __future__ import annotations

import pytest

from gaia_cli.steward import archive as a
from gaia_cli.steward import ledger as l
from gaia_cli.steward.fullrun import FullRunError
from tests.steward.test_archive import hosts, seed, run_record, refs, git, START, END, observation_phases
from tests.steward.test_archive_readers import reader


@pytest.mark.parametrize("mutation", ["memory", "pointer", "run", "head", "counter", "schema"])
def test_ordinary_writes_cannot_discard_or_rewrite_archival_history(hosts, mutation):
    _, one, two = hosts
    seed(one)
    a.migrate(one)
    before = two.load()
    def damage(d):
        if mutation == "memory":
            del d["operations"][a.MEMORY]
        elif mutation == "pointer":
            del d["runs"]["run-a"][a.POINTER]
        elif mutation == "run":
            del d["runs"]["run-a"]
        elif mutation == "head":
            d["operations"][a.MEMORY]["head"] = None
        elif mutation == "counter":
            d["operations"][a.MEMORY]["events"] += 1
        else:
            d["schemaVersion"] = l.LEDGER_SCHEMA
            d["operations"].pop(a.MEMORY)
            d["runs"]["run-a"].pop(a.POINTER)
    with pytest.raises(l.LedgerUnavailable):
        l.update(two, damage)
    assert one.load() == before
    assert a.show(one, "run-a")["run"]["status"] == "completed"


def test_unrelated_v2_writes_need_no_archive_reads_and_preserve_leases(hosts, monkeypatch):
    _, one, two = hosts
    seed(one)
    a.migrate(one)
    before = one.load()[0]
    def no_network(*args):
        raise AssertionError("unchanged archive metadata must not cause hydration")
    monkeypatch.setattr(a.GitArchive, "read", no_network)
    def mutate(d):
        assert l.acquire_lease(d, "other-run", "other", START, 100)
        d["operations"]["replay"] = {"idempotencyKey": "still-hot", "status": "pending"}
    l.update(two, mutate)
    after = one.load()[0]
    assert after["runs"] == before["runs"]
    assert after["operations"][a.MEMORY] == before["operations"][a.MEMORY]
    assert after["leases"]["other-run"]["holder"] == "other"


def test_references_to_work_adopted_by_another_run_are_not_terminal(hosts):
    remote, one, _ = hosts
    seed(one)
    l.update(one, lambda d: d["work"].update({"debt-c": {
        "debtId": "debt-c", "runId": "successor", "state": "escalated", "history": []}}))
    before, branches = one.load(), refs(remote)
    assert a.migrate(one)["archived"] == []
    assert one.load() == before
    assert refs(remote) == branches


def ambiguous_canonical_phases():
    # Retained exact old fixture: unconstrained reasons/detail now stay hot.
    # Actual FullRunner._observationSummary / triage / retro SHAPES, using only
    # synthetic identifiers. Routine 'state' is coverage, never a work verdict.
    return {
        "observe": {"scanReceiptId": "scan-synthetic", "observations": 1000,
                    "debtStatus": {"settled": "resolved"}, "openDebt": 0,
                    "openDebtIds": [], "freshOpenDebt": [], "created": 0,
                    "resolved": ["settled"], "authorityCounts": {},
                    "coverageUnknown": ["offline-sensor"],
                    "coverageUnknownReasons": {"offline-sensor": "unavailable"},
                    "notEvaluated": [{"sensor": "optional", "reason": "disabled"}],
                    "partialCoverage": [], "observationsBySensor": {"synthetic": {"drift": 0, "healthy": 1000}}},
        "triage": {"classA": [], "classB": [], "classC": [], "held": [],
                   "reportOnly": [], "skippedActive": [], "carried": [], "filtered": [], "counts": {}},
        "class_a": {"status": "ok", "landings": []},
        "class_b": {"status": "ok", "dispatched": None, "reason": "no eligible work"},
        "verify": {"status": "ok", "results": [], "deferred": [], "expired": []},
        "retro": {"routines": [{"routine": 18, "state": "observed", "detectors": ["sensor-synthetic"]}],
                  "registered": 18, "executed": 18, "sensors": ["sensor-synthetic"],
                  "unknown": ["offline-sensor"], "notEvaluated": [], "partiallyCovered": [],
                  "detail": "historical observation " * 3000},
    }


def canonical_phases():
    # Supported typed producer shapes, not sanitized copies of legacy payloads.
    phases = observation_phases(coverageUnknown=("offline-sensor",))
    phases["observe"].update(debtStatus={"settled": "resolved"}, resolved=["settled"])
    phases["retro"] = {
        "routines": [{"routine": 18, "state": "unknown", "detectors": [
            {"sensor": "offline-sensor", "state": "unknown"}]}],
        "sensors": [{"id": "offline-sensor", "registered": True, "state": "unknown",
                     "executed": False, "unknown": True, "notEvaluated": False,
                     "observations": {"drift": 0, "healthy": 0}, "routine_ids": [18]}],
        "registered": 1, "executed": 0, "unknown": ["offline-sensor"],
        "notEvaluated": [], "partiallyCovered": [],
    }
    return phases


def test_old_canonical_prose_fixture_stays_hot_without_normalizing_coverage(hosts):
    remote, one, two = hosts
    phases = ambiguous_canonical_phases()
    before = seed(one, {"run-a": run_record(phases=phases)})
    branches = refs(remote)
    baseline = reader(one)._view(before[0], "run-a").to_dict()
    assert a.phase_hold(phases) is not None
    assert a.migrate(one)["archived"] == []
    assert two.load() == before
    assert refs(remote) == branches
    assert reader(two)._view(two.load()[0], "run-a").to_dict() == baseline


def test_canonical_shapes_search_and_ordinary_view_equivalence(hosts):
    _, one, two = hosts
    phases = canonical_phases()
    record = run_record(phases=phases, desk={}, proofArtifacts=[], receipts=[{"kind": "scan", "id": "scan-synthetic"}])
    seed(one, {"run-a": record})
    # Historical 'resolved' alone was not settlement. This positive synthetic
    # transfer now supplies an explicit current authoritative work record.
    l.update(one, lambda doc: doc["work"].update({"settled": {
        "debtId": "settled", "authority": "B", "state": "resolved", "runId": "other",
        "history": [{"from": "escalated", "to": "resolved", "at": END, "reason": "synthetic settlement"}],
    }}))
    before, _ = one.load()
    baseline = reader(one)._view(before, "run-a").to_dict()
    assert a.migrate(one)["archived"] == ["run-a"]
    assert reader(two)._view(two.load()[0], "run-a").to_dict() == baseline
    found = a.history(two, run_id="run-a", debt_id="settled", routine="18", since=START, until=END)
    assert [r["runId"] for r in found["entries"]] == ["run-a"]
    assert a.references({"phases": {"retro": {"routines": 17}}})["routines"] == []
    assert a.references({"options": {"routine": 5}, "phases": {"retro": {"routines": [1, 18]}}})["routines"] == ["1", "18", "5"]


@pytest.mark.parametrize("stage", ["archive-push", "hot-cas"])
def test_lost_success_response_is_safe_to_retry_from_another_clone(hosts, monkeypatch, stage):
    remote, one, two = hosts
    original, _ = seed(one)
    if stage == "hot-cas":
        actual = one.compare_and_swap
        def ambiguous(*args):
            actual(*args)
            raise l.LedgerUnavailable("synthetic timeout after successful CAS")
        monkeypatch.setattr(one, "compare_and_swap", ambiguous)
    else:
        actual = l.GitRefLedgerStore.git
        raised = False
        def ambiguous(self, args, **kwargs):
            nonlocal raised
            result = actual(self, args, **kwargs)
            if args[0] == "push" and self.ref.startswith(a.PREFIX) and not raised:
                raised = True
                raise l.LedgerUnavailable("synthetic timeout after successful upload")
            return result
        monkeypatch.setattr(l.GitRefLedgerStore, "git", ambiguous)
    with pytest.raises(l.LedgerUnavailable, match="timeout"):
        a.migrate(one)
    result = a.migrate(two, run_ids=["run-a"])
    assert result["archived"] == ([] if stage == "hot-cas" else ["run-a"])
    assert a.show(two, "run-a")["run"] == original["runs"]["run-a"]
    assert len(a.history(two)["entries"]) == 1
    assert "steward/archive/v1/" in refs(remote)


def test_corrupt_colliding_publication_is_not_overwritten(hosts):
    remote, one, _ = hosts
    seed(one)
    a.migrate(one)
    archive = a.GitArchive(one)
    hot = one.load()
    segment = hot[0]["runs"]["run-a"][a.POINTER]["segment"]
    data = archive.read(segment)
    branch = f"refs/heads/{a.PREFIX}/run/{segment['sha256']}"
    blob = git(remote, "hash-object", "-w", "--stdin", data=b"{}\n")
    tree = git(remote, "mktree", data=f"100644 blob {blob}\tpayload\n".encode())
    commit = git(remote, "commit-tree", tree, "-m", "synthetic collision")
    git(remote, "update-ref", branch, commit)
    branches = refs(remote)
    with pytest.raises(l.LedgerUnavailable):
        archive.publish("run", data)
    assert refs(remote) == branches
    assert one.load() == hot


def test_missing_object_republication_restores_exact_cross_clone_read(hosts):
    remote, one, two = hosts
    original, _ = seed(one)
    a.migrate(one)
    hot = one.load()
    segment = hot[0]["runs"]["run-a"][a.POINTER]["segment"]
    verified = a.GitArchive(one).read(segment)
    git(remote, "update-ref", "-d", f"refs/heads/{a.PREFIX}/run/{segment['sha256']}")
    with pytest.raises(l.LedgerUnavailable, match="missing"):
        a.show(two, "run-a")
    assert a.GitArchive(one).publish("run", verified) == segment
    assert a.show(two, "run-a")["run"] == original["runs"]["run-a"]
    assert one.load() == hot


def test_index_growth_rolls_at_entry_bound_and_search_reads_one_page(hosts, monkeypatch):
    _, one, two = hosts
    # Exercise rollover with a reduced page bound, preserving the repository's
    # existing 60-second per-test safeguard on slower mobile Git transports.
    monkeypatch.setattr(a, "MAX_PAGE_ENTRIES", 2)
    seed(one, {f"r-{n:02}": run_record(f"r-{n:02}", phases=observation_phases(1)) for n in range(3)})
    assert len(a.migrate(one, max_runs=2)["archived"]) == 2
    assert a.plan(two, max_runs=2)["remainingEligible"] == 0
    assert a.migrate(two, max_runs=2)["archived"] == ["r-02"]
    hot = one.load()[0]
    assert a.memory(hot)["pages"] == 2
    assert a.memory(hot)["events"] == 3
    actual = a.GitArchive.read
    indexReads = []
    def tracked(self, ref):
        if ref["kind"] == "index":
            indexReads.append(ref)
        return actual(self, ref)
    monkeypatch.setattr(a.GitArchive, "read", tracked)
    first = a.history(one, pages=1)
    assert len(indexReads) == 1
    assert len(first["entries"]) == 1
    indexReads.clear()
    second = a.history(two, cursor=first["nextCursor"], pages=1)
    assert len(indexReads) == 1
    assert len(second["entries"]) == 2
    assert second["nextCursor"] is None
    assert all(ref["size"] <= a.MAX_INDEX_BYTES for ref in indexReads)


def test_concurrent_identical_publication_verifies_winner(hosts, monkeypatch):
    remote, one, two = hosts
    seed(one)
    a.migrate(one)
    pointer = one.load()[0]["runs"]["run-a"][a.POINTER]
    segment = pointer["segment"]
    archive = a.GitArchive(two)
    data = archive.read(segment)
    actual = l.GitRefLedgerStore.fetchRemote
    raced = False
    def stale(self):
        nonlocal raced
        if not raced and self.ref == f"{a.PREFIX}/run/{segment['sha256']}":
            raced = True
            return None  # a writer checked before the other writer published
        return actual(self)
    branches = refs(remote)
    monkeypatch.setattr(l.GitRefLedgerStore, "fetchRemote", stale)
    assert archive.publish("run", data) == segment
    assert raced
    assert refs(remote) == branches


@pytest.mark.parametrize("cursor", [{}, {"kind": "index", "size": 1, "sha256": "../main"},
                                    {"kind": "run", "size": 1, "sha256": "a" * 64}])
def test_unsafe_cursor_refused_before_transport(hosts, cursor):
    remote, one, _ = hosts
    before = refs(remote)
    with pytest.raises(l.LedgerUnavailable):
        a.history(one, cursor=cursor)
    assert refs(remote) == before


@pytest.mark.parametrize("protection", ["lease", "adopted-work"])
def test_cas_conflict_rechecks_lease_and_adopted_work(hosts, protection):
    _, one, two = hosts
    original, _ = seed(one)
    raced = False
    def checkpoint(stage):
        nonlocal raced
        if stage == "before-cas" and not raced:
            raced = True
            def protect(d):
                if protection == "lease":
                    l.acquire_lease(d, "current", "run-a", START, 600)
                else:
                    d["work"]["debt-c"] = {"debtId": "debt-c", "runId": "successor",
                                               "state": "blocked", "history": []}
            l.update(two, protect)
    assert a.migrate(one, checkpoint=checkpoint)["archived"] == []
    hot = two.load()[0]
    assert a.POINTER not in hot["runs"]["run-a"]
    assert hot["runs"]["run-a"]["phases"] == original["runs"]["run-a"]["phases"]
    assert not a.history(two)["entries"]
    if protection == "lease":
        assert hot["leases"]["current"]["holder"] == "run-a"
    else:
        assert hot["work"]["debt-c"]["state"] == "blocked"


def test_large_supported_phase_cas_retry_rechecks_new_ambiguous_text(hosts):
    _, one, two = hosts
    phases = observation_phases(16000, identityParts=12)
    assert len(a.packed(phases)) >= 2400309
    before, _ = seed(one, {"run-a": run_record(phases=phases)})
    raced = False

    def checkpoint(stage):
        nonlocal raced
        if stage == "before-cas" and not raced:
            raced = True
            l.update(two, lambda doc: doc["runs"]["run-a"]["phases"]["observe"].update(payload="proof"))

    assert a.migrate(one, checkpoint=checkpoint)["archived"] == []
    assert raced
    hot, _ = two.load()
    expected = {**phases["observe"], "payload": "proof"}
    assert hot["runs"]["run-a"]["phases"] == {"observe": expected}
    assert a.POINTER not in hot["runs"]["run-a"]
    for key in ("work", "leases", "lane"):
        assert hot[key] == before[key]
    assert a.history(two)["entries"] == []


def test_migration_size_telemetry_includes_generation_digit_growth(hosts):
    _, one, two = hosts
    seed(one)
    l.update(one, lambda d: d.update(generation=8))  # next committed generation = 9
    before, version = one.load()
    assert before["generation"] == 9
    result = a.migrate(one)
    hot, current = two.load()
    assert hot["generation"] == 10
    from tests.steward.test_archive import raw_source
    assert result["beforeBytes"] == len(raw_source(one, version))
    assert result["afterBytes"] == len(raw_source(two, current))


@pytest.mark.parametrize("control", ["explicit", "headroom", "ninety", "invalid"])
def test_growth_stop_prevents_new_run_before_any_work_or_lease(hosts, monkeypatch, control):
    _, one, _ = hosts
    seed(one)
    current, version = one.load()
    if control == "explicit":
        monkeypatch.setenv("GAIA_STEWARD_FULL_STOP_NEW_RUNS", "1")
    elif control == "headroom":
        monkeypatch.setenv("GAIA_STEWARD_FULL_MIN_HEADROOM_BYTES", str(l.ledgerByteLimit()))
    elif control == "invalid":
        monkeypatch.setenv("GAIA_STEWARD_FULL_STOP_NEW_RUNS", "perhaps")
    else:
        monkeypatch.setenv("GAIA_STEWARD_LEDGER_MAX_BYTES", str(int(len(l.serialize(current)) / .92)))
    runner = reader(one)
    with pytest.raises(FullRunError):
        runner.start("full")
    assert one.load() == (current, version)
    # The stop applies only to NEW growth, not ordinary reads/replay.
    assert runner._view(current, "run-a").status == "completed"
